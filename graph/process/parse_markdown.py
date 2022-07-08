"""
parse_markdown.py
Parsing markdown from content sources to ASTs.

Author: Ben Croisdale

Copyright (c) 2022 Ben Croisdale. All rights reserved.
Released under the Apache 2.0 license as described in the file LICENSE.
"""

import re
from collections import namedtuple

import marko
from marko.parser import Parser
from marko.helpers import Source
from marko.block import parser, BlockElement, BlankLine
from marko.inline import InlineElement, Link
from marko.ast_renderer import ASTRenderer


class SemanticLink(Link):
    override = True
    priority = 6

    def __init__(self, match):
        super().__init__(match)
        if self.dest and "[" in self.dest and "]" in self.dest:
            s = self.dest[1:-1]

            if "|" in s:
                self.predicate, self.object = s.split("|")
            else:
                self.predicate = "ref"
                self.object = s
            
            del self.dest

class InternalLink(InlineElement):
    pattern = r"\[\[ *(.+?) *(\| *(.+?) *)?\]\]"
    parse_children = True

    def __init__(self, match):
        g1, _, g2 = match.groups()

        self.predicate = "ref"
        self.object = ""
        self.view = ""
        self.text = ""

        if g2:
            self.predicate = g1
            self._set_obj(g2)
        else:
            self._set_obj(g1)

    def _set_obj(self, s):
        if "." in s:
            self.object, self.view = s.split(".")
        else:
            self.object = s


class FormatLink(InlineElement):
    pattern = r"\{\[ *(.+) *\]\}(.*)\{\[ */\1 *\]\}"
    parse_children = True

    def __init__(self, match):
        self.object, self.text = match.groups()
        self.view = ""
        self.predicate = "format"

class LinkExtension:
    elements = [InternalLink, FormatLink, SemanticLink]


class InlineLatex(InlineElement):
    priority = 7
    pattern = r"\$(.*)\$"
    parse_children = False

    def __init__(self, match):
        self.latex = match.group(1)


class BlockLatex(InlineElement):
    """ \[ \]"""
    priority = 8
    pattern = r"\$\$([\s\S]*)\$\$"
    parse_children = False

    def __init__(self, match):
        self.latex = match.group(1)


class LatexExtension:
    elements = [InlineLatex, BlockLatex]


class DirectiveBlock(BlockElement):
    """ RST-style directives """

    priority = 9
    pattern = re.compile(
        r"\.\. ([\d\s\w]*)::([\d\s\w]*)\n",
    )
    _parse_info = (None, None)

    @classmethod
    def match(cls, source: Source):
        m = source.expect_re(cls.pattern)
        if not m:
            return False
        cls._parse_info = (
            m.group(1).strip() or "anon",
            m.group(2).strip() or None,
        )
        return m is not None
    
    @classmethod
    def parse(cls, source: Source):
        state = cls()
        state.children = []
        state.directive_type, state.directive = cls._parse_info
        cls._parse_info = (None, None)
        options_done = False
        source.consume()
        source.anchor()
        with source.under_state(state):
            while not source.exhausted:
                if not options_done and DirectiveOption.match(source):
                    elm = DirectiveOption.parse(source)
                    state.children.append(elm)
                    source.anchor()
                elif BlankLine.match(source):
                    BlankLine.parse(source)
                elif DirectiveContent.match(source):
                    options_done = True
                    elm = DirectiveContent.parse(source)
                    state.children.append(elm)
                    source.anchor()
                else:
                    source.reset()  # Why?
                    break
        return state


class DirectiveOption(BlockElement):
    pattern = re.compile(r" {3}:([\w\d\-]+): *([ \w\d]*)")
    _parse_info = (None, None)
    
    @classmethod
    def match(cls, source: Source):
        m = source.expect_re(cls.pattern)
        if not m:
            return False
        
        parent = source.state
        assert isinstance(parent, DirectiveBlock)
        cls._parse_info = (
            m.group(1).strip(),
            m.group(2).strip() or None,
        )
        return m is not None
    
    @classmethod
    def parse(cls, source: Source):
        state = cls()
        state.option, state.value = cls._parse_info
        cls._parse_info = None, None
        source.consume()
        source.anchor()
        source.next_line()
        return state


class DirectiveContent(BlockElement):
    _prefix = r" {3}"

    @classmethod
    def match(cls, source: Source):
        m = source.expect_re(cls._prefix)
        if not m:
            return False
        
        parent = source.state
        assert isinstance(parent, DirectiveBlock)
        return m is not None
    
    @classmethod
    def parse(cls, source: Source):
        state = cls()
        state.content = ""
        source.consume()
        source.anchor()
        while not source.exhausted:
            line = source.next_line()
            if line is not None and not line.strip():
                source.consume()
                stripped_line = line.strip()
                if stripped_line:
                    state.content += line
                else:
                    state.content += "\n"
            elif cls.match(source):
                state.content += line + "\n"
                source.consume()
                source.anchor()
            else:
                source.reset()
                break
        return state

class DirectiveExtension:
    elements: [DirectiveBlock, DirectiveOption, DirectiveContent]


### TESTING / DEBUG CODE (delete when done) ###
from pathlib import Path

content_dir = Path("test-content")
content_map = {}
Content = namedtuple("Content", ["raw", "ast", "json"])

for path in content_dir.glob("*.md"):
    with path.open("r") as f:
        content_map[path.stem] = {"raw": f.read()}

renderer = marko.Markdown(
    extensions=[
        LinkExtension,
        DirectiveExtension,
        LatexExtension,
    ],
    renderer=ASTRenderer, 
)
renderer._setup_extensions()
renderer.parser.block_elements["DirectiveBlock"] = DirectiveBlock  # BUG: This shouldn't be needed...
ast_map = {}

for name in content_map.keys():
    item = content_map[name]
    item["ast"] = renderer.parse(item["raw"])
    ast_map[name] = item["ast"]
    item["json"] = renderer.render(item["ast"])
    globals()[name] = Content(**item)