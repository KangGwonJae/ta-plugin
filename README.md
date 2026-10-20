# ta — Teaching Assistant skills

<p align="center">
  <a href="README.md"><img alt="한국어" src="https://img.shields.io/badge/한국어-현재-2e7d32?style=for-the-badge"></a>
  <a href="README_eng.md"><img alt="English" src="https://img.shields.io/badge/English-switch-555555?style=for-the-badge"></a>
</p>

강의 PDF나 슬라이드를 주면 **중학생도 읽을 수 있는 학습자료 HTML**을 만들어 주는 AI 조교 스킬 모음입니다. 읽다가 막히면 그 자리에 보충 설명·예시·그림을 덧붙이고, 다 읽으면 퀴즈를 냅니다.

- 결과는 **HTML 파일 하나**입니다. 그림이 안에 들어 있어 그냥 열거나 보내면 됩니다.
- 모든 문장에 **출처(슬라이드 쪽수)** 가 붙고, 자료에 없는 내용은 "(자료 외 보충)"으로 표시됩니다.
- Claude Code와 Codex 양쪽에서 같은 저장소로 설치됩니다.

## 설치

**Claude Code**

```
/plugin marketplace add KangGwonJae/ta-plugin
/plugin install ta@ta-plugin
```

**Codex** (CLI 또는 ChatGPT 데스크톱 앱)

```
codex plugin marketplace add KangGwonJae/ta-plugin
```

그다음 `/plugins`에서 **ta**를 설치하고 새 세션을 엽니다.

**그 외 SKILL.md를 읽는 에이전트** (Gemini CLI, Cursor 등): 저장소를 받아 `skills/`와 `scripts/` 두 폴더를 에이전트의 스킬 폴더 옆에 복사합니다. 예: `~/.agents/skills/`와 `~/.agents/scripts/`.

## 사용법

강의 자료가 있는 폴더에서 에이전트를 엽니다. Claude Code는 `/ta:스킬이름`, Codex는 `$스킬이름`으로 부릅니다.

1. **학습자료 만들기**
   `/ta:generator 뉴턴 운동 법칙 chapter2.pdf`
   → `학습자료/chapter2.pdf_학습자료.html`이 만들어지고 브라우저로 열립니다.

2. **읽다가 막히면** 그 문장을 복사해 붙이고 물어봅니다.
   `"질량이 두 배가 되면 같은 힘으로는 가속도가 절반이 된다" 왜 그래?`
   → `supplement`가 그 문장 바로 아래에 접을 수 있는 **보충 설명**을 넣습니다.
   `예시 하나 더` → `example`, `그림으로 보여줘` → `viz`, `이 수식 풀어줘` → `math`.

3. **다 읽으면** `/ta:quiz`
   → `학습자료/chapter2.pdf_퀴즈.html`. 객관식은 바로 채점되고, 주관식은 모범답안을 보고 스스로 채점합니다.

자료 파일이 없으면 `/ta:research 주제`가 웹에서 찾아 같은 모양의 학습자료를 만듭니다. 출처는 번호 `[1]`로 달립니다.

### 학습자료 안에 있는 것

- 접을 수 있는 **용어 카드**. 본문의 용어를 누르면 오른쪽에 카드가 뜹니다.
- 개념마다 **실제 숫자로 된 예시**와, 필요하면 **도식**과 **수식 풀이**(항마다 뜻을 색으로 짝지어 설명).
- 원자료의 핵심 그림·문장을 가져와 붙인 **해설**.
- 왼쪽에 **슬라이드 쪽수 색인**. 지금 읽는 위치의 쪽이 표시되고, 누르면 그 쪽을 인용한 곳으로 갑니다.
- 절마다 **읽음 체크**와 **예상 읽기 시간**. 라이트/다크 모드, 인쇄용 레이아웃.
- 자료가 80쪽을 넘으면 여러 부로 나뉘고, `학습자료/index.html`에 목록이 생깁니다.

## 스킬 목록

학습자료를 **새로 만드는** 스킬 둘과, 이미 만든 학습자료에 **덧붙이는** 스킬 다섯입니다.

| 스킬 | 하는 일 | 부를 때 주는 것 |
|---|---|---|
| `generator` | 강의 PDF·슬라이드를 읽고 학습자료 HTML을 새로 만듭니다 | 주제, 자료 파일 이름 |
| `research` | 자료 파일이 없을 때 웹에서 조사해 학습자료 HTML을 새로 만듭니다 | 주제 |
| `supplement` | 학습자료에서 이해 안 되는 문장을 붙여 넣으면, 그 문장 바로 아래에 더 쉬운 보충 설명을 끼워 넣습니다 | 학습자료에서 복사한 문장(또는 그 화면 스크린샷), 질문 |
| `example` | 학습자료의 한 대목을 붙여 넣으면, 그 대목 바로 아래에 실제 숫자로 된 예시를 하나 더 끼워 넣습니다 | 학습자료에서 복사한 문장 |
| `viz` | 학습자료의 한 대목을 붙여 넣으면, 그 내용을 구조·흐름 도식으로 그려 넣습니다 | 학습자료에서 복사한 문장 |
| `math` | 학습자료에 글자로 적힌 수식을 제대로 조판하고, 식의 항마다 뜻을 풀어 적습니다 | 없음 (특정 수식만 고치려면 그 수식) |
| `quiz` | 학습자료 내용으로 자동 채점 퀴즈 HTML을 따로 만듭니다 | 없음 (문항 수를 정하려면 숫자) |

덧붙이는 스킬은 어느 학습자료를 고칠지 따로 말하지 않으면 `학습자료/`에서 가장 최근에 수정한 파일을 고릅니다.

## 설정 (선택)

자료가 있는 폴더에 `.ta.json`을 두면 바꿀 수 있습니다. 없으면 아래 기본값입니다.

```json
{ "level": "middle", "lang": "ko", "out_dir": null, "open": true }
```

| 키 | 뜻 |
|---|---|
| `level` | 읽는 사람. `middle`(중학생, 기본), `undergrad`(학부생), 또는 "박사과정 신입생"처럼 직접 쓴 문장 |
| `lang` | `ko` 또는 `en`. `en`이면 본문·버튼이 영어, 폴더는 `study-notes/`, 파일 이름 끝은 `_notes`·`_quiz` |
| `out_dir` | 출력 폴더 이름. `null`이면 `학습자료/`(영어는 `study-notes/`) |
| `open` | 만든 뒤 브라우저로 열지 |

## 필요한 것

| 무엇 | 언제 |
|---|---|
| Python 3.9+ | 항상. 스킬이 쓰는 공용 스크립트 `scripts/ta.py`가 Python입니다. |
| poppler (`pdftotext`, `pdftoppm`) | PDF를 읽을 때 |
| Pillow (`pip install pillow`) | 원자료 그림을 잘라 넣을 때. 없으면 그림만 빠집니다. |
| Node.js 18+ | 수식(`math`)을 그릴 때. Claude Code는 설치 때 자동으로 `npm install`을 하고, 그 외에는 저장소 루트에서 한 번 실행합니다. |
| Google Chrome | 그림·수식을 캡처해 확인하는 단계. 없으면 건너뜁니다. |

## 더 보기

- 저장소 구조, 공용 스크립트 명령, 테스트와 eval 실행법: [docs/development.md](docs/development.md)
- 예전에 만든 학습자료를 최신 기능(읽음 체크, 인쇄 레이아웃)으로 올리기: `python3 scripts/ta.py fragments <파일>`

## License

MIT
