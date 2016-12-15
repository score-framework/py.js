# Copyright © 2015,2016 STRG.AT GmbH, Vienna, Austria
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

from functools import reduce
import os
from score.init import (
    init_cache_folder, ConfiguredModule, init_object, parse_bool)
from score.webassets import VirtualAssets, AssetNotFound
from score.tpl import TemplateConverter
import logging
import urllib

log = logging.getLogger('score.js')


defaults = {
    'rootdir': None,
    'cachedir': None,
    'minifier': None,
    'combine': False,
}


def init(confdict, webassets, http, tpl, html=None):
    """
    Initializes this module acoording to :ref:`our module initialization
    guidelines <module_initialization>` with the following configuration keys:

    :confkey:`rootdir` :confdefault:`None`
        Denotes the root folder containing all javascript files. Will fall
        back to a sub-folder of the folder in :mod:`score.tpl`'s
        configuration, as described in :func:`score.tpl.init`.

    :confkey:`cachedir` :confdefault:`None`
        A dedicated cache folder for this module. It is generally sufficient
        to provide a ``cachedir`` for :mod:`score.tpl`, as this module will
        use a sub-folder of that by default.

    :confkey:`minifier` :confdefault:`None`
        The minifier to use for minification. Will be initialized using
        :func:`score.init.init_object`. See :mod:`score.tpl.minifier` for
        available minifiers.

    :confkey:`combine` :confdefault:`False`
        Whether javascript files should be delivered as a single file. If this
        value is `true` (as defined by :func:`score.init.parse_bool`), the
        default url will point to the combined javascript file.
    """
    conf = dict(defaults.items())
    conf.update(confdict)
    if conf['minifier']:
        conf['minifier'] = init_object(conf, 'minifier')
    if not conf['cachedir'] and webassets.cachedir:
        conf['cachedir'] = os.path.join(webassets.cachedir, 'js')
    if conf['cachedir']:
        init_cache_folder(conf, 'cachedir', autopurge=True)
    conf['combine'] = parse_bool(conf['combine'])
    return ConfiguredJsModule(
        http, tpl, webassets, conf['rootdir'], conf['cachedir'],
        conf['combine'], conf['minifier'])


_js_escapes = tuple([('%c' % z, '\\u%04X' % z) for z in range(32)] + [
    ('\\', r'\u005C'),
    ('\'', r'\u0027'),
    ('"', r'\u0022'),
    ('>', r'\u003E'),
    ('<', r'\u003C'),
    ('&', r'\u0026'),
    ('=', r'\u003D'),
    ('-', r'\u002D'),
    (';', r'\u003B'),
    (u'\u2028', r'\u2028'),
    (u'\u2029', r'\u2029'),
])


def escape(value):
    """
    Escapes a string *value* to ensure it is safe to embed it in a javascript
    string.
    """
    return reduce(lambda a, kv: a.replace(*kv), _js_escapes, value)


class ConfiguredJsModule(ConfiguredModule, TemplateConverter):
    """
    This module's :class:`configuration object
    <score.init.ConfiguredModule>`, which is also a
    :term:`template converter`.
    """

    def __init__(self, http, tpl, webassets, rootdir, cachedir, combine,
                 minifier):
        super().__init__(__package__)
        self.http = http
        self.tpl = tpl
        self.webassets = webassets
        self.combine = combine
        self.minifier = minifier
        tpl.renderer.register_format('js', rootdir, cachedir, self)
        self.virtfiles = VirtualAssets()
        self.virtjs = self.virtfiles.decorator('js')
        self._add_single_route()
        self._add_combined_route()

    def _add_single_route(self):

        @self.http.newroute('score.js:single', '/js/{path>.*\.js$}')
        def single(ctx, path):
            versionmanager = self.webassets.versionmanager
            if versionmanager.handle_request(ctx, 'js', path):
                return self._response(ctx)
            path = self._urlpath2path(path)
            if path in self.virtfiles.paths():
                js = self.virtfiles.render(ctx, path)
            else:
                js = self.tpl.renderer.render_file(ctx, path)
            return self._response(ctx, js)

        @single.vars2url
        def url_single(ctx, path):
            urlpath = self._path2urlpath(path)
            url = '/js/' + urllib.parse.quote(urlpath)
            versionmanager = self.webassets.versionmanager
            if path in self.virtfiles.paths():

                def hasher():
                    return self.virtfiles.hash(ctx, path)

                def renderer():
                    return self.virtfiles.render(ctx, path).encode('UTF-8')

            else:
                file = os.path.join(self.rootdir, path)
                hasher = versionmanager.create_file_hasher(file)

                def renderer():
                    return self.tpl.renderer.render_file(ctx, path).\
                        encode('UTF-8')

            hash_ = versionmanager.store('js', urlpath, hasher, renderer)
            if hash_:
                url += '?_v=' + hash_
            return url

        self.route_single = single

    def _add_combined_route(self):

        @self.http.newroute('score.js:combined', '/combined.js')
        def combined(ctx):
            versionmanager = self.webassets.versionmanager
            if versionmanager.handle_request(ctx, 'js', '__combined__'):
                return self._response(ctx)
            return self._response(ctx, self.render_combined(ctx))

        @combined.vars2url
        def url_combined(ctx):
            versionmanager = self.webassets.versionmanager
            hash_ = versionmanager.store(
                'js', '__combined__', self.generate_combined_hasher(ctx),
                lambda: self.render_combined(ctx).encode('UTF-8'))
            url = '/combined.js'
            if hash_:
                url += '?_v=' + hash_
            return url

        self.route_combined = combined

    def generate_combined_hasher(self, ctx):
        files = []
        vfiles = []
        for path in self.paths():
            if path in self.virtfiles.paths():
                vfiles.append(path)
            else:
                files.append(os.path.join(self.rootdir, path))
        versionmanager = self.webassets.versionmanager
        hashers = [versionmanager.create_file_hasher(files)]
        for path in vfiles:
            hashers.append(lambda: self.virtfiles.hash(ctx, path))
        return hashers

    def _finalize(self, tpl):
        if 'html' in tpl.renderer.formats:
            tpl.renderer.add_function(
                'html', 'js', self._tags, escape_output=False)
            tpl.renderer.add_filter(
                'html', 'escape_js', escape, escape_output=False)

    @property
    def minify(self):
        """
        Whether javascript content should be minified.
        """
        return bool(self.minifier)

    @property
    def rootdir(self):
        """
        The configured root folder of javascript files.
        """
        return self.tpl.renderer.format_rootdir('js')

    @property
    def cachedir(self):
        """
        The configured cache folder.
        """
        return self.tpl.renderer.format_cachedir('js')

    def paths(self, includehidden=False):
        """
        Provides a list of all js files found in the js root folder as
        :term:`paths <asset path>`, as well as the paths of all :term:`virtual
        javascript files <virtual asset>`.
        """
        paths = self.tpl.renderer.paths('js', self.virtfiles, includehidden)
        paths.sort()
        # FIXME: remove minified javascript files
        return paths

    def convert_string(self, ctx, js, path=None):
        cachefile = None
        if path and os.path.exists(path) and self.cachedir:
            cachefile = os.path.join(self.cachedir, path)
            file = os.path.join(self.rootdir, path)
            if os.path.isfile(cachefile) and \
                    os.path.getmtime(cachefile) > os.path.getmtime(file):
                return open(cachefile, 'r').read()
        if self.minifier:
            js = self.minifier.minify_string(js, path=path)
        if cachefile:
            os.makedirs(os.path.dirname(cachefile), exist_ok=True)
            open(cachefile, 'w').write(js)
        return js

    def convert_file(self, ctx, path):
        if path in self.virtfiles.paths():
            return self.convert_string(
                ctx, self.virtfiles.render(ctx, path), path)
        file = os.path.join(self.rootdir, path)
        if not os.path.isfile(file):
            raise AssetNotFound('js', path)
        if self.minifier and file.endswith('.js'):
            minfile = file[:-3] + '.min.js'
            if os.path.isfile(minfile):
                return open(minfile, 'r', encoding='utf-8-sig').read()
        js = open(file, 'r', encoding='utf-8-sig').read()
        return self.convert_string(ctx, js, path)

    def render_combined(self, ctx):
        """
        Renders the combined js file.
        """
        parts = []
        for path in self.paths():
            if not self.minify:
                s = '/*{0}*/\n/*{1:^76}*/\n/*{0}*/'.format('*' * 76, path)
                parts.append(s)
            parts.append(self.tpl.renderer.render_file(ctx, path))
        return '\n\n'.join(parts)

    def _response(self, ctx, js=None):
        """
        Sets appropriate headers on the http response.
        Will optionally set the response body to the given *js* string.
        """
        ctx.http.response.content_type = 'application/javascript; charset=UTF-8'
        if js:
            ctx.http.response.text = js
        return ctx.http.response

    def _path2urlpath(self, path):
        """
        Converts a :term:`path <asset path>` to the corresponding path to use
        in URLs.
        """
        urlpath = path
        if not urlpath.endswith('.js'):
            urlpath = urlpath[:urlpath.rindex('.')]
        assert urlpath.endswith('.js')
        return urlpath

    def _urlpath2path(self, urlpath):
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
        for ext in self.tpl.renderer.engines:
            file = os.path.join(self.rootdir, jspath + '.' + ext)
            if os.path.isfile(file):
                return jspath + '.' + ext
        raise ValueError('Could not determine path for url "%s"' % urlpath)

    def _tags(self, ctx, *paths):
        """
        Generates all ``script`` tags necessary to include all javascript
        files. It is possible to generate the tags to specific js *paths*
        only.
        """
        tag = '<script src="%s"></script>'
        if len(paths):
            return '\n'.join(tag % self.http.url(ctx, 'score.js:single', path)
                             for path in paths)
        if self.combine:
            return tag % self.http.url(ctx, 'score.js:combined')
        if not len(self.paths()):
            return ''
        return self._tags(ctx, *self.paths())
