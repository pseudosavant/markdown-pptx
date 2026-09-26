from __future__ import annotations

import io
import re
import shutil
import tempfile
import warnings
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx
from PIL import Image as PILImage
from PIL import UnidentifiedImageError
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.enum.shapes import PP_PLACEHOLDER
from pptx.enum.text import MSO_AUTO_SIZE, MSO_NUMBERED_BULLET_STYLE, MSO_TEXT_STRIKE_TYPE
from pptx.util import BulletStyle, Emu, Inches, Pt
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.styles import get_style_by_name
from pygments.util import ClassNotFound

from markdown_slides.assets import default_template_path
from markdown_slides.errors import AssetError, MarkdownSlidesError, RenderError, TemplateError
from markdown_slides.models import (
    Background,
    BodyContent,
    Deck,
    ImageBlock,
    InlineText,
    Paragraph,
    Slide,
    TableBlock,
    TableOptions,
    normalize_layout_name,
)

TITLE_PLACEHOLDERS = {PP_PLACEHOLDER.TITLE, PP_PLACEHOLDER.CENTER_TITLE}
SUBTITLE_PLACEHOLDERS = {PP_PLACEHOLDER.SUBTITLE, PP_PLACEHOLDER.BODY}
BODY_PLACEHOLDERS = {PP_PLACEHOLDER.BODY, PP_PLACEHOLDER.OBJECT}
TABLE_STYLE_MEDIUM_1_ACCENT_1 = "{B301B821-A1FF-4177-AEE7-76D212191A09}"
HEADING_SCALE = {2: 1.33, 3: 1.2, 4: 1.1, 5: 1.05, 6: 1.0}
DEFAULT_BODY_LINE_SPACING = 1.0
DEFAULT_BODY_SPACE_BEFORE_PT = 12
DEFAULT_BODY_SPACE_AFTER_PT = 6
MAX_REMOTE_IMAGE_BYTES = 25 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000
CODE_STYLE = get_style_by_name("default")
THEME_COLOR_VAR_RE = re.compile(r"^var\(\s*--(?P<name>[a-z0-9-]+)\s*\)$", re.IGNORECASE)
THEME_COLOR_SCHEME_MAP = {
    "dark-1": MSO_THEME_COLOR.DARK_1,
    "light-1": MSO_THEME_COLOR.LIGHT_1,
    "dark-2": MSO_THEME_COLOR.DARK_2,
    "light-2": MSO_THEME_COLOR.LIGHT_2,
    "accent-1": MSO_THEME_COLOR.ACCENT_1,
    "accent-2": MSO_THEME_COLOR.ACCENT_2,
    "accent-3": MSO_THEME_COLOR.ACCENT_3,
    "accent-4": MSO_THEME_COLOR.ACCENT_4,
    "accent-5": MSO_THEME_COLOR.ACCENT_5,
    "accent-6": MSO_THEME_COLOR.ACCENT_6,
    "hyperlink": MSO_THEME_COLOR.HYPERLINK,
    "followed-hyperlink": MSO_THEME_COLOR.FOLLOWED_HYPERLINK,
}

LAYOUT_PLACEHOLDER_REQUIREMENTS = {
    "Title Slide": ((TITLE_PLACEHOLDERS, "title"), (SUBTITLE_PLACEHOLDERS, "subtitle")),
    "Title and Content": ((TITLE_PLACEHOLDERS, "title"), (BODY_PLACEHOLDERS, "body")),
    "Two Content": ((TITLE_PLACEHOLDERS, "title"),),
    "Section Header": ((TITLE_PLACEHOLDERS, "title"), (SUBTITLE_PLACEHOLDERS, "subtitle")),
    "Title Only": ((TITLE_PLACEHOLDERS, "title"),),
    "Blank": (),
}


@dataclass(frozen=True, slots=True)
class MasterCatalogEntry:
    index: int
    master: object
    name: str | None
    theme_name: str | None
    display_name: str


def render_pptx(
    deck: Deck,
    *,
    output_path: Path,
    template_path: Path | None,
    force: bool,
    base_dir: Path,
    downloader: Downloader | None = None,
    allow_remote_images: bool = True,
    master: int | str | None = None,
    report: dict[str, object] | None = None,
) -> Path:
    if output_path.exists():
        if not output_path.is_file():
            raise RenderError("output_not_file", f"Output path is not a file: {output_path}")
        if not force:
            raise RenderError("output_exists", f"Output file already exists: {output_path}")
    template = template_path or default_template_path()
    preserve_template_paragraph_formatting = template_path is not None
    presentation = _load_presentation(template)
    presentation.slides.clear()
    master_catalog = _build_master_catalog(presentation)
    default_master = _resolve_master(master_catalog, master, context="The --master selection")
    _apply_aspect_ratio(presentation, deck.aspect_ratio)
    template_defaults = {entry.index: _read_template_defaults(entry.master) for entry in master_catalog}
    _apply_themes(master_catalog, deck)
    owns_downloader = downloader is None
    downloader = downloader or Downloader(enabled=allow_remote_images)
    original_downloader_enabled = downloader.enabled
    if not allow_remote_images:
        downloader.enabled = False
    try:
        if deck.background is not None:
            for entry in master_catalog:
                _apply_master_background(entry.master, deck.background, base_dir=base_dir, downloader=downloader)
        layout_groups = {entry.index: _layout_groups(entry.master) for entry in master_catalog}
        masters_used: set[int] = set()

        for slide_spec in deck.slides:
            selected_master = (
                default_master
                if slide_spec.master is None
                else _resolve_master(master_catalog, slide_spec.master, context=f"Slide {slide_spec.index} master")
            )
            masters_used.add(selected_master.index)
            matches = layout_groups[selected_master.index].get(normalize_layout_name(slide_spec.layout).casefold(), [])
            if not matches:
                raise TemplateError(
                    "missing_layout",
                    f"{_master_label(selected_master)} does not contain layout '{slide_spec.layout}'.",
                )
            if len(matches) > 1:
                raise TemplateError(
                    "ambiguous_layout",
                    f"{_master_label(selected_master)} contains more than one layout named '{slide_spec.layout}'.",
                )
            slide = presentation.slides.add_slide(matches[0])
            _apply_hide_background_graphics(slide, slide_spec)
            if slide_spec.background is not None:
                _apply_background(
                    slide,
                    slide_spec.background,
                    slide_width=presentation.slide_width,
                    slide_height=presentation.slide_height,
                    base_dir=base_dir,
                    downloader=downloader,
                )
            _render_title(slide, slide_spec, deck, template_defaults=template_defaults[selected_master.index])
            _render_body(
                slide,
                slide_spec,
                deck,
                template_defaults=template_defaults[selected_master.index],
                preserve_template_paragraph_formatting=preserve_template_paragraph_formatting,
                base_dir=base_dir,
                downloader=downloader,
            )
            _render_notes(slide, slide_spec)
        if report is not None:
            report.update(
                {
                    "default_master": _master_detail(default_master, master_catalog),
                    "retained_master_count": len(master_catalog),
                    "masters_used": [
                        _master_detail(entry, master_catalog) for entry in master_catalog if entry.index in masters_used
                    ],
                }
            )
    finally:
        if owns_downloader:
            downloader.close()
        else:
            downloader.enabled = original_downloader_enabled

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RenderError(
            "output_directory_error", f"Could not create output directory '{output_path.parent}': {exc}"
        ) from exc
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pptx") as temp_file:
        temp_path = Path(temp_file.name)
    try:
        try:
            presentation.save(str(temp_path))
            shutil.move(str(temp_path), str(output_path))
        except MarkdownSlidesError:
            raise
        except (OSError, ValueError) as exc:
            raise RenderError(
                "output_write_error", f"Could not write PowerPoint output '{output_path}': {exc}"
            ) from exc
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
    return output_path


class Downloader:
    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        enabled: bool = True,
        max_bytes: int = MAX_REMOTE_IMAGE_BYTES,
    ) -> None:
        self.enabled = enabled
        self.max_bytes = max_bytes
        self._client = client or httpx.Client(follow_redirects=True, timeout=30.0)
        self._owns_client = client is None
        self._cache: dict[str, bytes] = {}

    def fetch(self, url: str) -> bytes:
        display_url = _display_remote_url(url)
        if not self.enabled:
            raise AssetError("remote_images_disabled", f"Remote images are disabled: {display_url}")
        if url in self._cache:
            return self._cache[url]
        try:
            with self._client.stream("GET", url) as response:
                response.raise_for_status()
                content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                if content_type and not content_type.startswith("image/"):
                    raise AssetError(
                        "invalid_remote_image_type",
                        f"Remote asset is not an image ({content_type}): {display_url}",
                    )
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > self.max_bytes:
                    raise AssetError("remote_image_too_large", f"Remote image exceeds the 25 MiB limit: {display_url}")
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > self.max_bytes:
                        raise AssetError(
                            "remote_image_too_large", f"Remote image exceeds the 25 MiB limit: {display_url}"
                        )
                    chunks.append(chunk)
        except AssetError:
            raise
        except httpx.HTTPStatusError as exc:
            raise AssetError(
                "image_download_failed",
                f"Remote image request returned HTTP {exc.response.status_code}: {display_url}",
            ) from exc
        except httpx.HTTPError as exc:
            raise AssetError(
                "image_download_failed",
                f"Failed to download remote image '{display_url}' ({type(exc).__name__}).",
            ) from exc
        except ValueError as exc:
            raise AssetError(
                "invalid_remote_image_response",
                f"Remote image response metadata is invalid: {display_url}",
            ) from exc
        content = b"".join(chunks)
        self._cache[url] = content
        return content

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


def list_layouts(template_path: Path | None = None, *, master: int | str | None = None) -> list[str]:
    details = list_layout_details(template_path, master=master)
    return [layout["name"] for layout in details["layouts"]]


def list_master_details(template_path: Path | None = None) -> list[dict[str, object]]:
    presentation = _load_presentation(template_path or default_template_path())
    catalog = _build_master_catalog(presentation)
    return [_master_detail(entry, catalog) for entry in catalog]


def list_layout_details(
    template_path: Path | None = None,
    *,
    master: int | str | None = None,
) -> dict[str, object]:
    presentation = _load_presentation(template_path or default_template_path())
    catalog = _build_master_catalog(presentation)
    selected = _resolve_master(catalog, master, context="The --master selection")
    layouts = _layout_details(selected.master)
    return {
        "master": _master_detail(selected, catalog),
        "layouts": layouts,
    }


def _layout_groups(master: object) -> dict[str, list[object]]:
    groups: dict[str, list[object]] = {}
    for layout in master.slide_layouts:
        key = normalize_layout_name(layout.name).casefold()
        groups.setdefault(key, []).append(layout)
    return groups


def _layout_details(master: object) -> list[dict[str, object]]:
    groups = _layout_groups(master)
    layouts = []
    for layout in master.slide_layouts:
        compatible, reason = _layout_compatibility(layout)
        if len(groups[normalize_layout_name(layout.name).casefold()]) > 1:
            compatible = False
            reason = "layout name is duplicated on this master"
        placeholders = [
            {
                "index": placeholder.placeholder_format.idx,
                "type": placeholder.placeholder_format.type.name.lower(),
            }
            for placeholder in layout.placeholders
        ]
        detail: dict[str, object] = {
            "name": layout.name,
            "compatible": compatible,
            "placeholders": placeholders,
        }
        if reason:
            detail["reason"] = reason
        layouts.append(detail)
    return layouts


def _load_presentation(template_path: Path) -> Presentation:
    if not template_path.is_file():
        raise TemplateError("template_not_found", f"Template file does not exist: {template_path}")
    try:
        return Presentation(str(template_path))
    except Exception as exc:
        raise TemplateError(
            "invalid_template",
            f"Could not open template '{template_path}' as a PowerPoint presentation ({type(exc).__name__}).",
        ) from exc


def _build_master_catalog(presentation: Presentation) -> list[MasterCatalogEntry]:
    if len(presentation.slide_masters) == 0:
        raise TemplateError("missing_master", "Template does not contain a slide master.")
    catalog: list[MasterCatalogEntry] = []
    for index, slide_master in enumerate(presentation.slide_masters, start=1):
        theme_name = _master_theme_name(slide_master, index=index)
        name = slide_master.name.strip() or None
        catalog.append(
            MasterCatalogEntry(
                index=index,
                master=slide_master,
                name=name,
                theme_name=theme_name,
                display_name=name or theme_name or f"Master {index}",
            )
        )
    return catalog


def _master_theme_name(master: object, *, index: int) -> str | None:
    try:
        return master.theme.name.strip() or None
    except KeyError as exc:
        raise TemplateError("missing_theme", f"Master {index} does not reference a theme.") from exc
    except ValueError as exc:
        raise TemplateError("invalid_theme", f"Master {index} references an invalid theme.") from exc


def _resolve_master(
    catalog: list[MasterCatalogEntry],
    selector: int | str | None,
    *,
    context: str,
) -> MasterCatalogEntry:
    if selector is None:
        return catalog[0]
    if isinstance(selector, bool):
        raise TemplateError(
            "invalid_master_selector",
            f"{context} must be a positive 1-based index or an exact unique master/theme name.",
        )
    if isinstance(selector, int):
        index = selector
    elif isinstance(selector, str):
        normalized = selector.strip()
        if not normalized:
            raise TemplateError("invalid_master_selector", f"{context} cannot be empty.")
        if normalized.isdecimal():
            index = int(normalized)
        else:
            matches = [
                entry
                for entry in catalog
                if normalized.casefold()
                in {candidate.casefold() for candidate in (entry.name, entry.theme_name) if candidate is not None}
            ]
            if not matches:
                raise TemplateError(
                    "master_not_found",
                    f"{context} '{selector}' does not match a slide-master or theme name in the template.",
                )
            if len(matches) > 1:
                indices = ", ".join(str(entry.index) for entry in matches)
                raise TemplateError(
                    "ambiguous_master",
                    f"{context} '{selector}' matches multiple masters ({indices}); use a 1-based index.",
                )
            return matches[0]
    else:
        raise TemplateError(
            "invalid_master_selector",
            f"{context} must be a positive 1-based index or an exact unique master/theme name.",
        )
    if index < 1 or index > len(catalog):
        raise TemplateError(
            "master_not_found",
            f"{context} index {index} is outside the available range 1-{len(catalog)}.",
        )
    return catalog[index - 1]


def _master_detail(entry: MasterCatalogEntry, catalog: list[MasterCatalogEntry]) -> dict[str, object]:
    selectable_names = []
    for candidate in (entry.name, entry.theme_name):
        if candidate is None or candidate in selectable_names:
            continue
        matches = [
            item
            for item in catalog
            if candidate.casefold() in {value.casefold() for value in (item.name, item.theme_name) if value is not None}
        ]
        if len(matches) == 1:
            selectable_names.append(candidate)
    layout_details = _layout_details(entry.master)
    return {
        "index": entry.index,
        "name": entry.name,
        "theme_name": entry.theme_name,
        "display_name": entry.display_name,
        "selectable_names": selectable_names,
        "layout_count": len(layout_details),
        "compatible_layout_count": sum(bool(layout["compatible"]) for layout in layout_details),
        "embedded_master_count": len(catalog),
    }


def _master_label(entry: MasterCatalogEntry) -> str:
    return f"Master {entry.index} ('{entry.display_name}')"


def _layout_compatibility(layout) -> tuple[bool, str | None]:
    normalized = normalize_layout_name(layout.name)
    requirements = LAYOUT_PLACEHOLDER_REQUIREMENTS.get(normalized)
    if requirements is None:
        return False, "layout name is not supported by markdown-pptx"
    for allowed_types, kind in requirements:
        count = sum(placeholder.placeholder_format.type in allowed_types for placeholder in layout.placeholders)
        if count == 0:
            return False, f"missing required {kind} placeholder"
        if count > 1:
            return False, f"contains multiple matching {kind} placeholders"
    if normalized == "Two Content":
        try:
            _two_content_placeholders(layout)
        except TemplateError as exc:
            return False, exc.context.message
    return True, None


def _display_remote_url(url: str) -> str:
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname or "remote host"
        netloc = hostname if parsed.port is None else f"{hostname}:{parsed.port}"
        return urlunsplit((parsed.scheme, netloc, "", "", ""))
    except ValueError:
        return "remote image URL"


def _apply_aspect_ratio(presentation: Presentation, aspect_ratio: str) -> None:
    if aspect_ratio == "16:9":
        presentation.slide_width = Emu(12192000)
        presentation.slide_height = Emu(6858000)
    else:
        presentation.slide_width = Emu(9144000)
        presentation.slide_height = Emu(6858000)


def _render_title(slide, slide_spec: Slide, deck: Deck, *, template_defaults: dict[str, float]) -> None:
    if slide_spec.layout == "Blank":
        return
    title_shape = _require_placeholder(slide, TITLE_PLACEHOLDERS, "title")
    text_frame = title_shape.text_frame
    text_frame.clear()
    text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    paragraph = text_frame.paragraphs[0]
    title_color = _resolve_text_color(deck, slide_spec, "title")
    if title_color is not None:
        _set_paragraph_default_color(paragraph, title_color)
    title_model = Paragraph(kind="title", fragments=slide_spec.title_fragments)
    for fragment in slide_spec.title_fragments or [InlineText(kind="text", text="")]:
        _add_fragment_runs(
            paragraph,
            fragment,
            deck,
            title_model,
            template_defaults=template_defaults,
            text_color=title_color,
        )
    if not paragraph.runs:
        paragraph.add_run().text = ""


def _render_body(
    slide,
    slide_spec: Slide,
    deck: Deck,
    *,
    template_defaults: dict[str, float],
    preserve_template_paragraph_formatting: bool,
    base_dir: Path,
    downloader: Downloader,
) -> None:
    body = slide_spec.body
    body_color = _resolve_text_color(deck, slide_spec, "body")
    if body_color is None and slide_spec.layout in {"Title Slide", "Section Header"}:
        body_color = "var(--dark-1)"
    if slide_spec.layout == "Two Content":
        placeholders = _two_content_placeholders(slide)
        for placeholder, region in zip(placeholders, slide_spec.content_regions, strict=True):
            _render_content_area(
                slide,
                placeholder,
                region,
                slide_spec,
                deck,
                template_defaults=template_defaults,
                text_color=body_color,
                preserve_template_paragraph_formatting=preserve_template_paragraph_formatting,
                base_dir=base_dir,
                downloader=downloader,
            )
        return
    if slide_spec.layout in {"Blank", "Title Only"} or body.is_empty:
        return
    if slide_spec.layout in {"Title Slide", "Section Header"}:
        placeholder = _require_placeholder(slide, SUBTITLE_PLACEHOLDERS, "subtitle")
        _render_text_flow(
            placeholder,
            body,
            deck,
            template_defaults=template_defaults,
            text_color=body_color,
            preserve_template_paragraph_formatting=preserve_template_paragraph_formatting,
        )
        return
    if slide_spec.layout != "Title and Content":
        raise TemplateError("unsupported_layout", f"Layout '{slide_spec.layout}' is not renderable.")
    placeholder = _require_placeholder(slide, BODY_PLACEHOLDERS, "body")
    _render_content_area(
        slide,
        placeholder,
        body,
        slide_spec,
        deck,
        template_defaults=template_defaults,
        text_color=body_color,
        preserve_template_paragraph_formatting=preserve_template_paragraph_formatting,
        base_dir=base_dir,
        downloader=downloader,
    )


def _render_content_area(
    slide,
    placeholder,
    body: BodyContent,
    slide_spec: Slide,
    deck: Deck,
    *,
    template_defaults: dict[str, float],
    text_color: str | None,
    preserve_template_paragraph_formatting: bool,
    base_dir: Path,
    downloader: Downloader,
) -> None:
    placeholder.text_frame.clear()
    if body.paragraphs:
        _render_text_flow(
            placeholder,
            body,
            deck,
            template_defaults=template_defaults,
            text_color=text_color,
            preserve_template_paragraph_formatting=preserve_template_paragraph_formatting,
        )
        return
    if body.images:
        _render_image(
            slide,
            placeholder,
            body.images[0],
            base_dir=base_dir,
            downloader=downloader,
            contain=True,
            name="MarkdownSlidesImage",
        )
        return
    if body.tables:
        _render_table(slide, placeholder, body.tables[0], slide_spec.table_options, deck)
        return


def _render_text_flow(
    placeholder,
    body: BodyContent,
    deck: Deck,
    *,
    template_defaults: dict[str, float],
    text_color: str | None,
    preserve_template_paragraph_formatting: bool,
) -> None:
    text_frame = placeholder.text_frame
    text_frame.clear()
    text_frame.word_wrap = True
    text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    paragraphs = body.paragraphs
    for index, paragraph_model in enumerate(paragraphs):
        paragraph = text_frame.paragraphs[0] if index == 0 else text_frame.add_paragraph()
        paragraph.clear()
        _configure_paragraph_bullets(paragraph, paragraph_model)
        if paragraph_model.kind == "list_continuation":
            left, _ = _list_paragraph_indent(paragraph_model)
            _set_paragraph_indent(
                paragraph,
                left=left,
                hanging=0,
            )
        elif paragraph_model.quote_depth and paragraph_model.kind != "list_item":
            _set_paragraph_indent(
                paragraph,
                left=0.3 * paragraph_model.quote_depth + 0.3 * paragraph_model.level,
                hanging=0,
            )
        _apply_paragraph_spacing(
            paragraph, paragraph_model, preserve_template_paragraph_formatting=preserve_template_paragraph_formatting
        )
        if text_color is not None and not paragraph_model.quote_depth:
            _set_paragraph_default_color(paragraph, text_color)
        if paragraph_model.quote_depth:
            paragraph.space_before = Pt(6)
            paragraph.space_after = Pt(6)
        if paragraph_model.kind == "code":
            _render_code(paragraph, paragraph_model, deck, template_defaults=template_defaults, text_color=text_color)
            continue
        if paragraph_model.task_checked is not None:
            marker = "☑ " if paragraph_model.task_checked else "☐ "
            _add_fragment_runs(
                paragraph,
                InlineText(kind="text", text=marker),
                deck,
                paragraph_model,
                template_defaults=template_defaults,
                text_color=text_color,
            )
        fragments = paragraph_model.fragments or [InlineText(kind="text", text="")]
        for fragment in fragments:
            _add_fragment_runs(
                paragraph, fragment, deck, paragraph_model, template_defaults=template_defaults, text_color=text_color
            )
        if not paragraph.runs:
            run = paragraph.add_run()
            run.text = ""


def _add_fragment_runs(
    paragraph,
    fragment: InlineText,
    deck: Deck,
    paragraph_model,
    *,
    template_defaults: dict[str, float],
    text_color: str | None,
    styles: frozenset[str] = frozenset(),
    href: str | None = None,
) -> None:
    if fragment.kind == "break":
        paragraph.add_line_break()
        return
    if fragment.children:
        child_styles = styles | {fragment.kind}
        child_href = fragment.href if fragment.kind == "link" else href
        for child in fragment.children:
            _add_fragment_runs(
                paragraph,
                child,
                deck,
                paragraph_model,
                template_defaults=template_defaults,
                text_color=text_color,
                styles=frozenset(child_styles),
                href=child_href,
            )
        return
    if not fragment.text:
        return
    run = paragraph.add_run()
    run.text = fragment.text
    if href:
        run.hyperlink.address = href
    _apply_run_font(
        run,
        deck,
        paragraph_model,
        styles | {fragment.kind},
        template_defaults=template_defaults,
        text_color=text_color,
    )


def _apply_run_font(
    run,
    deck: Deck,
    paragraph_model,
    styles: frozenset[str] | set[str],
    *,
    template_defaults: dict[str, float],
    text_color: str | None,
) -> None:
    if paragraph_model.kind == "heading":
        _set_theme_font(run, major=True)
        base_size = template_defaults["body_font_pt"]
        scale = HEADING_SCALE.get(paragraph_model.heading_level or 6, 1.0)
        run.font.size = Pt(round(base_size * scale))
    elif paragraph_model.kind == "code" or "code" in styles:
        run.font.name = "Consolas"
    elif paragraph_model.kind != "title":
        _set_theme_font(run, major=False)
    if paragraph_model.kind == "heading" or "strong" in styles:
        run.font.bold = True
    elif paragraph_model.kind != "title":
        run.font.bold = False
    if paragraph_model.quote_depth or "emphasis" in styles:
        run.font.italic = True
    elif paragraph_model.kind != "title":
        run.font.italic = False
    if paragraph_model.quote_depth:
        _set_run_color(run, "var(--accent-1)")
    if "strike" in styles:
        run.font.strike = MSO_TEXT_STRIKE_TYPE.SINGLE
    if "superscript" in styles or "subscript" in styles:
        run.font.baseline = 0.3 if "superscript" in styles else -0.25
        if paragraph_model.kind == "title":
            base_size = template_defaults["title_font_pt"]
        elif paragraph_model.kind == "heading":
            base_size = template_defaults["body_font_pt"] * HEADING_SCALE.get(paragraph_model.heading_level or 6, 1.0)
        else:
            base_size = template_defaults["body_font_pt"]
        run.font.size = Pt(round(base_size * 0.7))
    if text_color is not None and not paragraph_model.quote_depth:
        _set_run_color(run, text_color)


def _render_code(
    paragraph, model: Paragraph, deck: Deck, *, template_defaults: dict[str, float], text_color: str | None
) -> None:
    code = model.fragments[0].text or "" if model.fragments else ""
    lexer = None
    if model.code_language:
        try:
            lexer = get_lexer_by_name(model.code_language, stripnl=False, ensurenl=False, tabsize=0)
        except ClassNotFound:
            pass
    tokens = list(lex(code, lexer)) if lexer is not None else []
    if not tokens or "".join(value for _, value in tokens) != code:
        _add_code_segment(
            paragraph,
            code,
            deck,
            model,
            template_defaults=template_defaults,
            text_color=text_color,
        )
        return
    for kind, value in tokens:
        if not value:
            continue
        style = CODE_STYLE.style_for_token(kind) if not value.isspace() else None
        _add_code_segment(
            paragraph,
            value,
            deck,
            model,
            template_defaults=template_defaults,
            text_color=text_color,
            highlight=style,
        )


def _add_code_segment(
    paragraph,
    value: str,
    deck: Deck,
    model: Paragraph,
    *,
    template_defaults: dict[str, float],
    text_color: str | None,
    highlight: dict | None = None,
) -> None:
    for index, part in enumerate(value.split("\n")):
        if index:
            paragraph.add_line_break()
        if not part:
            continue
        run = paragraph.add_run()
        run.text = part
        _apply_run_font(run, deck, model, {"code"}, template_defaults=template_defaults, text_color=text_color)
        if highlight:
            if highlight["color"]:
                run.font.color.rgb = RGBColor.from_string(highlight["color"])
            if highlight["bold"]:
                run.font.bold = True
            if highlight["italic"]:
                run.font.italic = True
            if highlight["underline"]:
                run.font.underline = True


def _resolve_text_color(deck: Deck, slide_spec: Slide, kind: str) -> str | None:
    if slide_spec.text_colors is not None:
        value = getattr(slide_spec.text_colors, kind)
        if value is not None:
            return value
    if deck.text_colors is not None:
        return getattr(deck.text_colors, kind)
    return None


def _set_run_color(run, color_value: str) -> None:
    _set_font_color(run.font, color_value)


def _set_paragraph_default_color(paragraph, color_value: str) -> None:
    _set_font_color(paragraph.font, color_value)
    _set_font_color(paragraph.end_font, color_value)


def _set_font_color(font, color_value: str) -> None:
    font.fill.background()
    font.fill.solid()
    _set_color(font.color, color_value)


def _set_color(color, color_value: str) -> None:
    value = _color_value(color_value)
    if isinstance(value, RGBColor):
        color.rgb = value
    else:
        color.theme_color = value


def _color_value(color_value: str):
    match = THEME_COLOR_VAR_RE.match(color_value.strip())
    if match is not None:
        return THEME_COLOR_SCHEME_MAP[match.group("name").lower()]
    return RGBColor.from_string(color_value[1:])


def _apply_paragraph_spacing(paragraph, paragraph_model, *, preserve_template_paragraph_formatting: bool) -> None:
    if preserve_template_paragraph_formatting:
        return
    if paragraph_model.kind != "paragraph":
        return
    paragraph.line_spacing = DEFAULT_BODY_LINE_SPACING
    paragraph.space_before = Pt(DEFAULT_BODY_SPACE_BEFORE_PT)
    paragraph.space_after = Pt(DEFAULT_BODY_SPACE_AFTER_PT)


def _render_table(slide, placeholder, table: TableBlock, options: TableOptions, deck: Deck) -> None:
    rows = 1 + len(table.rows)
    cols = len(table.headers)
    if cols == 0:
        raise RenderError("invalid_table", "Tables must contain at least one header cell.")
    shape = slide.shapes.add_table(rows, cols, placeholder.left, placeholder.top, placeholder.width, placeholder.height)
    shape.name = "MarkdownSlidesTable"
    table_shape = shape.table
    table_shape.style_id = TABLE_STYLE_MEDIUM_1_ACCENT_1
    table_shape.first_row = options.header_row
    table_shape.last_row = options.total_row
    table_shape.first_col = options.first_column
    table_shape.last_col = options.last_column
    table_shape.horz_banding = options.banded_rows
    table_shape.vert_banding = options.banded_columns
    for column_index, cell in enumerate(table.headers):
        table_shape.cell(0, column_index).text = _flatten_inline(cell)
    for row_index, row in enumerate(table.rows, start=1):
        for column_index, cell in enumerate(row):
            table_shape.cell(row_index, column_index).text = _flatten_inline(cell)
    for row in table_shape.rows:
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                for run in paragraph.runs:
                    _set_theme_font(run, major=False)


def _render_image(
    slide, placeholder, image: ImageBlock, *, base_dir: Path, downloader: Downloader, contain: bool, name: str
) -> None:
    image_source = _resolve_image_source(image.src, base_dir=base_dir, downloader=downloader)
    left, top, width, height = _fit_image(
        image_source, placeholder.left, placeholder.top, placeholder.width, placeholder.height, contain=contain
    )
    picture = slide.shapes.add_picture(image_source, left, top, width, height)
    picture.name = name
    picture.alt_text = image.alt
    picture.alt_text_title = image.title
    if image.href:
        picture.click_action.hyperlink.address = image.href


def _resolve_image_source(src: str, *, base_dir: Path, downloader: Downloader):
    if src.startswith(("http://", "https://")):
        if not getattr(downloader, "enabled", True):
            raise AssetError("remote_images_disabled", f"Remote images are disabled: {_display_remote_url(src)}")
        try:
            return io.BytesIO(downloader.fetch(src))
        except AssetError:
            raise
        except Exception as exc:
            display_url = _display_remote_url(src)
            raise AssetError(
                "image_download_failed",
                f"Failed to download remote image '{display_url}' ({type(exc).__name__}).",
            ) from exc
    path = (base_dir / src).resolve()
    if not path.is_file():
        raise AssetError("missing_asset", f"Image asset does not exist: {path}")
    return str(path)


def _fit_image(
    image_source, left: int, top: int, width: int, height: int, *, contain: bool
) -> tuple[int, int, int, int]:
    try:
        if isinstance(image_source, io.BytesIO):
            image_source.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", PILImage.DecompressionBombWarning)
            with PILImage.open(image_source) as image:
                image_width, image_height = image.size
                if image_width * image_height > MAX_IMAGE_PIXELS:
                    raise AssetError(
                        "image_dimensions_too_large",
                        f"Image exceeds the {MAX_IMAGE_PIXELS:,}-pixel limit.",
                    )
                image.load()
        if isinstance(image_source, io.BytesIO):
            image_source.seek(0)
    except AssetError:
        raise
    except (OSError, UnidentifiedImageError, PILImage.DecompressionBombError, PILImage.DecompressionBombWarning) as exc:
        raise AssetError("invalid_image", f"Image could not be decoded ({type(exc).__name__}).") from exc
    if image_width <= 0 or image_height <= 0:
        raise AssetError("invalid_image", "Image dimensions must be greater than zero.")
    scale = (
        min(width / image_width, height / image_height) if contain else max(width / image_width, height / image_height)
    )
    rendered_width = int(image_width * scale)
    rendered_height = int(image_height * scale)
    rendered_left = int(left + (width - rendered_width) / 2)
    rendered_top = int(top + (height - rendered_height) / 2)
    return rendered_left, rendered_top, rendered_width, rendered_height


def _render_notes(slide, slide_spec: Slide) -> None:
    if not slide_spec.notes:
        return
    notes_slide = slide.notes_slide
    notes_slide.notes_text_frame.text = slide_spec.notes


def _apply_hide_background_graphics(slide, slide_spec: Slide) -> None:
    if slide_spec.hide_background_graphics:
        slide.show_master_shapes = False


def _apply_background(
    slide, background: Background, *, slide_width: int, slide_height: int, base_dir: Path, downloader: Downloader
) -> None:
    if background.kind == "none":
        slide.background.fill.background()
        return
    if background.kind in {"color", "gradient"}:
        _apply_background_fill(slide.background.fill, background)
        return
    if background.kind == "image":
        image_source = _resolve_image_source(background.url or "", base_dir=base_dir, downloader=downloader)
        left, top, width, height = _fit_image(
            image_source,
            0,
            0,
            slide_width,
            slide_height,
            contain=False,
        )
        picture = slide.shapes.add_picture(image_source, left, top, width, height)
        picture.name = "MarkdownSlidesBackgroundImage"
        picture.send_to_back()
        return
    raise RenderError("invalid_background", f"Unsupported background kind '{background.kind}'.")


def _apply_master_background(master, background: Background, *, base_dir: Path, downloader: Downloader) -> None:
    if background.kind == "none":
        master.background.fill.background()
    elif background.kind in {"color", "gradient"}:
        _apply_background_fill(master.background.fill, background)
    elif background.kind == "image":
        source = _resolve_image_source(background.url or "", base_dir=base_dir, downloader=downloader)
        _fit_image(source, 0, 0, 1, 1, contain=True)
        master.set_background_picture(source)
    else:
        raise RenderError("invalid_background", f"Unsupported master background kind '{background.kind}'.")


def _apply_background_fill(fill, background: Background) -> None:
    if background.kind == "color":
        fill.background()
        fill.solid()
        _set_color(fill.fore_color, background.value or "")
    else:
        fill.set_gradient(
            [(stop.position, _color_value(stop.color)) for stop in background.stops],
            angle=180.0 if background.angle is None else background.angle,
            radial=background.gradient_kind == "radial",
        )


def _require_placeholder(slide, allowed_types: set[PP_PLACEHOLDER], kind: str):
    matches = [
        placeholder for placeholder in slide.placeholders if placeholder.placeholder_format.type in allowed_types
    ]
    if not matches:
        raise TemplateError("missing_placeholder", f"Selected layout does not contain the required {kind} placeholder.")
    if len(matches) > 1:
        raise TemplateError(
            "ambiguous_placeholder",
            f"Selected layout contains more than one matching {kind} placeholder.",
        )
    return matches[0]


def _two_content_placeholders(slide):
    matches = [shape for shape in slide.placeholders if shape.placeholder_format.type in BODY_PLACEHOLDERS]
    if len(matches) != 2:
        raise TemplateError(
            "invalid_content_placeholders",
            f"Two Content requires exactly two body/content placeholders. Found {len(matches)}.",
        )
    if any(shape.left is None or shape.width is None or shape.width <= 0 for shape in matches):
        raise TemplateError("invalid_content_placeholders", "Two Content placeholders need valid horizontal bounds.")
    matches.sort(key=lambda shape: shape.left)
    if matches[0].left + matches[0].width > matches[1].left:
        raise TemplateError(
            "invalid_content_placeholders", "Two Content placeholders must be side by side without horizontal overlap."
        )
    return matches


def _flatten_inline(fragments: list[InlineText]) -> str:
    parts: list[str] = []
    for fragment in fragments:
        if fragment.children:
            parts.append(_flatten_inline(fragment.children))
        else:
            parts.append(fragment.text or "")
    return "".join(parts)


def _configure_paragraph_bullets(paragraph, paragraph_model) -> None:
    paragraph.bullet = BulletStyle.DEFAULT
    if paragraph_model.kind == "list_item":
        paragraph.level = paragraph_model.level
        if paragraph_model.ordered_index is not None:
            paragraph.bullet = BulletStyle.numbered(
                MSO_NUMBERED_BULLET_STYLE.ARABIC_PERIOD, start_at=paragraph_model.ordered_index
            )
        elif paragraph_model.task_checked is not None:
            paragraph.bullet = BulletStyle.NO_BULLET
        left, hanging = _list_paragraph_indent(paragraph_model)
        _set_paragraph_indent(paragraph, left=left, hanging=hanging)
    else:
        paragraph.level = 0
        paragraph.left_indent = Emu(0)
        paragraph.first_line_indent = Emu(0)
        paragraph.bullet = BulletStyle.NO_BULLET


def _list_paragraph_indent(paragraph_model) -> tuple[float, float]:
    if paragraph_model.task_checked is not None and paragraph_model.ordered_index is None:
        return 0.3 * paragraph_model.quote_depth + 0.4 * paragraph_model.level, 0
    bullet_position = 0.3 * paragraph_model.quote_depth + 0.45 * (paragraph_model.level + 1) - 0.22
    if paragraph_model.ordered_index is not None:
        digits = len(str(paragraph_model.ordered_index))
        hanging = 0.4 + 0.16 * (digits - 1)
        return bullet_position + hanging, hanging
    return bullet_position + 0.22, 0.22


def _set_paragraph_indent(paragraph, *, left: float, hanging: float) -> None:
    paragraph.left_indent = Inches(left)
    paragraph.first_line_indent = Inches(-hanging)


def _set_theme_font(run, *, major: bool) -> None:
    run.font.theme_font = "major" if major else "minor"


def _read_template_defaults(master) -> dict[str, float]:
    body = master.text_style_font("body")
    title = master.text_style_font("title")
    return {
        "body_font_pt": body.size.pt if body is not None and body.size is not None else 28.0,
        "title_font_pt": title.size.pt if title is not None and title.size is not None else 44.0,
    }


def _apply_themes(catalog: list[MasterCatalogEntry], deck: Deck) -> None:
    if deck.color_scheme is None and not deck.fonts_override:
        return
    for entry in catalog:
        theme = entry.master.theme
        if deck.color_scheme is not None:
            scheme = theme.color_scheme
            scheme.name = deck.color_scheme.name
            for name, theme_color in THEME_COLOR_SCHEME_MAP.items():
                scheme[theme_color] = RGBColor.from_string(deck.color_scheme.colors[name.replace("-", "_")][1:])
        if deck.fonts_override:
            theme.font_scheme.major_latin = deck.fonts.headings
            theme.font_scheme.minor_latin = deck.fonts.body
