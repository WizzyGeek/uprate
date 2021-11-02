Rate
====

.. currentmodule:: uprate.rate

.. automodule:: uprate.rate
    :members:

Rate Group
----------
This is an internal component but has been documented for sake of typing.

.. autoclass:: uprate.rate.RateGroup

:class:`uprate.rate.RateGroup` objects are created when :class:`uprate.rate.Rate` objects are operated togather
with :py:func:`operator.__or__` that is the bitwise or operator ``a | b``

.. code-block:: python

    ApiRateGroup: uprate.rate.RateGroup = (2 / Seconds(3)) | (3 / Minutes(2) + Seconds(5))
