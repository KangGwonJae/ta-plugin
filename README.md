# ta — Teaching Assistant skills

<p align="center">
  <a href="README.md"><img alt="한국어" src="https://img.shields.io/badge/한국어-현재-2e7d32?style=for-the-badge"></a>
  <a href="README_eng.md"><img alt="English" src="https://img.shields.io/badge/English-switch-555555?style=for-the-badge"></a>
</p>

강의 PDF·슬라이드(또는 웹 조사)를 근거로 **중학생도 이해할 수 있는 학습자료 HTML**을 만들고, 거기에 보충 설명·예시·그림·수식·퀴즈를 덧붙이는 스킬 묶음입니다. 한국어·영어 자료 모두 다룹니다.

[Agent Skills](https://agentskills.io) 표준 SKILL.md로 작성되어 있고, 같은 저장소가 **Claude Code 플러그인**과 **Codex 플러그인**으로 동시에 설치됩니다. Gemini CLI, Cursor 등 SKILL.md를 읽는 다른 에이전트에서는 `skills/` 폴더를 그대로 복사해 씁니다.

## 설치

### Claude Code

```
/plugin marketplace add KangGwonJae/ta-plugin
/plugin install ta@ta-plugin
```

새 세션에서 `/ta:generator` 처럼 부릅니다.

### Codex (CLI / ChatGPT 데스크톱 앱)

```bash
codex plugin marketplace add KangGwonJae/ta-plugin
```

그 다음 Codex CLI에서 `/plugins`(또는 데스크톱 앱의 Plugins 탭)에서 마켓플레이스 `ta-plugin`의 **ta**를 설치하고 새 세션을 엽니다. 스킬은 `$generator`, `$quiz` 처럼 `$`로 부르거나 `/skills`에서 고릅니다. 플러그인 없이 쓰려면 `skills/*`를 `~/.agents/skills/`에 복사해도 됩니다.

### Gemini CLI · Cursor · 그 외 SKILL.md 지원 에이전트

```bash
git clone https://github.com/KangGwonJae/ta-plugin
cp -r ta-plugin/skills/* ~/.agents/skills/      # Gemini CLI는 gemini skills install ./ta-plugin/skills/<name> 도 가능
```

수식(`math`)을 쓰려면 플러그인 루트에서 `npm install`을 한 번 해 두세요.

### 선택 의존성

| 스킬 | 필요한 것 | 비고 |
|---|---|---|
| `math` | Node.js 18+ | 루트 `package.json`으로 MathJax를 설치합니다. Claude Code는 플러그인 설치 때 자동으로 하고, 그 외에는 루트에서 `npm install` 한 번. |
| `math`, `viz` | Google Chrome | 결과를 헤드리스로 캡처해 확인하는 단계에만 씁니다. 없으면 건너뜁니다. |
| `research` | 웹 검색·페이지 읽기 도구 | 에이전트가 제공하는 것을 씁니다(Claude Code: WebSearch/WebFetch). |

## 스킬

| 스킬 | 하는 일 | 입력 |
|---|---|---|
| `generator` | 사용자가 준 자료를 근거로 학습자료 HTML 생성 | `<주제> [자료 경로]` |
| `research` | 자료가 없을 때 웹에서 조사해 학습자료 HTML 생성(출처 번호 포함) | `<주제> [범위·수준 메모]` |
| `supplement` | 이해 안 되는 부분 바로 뒤에 "보충 설명" 블록 추가 | `"<막힌 문장 또는 스크린샷>" [질문] [경로]` |
| `example` | 해당 부분 바로 뒤에 "추가 예시" 블록 추가 | `"<복사한 부분 또는 스크린샷>" [경로]` |
| `viz` | 구조·흐름·크기 비교를 인라인 SVG/CSS 도식으로 추가 | `"<복사한 부분 또는 스크린샷>" [경로]` |
| `math` | 수식을 MathJax SVG로 바꾸고 항별·조합별 뜻 설명 추가 | `[경로] [수식 또는 위치]` |
| `quiz` | 학습자료를 근거로 자동 채점 퀴즈 HTML 생성 | `[경로] [문항 수]` |

Claude Code에서는 `/ta:<스킬>`, Codex에서는 `$<스킬>`로 부릅니다. `example`, `viz`, `math`는 다른 스킬이 예시·그림·수식을 쓸 때 따르는 **공용 규칙**이기도 합니다. 직접 부르면 기존 학습자료에 그 요소를 덧붙입니다.

### 전형적인 흐름

1. 강의 자료가 있는 폴더에서 `generator`에 "선형계획법 lecture3.pdf" → `학습자료/선형계획법_학습자료.html` 생성.
2. 읽다가 막히면 그 문장을 붙여 넣고 "이게 무슨 말이야?" → `supplement`가 보충 설명을 그 자리에 덧붙임.
3. "예시 하나 더" → `example`, "그림으로 보여줘" → `viz`.
4. `quiz` → `학습자료/선형계획법_퀴즈.html` 생성.

결과물은 **단일 HTML 파일**(이미지 base64 내장, 라이트/다크 모드, 왼쪽 페이지 색인, 용어 툴팁)이라 그대로 열거나 공유할 수 있습니다. 모든 산출물은 현재 작업 디렉터리의 `학습자료/` 폴더에 저장됩니다.

## 저장소 구조

```
plugin.json                    이식 가능한 플러그인 매니페스트(agent-plugins.org 스키마) — Codex가 읽음
.codex-plugin/plugin.json      Codex 호환 매니페스트(구버전용)
.agents/plugins/marketplace.json   Codex 마켓플레이스 정의
.claude-plugin/plugin.json     Claude Code 매니페스트
.claude-plugin/marketplace.json    Claude Code 마켓플레이스 정의
package.json                   MathJax 의존성(skills/math/tex2svg.js가 씀)
skills/
  generator/   SKILL.md + toc.css, jump.html, glossary.html, pageidx.html
  research/    SKILL.md + tocidx.html
  supplement/
  example/
  viz/         SKILL.md + viz.css
  math/        SKILL.md + tex2svg.js, math.css
  quiz/
```

SKILL.md 안의 파일 참조는 모두 **그 SKILL.md가 있는 폴더 기준 상대 경로**(`../math/math.css` 등)라 어느 에이전트에서든 같은 뜻입니다. 호출 이름과 도구 이름이 에이전트마다 다른 곳은 본문에 두 가지를 함께 적었습니다(`/ta:math` · `$math`, WebSearch · 그 환경의 검색 도구).

## 개발

```bash
claude plugin validate . --strict            # Claude Code 매니페스트·스킬 검사
claude --plugin-dir .                        # Claude Code에서 로컬 로드
codex plugin marketplace add .               # Codex에 로컬 마켓플레이스로 등록
```

## License

MIT
