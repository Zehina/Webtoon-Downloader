import argparse
import os
import pathlib
import textwrap
import sys
from rich.console import Console
from rich.markdown import Markdown

class MutuallyExclusiveArgumentsError(Exception):
    '''Exception raised when a group of arguments should be mutually exclusive from another set of arguments'''
    
    def __init__(self, args1, args2):
        self.args1 = args1
        self.args2 = args2
        self.message = f"Arguments from {args1} should be mutually exclusive from {args2}"
        super().__init__(self.message)
    pass

class Options():
    def __init__(self, description='Webtoon Downloader', console = Console()):
        self.parser = ArgumentParser()
        self.console = console
        self.initialized = False
    
    def initialize(self):
        '''
        sets the input parser with the different arguments

        Returns:
        ----------
        (argparse.ArgumentParser) parser object.
        '''
        self.parser.add_argument('url', metavar='url', type=str,
                            help='webtoon url of the title to download', nargs="?")
        self.parser.add_argument('-s', '--start', type=int,
                            help='start chapter', required= False, default=None)
        self.parser.add_argument('-e', '--end', type=int,
                            help='end chapter', required= False, default=None)
        self.parser.add_argument('-l', '--latest', required=False,
                            help='download only the latest chapter',
                            action='store_true', default=False)
        self.parser.add_argument('-d', '--dest', type=str,
                            help='download parent folder path', required= False)
        self.parser.add_argument('--images-format', required=False,
                            help='image format of downloaded images, available: (png, jpg)', 
                            choices=['jpg', 'png'], default='jpg')
        self.parser.add_argument('--seperate', required=False,
                            help='[DEPRECATED] download each chapter in seperate folders',
                            action='store_true', default=False)
        self.parser.add_argument('--separate', required=False,
                            help='download each chapter in seperate folders',
                            action='store_true', default=False)
        self.parser.add_argument('--readme', '-r', help=('displays readme file content for '
                            'more help details'), required=False, action='store_true')
        self.parser._positionals.title = "commands"

    def print_readme(self):
        parent_path = pathlib.Path(__file__).parent.parent.resolve()     
        with open(os.path.join(parent_path, "README.md")) as readme:
            markdown = Markdown(readme.read())
            self.console.print(markdown)
            return

    def parse(self):
        if len(sys.argv) == 1:
            self.parser.print_help()
            sys.exit(0)
        self.args = self.parser.parse_args()
        if self.args.readme:
            self.print_readme()
            sys.exit(0)
        elif self.args.url == None:
            self.parser.print_help()
            sys.exit(0)
        elif (self.args.start and self.args.latest) or (self.args.end and self.args.latest):
            self.parser.print_help()
            raise MutuallyExclusiveArgumentsError(['-s','--start', '-e', '--end'], ['-l', '--latest'])
        return self.args

class ArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, width=78, positional_color='red', options_color='yellow', **kwargs):
        self.program = { key: kwargs[key] for key in kwargs }
        self.positionals = []
        self.options = []
        self.width = width
        self.positional_color = positional_color
        self.options_color = options_color
        super(ArgumentParser, self).__init__(*args, **kwargs)

    def add_argument(self, *args, **kwargs):
        super(ArgumentParser, self).add_argument(*args, **kwargs)
        argument = { key: kwargs[key] for key in kwargs }

        # Positional: argument with only one name not starting with '-' provided as
        # positional argument to method -or- no name and only a 'dest=' argument
        if (len(args) == 0 or (len(args) == 1 and isinstance(args[0], str) and not args[0].startswith("-"))):
            argument["name"] = args[0] if (len(args) > 0) else argument["dest"]
            self.positionals.append(argument)
            return

        # Option: argument with one or more flags starting with '-' provided as
        # positional arguments to method
        argument["flags"] = [ item for item in args ]
        self.options.append(argument)

    def format_usage(self):

        # Use user-defined usage message
        if ("usage" in self.program):
            prefix = "Usage: "
            wrapper = textwrap.TextWrapper(width=self.width)
            wrapper.initial_indent = prefix
            wrapper.subsequent_indent = len(prefix) * " "
            if (self.program["usage"] == "" or str.isspace(self.program["usage"])):
                return wrapper.fill("No usage information available")
            return wrapper.fill(self.program["usage"])

        # Generate usage message from known arguments
        output = []

        # Determine what to display left and right, determine string length for left
        # and right
        left1 = "Usage: "
        left2 = self.program["prog"] if ("prog" in self.program and self.program["prog"] != "" and not str.isspace(self.program["prog"])) else os.path.basename(sys.argv[0]) if (len(sys.argv[0]) > 0 and sys.argv[0] != "" and not str.isspace(sys.argv[0])) else "script.py"
        llen = len(left1) + len(left2)
        arglist = []
        for option in self.options:
            #arglist += [ "[%s]" % item if ("action" in option and (option["action"] == "store_true" or option["action"] == "store_false")) else "[%s %s]" % (item, option["metavar"]) if ("metavar" in option) else "[%s %s]" % (item, option["dest"].upper()) if ("dest" in option) else "[%s]" % item for item in option["flags"] ]
            flags = str.join("|", option["flags"])
            arglist += [ "[%s]" % flags if ("action" in option and (option["action"] == "store_true" or option["action"] == "store_false")) else "[%s %s]" % (flags, option["metavar"]) if ("metavar" in option) else "[%s %s]" % (flags, option["dest"].upper()) if ("dest" in option) else "[%s]" % flags ]
        for positional in self.positionals:
            arglist += [ "%s" % positional["metavar"] if ("metavar" in positional) else "%s" % positional["name"] ]
        right = str.join(" ", arglist)
        rlen = len(right)

        # Determine width for left and right parts based on string lengths, define
        # output template. Limit width of left part to a maximum of self.width / 2.
        # Use max() to prevent negative values. -1: trailing space (spacing between
        # left and right parts), see template
        lwidth = llen
        rwidth = max(0, self.width - lwidth - 1)
        if (lwidth > int(self.width / 2) - 1):
            lwidth = max(0, int(self.width / 2) - 1)
            rwidth = int(self.width / 2)

        outtmp = "%-" + str(lwidth) + "s %s"

        # Wrap text for left and right parts, split into separate lines
        wrapper = textwrap.TextWrapper(width=lwidth)
        wrapper.initial_indent = left1
        wrapper.subsequent_indent = len(left1) * " "
        left = wrapper.wrap(left2)
        wrapper = textwrap.TextWrapper(width=rwidth)
        right = wrapper.wrap(right)

        # Add usage message to output
        for i in range(0, max(len(left), len(right))):
            left_ = left[i] if (i < len(left)) else ""
            right_ = right[i] if (i < len(right)) else ""
            output.append(outtmp % (left_, right_))

        # Return output as single string
        return str.join("\n", output)

    def format_help(self):
        output = []
        dewrapper = textwrap.TextWrapper(width=self.width)

        # Add usage message to output
        output.append(self.format_usage())

        # Add description to output if present
        if ("description" in self.program and self.program["description"] != "" and not str.isspace(self.program["description"])):
            output.append("")
            output.append(dewrapper.fill(self.program["description"]))

        # Determine what to display left and right for each argument, determine max
        # string lengths for left and right
        lmaxlen = rmaxlen = 0
        for positional in self.positionals:
            positional["left"] = positional["metavar"] if ("metavar" in positional) else positional["name"]
            lmaxlen = max(lmaxlen, len(positional["left"]))
        for option in self.options:
            if ("action" in option and (option["action"] == "store_true" or option["action"] == "store_false")):
                option["left"] = str.join(", ", option["flags"])
            else:
                option["left"] = str.join(", ", [ "%s %s" % (item, option["metavar"]) if ("metavar" in option) else "%s %s" % (item, option["dest"].upper()) if ("dest" in option) else item for item in option["flags"] ])
        for argument in self.positionals + self.options:
            if ("help" in argument and argument["help"] != "" and not str.isspace(argument["help"]) and "default" in argument and argument["default"] != argparse.SUPPRESS):
                argument["right"] = argument["help"] + " " + ( "(default: '%s')" % argument["default"] if isinstance(argument["default"], str) else "(default: %s)" % str(argument["default"]) )
            elif ("help" in argument and argument["help"] != "" and not str.isspace(argument["help"])):
                argument["right"] = argument["help"]
            elif ("default" in argument and argument["default"] != argparse.SUPPRESS):
                argument["right"] = "Default: '%s'" % argument["default"] if isinstance(argument["default"], str) else "Default: %s" % str(argument["default"])
            else:
                argument["right"] = "No description available"
            lmaxlen = max(lmaxlen, len(argument["left"]))
            rmaxlen = max(rmaxlen, len(argument["right"]))

        # Determine width for left and right parts based on maximum string lengths,
        # define output template. Limit width of left part to a maximum of self.width
        # / 2. Use max() to prevent negative values. -4: two leading spaces (indent)
        # + two trailing spaces (spacing between left and right), see template
        lwidth = lmaxlen
        rwidth = max(0, self.width - lwidth - 4)
        if (lwidth > int(self.width / 2) - 4):
            lwidth = max(0, int(self.width / 2) - 4)
            rwidth = int(self.width / 2)

        # Wrap text for left and right parts, split into separate lines
        lwrapper = textwrap.TextWrapper(width=lwidth)
        rwrapper = textwrap.TextWrapper(width=rwidth)
        for argument in self.positionals + self.options:
            argument["left"] = lwrapper.wrap(argument["left"])
            argument["right"] = rwrapper.wrap(argument["right"])

        # Add positional arguments to output
        tab_spaces = 2 * ' '
        seperation_spaces_left_right = 4
        if (len(self.positionals) > 0):
            output.append("")
            output.append("Positionals:")
            for positional in self.positionals:
                for i in range(0, max(len(positional["left"]), len(positional["right"]))):
                    if (i < len(positional["left"])):
                        left = f'{tab_spaces}[{self.positional_color}]{positional["left"][i]}[/{self.positional_color}]'
                        lwidth_formated = len(tab_spaces) + lwidth + ((len(self.positional_color) + 2) * 2 + 1) 
                    else:
                        left = len(tab_spaces)
                        lwidth_formated = lwidth
                    right = positional["right"][i] if (i < len(positional["right"])) else ""
                    output.append(left.ljust(lwidth_formated + seperation_spaces_left_right) + right)

        # Add option arguments to output
        if (len(self.options) > 0):
            output.append("")
            output.append("Options:")
            for option in self.options:
                for i in range(0, max(len(option["left"]), len(option["right"]))):                    
                    if (i < len(option["left"])):
                        replacements_made = option["left"][i].count(',')
                        left = f'{tab_spaces}[{self.options_color}]{option["left"][i].replace(",", f"[/{self.options_color}],[{self.options_color}]")}[/{self.options_color}]'
                        lwidth_formated = len(tab_spaces) + lwidth + ((len(self.options_color) + 2) * 2 + 1) * (replacements_made + 1)
                    else:
                        left = ""
                        lwidth_formated = lwidth + len(tab_spaces)

                    #left = option["left"][i] if (i < len(option["right"])) else ""
                    right = option["right"][i] if (i < len(option["right"])) else ""
                    output.append(left.ljust(lwidth_formated + seperation_spaces_left_right) + right)

        # Add epilog to output if present
        if ("epilog" in self.program and self.program["epilog"] != "" and not str.isspace(self.program["epilog"])):
            output.append("")
            output.append(dewrapper.fill(self.program["epilog"]))

        # Return output as single string
        return str.join("\n", output)

    # Method redefined as format_usage() does not return a trailing newline like
    # the original does
    def print_usage(self, file=None):
        if (file == None):
            file = sys.stdout
        file.write(self.format_usage() + "\n")
        file.flush()

    # Method redefined as format_help() does not return a trailing newline like
    # the original does

    def print_help(self, file=None):
        console = Console()
        console.print(self.format_help() + "\n")

    def error(self, message):
        sys.stderr.write(self.format_usage() + "\n")
        sys.stderr.write(("Error: %s" % message) + "\n")
        sys.exit(2)
