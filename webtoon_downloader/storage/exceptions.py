from dataclasses import dataclass


@dataclass
class StreamWriteError(Exception):
    """Exception raised for errors in the StreamWriter."""

    message: str
