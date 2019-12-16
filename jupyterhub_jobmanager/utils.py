import asyncio
import weakref

from .compat import get_running_loop


class TaskPool(object):
    def __init__(self):
        self.pending_tasks = weakref.WeakSet()
        self.background_tasks = weakref.WeakSet()

    def create_task(self, task):
        out = asyncio.ensure_future(task)
        self.pending_tasks.add(out)
        return out

    def create_background_task(self, task):
        out = asyncio.ensure_future(task)
        self.background_tasks.add(out)
        return out

    async def close(self, timeout=5):
        # Cancel all background tasks
        for task in self.background_tasks:
            task.cancel()

        # Wait for a short period for any ongoing tasks to complete, before
        # canceling them
        try:
            await asyncio.wait_for(
                asyncio.gather(*self.pending_tasks, return_exceptions=True), timeout
            )
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass

        # Now wait for all tasks to be actually completed
        try:
            await asyncio.gather(
                *self.pending_tasks, *self.background_tasks, return_exceptions=True
            )
        except asyncio.CancelledError:
            pass


class timeout(object):
    """An async-contextmanager for managing timeouts.

    If the timeout occurs before the block exits, any running operation under
    the context will be cancelled, and a ``asyncio.TimeoutError`` will be
    raised.

    To check if the timeout expired, you can check the ``expired`` attribute.
    """

    def __init__(self, t):
        self.t = t
        self._task = None
        self._waiter = None
        self.expired = False

    def _cancel_task(self):
        if self._task is not None:
            self._task.cancel()
            self.expired = True

    async def __aenter__(self):
        loop = get_running_loop()
        try:
            self._task = asyncio.current_task(loop=loop)
        except AttributeError:
            self._task = asyncio.Task.current_task(loop=loop)
        self._waiter = loop.call_later(self.t, self._cancel_task)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is asyncio.CancelledError and self.expired:
            self._waiter = None
            self._task = None
            raise asyncio.TimeoutError
        elif self._waiter is not None:
            self._waiter.cancel()
            self._waiter = None
        self._task = None
