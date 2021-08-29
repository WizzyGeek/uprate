from collections.abc import Coroutine
from typing import TypeVar

T_co = TypeVar("T_co", covariant=True)

def sync_runner(coro: Coroutine[None, None, T_co]) -> T_co:
    """
    .. note:: Don't use with any loop related code.
    """
    try:
        while True:
            coro.send(None)
    except StopIteration as err:
        return err.value
    except BaseException as err:
        raise BaseException from None
