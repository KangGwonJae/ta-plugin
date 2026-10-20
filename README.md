# ta — Teaching Assistant skills for Claude Code

강의 PDF·슬라이드(또는 웹 조사)를 근거로 **중학생도 이해할 수 있는 학습자료 HTML**을 만들고, 거기에 보충 설명·예시·그림·수식·퀴즈를 덧붙이는 Claude Code 플러그인입니다. 한국어·영어 자료 모두 다룹니다.

*English summary at the bottom.*

## 설치

Claude Code 안에서:

```
/plugin marketplace add KangGwonJae/ta-plugin
/plugin install ta@ta-plugin
```

설치 후 새 세션을 열면 `/ta:generator` 같은 명령이 생깁니다.

### 선택 의존성

| 스킬 | 필요한 것 | 비고 |
|---|---|---|
| `math` | Node.js 18+ | 플러그인 설치 시 루트의 package.json으로 MathJax가 자동 설치됩니다. 안 되어 있으면 플러그인 루트에서 `npm install`을 한 번 합니다. |
| `math`, `viz` | Google Chrome | 결과를 헤드리스로 캡처해 확인하는 단계에만 씁니다. 없으면 건너뜁니다. |
| `generator` | PDF/PPTX를 읽는 수단 | 자료가 PDF·슬라이드면 Claude Code의 파일 읽기 또는 `pdf`/`pptx` 스킬이 있으면 더 좋습니다. |

## 스킬

| 명령 | 하는 일 | 입력 |
|---|---|---|
| `/ta:generator` | 사용자가 준 자료를 근거로 학습자료 HTML 생성 | `<주제> [자료 경로]` |
| `/ta:research` | 자료가 없을 때 웹에서 조사해 학습자료 HTML 생성(출처 번호 포함) | `<주제> [범위·수준 메모]` |
| `/ta:supplement` | 이해 안 되는 부분 바로 뒤에 "보충 설명" 블록 추가 | `"<막힌 문장 또는 스크린샷>" [질문] [경로]` |
| `/ta:example` | 해당 부분 바로 뒤에 "추가 예시" 블록 추가 | `"<복사한 부분 또는 스크린샷>" [경로]` |
| `/ta:viz` | 구조·흐름·크기 비교를 인라인 SVG/CSS 도식으로 추가 | `"<복사한 부분 또는 스크린샷>" [경로]` |
| `/ta:math` | 수식을 MathJax SVG로 바꾸고 항별·조합별 뜻 설명 추가 | `[경로] [수식 또는 위치]` |
| `/ta:quiz` | 학습자료를 근거로 자동 채점 퀴즈 HTML 생성 | `[경로] [문항 수]` |

`example`, `viz`, `math`는 다른 스킬이 예시·그림·수식을 쓸 때 따르는 **공용 규칙**이기도 합니다. 직접 호출하면 기존 학습자료에 그 요소를 덧붙입니다.

### 전형적인 흐름

1. 강의 자료가 있는 폴더에서 `/ta:generator 선형계획법 lecture3.pdf` → `학습자료/선형계획법_학습자료.html` 생성.
2. 읽다가 막히면 그 문장을 붙여 넣고 "이게 무슨 말이야?" → `supplement`가 보충 설명을 그 자리에 덧붙임.
3. "예시 하나 더" → `example`, "그림으로 보여줘" → `viz`.
4. `/ta:quiz` → `학습자료/선형계획법_퀴즈.html` 생성.

결과물은 **단일 HTML 파일**(이미지 base64 내장, 라이트/다크 모드, 왼쪽 페이지 색인, 용어 툴팁)이라 그대로 열거나 공유할 수 있습니다. 모든 산출물은 현재 작업 디렉터리의 `학습자료/` 폴더에 저장됩니다.

## 구조

```
.claude-plugin/
  plugin.json          플러그인 매니페스트
  marketplace.json     깃허브에서 바로 설치하기 위한 마켓플레이스 정의
skills/
  generator/           SKILL.md + toc.css, jump.html, glossary.html, pageidx.html
  research/            SKILL.md + tocidx.html
  supplement/
  example/
  viz/                 SKILL.md + viz.css
  math/                SKILL.md + tex2svg.js, math.css
  quiz/
```

스킬 간 참조는 `${CLAUDE_PLUGIN_ROOT}/skills/<name>/...` 형태입니다. Claude Code가 이 변수를 플러그인 설치 경로로 채웁니다.

## 다른 에이전트에서 쓰기

각 `skills/<name>/SKILL.md`는 [Agent Skills](https://agentskills.io) 형식이라 Codex CLI, Gemini CLI, Cursor 등 SKILL.md를 읽는 에이전트에 폴더째 복사해 쓸 수 있습니다. 다만 다음은 Claude Code 전용이므로 그 환경에 맞게 읽어야 합니다.

- `${CLAUDE_PLUGIN_ROOT}`: 플러그인 루트. 변수가 없으면 `skills/` 상위 폴더를 뜻합니다.
- `argument-hint`, `$ARGUMENTS`, `/ta:<name>` 슬래시 명령 표기.
- `research`가 쓰는 WebSearch / WebFetch / Agent 도구 이름. 해당 에이전트의 웹 검색·페이지 읽기·서브에이전트 도구로 바꿔 읽으면 됩니다.

## 개발

```bash
claude plugin validate .                 # 매니페스트와 스킬 검사
claude --plugin-dir . # 로컬에서 플러그인을 올려 테스트
```

## License

MIT

---

## English

`ta` is a Claude Code plugin with seven skills that turn lecture PDFs/slides (`generator`) or web research (`research`) into single-file HTML study notes a middle-schooler can follow, in Korean or English. The other skills edit those notes in place: `supplement` adds an explanation right after the sentence you got stuck on, `example` adds a worked example, `viz` adds an inline SVG/CSS diagram, `math` converts formulas to MathJax SVG with term-by-term explanations, and `quiz` builds a self-grading quiz HTML from the notes.

Install inside Claude Code:

```
/plugin marketplace add KangGwonJae/ta-plugin
/plugin install ta@ta-plugin
```

Optional dependencies: Node.js for `math` (installed automatically from the root package.json, or run `npm install` at the plugin root once), Google Chrome for the headless preview step in `math`/`viz`. Output goes to a `학습자료/` folder in the current working directory. The SKILL.md files follow the open Agent Skills format and can be copied into other agents that read SKILL.md; see "다른 에이전트에서 쓰기" above for the Claude Code–specific bits.
