[local-photo]: ./showcase-local.png "Shared picture title"
[showcase-guide]: https://github.com/pseudosavant/markdown-pptx "Read the markdown-pptx guide"

# Default showcase

## Vanilla Markdown becomes editable PowerPoint.

# Markdown without metadata

This source has no markdown-pptx metadata. Ordinary content slides use Title and Content.

A title with an optional H2 subtitle infers the title layout first and section layouts later.

# Markdown chooses two content areas

## Left content

One top-level horizontal rule selects Two Content.

***

## Right content

Each side can contain text, an image, a table, or a video.

# What markdown-pptx is

`markdown-pptx` converts constrained Markdown slide decks into editable PowerPoint `.pptx` presentations.

It uses real PowerPoint layouts and placeholders, so the output stays easy to edit in PowerPoint instead of becoming a pile of free-positioned text boxes.

# Basic CLI usage

Run `uvx markdown-pptx deck.md` to write `deck.pptx` next to the source markdown file.

Use `uvx markdown-pptx deck.md out.pptx` to choose the output path, `--template theme.pptx` to render against an existing PowerPoint template, and `--force` to overwrite an existing file.

Run `uvx markdown-pptx` with no arguments for the quick reference or use `--about` for project metadata.

# Body text with hyperlinks

`markdown-pptx` can include links in normal body text, such as the [project repository](https://github.com/pseudosavant/markdown-pptx) and the [python-pptx documentation](https://python-pptx.readthedocs.io/en/latest/).

# Inline text styling

Normal text can mix **strong with *nested italic***, *italic emphasis*, `inline code`, ~~deleted text~~, H~2~O, x^2^, and [**formatted links**](https://github.com/pseudosavant/markdown-pptx) in the same editable placeholder.

# Line breaks

This source line wraps
without forcing a visual break.

This line ends here.\
The next line stays in the same paragraph.

# H2 through H6 headings

## H2 heading

### H3 heading

#### H4 heading

##### H5 heading

###### H6 heading

Setext H2 heading
-----------------

Setext H1 slide
===============

An H1 underline can start a slide without an ATX marker.

# Bulleted list

- Write a readable Markdown deck
- Choose a template if needed
- Render an editable PowerPoint file

# Nested lists

- Inspect the template
  - Select a master
    - Choose a compatible layout
- Write the Markdown
  - Keep each slide focused
- Render and review the PowerPoint

# Numbered list

1. Write the markdown source
2. Run the CLI
3. Open the generated `.pptx`

# Task lists and continuations

- [x] Create the editable deck
- [ ] Review the slides

1. Begin with a numbered item

   Continue its explanation without another number.

2. Finish the sequence

# Native table row sizing

Tables fill the content area's width. PowerPoint sizes each row to its content.

Short rows stay compact. Longer text wraps and makes its row taller. Cells are centered vertically and left aligned by default.

***

| Item | Description |
| --- | --- |
| Short | A brief entry |
| Wrapped | This longer entry wraps onto several lines. PowerPoint grows this row to fit the content while keeping the shorter row compact. |

# Blockquote

> markdown-pptx keeps the source format simple enough to read directly while still producing a real presentation.

> - Quoted lists keep their bullets.

>

# Code block: PowerShell

```powershell
uvx markdown-pptx sample/default-showcase.md sample/default-showcase.pptx --force
```

# Syntax highlighting: Python

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

# Table column alignment

| Region | Status | Revenue |
| :--- | :---: | ---: |
| North | Complete | $50,000 |
| South | Planned | $40,000 |

# Local image

[![Local markdown-pptx sample image](./showcase-local.png "Showcase image")](https://github.com/pseudosavant/markdown-pptx)

# Remote image

A remote image stays editable. Downloading it requires an internet connection.

***

![Remote Python logo](https://raw.githubusercontent.com/github/explore/main/topics/python/python.png)

# YouTube video: Big Buck Bunny

## Online playback

The video on the right is linked to YouTube.

Click the video to play the full film in PowerPoint. Playback requires internet access.

Big Buck Bunny is copyright 2008, Blender Foundation. Licensed under Creative Commons Attribution 3.0.

***

[Watch Big Buck Bunny on YouTube](https://www.youtube.com/watch?v=aqz-KE-bpKQ)

# An empty heading

An empty H1 with no body creates a Blank slide. The next slide demonstrates it.

#

# Two content areas

## First option

- Small initial scope
- Quick feedback

***

## Second option

- Broader initial scope
- More preparation

# Text beside a table

## Progress

- [x] Design agreed
- [ ] Delivery scheduled

***

| Milestone | Status |
| --- | --- |
| Design | Complete |
| Delivery | Planned |

# [Shared references][showcase-guide]

Read the [project guide][showcase-guide].

The same definition can supply links throughout the deck.

[**Formatted** *links*](https://github.com/pseudosavant/markdown-pptx "Open the markdown-pptx project") retain their ScreenTips.

# Code stays inside its list item

1. Run the check

   <!-- This implementation note stays out of the slide. -->

   ```python
   status = "Ready"
   print(status)
   ```

   ## Result

   Continue after checking the output.

2. Present the result

# Numbering and reusable definitions

0. Prepare the content
1. Render the presentation
2. Review in PowerPoint

Return to the [project guide][showcase-guide] for more examples.

[showcase-guide]: https://github.com/pseudosavant/markdown-pptx "Read the markdown-pptx guide"

# Pipe table

| Markdown input | PowerPoint result |
| --- | --- |
| `# H1` | New slide |
| `layout` | Real slide layout |
| `master` | Master-specific layout group |
| `notes` | Editable speaker notes |
| Total | All six native table-style flags |

# Video without metadata

The local clip uses its first decoded frame as its poster. Playback starts on click.

Big Buck Bunny is copyright 2008, Blender Foundation. Licensed under Creative Commons Attribution 3.0.

***

[Play Big Buck Bunny](big-buck-bunny-clip.mp4)

# A linked image supplies a video poster

A linked image pointing to an MP4 becomes its poster.

***

[![Play Big Buck Bunny](big-buck-bunny-poster.png)](big-buck-bunny-clip.mp4)

# Setext H2 heading

A smaller heading
-----------------

A hyphen underline creates an H2. A blank line before a horizontal rule makes the rule a content separator.

# Both hard-break spellings

This line ends with two spaces.  
The next line stays in the paragraph.

This line ends with a backslash.\
The next line also stays in its paragraph.

# Indented code

Code can be indented instead of fenced:

    status = 'Ready'
    print(status)

# Escapes and ordinary HTML

Escaped markers stay literal: \*asterisks\* and \_underscores\_.

Inline <span>HTML contributes its text</span>. The tags add no PowerPoint formatting.

<!-- An ordinary Markdown authoring comment stays invisible. -->

The comment above contributes no visible content.

# Starting numbers and empty items

5. Begin at five
6. Continue at six

- A visible item
-
- Another visible item

32768. Values beyond native numbering stay editable text
32769. The sequence continues

# Reference image forms

![Full image reference][local-photo]

***

![local-photo][]

# Shortcut image reference

![local-photo]

# Collapsed and shortcut links

Read the [showcase-guide][] and revisit [showcase-guide].

The first definition of a reference wins. Reference labels ignore case.

# A table can escape pipes

| Expression | Meaning |
| --- | --- |
| `a\|b` | Either a or b |
| a\|b | A literal pipe |

# Linked picture titles

[![Picture description](showcase-local.png "Picture title")](https://github.com/pseudosavant/markdown-pptx "Link ScreenTip")

# Markdown in. Editable PowerPoint out.

Run `uvx markdown-pptx default-showcase.md` to render this source with the packaged template.

# Other horizontal-rule spellings

A hyphen rule surrounded by blank lines creates two content areas.

---

An underscore rule works the same way on the next slide.

# Two tables without metadata

| Choice | Cost |
| --- | ---: |
| Small | 10 |

___

| Choice | Cost |
| --- | ---: |
| Large | 20 |

# Tilde fences and automatic links

~~~
# This is literal code, not a new slide
***
~~~

An angle-bracket link works too: <https://github.com/pseudosavant/markdown-pptx>.

# Mixed nested lists

1. Plan the presentation
   - Write the source
     1. Review the main point
2. Render the slides

# A section from H1 alone

# A section with a subtitle
## Native layout from ordinary headings

# Multiple H2s remain content

## First content heading

## Second content heading

# Rich table cells

| Kind | Example |
| --- | --- |
| Emphasis | **Bold** and *italic* |
| Code | `status = 'Ready'` |
| Strike | ~~Removed~~ |
| Baselines | Water is H~2~O, area is x^2^ |
| Links | [**Read the guide**][showcase-guide] |
