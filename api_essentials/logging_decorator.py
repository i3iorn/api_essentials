import inspect
import logging
import time
import functools
from typing import Any, Callable, Type


def log_method_calls(include_dunder: bool = False):
    """
    Class decorator to log method calls, input types, output type, and execution time.
    """
    def class_decorator(cls: Type):
        if not inspect.isclass(cls):
            raise TypeError(f"Expected a class, got {type(cls).__name__}")
        if not hasattr(cls, "__name__"):
            raise TypeError("Class must have a __name__ attribute")
        if not hasattr(cls, "__dict__"):
            raise TypeError("Class must have a __dict__ attribute")
        if not hasattr(cls, "__module__"):
            raise TypeError("Class must have a __module__ attribute")
        if not hasattr(cls, "__qualname__"):
            raise TypeError("Class must have a __qualname__ attribute")

        if not hasattr(cls, "logger"):
            cls.logger = logging.getLogger(f"{cls.__module__}.{cls.__name__}")

        for name, attr in cls.__dict__.items():
            if callable(attr) and (include_dunder or not name.startswith("__")):
                wrapped = _wrap_method(attr, cls.logger)
                cls.logger.debug(f"Wrapping method: {name}")
                setattr(cls, name, wrapped)
        return cls

    def _wrap_method(method: Callable, logger) -> Callable:
        if inspect.iscoroutinefunction(method):
            @functools.wraps(method)
            async def async_wrapper(*args, **kwargs):
                return await _log_execution(method, args, kwargs, logger)
            return async_wrapper

        @functools.wraps(method)
        def sync_wrapper(*args, **kwargs):
            return _log_execution(method, args, kwargs, logger)
        return sync_wrapper

    def _log_execution(method: Callable, args: tuple, kwargs: dict, logger) -> Any:
        sig = inspect.signature(method)
        bound = sig.bind_partial(*args, **kwargs)
        bound.apply_defaults()

        arg_types = {
            k: type(v).__name__ for k, v in bound.arguments.items()
        }

        start = time.perf_counter()
        result = method(*args, **kwargs) if not inspect.iscoroutinefunction(method) else None
        duration = time.perf_counter() - start

        if inspect.iscoroutinefunction(method):
            async def run_async():
                nonlocal result
                result = await method(*args, **kwargs)
                logger.debug(f"[{method.__qualname__}] Args: {arg_types}, "
                             f"Return: {type(result).__name__}, Time: {duration:.4f}s")
                return result
            return run_async()

        logger.debug(f"[{method.__qualname__}] Args: {arg_types}, "
                     f"Return: {type(result).__name__}, Time: {duration:.4f}s")
        return result

    return class_decorator
