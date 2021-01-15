from contextlib import AsyncExitStack, ExitStack
import contextvars
import functools
import inspect

__all__ = ['exit_stack']


class _ExitStackProxy:

    def __init__(self):
        self._stack = contextvars.ContextVar('exit_stack')

    def _call_with_stack(self, stack, func, *args, **kwargs):
        token = self._stack.set(stack)
        try:
            return func(*args, **kwargs)
        finally:
            self._stack.reset(token)

    async def _async_call_with_stack(self, stack, func, *args, **kwargs):
        token = self._stack.set(stack)
        try:
            return await func(*args, **kwargs)
        finally:
            self._stack.reset(token)

    def wrap(self, func):
        """Enable `exit_stack` in decorated function (as well as generator
        function, coroutine function or async-generator function).  Use it
        to avoid excessive indentation of nested `with`/`async with` blocks
        when you need a number of cleanup steps on return.

        Usage example:

            @exit_stack.wrap
            def some_func(path, ...):
                fp = exit_stack.enter_context(
                    pathlib.Path(path).open()
                )
                ...
        """
        if not inspect.isfunction(func):
            raise TypeError(f'{func} is not a function')

        if inspect.iscoroutinefunction(func):

            async def wrapper(*args, **kwargs):
                async with AsyncExitStack() as stack:
                    return await self._async_call_with_stack(
                        stack, func, *args, **kwargs,
                    )

        elif inspect.isasyncgenfunction(func):

            async def wrapper(*args, **kwargs):
                async with AsyncExitStack() as stack:
                    gen = func(*args, **kwargs)

                    # `yield from` equivalent for async generator (propagates
                    # `asend()`/`athrow()`)
                    item = await self._async_call_with_stack(
                        stack, gen.asend, None,
                    )
                    while True:
                        try:
                            value = yield item
                        except GeneratorExit:
                            await self._async_call_with_stack(stack, gen.aclose)
                            break
                        except BaseException as exc:
                            item = await self._async_call_with_stack(
                                stack, gen.athrow, exc,
                            )
                        else:
                            try:
                                item = await self._async_call_with_stack(
                                    stack, gen.asend, value,
                                )
                            except StopAsyncIteration:
                                break
                        yield item

        elif inspect.isgeneratorfunction(func):

            def wrapper(*args, **kwargs):
                with ExitStack() as stack:
                    gen = func(*args, **kwargs)

                    # `yield from` equivalent
                    item = self._call_with_stack(stack, gen.send, None)
                    while True:
                        try:
                            value = yield item
                        except GeneratorExit:
                            self._call_with_stack(stack, gen.close)
                            break
                        except BaseException as exc:
                            item = self._call_with_stack(stack, gen.throw, exc)
                        else:
                            try:
                                item = self._call_with_stack(stack, gen.send, value)
                            except StopIteration:
                                break
                        yield item

        else:

            def wrapper(*args, **kwargs):
                with ExitStack() as stack:
                    return self._call_with_stack(stack, func, *args, **kwargs)

        return functools.wraps(func)(wrapper)

    def get(self):
        stack = self._stack.get(None)
        if stack is None:
            raise TypeError(
                f"exit_stack is not enabled for this context. "
                f"Didn't you forget to decorate it with @exit_stack.wrap?"
            )
        return stack

    # Explicitly define methods for autocompletion in IDE

    # Common for ExitStack and AsyncExitStack
    def pop_all(self):
        return self.get().pop_all()
    def push(self, exit):
        return self.get().push(exit)
    def enter_context(self, cm):
        return self.get().enter_context(cm)
    def callback(self, callback, *args, **kwds):
        # TODO Update signature after dropping Python 3.7 support
        return self.get().callback(callback, *args, **kwds)

    # Only in ExitStack
    def close(self):
        self.get().close()

    # Only in AsyncExitStack
    async def enter_async_context(self, cm):
        return await self.get().enter_async_context(cm)
    def push_async_exit(self, exit):
        return self.get().push_async_exit(exit)
    def push_async_callback(self, callback, *args, **kwds):
        # TODO Update signature after dropping Python 3.7 support
        return self.get().push_async_callback(callback, *args, **kwds)
    async def aclose(self):
        await self.get().aclose()


exit_stack = _ExitStackProxy()
