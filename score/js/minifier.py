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
The minifier package provides means for reducing the size of javascript code
without altering its semantics. If one does not care, how the code is
minified, one can just use the functions :func:`minify_string` and
:func:`minify_file`.

Currently, the following minification backends are supported:

- slimit_: Provides good minification, but is quite slow. Does not preserve
  licensing information.
- jsmin_: Very fast, but not the best minification. Does not preserve
  licensing information.
- uglifyjs_: Moderate speed and good minification. Preserves licensing
  information; dependends on node.js.
- `yui compressor`_: Fast but moderate compression. Preserves licensing
  information; depends on java.


.. _slimit: https://pypi.python.org/pypi/slimit
.. _jsmin: https://pypi.python.org/pypi/jsmin
.. _uglifyjs: https://github.com/mishoo/UglifyJS
.. _yui compressor: http://yui.github.io/yuicompressor/
"""


from abc import ABCMeta, abstractmethod
import logging
import subprocess

log = logging.getLogger('score.js.minifier')


def minify_string(js, outfile=None):
    """
    Minifies given *js* string using uglifyjs, as this is the only
    configuration-free backend that preserves licensing information.

    By default, this function returns the minified string. It is also possible
    to provide an *outfile* to write the result to, instead of returning it.
    """
    return Uglifyjs().minify_string(js, outfile)


def minify_file(file, outfile=None):
    """
    Does the same as :func:`minify_string`, but operates on an input *file*,
    instead of a string.
    """
    return Uglifyjs().minify_file(file, outfile)


class MinifierBackend(metaclass=ABCMeta):
    """
    Abstract base class for minifier backends.
    """

    @abstractmethod
    def minify_file(self, file, outfile=None):
        """
        Backend-specific implementation of the global function
        :func:`minify_file`.
        """
        return

    @abstractmethod
    def minify_string(self, string, outfile=None):
        """
        Backend-specific implementation of the global function
        :func:`minify_string`.
        """
        return


class Slimit(MinifierBackend):
    """
    :class:`.MinifierBackend` using slimit_.

    .. _slimit: https://pypi.python.org/pypi/slimit
    """

    def __init__(self):
        """
        Initializes the slimit library. This will fix an error in current version
        of ply.
        See https://github.com/rspivak/slimit/issues/64#issuecomment-38801874 for
        details.
        """
        from ply import yacc
        def __getitem__(self,n):
            if isinstance(n, slice):
                return self.__getslice__(n.start, n.stop)
            if n >= 0:
                return self.slice[n].value
            else:
                return self.stack[n].value
        yacc.YaccProduction.__getitem__ = __getitem__

    def minify_file(self, file, outfile=None):
        return slimit_str(open(file, 'r').read(), outfile)

    def minify_string(self, string, outfile=None):
        from slimit import minify
        result = minify(js, mangle=True)
        if outfile:
            open(outfile, 'w').write(result)
        else:
            return result


class Jsmin(MinifierBackend):
    """
    :class:`.MinifierBackend` using jsmin_.

    .. _jsmin: https://pypi.python.org/pypi/jsmin
    """

    def minify_file(self, file, outfile=None):
        return self.jsmin_str(open(file, 'r').read())

    def minify_string(self, js, outfile=None):
        from jsmin import jsmin
        result = jsmin(js)
        if outfile:
            open(outfile, 'w').write(result)
        else:
            return result


class Uglifyjs(MinifierBackend):
    """
    :class:`.MinifierBackend` using uglifyjs_.

    .. _uglifyjs: https://github.com/mishoo/UglifyJS
    """

    def minify_file(self, file, outfile=None):
        args = ['uglifyjs', '--mangle', '--compress', '--lint',
                '--comments', '/^!|@license|@preserve/']
        if outfile:
            args += ['--output', outfile]
        args.append(file)
        process = subprocess.Popen(args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        output, error = process.communicate()
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode,
                    ' '.join(map(lambda x: repr(x), args)), error)
        if error:
            log.info('uglifyjs gave these warnings:\n%s' % error)
        if not outfile:
            return str(output, 'UTF-8')


    def minify_string(self, js, outfile=None):
        args = ['uglifyjs', '--mangle', '--compress', '--lint',
                '--comments', '/^!|@license|@preserve/']
        if outfile:
            args += ['--output', outfile]
        process = subprocess.Popen(args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        if isinstance(js, str):
            js = js.encode('UTF-8')
        output, error = process.communicate(js)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode,
                    ' '.join(map(lambda x: repr(x), args)), error)
        if error:
            log.info('uglifyjs gave these warnings:\n%s' % error)
        if not outfile:
            return str(output, 'UTF-8')


class YuiCompressor(MinifierBackend):
    """
    :class:`.MinifierBackend` using `yui compressor`_. Constructor needs the
    path to `yuicompressor's jar file`_.

    .. _yui compressor: http://yui.github.io/yuicompressor/
    .. _yuicompressor's jar file: https://github.com/yui/yuicompressor/releases
    """

    def __init__(self, jar):
        self.jar = jar

    def minify_file(self, file, outfile=None):
        args = ['java', '-jar', self.jar, '--type', 'js', '--charset', 'UTF-8', '-v']
        if outfile:
            args += ['-o', outfile]
        args.append(file)
        process = subprocess.Popen(args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        output, error = process.communicate()
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode,
                    ' '.join(map(lambda x: repr(x), args)), error)
        if error:
            log.info('yui gave these warnings:\n%s' % error)
        if not outfile:
            return str(output, 'UTF-8')


    def minify_string(self, js, outfile=None):
        if not js:
            # Yui seems to crash when trying to convert empty strings.
            return ''
        args = ['java', '-jar', self.jar, '--type', 'js', '--charset', 'UTF-8', '-v']
        if outfile:
            args += ['-o', outfile]
        process = subprocess.Popen(args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        output, error = process.communicate(js)
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode,
                    ' '.join(args), error)
        if error:
            log.info('yui gave these warnings:\n%s' % error)
        if not outfile:
            return str(output, 'UTF-8')


