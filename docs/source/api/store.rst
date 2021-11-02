Store
=====
A store is the lowest level implementation of rate limits, it manages all the resources
and resetting of the buckets/keys when they expire. It can be said that uprate's complete
performance is majorly dependent on stores, hence using a fast store will lower the ratelimit
overhead introduced by uprate.

Uprate already provides some in-memory stores. More stores targetting different technologies
like redis, SQL etc. are planned be added in future as of now. You are encouraged to write your
own store and publish it or to contribute it to uprate, we will gladly accept store implementations.

.. autoclass:: uprate.store.BaseStore
    :members:
    :show-inheritance:

.. autoclass:: uprate.store.MemoryStore
    :show-inheritance:


Sync Store
----------

.. autoclass:: uprate._sync.SyncStore
    :members:
    :show-inheritance:

.. autoclass:: uprate._sync.SyncMemoryStore
    :show-inheritance:

