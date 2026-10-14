<!-- markdown-pptx:deck
aspect_ratio: '16:9'
fonts:
  body: Aptos
  headings: Aptos Display
color_scheme:
  preset: null
  dark_1: '#10263F'
  light_1: '#F9F9F9'
  dark_2: '#355A78'
  light_2: '#EEF8FF'
  accent_1: '#1D6FA8'
  accent_2: '#5AA9E6'
  accent_3: '#7FC8F8'
  accent_4: '#FFB347'
  accent_5: '#FF6392'
  accent_6: '#144F79'
  hyperlink: '#1D6FA8'
  followed_hyperlink: '#355A78'
title_color: var(--accent-6)
body_color: var(--dark-1)
media_layout:
  width: auto
  align: center
  valign: top
table_layout:
  width: auto
  align: center
media_effects:
  border: 1pt solid var(--accent-1)
  border_radius: 12pt
  shadow: 2pt 2pt 6pt rgba(0, 0, 0, 0.25)
  reflection: 4pt 20%
table_effects:
  border: 1pt solid var(--accent-1)
  shadow: 1pt 1pt 3pt rgba(0, 0, 0, 0.15)
  reflection: 4pt 20%
table:
  header_row: true
  total_row: false
  first_column: false
  last_column: false
  banded_rows: true
  banded_columns: false
  header_fill: var(--accent-1)
  row_fill: var(--light-1)
  banded_row_fill: var(--light-2)
background: 'linear-gradient(90deg, #F3FAFF 0%, #E6F4FF 54%, #FFE7BF 100%)'
layout: Title Slide
code_highlighting: theme-dark
-->

[local-photo]: ./showcase-local.png "Shared picture title"
[showcase-guide]: https://github.com/pseudosavant/markdown-pptx "Read the markdown-pptx guide"

# markdown-pptx
<!-- markdown-pptx:slide
notes: The deck contains every supported deck metadata key. A content separator can
  infer Two Content before the deck default.
-->

Markdown in. Editable PowerPoint out.

Advanced showcase: deck defaults, slide settings, and element settings.

# Slide metadata
<!-- markdown-pptx:slide
layout: Section Header
-->

The first group shows slide layouts, colors, backgrounds, notes, visibility, table styling, and media effects.

# Deck defaults used by both groups

The opening deck comment sets layout, aspect ratio, fonts, theme colors, text colors, background, and code highlighting.

It also supplies media and table placement, effects, and table-style defaults. Media defaults to center and top. Tables always stay top aligned.

***

```yaml
layout: Title Slide
aspect_ratio: "16:9"
code_highlighting: theme-dark
```

A single content separator still selects Two Content.

# How the format works
<!-- markdown-pptx:slide
layout: Title and Content
-->

An optional `markdown-pptx:deck` comment sets deck-wide defaults such as aspect ratio, fonts, colors, and background behavior.

Each ATX `# H1` or Setext H1 starts a new slide. An optional `markdown-pptx:slide` comment appears immediately after the heading. Everything until the next H1 belongs to that slide.

One top-level thematic break infers Two Content when there is no explicit slide layout.

# Inspection-friendly CLI modes
<!-- markdown-pptx:slide
layout: Title and Content
-->

Use `--syntax` to print the supported deck format, `--list-masters` to inspect a template's slide masters, `--list-layouts` to inspect layouts on a selected master, and `--list-color-schemes` to see the built-in theme presets.

Add `--json` for structured results. Master and layout inspection report names, indices, placeholder inventory, and compatibility so people and coding agents can discover valid inputs before generating a deck.

# Master and layout selection
<!-- markdown-pptx:slide
master: Showcase Alternate
layout: Title and Content
-->

This slide uses the template's `Showcase Alternate` master while the rest of the deck defaults to master 1. Templates keep every embedded master in the output.

Master selection uses slide metadata first, then the CLI default, then master 1. Layout names are resolved within the selected master.

# Agent skill support
<!-- markdown-pptx:slide
layout: Title and Content
-->

Run `uvx markdown-pptx skill install` to install the managed agent skill under `~/.agents/skills`, or `uvx markdown-pptx skill remove` to remove it safely.

The skill teaches agents to inspect syntax, masters, and layouts; prefer structured output; respect overwrite safety; and handle local or remote images predictably.

# Color and template control
<!-- markdown-pptx:slide
layout: Title and Content
-->

Markdown can set document-level and slide-level colors with `color_scheme`, `title_color`, `body_color`, and background values such as solid colors, gradients, and images.

When a template already has the colors you want, `--ignore-document-colors` and `--ignore-slide-colors` let the template remain the source of truth for those color settings.

# Supported color formats
<!-- markdown-pptx:slide
title_color: hsl(204, 71%, 39%)
body_color: rgb(16, 38, 63)
background: '#DEF'
layout: Title and Content
-->

Colors accept short or long hex, RGB, HSL, and PowerPoint theme references such as `var(--accent-1)`.

# Every PowerPoint theme color
<!-- markdown-pptx:slide
layout: Title Only
title_color: var(--light-1)
background: linear-gradient(270deg, var(--dark-1) 0%, var(--dark-1) 20%, var(--light-1)
  20%, var(--light-1) 27.273%, var(--dark-2) 27.273%, var(--dark-2) 34.545%, var(--light-2)
  34.545%, var(--light-2) 41.818%, var(--accent-1) 41.818%, var(--accent-1) 49.091%,
  var(--accent-2) 49.091%, var(--accent-2) 56.364%, var(--accent-3) 56.364%, var(--accent-3)
  63.636%, var(--accent-4) 63.636%, var(--accent-4) 70.909%, var(--accent-5) 70.909%,
  var(--accent-5) 78.182%, var(--accent-6) 78.182%, var(--accent-6) 85.455%, var(--hyperlink)
  85.455%, var(--hyperlink) 92.727%, var(--followed-hyperlink) 92.727%, var(--followed-hyperlink)
  100%)
notes: |-
  This slide uses every theme color as a hard band in the background.
  From top to bottom: Dark 1, Light 1, Dark 2, Light 2, Accent 1 through Accent 6, Hyperlink, and Followed Hyperlink.
-->

# Feature examples
<!-- markdown-pptx:slide
layout: Section Header
-->

Each slide after this one isolates a single `markdown-pptx` feature.

# Title Slide layout
<!-- markdown-pptx:slide
layout: Title Slide
-->

This slide uses the Title Slide layout.

# Section Header layout
<!-- markdown-pptx:slide
layout: Section Header
-->

This slide uses the Section Header layout.

# Title and Content layout
<!-- markdown-pptx:slide
master: 1
layout: Title and Content
-->

This slide overrides the deck's Title Slide default with Title and Content on master 1. Without a deck default, ordinary H1 slides use Title and Content and need no layout setting.

# Deck-wide default layout

The built-in default is **Title and Content**. This deck sets **Title Slide** for its cover.

Slide layouts, content separators, and heading-only slides take priority over the deck default.

***

```markdown
<!-- markdown-pptx:deck
layout: Two Content
-->

# Compare options

First option

***

Second option
```

# Title Only layout
<!-- markdown-pptx:slide
layout: Title Only
-->

# Pipe table
<!-- markdown-pptx:slide
table:
  header_row: true
  total_row: true
  first_column: true
  last_column: true
  banded_rows: true
  banded_columns: true
layout: Title and Content
-->

| Markdown input | PowerPoint result |
| --- | --- |
| `# H1` | New slide |
| `layout` | Real slide layout |
| `master` | Master-specific layout group |
| `notes` | Editable speaker notes |
| Total | All six native table-style flags |

# Syntax highlighting: Python
<!-- markdown-pptx:slide
notes: Language labels select syntax coloring. The highlighted code remains editable
  PowerPoint text.
code_highlighting: default
layout: Title and Content
-->

```python
# Summarize completed work
def summarize(tasks: list[str]) -> str:
    count = len(tasks)
    return f"Completed {count} tasks"


tasks = ["Design", "Build", "Review"]
if len(tasks) >= 3:
    print(summarize(tasks))
```

# Syntax highlighting: TypeScript
<!-- markdown-pptx:slide
notes: TypeScript highlights type declarations, keywords, strings, and numeric values.
code_highlighting: default
layout: Title and Content
-->

```typescript
// Calculate the remaining work
type Project = { name: string, completed: number }

const remaining = (project: Project): number => {
  return Math.max(0, 10 - project.completed)
}

const launch = { name: "Launch", completed: 7 }
console.log(`Remaining: ${remaining(launch)}`)
```

# Syntax highlighting: HTML
<!-- markdown-pptx:slide
notes: HTML highlights tags, attribute names, quoted values, and comments.
code_highlighting: default
layout: Title and Content
-->

```html
<!-- A compact project card -->
<article class="project-card">
  <h2 id="title">Launch checklist</h2>
  <p>Three steps remain before release.</p>
  <ul>
    <li>Review the preview</li>
    <li>Publish the update</li>
  </ul>
  <a href="/projects/launch">View project</a>
</article>
```

# Syntax highlighting: CSS
<!-- markdown-pptx:slide
notes: CSS highlights selectors, property names, color values, and units.
code_highlighting: default
layout: Title and Content
-->

```css
/* Style the project card */
.project-card {
  display: grid;
  gap: 12px;
  padding: 24px;
  color: #10263f;
  background: #eef8ff;
}

.project-card a:hover { color: #1d6fa8; }
```

# Effects defaults and overrides
<!-- markdown-pptx:slide
media_effects:
  reflection: 4pt 20%
  border_radius: 0
  shadow: none
  border: 1pt solid var(--accent-2)
notes: Deck media defaults round and shadow every content image and video. This slide
  adds reflection. The slide disables rounding and shadow while inheriting reflection.
-->

Deck media defaults apply to images and videos. This slide adds a reflection.

This slide overrides two properties:

```yaml
border_radius: 0
shadow: none
```

***

![Individual media override](./showcase-local.png)

# Table colors and effects
<!-- markdown-pptx:slide
table:
  row_fill: var(--light-1)
  banded_row_fill: var(--light-2)
  total_row: true
table_effects:
  reflection: 4pt 20%
  border: 1.5pt solid var(--accent-2)
  shadow: none
notes: Header color inherits from deck table settings. Body fills are slide overrides.
  The slide sets the table border and reflection and disables the deck shadow. Its
  total row retains native styling.
-->

The header inherits its deck color. Body colors are slide settings.

This table has a slide border and reflection. Its slide settings disable the deck shadow.

The final row uses native total-row styling. Markdown supplies the total value.

***

| Region | Revenue |
| --- | ---: |
| North | $50,000 |
| South | $40,000 |
| Total | $90,000 |

# Background color
<!-- markdown-pptx:slide
background: '#EAF3FF'
layout: Title and Content
-->

This slide uses a solid slide background color.

# Transparent background and hidden master graphics
<!-- markdown-pptx:slide
master: 2
background: none
hide_background_graphics: true
layout: Title and Content
-->

This slide removes its slide-level fill and hides the orange accent graphic inherited from the alternate master.

#
<!-- markdown-pptx:slide
layout: Blank
background: url('./showcase-local.png')
notes: This slide demonstrates a full-slide background image on the Blank layout.
-->

# Linear gradient background
<!-- markdown-pptx:slide
background: linear-gradient(90deg, var(--accent-2) 0%, var(--accent-3) 48%, var(--accent-4)
  100%)
layout: Title and Content
-->

This slide uses a three-stop linear gradient background.

# Radial gradient background
<!-- markdown-pptx:slide
background: radial-gradient(circle, var(--accent-2) 0%, var(--accent-4) 58%, var(--light-1)
  100%)
layout: Title and Content
-->

This slide uses a radial gradient background.

# Slide colors override document colors
<!-- markdown-pptx:slide
title_color: var(--light-1)
body_color: var(--light-1)
background: linear-gradient(90deg, var(--accent-1) 0%, var(--accent-4) 100%)
layout: Title and Content
-->

This slide overrides the document-level title and body colors.

#
<!-- markdown-pptx:slide
layout: Blank
notes: This slide intentionally demonstrates the Blank layout.
-->

# Theme syntax: dark colors
<!-- markdown-pptx:slide
code_highlighting: theme-dark
background: '#FFFFFF'
notes: Dark 1 supplies ordinary code. Accents 1, 2, and 3 supply keywords, values,
  and named tokens. Brightness is adjusted only as needed for 4.5 to 1 contrast.
layout: Title and Content
-->

`code_highlighting: theme-dark` on a white background.

```python
# Colors follow this deck's blue theme
def greet(name: str, count: int = 3):
    for index in range(count):
        print(f"Hello, {name}: {index}")


greet("PowerPoint")
```

# Theme syntax: light colors
<!-- markdown-pptx:slide
code_highlighting: theme-light
background: '#10263F'
title_color: '#FFFFFF'
body_color: '#FFFFFF'
notes: Light 1 supplies ordinary code. The same accent slots are used with lighter
  variants where needed. Comments meet the same contrast target as other code.
layout: Title and Content
-->

`code_highlighting: theme-light` on a navy background.

```typescript
// Editable theme colors on a dark slide
interface Greeting { message: string }
const greet = (name: string): Greeting => ({
  message: `Hello, ${name}`
});

console.log(greet("PowerPoint"));
```

# Theme syntax: a light gradient
<!-- markdown-pptx:slide
code_highlighting: theme-dark
background: 'linear-gradient(0deg, #FFFFFF 0%, #D8EBFF 100%)'
notes: A 16 by 16 grid estimates the background range beneath the content placeholder.
  HTML tags use Accent 1, values use Accent 2, and attributes use Accent 3.
layout: Title and Content
-->

The background range guides the brightness adjustments.

```html
<!-- Theme colors stay editable -->
<article class="greeting">
  <h2>Hello, PowerPoint</h2>
  <p data-state="ready">Ready to present.</p>
</article>
```

# Theme syntax: a dark gradient
<!-- markdown-pptx:slide
code_highlighting: theme-light
background: 'radial-gradient(circle, #254D70 0%, #102030 100%)'
title_color: '#FFFFFF'
body_color: '#FFFFFF'
notes: A dark radial gradient demonstrates the light variant. Native theme references
  retain their slot and use brightness adjustments for the estimated background range.
layout: Title and Content
-->

One palette is reused across all code blocks in this area.

```css
/* Presentation colors follow the theme */
.greeting {
  color: #1d6fa8;
  padding: 24px;
  display: grid;
  gap: 12px;
}
```

# Code stays inside its list item
<!-- markdown-pptx:slide
code_highlighting: theme-dark
background: '#FFFFFF'
notes: The code block and result heading align with the parent list text. The HTML
  comment is omitted.
layout: Title and Content
-->

1. Run the check

   <!-- This implementation note stays out of the slide. -->

   ```python
   status = "Ready"
   print(status)
   ```

   ## Result

   Continue after checking the output.

2. Present the result

# Hidden slide setting

Set `hidden: true` on a slide to keep backup material in the file while skipping it during ordinary slide-show navigation.

The hidden backup slide in this group is a working example. Its content and speaker notes remain editable in PowerPoint.

***

```markdown
# Hidden backup details
<!-- markdown-pptx:slide
hidden: true
-->

Backup material.
```

# Hidden backup details
<!-- markdown-pptx:slide
hidden: true
notes: This slide stays available in the deck but is skipped during ordinary slide-show
  navigation.
layout: Title and Content
-->

Native content sizing keeps short table rows compact. Markdown separator colons control horizontal column alignment. Cells are centered vertically.

# Markdown in. Editable PowerPoint out.
<!-- markdown-pptx:slide
layout: Title Slide
-->

Run `uvx markdown-pptx --help` to get started.

# Deck alternatives: aspect ratio and preset
<!-- markdown-pptx:slide
layout: Title and Content
-->

A document has one aspect ratio and one theme configuration. This complete alternative source uses 4:3 and a preset.

```markdown
<!-- markdown-pptx:deck
aspect_ratio: "4:3"
color_scheme:
  preset: Office
background: none
-->

# Preset example

A template can supply the remaining defaults.
```

# Deck alternatives: image background
<!-- markdown-pptx:slide
layout: Title and Content
-->

A deck background can also be an image.

```markdown
<!-- markdown-pptx:deck
background: url('./showcase-local.png')
-->

# Image-backed deck

Text uses the ordinary content layout.
```

# Slide media effects on a video
<!-- markdown-pptx:slide
media_effects:
  border: 2px dotted var(--accent-2)
  border_radius: 16pt
  shadow: -2pt 3pt 4pt rgba(0, 0, 0, 0.25)
  reflection: 4pt 30%
-->

The slide controls the video's border, rounded corners, shadow, and reflection.

It inherits other deck settings.

***

[![Play clip](big-buck-bunny-poster.png)](big-buck-bunny-clip.mp4)

# Slide table flags: plain rows
<!-- markdown-pptx:slide
table:
  header_row: false
  total_row: false
  first_column: false
  last_column: false
  banded_rows: false
  banded_columns: false
-->

All six native table-style switches can be disabled. Markdown still supplies a syntactic header. The word Total does not enable total styling.

***

| Item | Count |
| --- | ---: |
| Review | 2 |
| Total | 2 |

# Native column banding without custom fills

Explicit row fills override native cell shading. This complete source leaves fills unspecified to show native column banding.

***

```markdown
<!-- markdown-pptx:deck
table:
  banded_rows: false
  banded_columns: true
-->

# Column bands

| Item | Q1 | Q2 |
| --- | ---: | ---: |
| Design | 2 | 3 |
| Review | 1 | 2 |
```

# Slide header fill override
<!-- markdown-pptx:slide
table:
  header_fill: '#123'
-->

A slide can override the header color while inheriting both body fills.

***

| Item | Count |
| --- | ---: |
| Design | 3 |
| Review | 2 |

# Master graphics remain visible
<!-- markdown-pptx:slide
layout: Title and Content
master: 2
background: none
hide_background_graphics: false
-->

This slide keeps the alternate master's graphics visible. The transparent background and master selection remain independent.

The companion slide hides those graphics.

# Visible slide setting
<!-- markdown-pptx:slide
layout: Title and Content
hidden: false
-->

Visibility defaults to true. An explicit false hidden setting keeps ordinary navigation enabled.

# Slide notes and media sources
<!-- markdown-pptx:slide
layout: Title and Content
notes: |-
  Every PowerPoint theme color
  This slide uses every theme color as a hard band in the background.
  From top to bottom: Dark 1, Light 1, Dark 2, Light 2, Accent 1 through Accent 6, Hyperlink, and Followed Hyperlink.

  Syntax highlighting: Python
  Language labels select syntax coloring. The highlighted code remains editable PowerPoint text.

  Syntax highlighting: TypeScript
  TypeScript highlights type declarations, keywords, strings, and numeric values.

  Syntax highlighting: HTML
  HTML highlights tags, attribute names, quoted values, and comments.

  Syntax highlighting: CSS
  CSS highlights selectors, property names, color values, and units.

  Table column alignment
  Separator colons set left, center, and right alignment. All table cells are centered vertically. Columns without alignment colons default to left alignment.

  Effects defaults and overrides
  Deck media defaults round and shadow every content image and video. This slide adds reflection. The individual image disables rounding and shadow while inheriting reflection.

  Table colors and effects
  Header color inherits from deck table settings. Body fills are slide overrides. The table inherits slide reflection and overrides its border and deck shadow. Its total row retains native styling.

  Native picture effects
  This picture uses an editable native border, rounded corners, drop shadow, and reflection. The adjacent image comment sets each effect with a compact CSS-style value.

  Remote image
  This slide demonstrates downloading a remote image during rendering.
  [Sources]
  - https://raw.githubusercontent.com/github/explore/main/topics/python/python.png (Python logo)

  Local video: Big Buck Bunny
  The local MP4 is embedded in this PowerPoint file. Click Next to start playback.
  The slide stays in place when the clip ends.
  The preview image is generated from the first video frame.
  Clip: (c) copyright 2008, Blender Foundation / www.bigbuckbunny.org
  Licensed under Creative Commons Attribution 3.0.

  Local video: automatic fullscreen playback
  The embedded Big Buck Bunny clip starts when this slide appears.
  It fills the screen, loops, and plays with sound muted.
  Advance the slide manually when you are ready to continue.
  Clip and poster: (c) copyright 2008, Blender Foundation / www.bigbuckbunny.org
  Licensed under Creative Commons Attribution 3.0.

  YouTube video: Big Buck Bunny
  This slide uses an online YouTube media object. Playback needs internet access.
  The film is (c) copyright 2008, Blender Foundation / www.bigbuckbunny.org

  Blank slide
  This slide demonstrates a full-slide background image on the Blank layout.

  Blank slide
  This slide intentionally demonstrates the Blank layout.

  Two content areas
  A single top-level thematic break separates the left and right placeholders.

  Theme syntax: dark colors
  Dark 1 supplies ordinary code. Accents 1, 2, and 3 supply keywords, values, and named tokens. Brightness is adjusted only as needed for 4.5 to 1 contrast.

  Theme syntax: light colors
  Light 1 supplies ordinary code. The same accent slots are used with lighter variants where needed. Comments meet the same contrast target as other code.

  Theme syntax: a light gradient
  A 16 by 16 grid estimates the background range beneath the content placeholder. HTML tags use Accent 1, values use Accent 2, and attributes use Accent 3.

  Theme syntax: a dark gradient
  A dark radial gradient demonstrates the light variant. Native theme references retain their slot and use brightness adjustments for the estimated background range.

  [Shared references][showcase-guide]
  The title and body use a reference defined on a later slide. The optional link title becomes a ScreenTip in PowerPoint. Hover over a link in Slide Show view to see the tip.

  Code stays inside its list item
  The code block and result heading align with the parent list text. The HTML comment is omitted.

  Numbering and reusable definitions
  Zero is preserved with an editable text marker. Native numbering is used where PowerPoint supports it. The reference definition at the bottom is invisible and serves earlier slides.

  Hidden backup details
  This slide stays available in the deck but is skipped during ordinary slide-show navigation.
-->

Speaker notes stay editable in PowerPoint. They can record sources, licensing, and presentation guidance.

This note retains the original media credits and syntax guidance.

# Explicit Two Content layout
<!-- markdown-pptx:slide
layout: Two Content
-->

An explicit Two Content layout still requires exactly one separator.

***

The source can name the layout when demonstrating an explicit override.

# Slide image placement
<!-- markdown-pptx:slide
media_layout:
  width: 50%
  align: left
  valign: middle
-->

The slide overrides the deck placement for images and videos.

This image uses half of its own content box, aligned left and vertically centered.

***

![Slide-level image placement](showcase-local.png)

# Slide video placement
<!-- markdown-pptx:slide
media_layout:
  width: 70%
  align: right
  valign: bottom
-->

The same slide settings apply to a video frame.

Its reflection can extend below the content area without reducing the video's size.

***

[![Play Big Buck Bunny](big-buck-bunny-poster.png)](big-buck-bunny-clip.mp4)

# Slide table placement
<!-- markdown-pptx:slide
table_layout:
  width: 50%
  align: right
-->

50% means half of the table's own content box.

The table stays top aligned. Row heights still follow the content.

***

| Item | Count |
| --- | ---: |
| Design | 3 |
| Review | 2 |

# Heading inference precedes the deck default
## This is a section despite the Title Slide deck default

# Explicit layout overrides heading inference
<!-- markdown-pptx:slide
layout: Title and Content
-->

## This remains a body heading

# Rich cells retain native table styling
<!-- markdown-pptx:slide
table:
  first_column: true
table_layout:
  width: 85%
-->

Inline Markdown works inside native styled cells. Links retain their targets and ScreenTips.

***

| Kind | Example |
| --- | --- |
| Emphasis | **Bold** and *italic* |
| Code | `status` |
| Strike | ~~Removed~~ |
| Baselines | H~2~O and x^2^ |
| Links | [**Guide**][showcase-guide] |

# Element metadata
<!-- markdown-pptx:slide
layout: Section Header
-->

The second group applies placement, effects, and video settings directly to individual elements.

# Native picture effects

Native border, rounded corners, shadow, and reflection apply to this image.

***

![Local sample with editable picture effects](./showcase-local.png "Picture effects")

<!-- markdown-pptx:media_effects
border: "1.5pt solid var(--accent-1)"
border_radius: 12pt
shadow: "2pt 2pt 6pt rgba(0, 0, 0, 0.25)"
reflection: "4pt 30%"
-->

# Local video: Big Buck Bunny

The element sets video width. Its media effects round the frame and add a reflection.

Big Buck Bunny is copyright 2008, Blender Foundation. Licensed under Creative Commons Attribution 3.0.

***

[Play Big Buck Bunny](big-buck-bunny-clip.mp4)

<!-- markdown-pptx:video
width: 88%
-->

<!-- markdown-pptx:media_effects
border_radius: 16pt
reflection: 4pt 20%
-->

# Local video: automatic fullscreen playback

The element starts playback automatically, fills the screen, loops, and mutes audio. Its linked image supplies the poster.

Big Buck Bunny is copyright 2008, Blender Foundation. Licensed under Creative Commons Attribution 3.0.

***

[![Play Big Buck Bunny](big-buck-bunny-poster.png)](big-buck-bunny-clip.mp4)

<!-- markdown-pptx:video
start: automatic
fullscreen: true
loop: true
mute: true
-->

<!-- markdown-pptx:media_effects
border: "1.5pt solid var(--accent-2)"
border_radius: 20pt
reflection: "4pt 20%"
-->

# Element media effects: disable inherited styling

```yaml
border: none
border_radius: 0
shadow: none
reflection: none
```

***

![Editable image](showcase-local.png)

<!-- markdown-pptx:media_effects
border: none
border_radius: 0
shadow: none
reflection: none
-->

# Element media effects: dashed border and alpha hex

```yaml
border: '2px dashed #1234'
border_radius: 0.1in
shadow: '0 2pt #00000040'
reflection: 4pt
```

***

![Editable image](showcase-local.png)

<!-- markdown-pptx:media_effects
border: '2px dashed #1234'
border_radius: 0.1in
shadow: '0 2pt #00000040'
reflection: 4pt
-->

# Element media effects: dotted border and signed shadow

```yaml
border: 1pt dotted rgb(29, 111, 168)
border_radius: 8px
shadow: -2pt -2pt 4pt var(--accent-2)
reflection: 2px 40%
```

***

![Editable image](showcase-local.png)

<!-- markdown-pptx:media_effects
border: 1pt dotted rgb(29, 111, 168)
border_radius: 8px
shadow: -2pt -2pt 4pt var(--accent-2)
reflection: 2px 40%
-->

# Element media effects: radius clamping

```yaml
border_radius: 100in
border: none
reflection: none
```

***

![Editable image](showcase-local.png)

<!-- markdown-pptx:media_effects
border_radius: 100in
border: none
reflection: none
-->

# Element table effects: solid perimeter

```yaml
border: 2pt solid var(--accent-2)
shadow: 2pt 2pt 6pt rgba(0, 0, 0, 0.25)
reflection: 4pt 30%
```

***

| Item | Count |
| --- | ---: |
| Design | 3 |
| Review | 2 |

<!-- markdown-pptx:table_effects
border: 2pt solid var(--accent-2)
shadow: 2pt 2pt 6pt rgba(0, 0, 0, 0.25)
reflection: 4pt 30%
-->

# Element table effects: dashed perimeter

```yaml
border: '1pt dashed #12345680'
shadow: -2pt 3pt hsl(204, 71%, 39%)
reflection: 2px 40%
```

***

| Item | Count |
| --- | ---: |
| Design | 3 |
| Review | 2 |

<!-- markdown-pptx:table_effects
border: '1pt dashed #12345680'
shadow: -2pt 3pt hsl(204, 71%, 39%)
reflection: 2px 40%
-->

# Element table effects: dotted perimeter

```yaml
border: 2px dotted rgb(29, 111, 168)
shadow: 0 2pt
reflection: 4pt
```

***

| Item | Count |
| --- | ---: |
| Design | 3 |
| Review | 2 |

<!-- markdown-pptx:table_effects
border: 2px dotted rgb(29, 111, 168)
shadow: 0 2pt
reflection: 4pt
-->

# Element table effects: disable inherited styling

```yaml
border: none
shadow: none
reflection: none
```

***

| Item | Count |
| --- | ---: |
| Design | 3 |
| Review | 2 |

<!-- markdown-pptx:table_effects
border: none
shadow: none
reflection: none
-->

# Element video: upper left

```yaml
width: 50%
align: left
valign: top
aspect_ratio: '4:3'
start: click
fullscreen: false
loop: false
mute: false
```

***

[Play Big Buck Bunny](big-buck-bunny-clip.mp4)

<!-- markdown-pptx:video
width: 50%
align: left
valign: top
aspect_ratio: '4:3'
start: click
fullscreen: false
loop: false
mute: false
-->

# Element video: lower right

```yaml
width: 4in
align: right
valign: bottom
aspect_ratio: '1:1'
```

***

[Play Big Buck Bunny](big-buck-bunny-clip.mp4)

<!-- markdown-pptx:video
width: 4in
align: right
valign: bottom
aspect_ratio: '1:1'
-->

# Element video: automatic size

```yaml
width: auto
align: center
valign: middle
aspect_ratio: '16:9'
```

***

[Play Big Buck Bunny](big-buck-bunny-clip.mp4)

<!-- markdown-pptx:video
width: auto
align: center
valign: middle
aspect_ratio: '16:9'
-->

# Element video: remote MP4

```yaml
width: 80%
mute: true
```

***

[Play Big Buck Bunny](https://raw.githubusercontent.com/pseudosavant/markdown-pptx/main/sample/big-buck-bunny-clip.mp4)

<!-- markdown-pptx:video
width: 80%
mute: true
-->

# Element YouTube: watch URL

YouTube watch links normalize to the same online video. Placement settings and media effects apply to the frame.

***

[Watch Big Buck Bunny](https://www.youtube.com/watch?v=aqz-KE-bpKQ)

<!-- markdown-pptx:media_effects
border_radius: 8pt
reflection: none
-->

<!-- markdown-pptx:video
width: 75%
aspect_ratio: '16:9'
align: center
valign: middle
-->

# Element YouTube: share URL

YouTube share links normalize to the same online video. Placement settings and media effects apply to the frame.

***

[Watch Big Buck Bunny](https://youtu.be/aqz-KE-bpKQ)

<!-- markdown-pptx:media_effects
border_radius: 8pt
reflection: none
-->

<!-- markdown-pptx:video
width: 75%
aspect_ratio: '16:9'
align: center
valign: middle
-->

# Element YouTube: Shorts URL

YouTube Shorts links normalize to the same online video. Placement settings and media effects apply to the frame.

***

[Watch Big Buck Bunny](https://www.youtube.com/shorts/aqz-KE-bpKQ)

<!-- markdown-pptx:media_effects
border_radius: 8pt
reflection: none
-->

<!-- markdown-pptx:video
width: 75%
aspect_ratio: '16:9'
align: center
valign: middle
-->

# Element YouTube: embed URL

YouTube embed links normalize to the same online video. Placement settings and media effects apply to the frame.

***

[Watch Big Buck Bunny](https://www.youtube.com/embed/aqz-KE-bpKQ)

<!-- markdown-pptx:media_effects
border_radius: 8pt
reflection: none
-->

<!-- markdown-pptx:video
width: 75%
aspect_ratio: '16:9'
align: center
valign: middle
-->

# Independent element effects in two content areas

![Editable image](showcase-local.png)

<!-- markdown-pptx:media_effects
shadow: none
reflection: none
-->

***

| Item | Count |
| --- | ---: |
| Design | 3 |
| Review | 2 |

<!-- markdown-pptx:table_effects
shadow: none
border: 2pt dashed var(--accent-2)
-->

# Linked reference media effects

[![local-photo][]](https://github.com/pseudosavant/markdown-pptx "Project ScreenTip")

<!-- markdown-pptx:media_effects
border_radius: 0.1in
reflection: none
-->

***

A reference image retains its description, picture title, hyperlink, and ScreenTip. Its effects remain editable.

# Empty content sides remain valid

***

![Editable image](showcase-local.png)

<!-- markdown-pptx:media_effects
reflection: none
-->

# Element image placement: upper left

A linked image keeps its hyperlink while its layout comment controls placement.

***

[![Open the project](showcase-local.png)](https://github.com/pseudosavant/markdown-pptx)

<!-- markdown-pptx:media_layout
width: 50%
align: left
valign: top
-->

# Element image placement: middle

This image opts into vertical centering while preserving the deck's horizontal centering.

***

![Vertically centered image](showcase-local.png)

<!-- markdown-pptx:media_layout
width: auto
valign: middle
-->

# Element video placement: lower right

Placement, effects, and playback comments can appear together in any order.

***

[![Play Big Buck Bunny](big-buck-bunny-poster.png)](big-buck-bunny-clip.mp4)

<!-- markdown-pptx:media_layout
width: 2in
align: right
valign: bottom
-->
<!-- markdown-pptx:video
mute: true
loop: false
-->
<!-- markdown-pptx:media_effects
shadow: none
reflection: 4pt 30%
-->

# Element table placement: centered percentage

The table is centered within the right content box. Its 50% width does not refer to the whole slide.

***

| Item | Count |
| --- | ---: |
| Design | 3 |
| Review | 2 |

<!-- markdown-pptx:table_layout
width: 50%
align: center
-->

# Element table placement: inches and left alignment

An inch width can also be aligned left. Width requests are capped to the content box.

***

| Item | Count |
| --- | ---: |
| Design | 3 |
| Review | 2 |

<!-- markdown-pptx:table_effects
shadow: none
-->
<!-- markdown-pptx:table_layout
width: 2in
align: left
-->

# Independent table widths

| Small | Count |
| --- | ---: |
| Design | 3 |

<!-- markdown-pptx:table_layout
width: 50%
align: right
-->

***

| Full width | Count |
| --- | ---: |
| Review | 2 |

<!-- markdown-pptx:table_layout
width: auto
align: center
-->
