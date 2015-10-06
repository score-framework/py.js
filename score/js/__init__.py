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

from functools import reduce
import os
from score.init import init_cache_folder, ConfiguredModule, init_object
from score.webassets import VirtualAssets, AssetNotFound
from score.tpl import TemplateConverter

import logging
log = logging.getLogger(__name__)


defaults = {
    'rootdir': None,
    'cachedir': None,
    'minifier': None,
}


def init(confdict, webassets_conf, tpl_conf, html_conf=None):
    """
    Initializes this module acoording to :ref:`our module initialization
    guidelines <module_initialization>` with the following configuration keys:

    :confkey:`rootdir` :faint:`[default=None]`
        Denotes the root folder containing all javascript files. Will fall
        back to a sub-folder of the folder in :mod:`score.tpl`'s
        configuration, as described in :func:`score.tpl.init`.

    :confkey:`cachedir` :faint:`[default=None]`
        A dedicated cache folder for this module. It is generally sufficient
        to provide a ``cachedir`` for :mod:`score.tpl`, as this module will
        use a sub-folder of that by default.

    :confkey:`minifier` :faint:`[default=None]`
        The minifier to use for minification. Will be initialized using
        :func:`score.init.init_object`. See :mod:`score.tpl.minifier` for
        available minifiers.
    """
    conf = dict(defaults.items())
    conf.update(confdict)
    if conf['minifier']:
        conf['minifier'] = init_object(conf, 'minifier')
    if not conf['cachedir'] and webassets_conf.cachedir:
        conf['cachedir'] = os.path.join(webassets_conf.cachedir, 'js')
    if conf['cachedir']:
        init_cache_folder(conf, 'cachedir', autopurge=True)
    if 'html' in tpl_conf.renderer.formats:
        tpl_conf.renderer.add_filter('html', 'escape_js',
                                     escape, escape_output=False)
    return ConfiguredJsModule(tpl_conf, conf['rootdir'],
                              conf['cachedir'], conf['minifier'])


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

    def __init__(self, tpl_conf, rootdir, cachedir, minifier):
        super().__init__(__package__)
        self.tpl_conf = tpl_conf
        self.minifier = minifier
        tpl_conf.renderer.register_format('js', rootdir, cachedir, self)
        self.virtfiles = VirtualAssets()
        self.virtjs = self.virtfiles.decorator('js')

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
        return self.tpl_conf.renderer.format_rootdir('js')

    @property
    def cachedir(self):
        """
        The configured cache folder.
        """
        return self.tpl_conf.renderer.format_cachedir('js')

    def paths(self, includehidden=False):
        """
        Provides a list of all js files found in the js root folder as
        :term:`paths <asset path>`, as well as the paths of all :term:`virtual
        javascript files <virtual asset>`.
        """
        paths = self.virtfiles.paths()
        if not includehidden:
            paths = [p for p in paths if os.path.basename(p)[0] != '_']
        for parent, _, files in os.walk(self.rootdir, followlinks=True):
            for file in files:
                if not file.endswith('.js'):
                    continue
                if file.endswith('.min.js'):
                    continue
                if not includehidden and file[0] == '_':
                    continue
                fullpath = os.path.join(parent, file)
                if not os.path.exists(fullpath):
                    log.warn('Unreadable js path: ' + fullpath)
                    continue
                relpath = os.path.relpath(fullpath, self.rootdir)
                if file in ('require.js', 'globals.js'):
                    paths.insert(0, relpath)
                else:
                    paths.append(relpath)
        return paths

    def convert_string(self, js, path=None):
        if path and self.cachedir:
            cachefile = os.path.join(self.cachedir, path)
            file = os.path.join(self.rootdir, path)
            if os.path.isfile(cachefile) and \
                    os.path.getmtime(cachefile) > os.path.getmtime(file):
                return open(cachefile, 'r').read()
        if self.minifier:
            js = self.minifier.minify_string(js)
        if path and self.cachedir:
            os.makedirs(os.path.dirname(cachefile), exist_ok=True)
            open(cachefile, 'w').write(js)
        return js

    def convert_file(self, path):
        if path in self.virtfiles.paths():
            return self.convert_string(self.virtfiles.render(path))
        file = os.path.join(self.rootdir, path)
        if not os.path.isfile(file):
            raise AssetNotFound('js', path)
        if self.minifier and file.endswith('.js'):
            minfile = file[:-3] + '.min.js'
            if os.path.isfile(minfile):
                return open(minfile, 'r').read()
        js = open(file, 'r').read()
        return self.convert_string(js, path)
