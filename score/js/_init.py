# Copyright © 2015-2017 STRG.AT GmbH, Vienna, Austria
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
from score.init import ConfiguredModule, init_object, parse_list, parse_bool
import logging

log = logging.getLogger('score.js')


defaults = {
    'minifier': None,
    'tpl.extensions': ['js'],
    'tpl.register_minifier': True,
}


def init(confdict, tpl):
    """
    Initializes this module acoording to :ref:`our module initialization
    guidelines <module_initialization>` with the following configuration keys:

    :confkey:`minifier` :confdefault:`None`
        The minifier to use for minification. Will be initialized using
        :func:`score.init.init_object`. See :mod:`score.tpl.minifier` for
        available minifiers.

    :confkey:`tpl.extensions` :confdefault:`js`
        The extensions to register with the tpl module.
    """
    conf = dict(defaults.items())
    conf.update(confdict)
    filetype = tpl.filetypes['application/javascript']
    minifier = None
    if conf['minifier']:
        minifier = init_object(conf, 'minifier')
        if parse_bool(conf['tpl.register_minifier']):
            filetype.postprocessors.append(minifier.minify_string)
    extensions = parse_list(conf['tpl.extensions'])
    filetype.extensions.extend(extensions)
    return ConfiguredJsModule(tpl, minifier, extensions)


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


class ConfiguredJsModule(ConfiguredModule):
    """
    This module's :class:`configuration object
    <score.init.ConfiguredModule>`, which is also a
    :term:`template converter`.
    """

    def __init__(self, tpl, minifier, extensions):
        super().__init__(__package__)
        self.tpl = tpl
        self.minifier = minifier
        self.extensions = extensions

    def score_webassets_proxy(self):
        from score.webassets import TemplateWebassetsProxy

        class JavascriptWebassetsProxy(TemplateWebassetsProxy):

            def __init__(self, tpl):
                super().__init__(tpl, 'application/javascript')

            def render_url(self, url):
                return '<script src="%s"></script>' % (url,)

            def create_bundle(self, paths):
                """
                Renders the combined js file.
                """
                parts = []
                for path in sorted(paths):
                    s = '/*{0}*/\n/*{1:^74}*/\n/*{0}*/'.format('*' * 74, path)
                    parts.append(s)
                    parts.append(self.tpl.render(path,
                                                 apply_postprocessors=False))
                content = '\n\n'.join(parts)
                filetype = self.tpl.filetypes['application/javascript']
                for postprocessor in filetype.postprocessors:
                    content = postprocessor(content)
                return content

        return JavascriptWebassetsProxy(self.tpl)
