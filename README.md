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

SKILL.md가 공용 스크립트를 `../../scripts/ta.py`로 찾으므로 `scripts/` 폴더도 함께 복사합니다(`cp -r ta-plugin/scripts ~/.agents/scripts`). 수식(`math`)을 쓰려면 플러그인 루트에서 `npm install`을 한 번 해 두세요.

### 선택 의존성

| 스킬 | 필요한 것 | 비고 |
|---|---|---|
| 모든 스킬 | Python 3.9+ | 공용 스크립트 `scripts/ta.py`(표준 라이브러리만)가 텍스트 추출·검색·삽입·공용 조각 주입을 맡습니다. |
| `generator` | poppler(`pdftotext`, `pdftoppm`), Pillow | PDF 읽기와 원자료 그림 자르기(`ta.py clip`)에 씁니다. Pillow가 없으면 그림만 건너뜁니다. |
| `math` | Node.js 18+ | 루트 `package.json`으로 MathJax를 설치합니다. Claude Code는 플러그인 설치 때 자동으로 하고, 그 외에는 루트에서 `npm install` 한 번. |
| `math`, `viz` | Google Chrome | 결과를 헤드리스로 캡처해 확인하는 단계(`ta.py shot`)에만 씁니다. 없으면 건너뜁니다(`TA_CHROME`으로 경로 지정 가능). |
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

결과물은 **단일 HTML 파일**(이미지 base64 내장, 라이트/다크 모드, 왼쪽 페이지 색인, 용어 툴팁, 절별 읽음 체크와 예상 읽기 시간, 인쇄용 CSS)이라 그대로 열거나 공유할 수 있습니다. 모든 산출물은 현재 작업 디렉터리의 `학습자료/` 폴더(설정으로 변경 가능)에 저장됩니다. 80쪽이 넘는 자료는 여러 부로 나뉘고 `학습자료/index.html`(허브)이 함께 만들어집니다.

## 설정 (`.ta.json`)

작업 디렉터리(강의 자료가 있는 곳)에 `.ta.json`을 두면 모든 스킬이 읽습니다. 없으면 `~/.ta.json`, 그것도 없으면 기본값입니다.

```json
{ "level": "middle", "lang": "ko", "out_dir": null, "open": true }
```

| 키 | 값 | 뜻 |
|---|---|---|
| `level` | `middle`(기본) · `undergrad` · 자유 문장 | 학습 대상. `middle`은 분야 지식 없는 중학생, `undergrad`는 고교 수학·기초 프로그래밍을 아는 학부생. 자유 문장은 그대로 대상 정의로 씁니다. |
| `lang` | `ko`(기본) · `en` | 본문과 UI 언어. `en`이면 출력 폴더가 `study-notes/`, 접미사가 `_notes`·`_quiz`가 되고 버튼·라벨도 영어가 됩니다. |
| `out_dir` | 폴더명 또는 `null` | 출력 폴더. `null`이면 언어 기본값. |
| `open` | `true`/`false` | 생성 후 브라우저로 열지. |

`python3 scripts/ta.py config`로 합쳐진 값을 볼 수 있습니다.

## 공용 스크립트 `scripts/ta.py`

스킬들이 즉석 코드를 짜는 대신 쓰는 결정론적 도구입니다(Python 3 표준 라이브러리, `clip`만 Pillow).

| 명령 | 하는 일 |
|---|---|
| `config` | 설정 출력 |
| `text <html>` | style/script/svg/base64를 떼고 태그를 벗긴 텍스트(블록 id·출처·수식 표시 유지) |
| `find <html> "<문장>"` | 공백 차이를 무시하고(없으면 유사 문장으로) 그 문장을 담는 가장 작은 블록과 원본 오프셋 |
| `insert` · `wrap` · `backup` | 블록 뒤 삽입, 구간을 태그로 감싸기(형광펜), `.backup/`으로 복사 |
| `fragments <html> [--check]` | 공용 조각(toc/viz/math CSS, jump·glossary·pageidx|tocidx·reader)을 넣거나 구버전을 교체 |
| `clip <pdf> <쪽> [--box …]` | 페이지를 렌더링해 비율 박스로 자르고 폭 1200 JPEG data URI로 |
| `shot <html> --id …` | 요소 하나를 문서 CSS와 함께 헤드리스 Chrome으로 캡처(`--dark`) |
| `hub` · `stats` · `mathscan` | 출력 폴더 index.html, 글자 수·읽기 시간, SVG로 안 바뀐 수식 후보 |

공용 조각에는 버전이 있습니다(`<!--jump:start v2-->`, `/*ta-math:start v1*/`). 예전에 만든 학습자료는 `python3 scripts/ta.py fragments <파일>` 한 번으로 최신 조각(읽음 체크·읽기 시간·인쇄 CSS 포함)으로 올라갑니다.

## 저장소 구조

```
plugin.json                    이식 가능한 플러그인 매니페스트(agent-plugins.org 스키마) — Codex가 읽음
.codex-plugin/plugin.json      Codex 호환 매니페스트(구버전용)
.agents/plugins/marketplace.json   Codex 마켓플레이스 정의
.claude-plugin/plugin.json     Claude Code 매니페스트
.claude-plugin/marketplace.json    Claude Code 마켓플레이스 정의
package.json                   MathJax 의존성(skills/math/tex2svg.js가 씀)
scripts/
  ta.py                        공용 스크립트(위 표)
  tests/test_ta.py             단위 테스트
skills/
  generator/   SKILL.md + toc.css, jump.html, glossary.html, pageidx.html, reader.html
  research/    SKILL.md + tocidx.html
  supplement/
  example/
  viz/         SKILL.md + viz.css
  math/        SKILL.md + tex2svg.js, math.css
  quiz/
evals/                         claude plugin eval 케이스(prompt.md + graders/)와 픽스처
docs/superpowers/specs/        설계 문서
```

SKILL.md 안의 파일 참조는 모두 **그 SKILL.md가 있는 폴더 기준 상대 경로**(`../math/math.css` 등)라 어느 에이전트에서든 같은 뜻입니다. 호출 이름과 도구 이름이 에이전트마다 다른 곳은 본문에 두 가지를 함께 적었습니다(`/ta:math` · `$math`, WebSearch · 그 환경의 검색 도구).

## 개발

```bash
claude plugin validate . --strict            # Claude Code 매니페스트·스킬 검사
python3 -m unittest discover -s scripts/tests   # 공용 스크립트 단위 테스트
claude plugin eval . --scaffold --trust-plugin --allow-tools Bash Write Edit Read Glob Grep Skill --no-publish   # 스킬 회귀 테스트(실제 모델 실행, 비용 발생; --scaffold가 픽스처를 복사)
claude plugin eval . --case 'math-*' ...     # 케이스 하나만
claude --plugin-dir .                        # Claude Code에서 로컬 로드
codex plugin marketplace add .               # Codex에 로컬 마켓플레이스로 등록
```

eval 케이스는 `evals/<이름>/prompt.md`와 `graders/*.md`입니다. 픽스처(`evals/fixtures/`)를 `/tmp/ta-eval-<이름>/`에 복사해 작업하고, 결정론적 채점기(스킬 발화, 파일 생성, 정규식)와 llm 채점기 하나로 채점합니다.

## License

MIT
