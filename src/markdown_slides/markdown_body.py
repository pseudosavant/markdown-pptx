from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.subscript import sub_plugin
from mdit_py_plugins.superscript import superscript_plugin

from markdown_slides.errors import ParseError, UnsupportedContentError
from markdown_slides.models import BodyContent, ImageBlock, InlineText, Paragraph, TableBlock

MD = MarkdownIt("commonmark").enable(["table", "strikethrough"])
MD.use(sub_plugin)
MD.use(superscript_plugin)
TASK_ITEM_RE = re.compile(r"^\[[ xX]\](?:\s+|$)")
FOOTNOTE_RE = re.compile(r"\[\^[^\]\r\n]+\](?::)?")


class _HTMLText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden_depth:
            self.parts.append(data)


def _html_text(value: str) -> str:
    parser = _HTMLText()
    parser.feed(value)
    return "".join(parser.parts).strip()


@dataclass(slots=True)
class _Cursor:
    tokens: list[Token]
    index: int = 0


def parse_body_regions(
    text: str, *, two_content: bool, source_name: str, slide_index: int, base_line: int
) -> list[BodyContent]:
    tokens = MD.parse(text)
    _validate_supported_tokens(
        tokens,
        source_name=source_name,
        slide_index=slide_index,
        base_line=base_line,
    )
    separators = []
    for index, token in enumerate(tokens):
        if token.type != "hr":
            continue
        if not two_content or token.level != 0:
            raise _unsupported_token_error(
                token,
                "Horizontal rules require layout: Two Content and must appear at the top level of the slide body.",
                source_name,
                slide_index,
                base_line,
            )
        separators.append(index)
    if two_content and len(separators) != 1:
        token = tokens[separators[1]] if len(separators) > 1 else Token("hr", "hr", 0)
        raise _unsupported_token_error(
            token,
            "Two Content slides require exactly one top-level horizontal rule separating the two content areas.",
            source_name,
            slide_index,
            base_line,
        )
    groups = [tokens] if not separators else [tokens[: separators[0]], tokens[separators[0] + 1 :]]
    regions = []
    for group in groups:
        content = BodyContent()
        _parse_block_sequence(
            _Cursor(tokens=group), content, source_name=source_name, slide_index=slide_index, base_line=base_line
        )
        regions.append(content)
    return regions


def _validate_supported_tokens(
    tokens: list[Token],
    *,
    source_name: str,
    slide_index: int,
    base_line: int,
) -> None:
    for token in tokens:
        for child in token.children or []:
            if child.type != "text":
                continue
            if FOOTNOTE_RE.search(child.content):
                raise _unsupported_token_error(
                    token, "Footnotes are not supported.", source_name, slide_index, base_line
                )


def _parse_block_sequence(
    cursor: _Cursor,
    content: BodyContent,
    *,
    source_name: str,
    slide_index: int,
    base_line: int,
    end_type: str | None = None,
    quote_depth: int = 0,
) -> None:
    while cursor.index < len(cursor.tokens):
        token = cursor.tokens[cursor.index]
        if end_type and token.type == end_type:
            cursor.index += 1
            return
        if token.type == "heading_open":
            _parse_heading(
                cursor,
                content,
                source_name=source_name,
                slide_index=slide_index,
                base_line=base_line,
                quote_depth=quote_depth,
            )
        elif token.type == "paragraph_open":
            _parse_paragraph(
                cursor,
                content,
                source_name=source_name,
                slide_index=slide_index,
                base_line=base_line,
                quote_depth=quote_depth,
            )
        elif token.type in {"bullet_list_open", "ordered_list_open"}:
            _parse_list(
                cursor,
                content,
                source_name=source_name,
                slide_index=slide_index,
                base_line=base_line,
                level=0,
                quote_depth=quote_depth,
            )
        elif token.type == "blockquote_open":
            _parse_blockquote(
                cursor,
                content,
                source_name=source_name,
                slide_index=slide_index,
                base_line=base_line,
                quote_depth=quote_depth,
            )
        elif token.type == "fence":
            _parse_fence(token, content, quote_depth=quote_depth)
            cursor.index += 1
        elif token.type == "code_block":
            _parse_fence(token, content, quote_depth=quote_depth)
            cursor.index += 1
        elif token.type == "table_open":
            content.tables.append(
                _parse_table(cursor, source_name=source_name, slide_index=slide_index, base_line=base_line)
            )
        elif token.type in {"html_block", "html_inline"}:
            visible = _html_text(token.content)
            if visible:
                content.paragraphs.append(
                    Paragraph(
                        kind="paragraph", fragments=[InlineText(kind="text", text=visible)], quote_depth=quote_depth
                    )
                )
            cursor.index += 1
        elif token.type == "hr":
            raise _unsupported_token_error(
                token, "Horizontal rules are not supported.", source_name, slide_index, base_line
            )
        else:
            raise _unsupported_token_error(
                token, f"Unsupported markdown block '{token.type}'.", source_name, slide_index, base_line
            )
    if end_type:
        raise ParseError(
            "invalid_markdown",
            f"Expected closing token '{end_type}'.",
            slide_index=slide_index,
            input_path=source_name,
        )


def _parse_heading(
    cursor: _Cursor,
    content: BodyContent,
    *,
    source_name: str,
    slide_index: int,
    base_line: int,
    quote_depth: int = 0,
) -> None:
    open_token = cursor.tokens[cursor.index]
    level = int(open_token.tag[1])
    inline = cursor.tokens[cursor.index + 1]
    if level == 1:
        raise _unsupported_token_error(
            open_token, "H1 headings are only allowed as slide boundaries.", source_name, slide_index, base_line
        )
    content.paragraphs.append(
        Paragraph(
            kind="heading", fragments=_parse_inline(inline.children or []), heading_level=level, quote_depth=quote_depth
        )
    )
    cursor.index += 3


def _parse_paragraph(
    cursor: _Cursor,
    content: BodyContent,
    *,
    source_name: str,
    slide_index: int,
    base_line: int,
    quote_depth: int = 0,
) -> None:
    inline = cursor.tokens[cursor.index + 1]
    non_space_children = [
        child
        for child in (inline.children or [])
        if child.type != "html_inline" and not (child.type == "text" and child.content.strip() == "")
    ]
    if len(non_space_children) == 1 and non_space_children[0].type == "image":
        image = non_space_children[0]
        content.images.append(_image_block(image))
        cursor.index += 3
        return
    if len(non_space_children) == 3 and [child.type for child in non_space_children] == [
        "link_open",
        "image",
        "link_close",
    ]:
        content.images.append(_image_block(non_space_children[1], href=non_space_children[0].attrGet("href")))
        cursor.index += 3
        return
    if any(child.type == "image" for child in non_space_children):
        raise _unsupported_token_error(
            inline,
            "Images must appear as a standalone paragraph.",
            source_name,
            slide_index,
            base_line,
        )
    fragments = _parse_inline(inline.children or [])
    if fragments:
        content.paragraphs.append(
            Paragraph(kind="blockquote" if quote_depth else "paragraph", fragments=fragments, quote_depth=quote_depth)
        )
    cursor.index += 3


def _image_block(token: Token, *, href: str | None = None) -> ImageBlock:
    return ImageBlock(
        src=token.attrGet("src") or "",
        alt=_image_alt_text(token.children or []),
        title=token.attrGet("title"),
        href=href or None,
    )


def _image_alt_text(tokens: list[Token]) -> str:
    parts: list[str] = []
    for token in tokens:
        if token.type in {"text", "code_inline"}:
            parts.append(token.content)
        elif token.type in {"softbreak", "hardbreak"}:
            parts.append("\n")
        elif token.type == "image":
            parts.append(_image_alt_text(token.children or []))
    return "".join(parts)


def _parse_list(
    cursor: _Cursor,
    content: BodyContent,
    *,
    source_name: str,
    slide_index: int,
    base_line: int,
    level: int,
    quote_depth: int = 0,
) -> None:
    if level >= 3:
        raise _unsupported_token_error(
            cursor.tokens[cursor.index],
            "Nested lists deeper than 3 levels are not supported.",
            source_name,
            slide_index,
            base_line,
        )
    open_token = cursor.tokens[cursor.index]
    ordered = open_token.type == "ordered_list_open"
    next_number = int(open_token.attrGet("start") or "1")
    close_type = "ordered_list_close" if ordered else "bullet_list_close"
    cursor.index += 1
    while cursor.index < len(cursor.tokens):
        token = cursor.tokens[cursor.index]
        if token.type == close_type:
            cursor.index += 1
            return
        if token.type != "list_item_open":
            raise _token_error(
                token, f"Unexpected token '{token.type}' inside list.", source_name, slide_index, base_line
            )
        cursor.index += 1
        has_marker = False
        while cursor.index < len(cursor.tokens) and cursor.tokens[cursor.index].type != "list_item_close":
            item_token = cursor.tokens[cursor.index]
            if item_token.type == "paragraph_open":
                inline = cursor.tokens[cursor.index + 1]
                fragments = _parse_inline(inline.children or [])
                checked = _consume_task_marker(fragments) if not has_marker else None
                content.paragraphs.append(
                    Paragraph(
                        kind="list_item" if not has_marker else "list_continuation",
                        fragments=fragments,
                        level=level,
                        ordered_index=next_number if ordered else None,
                        quote_depth=quote_depth,
                        task_checked=checked,
                    )
                )
                has_marker = True
                cursor.index += 3
            else:
                if not has_marker:
                    content.paragraphs.append(
                        Paragraph(
                            kind="list_item",
                            fragments=[],
                            level=level,
                            ordered_index=next_number if ordered else None,
                            quote_depth=quote_depth,
                        )
                    )
                    has_marker = True
                if item_token.type in {"bullet_list_open", "ordered_list_open"}:
                    _parse_list(
                        cursor,
                        content,
                        source_name=source_name,
                        slide_index=slide_index,
                        base_line=base_line,
                        level=level + 1,
                        quote_depth=quote_depth,
                    )
                elif item_token.type == "blockquote_open":
                    nested = BodyContent()
                    _parse_blockquote(
                        cursor,
                        nested,
                        source_name=source_name,
                        slide_index=slide_index,
                        base_line=base_line,
                        quote_depth=quote_depth,
                    )
                    for paragraph in nested.paragraphs:
                        paragraph.level = level + 1
                    content.paragraphs.extend(nested.paragraphs)
                elif item_token.type == "heading_open":
                    nested = BodyContent()
                    _parse_heading(
                        cursor,
                        nested,
                        source_name=source_name,
                        slide_index=slide_index,
                        base_line=base_line,
                        quote_depth=quote_depth,
                    )
                    nested.paragraphs[0].level = level + 1
                    content.paragraphs.extend(nested.paragraphs)
                elif item_token.type in {"fence", "code_block"}:
                    nested = BodyContent()
                    _parse_fence(item_token, nested, quote_depth=quote_depth)
                    nested.paragraphs[0].level = level + 1
                    content.paragraphs.extend(nested.paragraphs)
                    cursor.index += 1
                else:
                    raise _unsupported_token_error(
                        item_token,
                        "This block is not supported inside a list item.",
                        source_name,
                        slide_index,
                        base_line,
                    )
        if not has_marker:
            content.paragraphs.append(
                Paragraph(
                    kind="list_item",
                    fragments=[],
                    level=level,
                    ordered_index=next_number if ordered else None,
                    quote_depth=quote_depth,
                )
            )
        if cursor.index >= len(cursor.tokens):
            raise _token_error(open_token, "List is not closed.", source_name, slide_index, base_line)
        cursor.index += 1
        next_number += 1
    raise _token_error(open_token, "List is not closed.", source_name, slide_index, base_line)


def _parse_blockquote(
    cursor: _Cursor,
    content: BodyContent,
    *,
    source_name: str,
    slide_index: int,
    base_line: int,
    quote_depth: int = 0,
) -> None:
    cursor.index += 1
    nested = BodyContent()
    _parse_block_sequence(
        cursor,
        nested,
        source_name=source_name,
        slide_index=slide_index,
        base_line=base_line,
        end_type="blockquote_close",
        quote_depth=quote_depth + 1,
    )
    if nested.images or nested.tables:
        raise UnsupportedContentError(
            "Blockquotes only support text-flow content.",
            slide_index=slide_index,
            input_path=source_name,
        )
    if not nested.paragraphs:
        nested.paragraphs.append(Paragraph(kind="blockquote", fragments=[], quote_depth=quote_depth + 1))
    content.paragraphs.extend(nested.paragraphs)


def _parse_fence(token: Token, content: BodyContent, *, quote_depth: int = 0) -> None:
    language = token.info.split(maxsplit=1)[0] if token.type == "fence" and token.info.strip() else None
    content.paragraphs.append(
        Paragraph(
            kind="code",
            fragments=[InlineText(kind="code", text=token.content.removesuffix("\n"))],
            quote_depth=quote_depth,
            code_language=language,
        )
    )


def _consume_task_marker(fragments: list[InlineText]) -> bool | None:
    if not fragments or fragments[0].kind != "text" or not fragments[0].text:
        return None
    match = TASK_ITEM_RE.match(fragments[0].text)
    if match is None:
        return None
    checked = fragments[0].text[1].lower() == "x"
    fragments[0].text = fragments[0].text[match.end() :]
    if not fragments[0].text:
        fragments.pop(0)
    return checked


def _parse_table(cursor: _Cursor, *, source_name: str, slide_index: int, base_line: int) -> TableBlock:
    cursor.index += 1
    headers: list[list[InlineText]] = []
    rows: list[list[list[InlineText]]] = []
    current_row: list[list[InlineText]] | None = None
    while cursor.index < len(cursor.tokens):
        token = cursor.tokens[cursor.index]
        if token.type == "table_close":
            cursor.index += 1
            return TableBlock(headers=headers[0] if headers else [], rows=rows)
        if token.type == "tr_open":
            current_row = []
            cursor.index += 1
            continue
        if token.type in {"th_open", "td_open"}:
            inline = cursor.tokens[cursor.index + 1]
            cell = _parse_inline(inline.children or [])
            if current_row is None:
                raise _token_error(token, "Malformed table row.", source_name, slide_index, base_line)
            current_row.append(cell)
            cursor.index += 3
            continue
        if token.type == "tr_close":
            if current_row is None:
                raise _token_error(token, "Malformed table row.", source_name, slide_index, base_line)
            if not headers:
                headers.append(current_row)
            else:
                rows.append(current_row)
            current_row = None
            cursor.index += 1
            continue
        cursor.index += 1
    raise ParseError("invalid_markdown", "Table is not closed.", slide_index=slide_index, input_path=source_name)


def parse_inline_children(tokens: list[Token]) -> list[InlineText]:
    return _parse_inline(tokens)


def _parse_inline(tokens: list[Token]) -> list[InlineText]:
    fragments, _ = _parse_inline_with_index(tokens, 0, set())
    return fragments


def _parse_inline_with_index(tokens: list[Token], index: int, end_types: set[str]) -> tuple[list[InlineText], int]:
    output: list[InlineText] = []
    while index < len(tokens):
        token = tokens[index]
        if token.type in end_types:
            return output, index + 1
        if token.type in {"text", "text_special"}:
            output.append(InlineText(kind="text", text=token.content))
            index += 1
        elif token.type == "softbreak":
            output.append(InlineText(kind="text", text=" "))
            index += 1
        elif token.type == "hardbreak":
            output.append(InlineText(kind="break"))
            index += 1
        elif token.type == "code_inline":
            output.append(InlineText(kind="code", text=token.content))
            index += 1
        elif token.type in {"em_open", "strong_open", "s_open", "sup_open", "sub_open"}:
            kind = {
                "em_open": "emphasis",
                "strong_open": "strong",
                "s_open": "strike",
                "sup_open": "superscript",
                "sub_open": "subscript",
            }[token.type]
            inner, index = _parse_inline_with_index(tokens, index + 1, {token.type.replace("_open", "_close")})
            output.append(InlineText(kind=kind, children=inner))
        elif token.type == "link_open":
            inner, index = _parse_inline_with_index(tokens, index + 1, {"link_close"})
            output.append(InlineText(kind="link", href=token.attrGet("href"), children=inner))
        elif token.type == "html_inline":
            index += 1
        else:
            index += 1
    return output, index


def _token_error(token: Token, message: str, source_name: str, slide_index: int, base_line: int) -> ParseError:
    line = base_line + token.map[0] if token.map else None
    return ParseError("invalid_markdown", message, line=line, slide_index=slide_index, input_path=source_name)


def _unsupported_token_error(
    token: Token, message: str, source_name: str, slide_index: int, base_line: int
) -> UnsupportedContentError:
    line = base_line + token.map[0] if token.map else None
    return UnsupportedContentError(message, line=line, slide_index=slide_index, input_path=source_name)
