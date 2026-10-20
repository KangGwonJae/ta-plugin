# ta — Teaching Assistant skills

<p align="center">
  <a href="README.md"><img alt="한국어" src="https://img.shields.io/badge/한국어-전환-555555?style=for-the-badge"></a>
  <a href="README.en.md"><img alt="English" src="https://img.shields.io/badge/English-current-2e7d32?style=for-the-badge"></a>
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

To use formulas (`math`), run `npm install` once at the plugin root.

### Optional dependencies

| Skill | Requires | Notes |
|---|---|---|
| `math` | Node.js 18+ | MathJax is installed from the root `package.json`. Claude Code does this automatically on plugin install; elsewhere run `npm install` once at the root. |
| `math`, `viz` | Google Chrome | Used only in the step that captures the result headlessly for checking. Skipped if absent. |
| `research` | Web search and page-reading tools | Uses whatever the agent provides (Claude Code: WebSearch/WebFetch). |

## Skills

| Skill | What it does | Input |
|---|---|---|
| `generator` | Generates study-note HTML from the materials you provide | `<topic> [path to materials]` |
| `research` | When you have no materials, researches the web and generates study-note HTML (with numbered sources) | `<topic> [scope/level notes]` |
| `supplement` | Adds a "supplementary explanation" block right after the part you did not understand | `"<sentence you got stuck on, or screenshot>" [question] [path]` |
| `example` | Adds an "additional example" block right after the given part | `"<copied part or screenshot>" [path]` |
| `viz` | Adds an inline SVG/CSS diagram for structure, flow, or size comparison | `"<copied part or screenshot>" [path]` |
| `math` | Converts formulas to MathJax SVG and adds term-by-term and combined meaning explanations | `[path] [formula or location]` |
| `quiz` | Generates a self-grading quiz HTML based on the study notes | `[path] [number of questions]` |

Invoke as `/ta:<skill>` in Claude Code and `$<skill>` in Codex. `example`, `viz`, and `math` also serve as **shared rules** that the other skills follow whenever they write examples, diagrams, or formulas. Invoked directly, they add that element to existing study notes.

### Typical flow

1. In the folder with your lecture materials, give `generator` "Linear programming lecture3.pdf" → creates `학습자료/Linear programming_학습자료.html`.
2. When you get stuck while reading, paste the sentence and ask "What does this mean?" → `supplement` adds an explanation at that spot.
3. "One more example" → `example`; "Show me as a diagram" → `viz`.
4. `quiz` → creates `학습자료/Linear programming_퀴즈.html`.

The output is a **single HTML file** (images embedded as base64, light/dark mode, a page index on the left, glossary tooltips), so you can open or share it as is. All output is saved to a `학습자료/` folder in the current working directory.

## Repository layout

```
plugin.json                    Portable plugin manifest (agent-plugins.org schema) — read by Codex
.codex-plugin/plugin.json      Codex compatibility manifest (for older versions)
.agents/plugins/marketplace.json   Codex marketplace definition
.claude-plugin/plugin.json     Claude Code manifest
.claude-plugin/marketplace.json    Claude Code marketplace definition
package.json                   MathJax dependency (used by skills/math/tex2svg.js)
skills/
  generator/   SKILL.md + toc.css, jump.html, glossary.html, pageidx.html
  research/    SKILL.md + tocidx.html
  supplement/
  example/
  viz/         SKILL.md + viz.css
  math/        SKILL.md + tex2svg.js, math.css
  quiz/
```

Every file reference inside a SKILL.md is a **path relative to that SKILL.md's folder** (for example `../math/math.css`), so it means the same thing in any agent. Where invocation names and tool names differ between agents, the text gives both (`/ta:math` · `$math`, WebSearch · the environment's search tool).

## Development

```bash
claude plugin validate . --strict            # Check Claude Code manifests and skills
claude --plugin-dir .                        # Load locally in Claude Code
codex plugin marketplace add .               # Register as a local marketplace in Codex
```

## License

MIT
