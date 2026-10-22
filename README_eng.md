# ta — Teaching Assistant skills

<p align="center">
  <a href="README.md"><img alt="한국어" src="https://img.shields.io/badge/한국어-전환-555555?style=for-the-badge"></a>
  <a href="README_eng.md"><img alt="English" src="https://img.shields.io/badge/English-current-2e7d32?style=for-the-badge"></a>
</p>

A set of skills that turns lecture PDFs/slides (or web research) into **HTML study notes a middle-schooler can follow**, then adds supplementary explanations, examples, diagrams, formulas, and quizzes to them. Works with Korean and English materials.

The skills are written as [Agent Skills](https://agentskills.io) standard SKILL.md files, and this one repository installs as both a **Claude Code plugin** and a **Codex plugin**. For other agents that read SKILL.md, such as Gemini CLI or Cursor, copy the `skills/` folder as is.

## Installation

### Claude Code

```
/plugin marketplace add KangGwonJae/ta-plugin
/plugin install ta@ta-plugin
```

In a new session, invoke skills as `/ta:generator` and so on.

### Codex (CLI / ChatGPT desktop app)

```bash
codex plugin marketplace add KangGwonJae/ta-plugin
```

Then install **ta** from the `ta-plugin` marketplace via `/plugins` in Codex CLI (or the Plugins tab in the desktop app) and open a new session. Invoke skills with `$`, such as `$generator` or `$quiz`, or pick them from `/skills`. To use them without the plugin, copy `skills/*` into `~/.agents/skills/`.

### Gemini CLI, Cursor, and other SKILL.md-aware agents

```bash
git clone https://github.com/KangGwonJae/ta-plugin
cp -r ta-plugin/skills/* ~/.agents/skills/      # Gemini CLI also accepts: gemini skills install ./ta-plugin/skills/<name>
```

The SKILL.md files look for the shared script at `../../scripts/ta.py`, so copy `scripts/` too (`cp -r ta-plugin/scripts ~/.agents/scripts`). To use formulas (`math`), run `npm install` once at the plugin root.

### Optional dependencies

| Skill | Requires | Notes |
|---|---|---|
| all skills | Python 3.9+ | The shared script `scripts/ta.py` (standard library only) handles text extraction, search, insertion, and shared-fragment injection. |
| `generator` | poppler (`pdftotext`, `pdftoppm`), Pillow | For reading PDFs and cropping source figures (`ta.py clip`). Without Pillow only the figures are skipped. |
| `math` | Node.js 18+ | MathJax is installed from the root `package.json`. Claude Code does this automatically on plugin install; elsewhere run `npm install` once at the root. |
| `math`, `viz` | Google Chrome | Used only in the step that captures the result headlessly for checking (`ta.py shot`). Skipped if absent (set `TA_CHROME` to point at a binary). |
| `research` | Web search and page-reading tools | Uses whatever the agent provides (Claude Code: WebSearch/WebFetch). |

## Skills

| Skill | What it does | Input |
|---|---|---|
| `generator` | Generates study-note HTML from the materials you provide | `<topic> [path to materials]` |
| `research` | When you have no materials, researches the web and generates study-note HTML (with numbered sources) | `<topic> [scope/level notes]` |
| `supplement` | Adds a "supplementary explanation" block right after the part you did not understand | `"<sentence you got stuck on, or screenshot>" [question] [path]` |
| `example` | Adds an "additional example" block right after the given part | `"<copied part or screenshot>" [path]` |
| `viz` | Adds an inline SVG/CSS diagram for structure, flow, or size comparison; when depth, volume, or stacking is the point, a stepped 3D scene (three.js) with a 2D fallback | `"<copied part or screenshot>" [path]` |
| `math` | Converts formulas to MathJax SVG and adds term-by-term and combined meaning explanations | `[path] [formula or location]` |
| `quiz` | Generates a self-grading quiz HTML based on the study notes | `[path] [number of questions]` |

Invoke as `/ta:<skill>` in Claude Code and `$<skill>` in Codex. `example`, `viz`, and `math` also serve as **shared rules** that the other skills follow whenever they write examples, diagrams, or formulas. Invoked directly, they add that element to existing study notes.

### Typical flow

1. In the folder with your lecture materials, give `generator` "Newton's laws of motion chapter2.pdf" → creates `학습자료/chapter2.pdf_학습자료.html` (`study-notes/chapter2.pdf_notes.html` when `lang` is `en`).
2. When you get stuck while reading, paste the sentence and ask "What does this mean?" → `supplement` adds an explanation at that spot.
3. "One more example" → `example`; "Show me as a diagram" → `viz`.
4. `quiz` → creates `학습자료/chapter2.pdf_퀴즈.html` (`study-notes/chapter2.pdf_quiz.html` in English mode).

The output is a **single HTML file** (images embedded as base64, light/dark mode, a page index on the left, glossary tooltips, per-section read checkboxes with an estimated reading time, print CSS), so you can open or share it as is. All output is saved to a `학습자료/` folder in the current working directory (`study-notes/` when `lang` is `en`; configurable). Materials longer than about 80 pages are split into parts, and a hub `index.html` is built alongside.

## Configuration (`.ta.json`)

Put a `.ta.json` in the working directory (where the lecture files live) and every skill reads it. Falls back to `~/.ta.json`, then to defaults.

```json
{ "level": "middle", "lang": "en", "out_dir": null, "open": true }
```

| Key | Values | Meaning |
|---|---|---|
| `level` | `middle` (default) · `undergrad` · free text | Target reader. `middle` is a middle-schooler with no background; `undergrad` assumes high-school math and basic programming. Free text is used verbatim as the reader definition. |
| `lang` | `ko` (default) · `en` | Language of the body and UI. With `en` the output folder becomes `study-notes/`, suffixes become `_notes`/`_quiz`, and buttons and labels switch to English. |
| `out_dir` | folder name or `null` | Output folder. `null` means the language default. |
| `open` | `true`/`false` | Open the result in a browser after generating. |

`python3 scripts/ta.py config` prints the merged values.

## Shared script `scripts/ta.py`

A deterministic toolbox the skills call instead of writing ad-hoc code (Python 3 standard library; only `clip` needs Pillow).

| Command | What it does |
|---|---|
| `config` | Print the merged configuration |
| `text <html>` | Tag-stripped text with style/script/svg/base64 removed (keeps block ids, source badges, formulas) |
| `find <html> "<sentence>"` | Locate the smallest block containing the sentence, ignoring whitespace (fuzzy fallback), with raw offsets |
| `insert` · `wrap` · `backup` | Insert after a block, wrap a span in tags (highlighting), copy to `.backup/` |
| `fragments <html> [--check]` | Inject or upgrade the shared fragments (toc/viz/math/v3d CSS, jump · glossary · pageidx\|tocidx · reader · v3d) |
| `clip <pdf> <page> [--box …]` | Render a page, crop by fractional box, emit a 1200px JPEG data URI |
| `shot <html> --id …` | Capture one element with the document's CSS in headless Chrome (`--dark`; `--step N` for a 3D figure) |
| `hub` · `stats` · `mathscan` | Folder index.html, character count and reading time, formulas not yet converted to SVG |

Shared fragments carry versions (`<!--jump:start v2-->`, `/*ta-math:start v1*/`). Older study notes upgrade to the latest fragments (read checkboxes, reading time, print CSS) with a single `python3 scripts/ta.py fragments <file>`.

## Repository layout

```
plugin.json                    Portable plugin manifest (agent-plugins.org schema) — read by Codex
.codex-plugin/plugin.json      Codex compatibility manifest (for older versions)
.agents/plugins/marketplace.json   Codex marketplace definition
.claude-plugin/plugin.json     Claude Code manifest
.claude-plugin/marketplace.json    Claude Code marketplace definition
package.json                   MathJax dependency (used by skills/math/tex2svg.js)
scripts/
  ta.py                        Shared script (table above)
  tests/test_ta.py             Unit tests
skills/
  generator/   SKILL.md + toc.css, jump.html, glossary.html, pageidx.html, reader.html
  research/    SKILL.md + tocidx.html
  supplement/
  example/
  viz/         SKILL.md + viz.css, v3d.css, v3d.html (built from 3d/)
  math/        SKILL.md + tex2svg.js, math.css
  quiz/
evals/                         claude plugin eval cases (prompt.md + graders/ + fixtures/)
docs/superpowers/specs/        Design notes
```

Every file reference inside a SKILL.md is a **path relative to that SKILL.md's folder** (for example `../math/math.css`), so it means the same thing in any agent. Where invocation names and tool names differ between agents, the text gives both (`/ta:math` · `$math`, WebSearch · the environment's search tool).

## Development

```bash
claude plugin validate . --strict            # Check Claude Code manifests and skills
python3 -m unittest discover -s scripts/tests   # Unit tests for the shared script
claude plugin eval . --scaffold --trust-plugin --allow-tools Bash Write Edit Read Glob Grep Skill --no-publish   # Skill regression evals (runs real models, costs money; --scaffold copies the fixtures)
claude plugin eval . --case 'math-*' ...     # A single case
claude --plugin-dir .                        # Load locally in Claude Code
codex plugin marketplace add .               # Register as a local marketplace in Codex
```

Each eval case is `evals/<name>/prompt.md` plus `graders/*.md`, with its input files in `evals/<name>/fixtures/` (exposed to the run through `case.yaml`). Grading is mostly deterministic (skill fired, file created, regex on the produced file) plus one llm rubric.

## License

MIT
