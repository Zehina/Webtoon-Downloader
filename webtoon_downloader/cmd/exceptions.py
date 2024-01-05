from __future__ import annotations

from typing import Any

import rich_click as click


class LatestWithStartOrEndError(click.UsageError):
    """
    This error is raised when the user attempts to use --latest in conjunction
    with either --start or --end options, which is not allowed due to their
    conflicting nature.

    Args:
        ctx: The Click context associated with the error, if any.
    """

    def __init__(self, ctx: click.Context | None = None) -> None:
        message = "Options --start/--end and --latest cannot be used together."
        super().__init__(message, ctx)


class SeparateOptionWithNonImageSaveAsError(click.UsageError):
    """
    This error is raised when the user attempts to use --separate with a save-as
    option other than 'images'. The --separate option is only compatible with
    saving chapters as individual images.

    Args:
        ctx: The Click context associated with the error, if any.
    """

    def __init__(self, ctx: click.Context | None = None) -> None:
        message = "Option --separate is only compatible with --save-as 'images'."
        super().__init__(message, ctx)


class DeprecatedOptionError(click.UsageError):
    """
    Custom error for handling deprecated options in the CLI.
    """

    def __init__(self, deprecated_option: str, use_instead_option: str):
        message = f"{deprecated_option} is deprecated; use {use_instead_option} instead."
        super().__init__(message)


def handle_deprecated_options(_: click.Context, param: click.Parameter, value: Any) -> None:
    """Handler for deprecated options"""
    if param.name == "export_texts" and value:
        raise DeprecatedOptionError(deprecated_option="--export-texts", use_instead_option="--export-metadata")
    elif param.name == "dest" and value is not None:
        raise DeprecatedOptionError(deprecated_option="--dest", use_instead_option="--out")
