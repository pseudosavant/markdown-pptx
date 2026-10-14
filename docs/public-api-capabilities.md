# PowerPoint library boundary

`markdown-pptx` uses the `ps-python-pptx` distribution from
[pseudosavant/python-pptx](https://github.com/pseudosavant/python-pptx).
The Python import remains `pptx`.

The converter owns Markdown parsing, validation, layout selection, sizing, and
rendering policy. The library owns PowerPoint XML, package relationships, and
serialization wherever its public APIs cover the feature. The boundary test
prevents direct XML imports, ZIP manipulation, and private pptx access outside
two compatibility modules. Tests may inspect XML to verify the resulting file.

`video.py` contains the existing native adapters for online video relationships
and playback timing. `native_pptx.py` isolates content placeholder replacement,
slide visibility, picture corner geometry adjustments, effect opacity, outer
shadows, and reflections missing from the pinned library. Its exception allows only the two XML helper imports
and `_element` access. Move these adapters to public library APIs when available.

| Capability | Public API |
| --- | --- |
| Template slide removal | `Presentation.slides.clear()` |
| Master graphics visibility | `Slide.show_master_shapes` |
| Theme discovery and edits | `SlideMaster.theme` |
| Master text defaults | `SlideMaster.text_style_font()` |
| Theme font references | `Font.theme_font` |
| Strikethrough and baseline shifts | `Font.strike`, `Font.baseline` |
| Paragraph mark formatting | `Paragraph.end_font` |
| Lists and numbering starts | `Paragraph.bullet`, `BulletStyle.numbered()` |
| List and quote indentation | `Paragraph.left_indent`, `first_line_indent` |
| Table style references | `Table.style_id` |
| Native content-sized rows | `Row.height = Pt(0)` |
| Filled content placeholders | Isolated replacement adapter retains the layout placeholder identity and removes the empty shape |
| Markdown table alignment | `Paragraph.alignment`, `Cell.vertical_anchor` |
| Rich table cells and native subtitles | Shared inline run rendering preserves inherited native formatting unless Markdown requests an override |
| Picture borders | `Picture.line` |
| Video frame borders | `Movie.line` |
| Table fill overrides | `Cell.fill`, `ColorFormat` |
| Table perimeter borders and effects | Isolated native table adapter |
| Rounded picture masking | `Picture.auto_shape_type` plus the isolated geometry adjustment adapter |
| Rounded video masking | Isolated native media geometry adapter |
| Explicit gradients | `FillFormat.set_gradient()` |
| Master image backgrounds | `SlideMaster.set_background_picture()` |
| Inherited background inspection without edits | `Slide.background_info`, `SlideLayout.background_info`, `SlideMaster.background_info` |
| Theme syntax colors and brightness variants | `ColorFormat.theme_color`, `ColorFormat.brightness` |
| Picture stacking order | `Shape.send_to_back()` |
| Picture description and title | `Shape.alt_text`, `alt_text_title` |
| Text and picture hyperlink ScreenTips | `Run.hyperlink.screen_tip`, `Shape.click_action.hyperlink.screen_tip` |

Existing public python-pptx APIs provide hyperlinks, linked pictures, hard line
breaks, table flags, theme colors, notes, and ordinary font styling.

The dependency is pinned to a tested fork release. Do not install `python-pptx`
and `ps-python-pptx` together. Both distributions provide the same `pptx` package.
Use a fresh environment when switching distributions.

Zero row heights let PowerPoint calculate visible row heights from content at
layout time. The stored row heights and table frame height do not report that
calculated geometry. This supports compact tables without text measurement.
Detecting or shrinking an oversized table remains a separate rendering policy.
