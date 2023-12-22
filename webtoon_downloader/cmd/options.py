import argparse
import os
import pathlib
import sys
from typing import List

import rich_argparse._lazy_rich as r
from rich.console import Console
from rich.markdown import Markdown
from rich_argparse import RichHelpFormatter


class MutuallyExclusiveArgumentsError(Exception):
    """Exception raised when a group of arguments should be mutually exclusive from another set of arguments"""

    def __init__(self, args1: List[str], args2: List[str]):
        self.args1 = args1
        self.args2 = args2
        self.message = f"Arguments from {args1} should be mutually exclusive from {args2}"
        super().__init__(self.message)


class CustomRichHelpFormatter(RichHelpFormatter):
    def _rich_format_action_invocation(self, action: argparse.Action) -> r.Text:
        if not action.option_strings:
            metavar = self._get_default_metavar_for_positional(action)
            return r.Text(metavar, "argparse.args")
        else:
            action_header = r.Text(", ").join(r.Text(o, "argparse.args") for o in action.option_strings)
            return action_header

    def _rich_expand_help(self, action: argparse.Action) -> r.Text:
        if action.help is argparse.SUPPRESS:
            return r.Text()

        # Original help text
        original_help = super()._rich_expand_help(action)

        # Append metavar to the help text for options with arguments
        if action.option_strings and action.nargs != 0 and action.choices is not None:
            metavar = self._format_args(action, self._get_default_metavar_for_optional(action))
            original_help.append(f" {metavar}", style="argparse.metavar")

        return original_help


class Options:
    def __init__(self, description="Webtoon Downloader", console=None):
        self.parser = argparse.ArgumentParser(
            formatter_class=CustomRichHelpFormatter,
            description=Markdown(description, style="argparse.text"),
        )
        RichHelpFormatter.styles["argparse.text"] = "italic"
        self.console = console if console else Console()
        self.initialized = False

    def initialize(self) -> None:
        """
        sets the input parser with the different arguments
        """
        self.parser.add_argument(
            "url",
            metavar="url",
            type=str,
            help="webtoon url of the title to download",
            nargs="?",
        )
        self.parser.add_argument(
            "-s",
            "--start",
            type=int,
            help="start chapter",
            required=False,
            default=None,
        )
        self.parser.add_argument("-e", "--end", type=int, help="end chapter", required=False, default=None)
        self.parser.add_argument(
            "-l",
            "--latest",
            required=False,
            help="download only the latest chapter",
            action="store_true",
            default=False,
        )
        self.parser.add_argument("-d", "--dest", type=str, help="download parent folder path", required=False)
        self.parser.add_argument(
            "--images-format",
            required=False,
            help="image format of downloaded images, available",
            choices=["jpg", "png"],
            default="jpg",
        )
        self.parser.add_argument(
            "--separate",
            required=False,
            help="download each chapter in separate folders",
            action="store_true",
            default=False,
        )
        self.parser.add_argument(
            "--export-texts",
            required=False,
            help=("export texts like series summary, chapter name or author " "notes into additional files"),
            action="store_true",
            default=False,
        )
        self.parser.add_argument(
            "--export-format",
            required=False,
            help="format to store exported texts in, available",
            choices=["all", "json", "text"],
            default="json",
        )
        self.parser.add_argument(
            "--readme",
            help="displays readme file content for more help details",
            required=False,
            action="store_true",
        )
        self.parser.add_argument(
            "--version",
            action="version",
            version="[argparse.prog]%(prog)s[/] version [i]1.0.0[/]",
        )

    def print_readme(self) -> None:
        script_dir = pathlib.Path(__file__).parent.parent
        # Path as for an installed module
        readme_path = script_dir.joinpath("data", "README.md").resolve()
        if not os.path.exists(readme_path):
            # Fallback if executed from project-directory
            readme_path = script_dir.parent.joinpath("README.md").resolve()
        with open(readme_path, encoding="utf-8") as readme:
            markdown = Markdown(readme.read())
            self.console.print(markdown)

    def parse(self) -> argparse.Namespace:
        if len(sys.argv) == 1:
            self.parser.print_help()
            sys.exit(0)

        self.args = self.parser.parse_args()
        if self.args.readme:
            self.print_readme()
            sys.exit(0)
        elif not self.args.url:
            self.parser.print_help()
            sys.exit(0)
        elif (self.args.start and self.args.latest) or (self.args.end and self.args.latest):
            self.parser.print_help()
            raise MutuallyExclusiveArgumentsError(["-s", "--start", "-e", "--end"], ["-l", "--latest"])
        return self.args
