Decorators
==========
High level API for limiting callbacks with static rates.

.. autodecorator:: uprate.decorators.ratelimit

.. autofunction:: uprate.decorators.on_retry_sleep

.. note::

    :func:`uprate.decorators.on_retry_sleep` can be used with
    :func:`uprate.decorators.ratelimit` only when the decorated function is async.

.. autofunction:: uprate.decorators.on_retry_block