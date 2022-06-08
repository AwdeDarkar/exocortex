"""
logformat.py
Custom logging for the CLI

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

import os
import inspect
import pprint
import logging
from pathlib import Path
from html.parser import HTMLParser
from collections import namedtuple

from typing import List

import click

from libtool.utils.formatting import ANSIFormatter


class EchoHTML(HTMLParser):
    """
    Write log messages in an HTML-like format and print with click echo.

    Supports the following tags:
      - br: newline
      - b: bold
      - i: italic
      - u: underline
      - over: overline
      - strike: strikethrough
      - blink: blink
      - fg: foreground color (see COLORS)
    """

    EchoAtom = namedtuple("EchoAtom", ["text", "style"])

    COLORS = {
        "magenta": (255, 0, 255),
        "cyan": (0, 255, 255),
        "lime": (0, 255, 0),
        "silver": (192, 192, 192),
        "gray": (128, 128, 128),
        "maroon": (128, 0, 0),
        "olive": (128, 128, 0),
        "green": (0, 128, 0),
        "navy": (0, 0, 128),
        "teal": (0, 128, 128),
    }
    """ Colors referenced in the 'color' tag; fallback to ANSI colors """

    @classmethod
    def echo(cls, text):
        """
        Echo a string in HTML format.
        """
        parser = cls()
        parser.feed(text)
        parser.do_echo()

    def __init__(self):
        super().__init__()
        self.echo_atoms: List[EchoHTML.EchoAtom] = []
        self.current_style = {}
        self.current_text = ""

        self.fg_stack = []
        self.bg_stack = []
    
    def do_echo(self):
        """ Echo all accumulated atoms """
        print(self.echo_atoms)
        for atom in self.echo_atoms:
            click.secho(atom.text, nl=False, reset=True, **atom.style)
        click.secho("", reset=True)
    
    def handle_data(self, data):
        """
        Handle data.
        """
        print(f"Got data {data}")
        self.current_text += data
        self.echo_atoms.append(EchoHTML.EchoAtom(self.current_text, self.current_style.copy()))
        self.current_text = ""
    
    def handle_starttag(self, tag, attrs):
        """
        Handle start tags.
        """
        print(f"Got start tag {tag}")
        if tag == "br":
            self.current_text += "\n"
        if tag == "b":
            self.current_style["bold"] = True
        if tag == "i":
            self.current_style["italic"] = True
        if tag == "u":
            self.current_style["underline"] = True
        if tag == "over":
            self.current_style["overline"] = True
        if tag == "strike":
            self.current_style["strikethrough"] = True
        if tag == "blink":
            self.current_style["blink"] = True
        if tag == "fg":
            color_name = attrs[0][1]
            color = self.COLORS.get(color_name, color_name)
            if "fg" in self.current_style:
                self.fg_stack.append(self.current_style[pos])
            self.current_style["fg"] = color
        if tag == "bg":
            color_name = attrs[0][1]
            color = self.COLORS.get(color_name, color_name)
            if "bg" in self.current_style:
                self.bg_stack.append(self.current_style[pos])
            self.current_style["bg"] = color

    def handle_endtag(self, tag):
        """
        Handle end tags.
        """
        print(f"Got end tag {tag}")
        if tag == "b":
            self.current_style["bold"] = False
        if tag == "i":
            self.current_style["italic"] = False
        if tag == "u":
            self.current_style["underline"] = False
        if tag == "over":
            self.current_style["overline"] = False
        if tag == "strike":
            self.current_style["strikethrough"] = False
        if tag == "blink":
            self.current_style["blink"] = False
        if tag == "fg":
            if self.fg_stack:
                color_name = self.fg_stack.pop()
                color = self.COLORS.get(color_name, color_name)
                self.current_style["fg"] = color
            else:
                del self.current_style["fg"]
        if tag == "bg":
            if self.bg_stack:
                color_name = self.bg_stack.pop()
                color = self.COLORS.get(color_name, color_name)
                self.current_style["bg"] = color
            else:
                del self.current_style["bg"]


class CustomFormatter(logging.Formatter):
    """
    Color log outputs by level.
    """

    STYLES = {
        "DEBUG": ["BLUE", ],
        "INFO": ["WHITE", ],
        "WARNING": ["MAGENTA", ],
        "ERROR": ["RED", ],
        "CRITICAL": ["RED", "BOLD", ],
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.trace = self.trace
        self.printer = pprint.PrettyPrinter(indent=2, width=self.width)

    @staticmethod
    def setup_logging():
        logger = logging.getLogger()
        logger.setLevel(logging.ERROR)

        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        ch.setFormatter(CustomFormatter())
        logger.addHandler(ch)

    @staticmethod
    def set_level(level):
        logger = logging.getLogger()
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)

    @property
    def level(self):
        logger = logging.getLogger()
        return logger.level

    @property
    def width(self):
        return self.get_width()

    @staticmethod
    def get_width():
        return os.get_terminal_size().columns

    def format_file(self, fpath):
        path = Path(fpath)
        return f"{path.parent.name}/{path.name}"

    def trace(self, obj, *args, **kwargs):
        """ Pretty-print smart tracing utility """
        if self.level > 5:
            return

        frame = inspect.getouterframes(inspect.currentframe(), 2)[1]
        cline = frame.code_context[-1]  # Get the string of the trace call line
        pre, *desc = cline.split("#")  # Find any description in a comment after
        desc = desc or None
        argstring = pre[pre.find("(")+1:pre.rfind(")")]  # Extract the outermost parentheses
        otype = type(obj)

        head = f"\u2192 {argstring} of type '{otype.__name__}'"
        loc = f"{self.format_file(frame.filename)}, line {frame.lineno}"
        head = head.ljust(self.width - len(loc) - 2)

        dump = self.printer.pformat(obj)
        full = ""\
            + ANSIFormatter.ansify_string(["BLUE", "BOLD"], head)\
            + ANSIFormatter.ansify_string(["BLUE", ], loc) + "  \n"\
            + ANSIFormatter.ansify_string(["WHITE"], dump)\
            + "\n"

        print(full)

    def format(self, record):
        if record.levelname == "INFO":
            full = record.msg
        else:
            right = f"{self.format_file(record.pathname)}, line {record.lineno}  "
            message = record.msg
            rcols = " " * (self.width - len(message) - len(right))
            full = f"{message}{rcols}{right}"
        return ANSIFormatter.ansify_string(self.STYLES[record.levelname], full)


# BUG Click >8.0 is needed for the RGB colors but cookiecutter is incompatible, pls fix
def print_columns(
        columns,
        header_rows=1,
        bold_first_col=True,
        vbars=True,
        outer_borders=True,
        header_color=(221, 232, 237),
        even_color=(189, 211, 219),
        odd_color=(145, 188, 204),
        ):
    maxlens = [max([len(s) for s in col]) for col in columns]
    width = CustomFormatter.get_width()
    if vbars:
        width -= len(columns)
    spare = width - sum(maxlens)
    margin = int(spare / len(columns))

    for i in range(len(columns[0])):
        for j in range(len(columns)):
            click.echo(
                click.style(
                    columns[j][i].ljust(maxlens[j] + margin),
                    underline=(i < header_rows),
                    bold=(i < header_rows) or (bold_first_col and j == 0),
                    fg=header_color if i < header_rows else
                      (even_color if i % 2 == 0 else odd_color),
                ),
                nl=False,
            )
            if vbars:
                click.echo(
                    click.style(
                        "|",
                        underline=(i < header_rows),
                        fg=header_color,
                    ),
                    nl=False,
                )
        click.echo()
    click.echo()


def print_table(table, **kwargs):
    columns = []
    for head, rows in table.items():
        columns.append([head, *rows])
    print_columns(columns, **kwargs)


def print_dicts(dcts, fill_missing="?", mapper={}, **kwargs):
    table = {}
    for i, dct in enumerate(dcts):
        for col_name, col_val in dct.items():
            if col_name in mapper:
                col_val = mapper[col_name].get("transform", lambda x: x)(col_val)
                col_name = mapper[col_name].get("name", col_name)
            elif mapper:
                continue
            if col_name not in table:
                table[col_name] = [*[fill_missing]*i, col_val]
            else:
                table[col_name] += [col_val]
    if table:
        print_table(table, **kwargs)