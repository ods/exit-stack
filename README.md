# Decorator to run clean-up on exit from [async] function/generator

This overcomplicates peace of code just removes one level of indentation from
your code that uses `ExitStack` or `AsyncExitStack`.  That is the following
code

    def func(...):
        with ExitStack() as exit_stack:
            value = exit_stack.enter_context(...)
            exit_stack.callback(...)
            ...

turns into

    @exit_stack.wrap
    def func(...):
        value = exit_stack.enter_context(...)
        exit_stack.callback(...)
        ...

Works for functions, coroutine functions, generators and async generators.
Thus you can use it to create context manager:

    @asynccontextmanager
    @exit_stack.wrap
    async def manager(...):
        value = await exit_stack.enter_async_context(...)
        await exit_stack.push_async_callback(...)
        yield ...
