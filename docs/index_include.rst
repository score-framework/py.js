.. module:: score.js
.. role:: faint
.. role:: confkey


********
score.js
********

Introduction
============

This module manages the javascript file :term:`format <template format>`
``js`` in :mod:`score.tpl`.


Minification
------------

.. automodule:: score.js.minifier

Configuration
=============

.. autofunction:: score.js.init

.. autoclass:: score.js.ConfiguredJsModule
    :members:


Minifier
========

.. autofunction:: score.js.minifier.minify_string

.. autofunction:: score.js.minifier.minify_file

.. autoclass:: score.js.minifier.MinifierBackend
    :members:

.. autoclass:: score.js.minifier.Slimit

.. autoclass:: score.js.minifier.Jsmin

.. autoclass:: score.js.minifier.Uglifyjs

.. autoclass:: score.js.minifier.YuiCompressor


Pyramid Integration
===================

.. automodule:: score.js.pyramid
    :members:

