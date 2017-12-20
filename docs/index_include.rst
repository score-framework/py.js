.. module:: score.js
.. role:: confkey
.. role:: confdefault


********
score.js
********

This small module just defines the 'application/javascript' mime type for
:mod:`score.tpl` and configures some parameters for javascript rendering.


Quickstart
==========

Usually, it is sufficient to add this module to your initialization list:


.. code-block:: ini

    [score.init]
    modules =
        score.tpl
        score.js


Configuration
=============

.. autofunction:: init

Details
=======

Minification
------------

.. automodule:: score.js.minifier

API
===

Configuration
-------------

.. autofunction:: score.js.init

.. autoclass:: score.js.ConfiguredJsModule
    :members:


.. _js_minification:

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
