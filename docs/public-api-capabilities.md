# PowerPoint library boundary

`markdown-pptx` uses the `ps-python-pptx` distribution from
[pseudosavant/python-pptx](https://github.com/pseudosavant/python-pptx).
The Python import remains `pptx`.

The converter owns Markdown parsing, validation, layout selection, sizing, and
rendering policy. The library owns PowerPoint XML, package relationships, and
serialization. Production converter code uses public APIs only. The boundary
test prevents direct XML imports, ZIP manipulation, and private pptx access.
Tests may inspect XML to verify the resulting file.

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
| Explicit gradients | `FillFormat.set_gradient()` |
| Master image backgrounds | `SlideMaster.set_background_picture()` |
| Inherited background inspection without edits | `Slide.background_info`, `SlideLayout.background_info`, `SlideMaster.background_info` |
| Theme syntax colors and brightness variants | `ColorFormat.theme_color`, `ColorFormat.brightness` |
| Picture stacking order | `Shape.send_to_back()` |
| Picture description and title | `Shape.alt_text`, `alt_text_title` |

Existing public python-pptx APIs provide hyperlinks, linked pictures, hard line
breaks, table flags, theme colors, notes, and ordinary font styling.

The dependency is pinned to a tested fork release. Do not install `python-pptx`
and `ps-python-pptx` together. Both distributions provide the same `pptx` package.
Use a fresh environment when switching distributions.
