from __future__ import annotations

import re
from dataclasses import dataclass

from markdown_it import MarkdownIt
from markdown_it.token import Token

from markdown_slides.errors import ParseError, UnsupportedContentError
from markdown_slides.models import BodyContent, ImageBlock, InlineText, Paragraph, TableBlock

MD = MarkdownIt("commonmark").enable("table")
TASK_ITEM_RE = re.compile(r"^\[[ xX]\](?:\s+|$)")
FOOTNOTE_RE = re.compile(r"\[\^[^\]\r\n]+\](?::)?")


@dataclass(slots=True)
class _Cursor:
    tokens: list[Token]
    index: int = 0


def parse_body_markdown(text: str, *, source_name: str, slide_index: int, base_line: int) -> BodyContent:
    if not text.strip():
        return BodyContent()
    tokens = MD.parse(text)
    _validate_supported_tokens(
        tokens,
        source_name=source_name,
        slide_index=slide_index,
        base_line=base_line,
    )
    cursor = _Cursor(tokens=tokens)
    content = BodyContent()
    _parse_block_sequence(cursor, content, source_name=source_name, slide_index=slide_index, base_line=base_line)
    return content


def _validate_supported_tokens(
    tokens: list[Token],
    *,
    source_name: str,
    slide_index: int,
    base_line: int,
) -> None:
    for token in tokens:
        if token.type in {"html_block", "html_inline"}:
            raise _unsupported_token_error(token, "Raw HTML is not supported.", source_name, slide_index, base_line)
        for child in token.children or []:
            if child.type == "html_inline":
                raise _unsupported_token_error(token, "Raw HTML is not supported.", source_name, slide_index, base_line)
            if child.type != "text":
                continue
            if TASK_ITEM_RE.match(child.content):
                raise _unsupported_token_error(
                    token, "Task lists are not supported.", source_name, slide_index, base_line
                )
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
) -> None:
    while cursor.index < len(cursor.tokens):
        token = cursor.tokens[cursor.index]
        if end_type and token.type == end_type:
            cursor.index += 1
            return
        if token.type == "heading_open":
            _parse_heading(cursor, content, source_name=source_name, slide_index=slide_index, base_line=base_line)
        elif token.type == "paragraph_open":
            _parse_paragraph(cursor, content, source_name=source_name, slide_index=slide_index, base_line=base_line)
        elif token.type in {"bullet_list_open", "ordered_list_open"}:
            _parse_list(cursor, content, source_name=source_name, slide_index=slide_index, base_line=base_line, level=0)
        elif token.type == "blockquote_open":
            _parse_blockquote(cursor, content, source_name=source_name, slide_index=slide_index, base_line=base_line)
        elif token.type == "fence":
            _parse_fence(token, content)
            cursor.index += 1
        elif token.type == "code_block":
            raise _unsupported_token_error(
                token, "Indented code blocks are not supported.", source_name, slide_index, base_line
            )
        elif token.type == "table_open":
            content.tables.append(
                _parse_table(cursor, source_name=source_name, slide_index=slide_index, base_line=base_line)
            )
        elif token.type in {"html_block", "html_inline"}:
            raise _unsupported_token_error(token, "Raw HTML is not supported.", source_name, slide_index, base_line)
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
    cursor: _Cursor, content: BodyContent, *, source_name: str, slide_index: int, base_line: int
) -> None:
    open_token = cursor.tokens[cursor.index]
    level = int(open_token.tag[1])
    inline = cursor.tokens[cursor.index + 1]
    if level == 1:
        raise _unsupported_token_error(
            open_token, "H1 headings are only allowed as slide boundaries.", source_name, slide_index, base_line
        )
    content.paragraphs.append(
        Paragraph(kind="heading", fragments=_parse_inline(inline.children or []), heading_level=level)
    )
    cursor.index += 3


def _parse_paragraph(
    cursor: _Cursor, content: BodyContent, *, source_name: str, slide_index: int, base_line: int
) -> None:
    inline = cursor.tokens[cursor.index + 1]
    non_space_children = [
        child for child in (inline.children or []) if not (child.type == "text" and child.content.strip() == "")
    ]
    if len(non_space_children) == 1 and non_space_children[0].type == "image":
        image = non_space_children[0]
        content.images.append(ImageBlock(src=image.attrGet("src") or "", alt=image.content or ""))
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
    content.paragraphs.append(Paragraph(kind="paragraph", fragments=_parse_inline(inline.children or [])))
    cursor.index += 3


def _parse_list(
    cursor: _Cursor,
    content: BodyContent,
    *,
    source_name: str,
    slide_index: int,
    base_line: int,
    level: int,
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
        while cursor.tokens[cursor.index].type != "list_item_close":
            item_token = cursor.tokens[cursor.index]
            if item_token.type == "paragraph_open":
                inline = cursor.tokens[cursor.index + 1]
                content.paragraphs.append(
                    Paragraph(
                        kind="list_item",
                        fragments=_parse_inline(inline.children or []),
                        level=level,
                        ordered_index=next_number if ordered else None,
                    )
                )
                cursor.index += 3
            elif item_token.type in {"bullet_list_open", "ordered_list_open"}:
                _parse_list(
                    cursor,
                    content,
                    source_name=source_name,
                    slide_index=slide_index,
                    base_line=base_line,
                    level=level + 1,
                )
            else:
                raise _token_error(
                    item_token,
                    "Only paragraphs and nested lists are supported inside list items.",
                    source_name,
                    slide_index,
                    base_line,
                )
        cursor.index += 1
        next_number += 1
    raise _token_error(open_token, "List is not closed.", source_name, slide_index, base_line)


def _parse_blockquote(
    cursor: _Cursor, content: BodyContent, *, source_name: str, slide_index: int, base_line: int
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
    )
    if nested.images or nested.tables:
        raise UnsupportedContentError(
            "Blockquotes only support text-flow content.",
            slide_index=slide_index,
            input_path=source_name,
        )
    for paragraph in nested.paragraphs:
        paragraph.kind = "blockquote"
        content.paragraphs.append(paragraph)


def _parse_fence(token: Token, content: BodyContent) -> None:
    lines = token.content.rstrip("\n").splitlines() or [""]
    for line in lines:
        content.paragraphs.append(Paragraph(kind="code", fragments=[InlineText(kind="code", text=line)]))


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


def _parse_inline(tokens: list[Token], index: int = 0, end_types: set[str] | None = None) -> list[InlineText]:
    end_types = end_types or set()
    output: list[InlineText] = []
    while index < len(tokens):
        token = tokens[index]
        if token.type in end_types:
            return output
        if token.type == "text":
            output.append(InlineText(kind="text", text=token.content))
            index += 1
        elif token.type in {"softbreak", "hardbreak"}:
            output.append(InlineText(kind="text", text=" "))
            index += 1
        elif token.type == "code_inline":
            output.append(InlineText(kind="code", text=token.content))
            index += 1
        elif token.type == "em_open":
            inner, index = _parse_inline_with_index(tokens, index + 1, {"em_close"})
            output.append(InlineText(kind="emphasis", children=inner))
        elif token.type == "strong_open":
            inner, index = _parse_inline_with_index(tokens, index + 1, {"strong_close"})
            output.append(InlineText(kind="strong", children=inner))
        elif token.type == "link_open":
            inner, index = _parse_inline_with_index(tokens, index + 1, {"link_close"})
            output.append(InlineText(kind="link", href=token.attrGet("href"), children=inner))
        else:
            index += 1
    return output


def _parse_inline_with_index(tokens: list[Token], index: int, end_types: set[str]) -> tuple[list[InlineText], int]:
    output: list[InlineText] = []
    while index < len(tokens):
        token = tokens[index]
        if token.type in end_types:
            return output, index + 1
        if token.type == "text":
            output.append(InlineText(kind="text", text=token.content))
            index += 1
        elif token.type in {"softbreak", "hardbreak"}:
            output.append(InlineText(kind="text", text=" "))
            index += 1
        elif token.type == "code_inline":
            output.append(InlineText(kind="code", text=token.content))
            index += 1
        elif token.type == "em_open":
            inner, index = _parse_inline_with_index(tokens, index + 1, {"em_close"})
            output.append(InlineText(kind="emphasis", children=inner))
        elif token.type == "strong_open":
            inner, index = _parse_inline_with_index(tokens, index + 1, {"strong_close"})
            output.append(InlineText(kind="strong", children=inner))
        elif token.type == "link_open":
            inner, index = _parse_inline_with_index(tokens, index + 1, {"link_close"})
            output.append(InlineText(kind="link", href=token.attrGet("href"), children=inner))
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
