from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable


@dataclass
class StreamWriteError(Exception):
    """Exception raised for errors in the StreamWriter."""

    message: str


def stream_error_handler(func: Callable) -> Callable:
    """
    A decorator to wrap Exception over a StreamWriteError.

    Args:
        func: The asynchronous function to be decorated.

    Returns:
        The wrapped function.
    """

    @wraps(func)
    async def wrapper(*args: tuple, **kwargs: dict) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as exc:
            raise StreamWriteError(str(exc)) from exc

    return wrapper
