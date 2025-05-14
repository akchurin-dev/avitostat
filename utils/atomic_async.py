from asgiref.sync import async_to_sync
from asgiref.sync import sync_to_async
from asyncio import wrap_future
from concurrent.futures import ThreadPoolExecutor
from django.db import connections
from django.db.transaction import Atomic


class AsyncAtomicContextManager(Atomic):
    """To async use atomic context, you need to use run_in_context on db related methods."""

    def __init__(self, using=None, savepoint=True, durable=False):
        super().__init__(using, savepoint, durable)
        self.executor = ThreadPoolExecutor(1)

    async def __aenter__(self):
        await sync_to_async(super().__enter__, thread_sensitive=False, executor=self.executor)()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await sync_to_async(super().__exit__, thread_sensitive=False, executor=self.executor)(exc_type, exc_value, traceback)
        future = wrap_future(self.executor.submit(self.close_connections))
        await future
        self.executor.shutdown()

    async def run_in_context(self, fun, *args, **kwargs):
        """Use this method to run db related methods in atomic context."""
        future = wrap_future(self.executor.submit(fun, *args, **kwargs))
        await future
        return future.result()
    
    def close_connections(self):
        """It is necessary to close connections before shutdown."""
        for conn in connections.all():
            conn.close()


def aatomic(using=None, savepoint=True, durable=False):
    """This decorator will run function in new atomic context. Which will be destroyed after function ends."""
    def decorator(fun):
        async def wrapper(*args, **kwargs):
            async with AsyncAtomicContextManager(using, savepoint, durable) as aacm:
                future = wrap_future(aacm.executor.submit(async_to_sync(fun), *args, **kwargs))
                await future
                return future.result()
        return wrapper
    return decorator
