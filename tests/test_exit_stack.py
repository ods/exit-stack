import contextlib

import pytest

from exit_stack import exit_stack


@pytest.fixture
def history():
    return []


@pytest.fixture
def callback(history):

    def _callback():
        history.append('cb')

    return _callback


@pytest.fixture
def create_context_manager(history):

    @contextlib.contextmanager
    def _context_manager():
        history.append('+cm')
        try:
            yield
        finally:
            history.append('-cm')

    return _context_manager


@pytest.fixture
def async_callback(history):

    async def _async_callback():
        history.append('acb')

    return _async_callback


@pytest.fixture
def create_async_context_manager(history):

    @contextlib.asynccontextmanager
    async def _async_context_manager():
        history.append('+acm')
        try:
            yield
        finally:
            history.append('-acm')

    return _async_context_manager


def test_not_wrapped(callback):

    def func():
        exit_stack.callback(callback)

    with pytest.raises(TypeError):
        func()


def test_function(history, callback, create_context_manager):

    @exit_stack.wrap
    def func(result):
        exit_stack.callback(callback)
        exit_stack.enter_context(create_context_manager())
        if isinstance(result, Exception):
            raise result
        else:
            return result

    expected = ['+cm', '-cm', 'cb']

    history.clear()
    result = func(123)
    assert result == 123
    assert history == expected

    history.clear()
    with pytest.raises(RuntimeError):
        func(RuntimeError())
    assert history == expected

    with pytest.raises(TypeError):
        exit_stack.get()


def test_generator_function(history, callback, create_context_manager):

    @exit_stack.wrap
    def func(result):
        exit_stack.callback(callback)
        exit_stack.enter_context(create_context_manager())
        if isinstance(result, Exception):
            raise result
        else:
            yield result

    expected = ['+cm', '-cm', 'cb']

    history.clear()
    result = list(func(123))
    assert result == [123]
    assert history == expected

    history.clear()
    with pytest.raises(RuntimeError):
        list(func(RuntimeError()))
    assert history == expected

    history.clear()
    gen = func(123)
    result = next(gen)
    assert result == 123
    assert history == ['+cm']

    with pytest.raises(TypeError):
        exit_stack.get()

    gen.close()
    assert history == expected

    with pytest.raises(TypeError):
        exit_stack.get()


async def test_coroutine_function(
    history, callback, create_context_manager, async_callback,
    create_async_context_manager,
):

    @exit_stack.wrap
    async def func(result):
        exit_stack.callback(callback)
        exit_stack.enter_context(create_context_manager())
        exit_stack.push_async_callback(async_callback)
        await exit_stack.enter_async_context(create_async_context_manager())
        if isinstance(result, Exception):
            raise result
        else:
            return result

    expected = ['+cm', '+acm', '-acm', 'acb', '-cm', 'cb']

    history.clear()
    result = await func(123)
    assert result == 123
    assert history == expected

    history.clear()
    with pytest.raises(RuntimeError):
        await func(RuntimeError())
    assert history == expected

    with pytest.raises(TypeError):
        exit_stack.get()


async def test_async_generator_function(
    history, callback, create_context_manager, async_callback,
    create_async_context_manager,
):

    @exit_stack.wrap
    async def func(result):
        exit_stack.callback(callback)
        exit_stack.enter_context(create_context_manager())
        exit_stack.push_async_callback(async_callback)
        await exit_stack.enter_async_context(create_async_context_manager())
        if isinstance(result, Exception):
            raise result
        else:
            yield result

    expected = ['+cm', '+acm', '-acm', 'acb', '-cm', 'cb']

    history.clear()
    result = [item async for item in func(123)]
    assert result == [123]
    assert history == expected

    history.clear()
    with pytest.raises(RuntimeError):
        [item async for item in func(RuntimeError())]
    assert history == expected

    history.clear()
    agen = func(123)
    result = await agen.__anext__()
    assert result == 123
    assert history == ['+cm', '+acm']

    with pytest.raises(TypeError):
        exit_stack.get()

    await agen.aclose()
    assert history == expected

    with pytest.raises(TypeError):
        exit_stack.get()
