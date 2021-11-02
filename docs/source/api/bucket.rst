Bucket
======
A bucket is a client aimed utility to aid concurrency and
ratelimit combinations, it is also async context manager
syntatic sugar over :class:`~uprate.ratelimit.RateLimit`

.. autoclass:: uprate.bucket.Bucket
    :members:

Example
-------
.. literalinclude:: ../examples/bucket.py
    :language: py
    :caption: An example of concurrency management with buckets
