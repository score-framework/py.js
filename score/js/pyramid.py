# Copyright © 2015 STRG.AT GmbH, Vienna, Austria
#
# This file is part of the The SCORE Framework.
#
# The SCORE Framework and all its parts are free software: you can redistribute
# them and/or modify them under the terms of the GNU Lesser General Public
# License version 3 as published by the Free Software Foundation which is in the
# file named COPYING.LESSER.txt.
#
# The SCORE Framework and all its parts are distributed without any WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. For more details see the GNU Lesser General Public
# License.
#
# If you have not received a copy of the GNU Lesser General Public License see
# http://www.gnu.org/licenses/.
#
# The License-Agreement realised between you as Licensee and STRG.AT GmbH as
# Licenser including the issue of its valid conclusion and its pre- and
# post-contractual effects is governed by the laws of Austria. Any disputes
# concerning this License-Agreement including the issue of its valid conclusion
# and its pre- and post-contractual effects are exclusively decided by the
# competent court, in whose district STRG.AT GmbH has its registered seat, at
# the discretion of STRG.AT GmbH also the competent court, in whose district the
# Licensee has his registered seat, an establishment or assets.

"""
This package :ref:`integrates <framework_integration>` the module with
pyramid.
"""


import os
from pyramid.request import Request
from score.js import ConfiguredJsModule
from score.init import parse_bool


def init(confdict, configurator, webassets_conf, tpl_conf, html_conf=None):
    """
    Apart from calling the :func:`basic initializer <score.js.init>`, this
    function interprets the following *confdict* keys:

    :confkey:`combine` :faint:`[default=False]`
        Whether javascript files should be delivered as a single file. If this
        value is `true` (as defined by :func:`score.init.parse_bool`), the
        default url will point to the combined javascript file.

    :confkey:`dummy_request` :faint:`[default=None]`
        An optional request object to use for creating urls. Will fall back to
        the request object of the :func:`webassets configuration
        <score.webassets.pyramid.init>`.
    """
    import score.js
    jsconf = score.js.init(confdict, webassets_conf, tpl_conf)
    try:
        combine = parse_bool(confdict['combine'])
    except KeyError:
        combine = False
    try:
        assert isinstance(confdict['dummy_request'], Request)
        dummy_request = confdict['dummy_request']
        webassets_conf.dummy_request.registry = configurator.registry
    except KeyError:
        dummy_request = webassets_conf.dummy_request
    return ConfiguredJsPyramidModule(configurator, webassets_conf, tpl_conf,
                                     jsconf, combine, dummy_request)


class ConfiguredJsPyramidModule(ConfiguredJsModule):
    """
    Pyramid-specific configuration of this module.
    """

    def __init__(self, configurator, webconf, tplconf,
                 jsconf, combine, dummy_request):
        self.webconf = webconf
        self.tplconf = tplconf
        self.jsconf = jsconf
        self.combine = combine
        self.dummy_request = dummy_request
        if 'html' in tplconf.renderer.formats:
            tplconf.renderer.add_function('html', 'js',
                                          self.tags, escape_output=False)
        configurator.add_route('score.js:single', '/js/{path:.*\.js$}')
        configurator.add_route('score.js:combined', '/combined.js')
        configurator.add_view(self.js_single, route_name='score.js:single')
        configurator.add_view(self.js_combined, route_name='score.js:combined')

    def __getattr__(self, attr):
        return getattr(self.jsconf, attr)

    def response(self, request, js=None):
        """
        Returns a pyramid response object with the optional *js* string as its
        body. Will only set the headers, if *js* is `None`.
        """
        request.response.content_type = 'application/javascript; charset=UTF-8'
        if js:
            request.response.text = js
        return request.response

    def path2urlpath(self, path):
        """
        Converts a :term:`path <asset path>` to the corresponding path to use
        in URLs.
        """
        urlpath = path
        if not urlpath.endswith('.js'):
            urlpath = urlpath[:urlpath.rindex('.')]
        assert urlpath.endswith('.js')
        return urlpath

    def urlpath2path(self, urlpath):
        """
        Converts a *urlpath*, as passed in via the URL, into the actual
        :term:`asset path`.
        """
        assert urlpath.endswith('.js')
        jspath = urlpath
        if jspath in self.virtfiles.paths():
            return jspath
        if os.path.isfile(os.path.join(self.rootdir, jspath)):
            return jspath
        for ext in self.tplconf.renderer.engines:
            file = os.path.join(self.rootdir, jspath + '.' + ext)
            if os.path.isfile(file):
                return jspath + '.' + ext
        raise ValueError('Could not determine path for url "%s"' % urlpath)

    def js_single(self, request):
        """
        Pyramid :term:`route <pyramid:route configuration>` that generates the
        response for a single javascript asset.
        """
        urlpath = request.matchdict['path']
        versionmanager = self.webconf.versionmanager
        if versionmanager.handle_pyramid_request('js', urlpath, request):
            return self.response(request)
        path = self.urlpath2path(urlpath)
        if path in self.virtfiles.paths():
            js = self.virtfiles.render(path)
        else:
            js = self.tplconf.renderer.render_file(path)
        return self.response(request, js)

    def js_combined(self, request):
        """
        Pyramid :term:`route <pyramid:route configuration>` that generets the
        response for the combined javascript file.
        """
        versionmanager = self.webconf.versionmanager
        if versionmanager.handle_pyramid_request('js', '__combined__', request):
            return self.response(request)
        return self.response(request, self.render_combined())

    def render_combined(self):
        """
        Renders the combined js file.
        """
        parts = []
        for path in self.paths():
            if not self.minify:
                s = '/*{0}*/\n/*{1:^76}*/\n/*{0}*/'.format('*' * 76, path)
                parts.append(s)
            parts.append(self.tplconf.renderer.render_file(path))
        return '\n\n'.join(parts)

    def url_single(self, path):
        """
        Generates the url to a single javascript *path*.
        """
        urlpath = self.path2urlpath(path)
        versionmanager = self.webconf.versionmanager
        if path in self.virtfiles.paths():
            def hasher():
                return self.virtfiles.hash(path)
            def renderer():
                return self.virtfiles.render(path).encode('UTF-8')
        else:
            file = os.path.join(self.rootdir, path)
            hasher = versionmanager.create_file_hasher(file)
            def renderer():
                return self.tplconf.renderer.render_file(path).encode('UTF-8')
        hash_ = versionmanager.store('js', urlpath, hasher, renderer)
        _query = {'_v': hash_} if hash_ else None
        genurl = self.dummy_request.route_url
        return genurl('score.js:single', path=urlpath, _query=_query)

    def url_combined(self):
        """
        Generates the url to the combined javascript file.
        """
        files = []
        vfiles = []
        for path in self.paths():
            if path in self.virtfiles.paths():
                vfiles.append(path)
            else:
                files.append(os.path.join(self.rootdir, path))
        versionmanager = self.webconf.versionmanager
        hashers = [versionmanager.create_file_hasher(files)]
        for path in vfiles:
            hashers.append(lambda: self.virtfiles.hash(path))
        hash_ = versionmanager.store(
            'js', '__combined__', hashers,
            lambda: self.render_combined().encode('UTF-8'))
        _query = {'_v': hash_} if hash_ else None
        genurl = self.dummy_request.route_url
        return genurl('score.js:combined', _query=_query)

    def tags(self, *paths):
        """
        Generates all ``script`` tags necessary to include all javascript
        files. It is possible to generate the tags to specific js *paths*
        only.
        """
        tag = '<script src="%s"></script>'
        if len(paths):
            links = [tag % self.url_single(path) for path in paths]
            return '\n'.join(links)
        if self.combine:
            return tag % self.url_combined()
        if not len(self.paths()):
            return ''
        return self.tags(*self.paths())
