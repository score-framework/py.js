.. module:: score.js
.. role:: confkey
.. role:: confdefault


********
score.js
********

This module manages the javascript file :term:`format <template format>`
``js`` in :mod:`score.tpl`.

Quickstart
==========

This module does the exact same thing as :mod:`score.css`, except that the
function is called ``js`` and operates on javascript files:

.. code-block:: python

    js('foo.js', 'bar.js')

The above code will generate the following by default:

.. code-block:: html

    <script src="/js/foo.js"></script>
    <script src="/js/bar.js"></script>


Configuration
=============

.. autofunction:: score.js.init

Details
=======

Minification
------------

.. automodule:: score.js.minifier

API
===

.. autofunction:: score.js.init

.. autoclass:: score.js.ConfiguredJsModule
    :members:


Minifier
--------

.. autofunction:: score.js.minifier.minify_string

.. autofunction:: score.js.minifier.minify_file

.. autoclass:: score.js.minifier.MinifierBackend
    :members:

.. autoclass:: score.js.minifier.Slimit

.. autoclass:: score.js.minifier.Jsmin

.. autoclass:: score.js.minifier.Uglifyjs

.. autoclass:: score.js.minifier.YuiCompressor
