# ta 플러그인 1.2: 공용 스크립트·설정·조각 버전·eval·generator 보강

작성 2026-10-20. 브레인스토밍에서 사용자가 고른 다섯 항목을 한 번에 적용한다.

## 의도

- 다섯 스킬이 각자 즉석에서 짜던 절차(태그 뗀 텍스트 검색, 백업, 공용 조각 주입, 그림 자르기, Chrome 캡처)를 **결정론적 스크립트**로 옮겨 토큰을 줄이고 결과를 일정하게 한다.
- 학습 대상·언어·출력 폴더를 **설정 파일**로 뺀다. 영어 사용자가 `학습자료/`라는 폴더명과 한국어 UI 없이 쓸 수 있게 한다.
- 공용 조각(jump/glossary/pageidx/tocidx/toc.css/viz.css/math.css)에 **버전**을 넣어 구버전 문서를 판별·갱신할 수 있게 한다(나중의 `doctor` 스킬 전제).
- `claude plugin eval`로 돌릴 **회귀 테스트**를 둔다.
- `generator`: 긴 자료 분할 + 허브 index, 절별 읽음 체크, 인쇄 CSS, 예상 읽기 시간.

## 비목표

- 새 스킬(doctor, teach, hub 스킬)은 만들지 않는다. 허브는 스크립트 한 줄로 만드는 `index.html`까지만.
- 사용자의 기존 학습자료 파일을 이번에 갱신하지 않는다(스크립트로 가능해지기만 한다).
- 모바일 레이아웃 개선은 하지 않는다.

## 제약

- 스크립트는 Python 3 표준 라이브러리만 쓴다. 그림 자르기만 Pillow를 선택 의존(없으면 안내 후 종료).
- SKILL.md는 런타임 중립을 유지한다. 스크립트 경로는 SKILL.md 기준 상대 경로 `../../scripts/ta.py`로 적는다.
- 마커 이름(`/*ta-math:start*/`, `/*ta-viz:start*/`, `<!--jump:start-->` 등)은 바꾸지 않고 **버전만 덧붙인다**. 옛 마커(버전 없음)는 v0으로 읽는다.
- 출력은 계속 단일 HTML 파일이다.

## A. `scripts/ta.py` (단일 진입점, 서브커맨드)

호출: `python3 <플러그인 루트>/scripts/ta.py <cmd> …`. 모든 서브커맨드는 `--json`으로 기계가 읽을 결과를 낸다.

| cmd | 하는 일 |
|---|---|
| `config [--dir D]` | `.ta.json`을 찾아 기본값과 합친 설정과 파생값(출력 폴더, 파일 접미사, 대상 설명문)을 출력 |
| `text <html> [--out F]` | style/script/svg/base64를 떼고 태그를 벗긴 텍스트. 블록마다 `[id=…]`, `.src` 배지는 `⟦p.N⟧`, 수식은 `⟦tex: …⟧`로 남긴다. quiz·supplement가 읽는 용도 |
| `find <html> "<query>" [--all]` | 공백·줄바꿈 차이를 무시하고(없으면 유사 문장으로) 질의를 담는 **가장 작은 블록**을 찾아 후보 목록 출력: 점수, 태그, id, 블록의 원본 오프셋(start,end), 질의 텍스트의 원본 오프셋, 앞뒤 문맥 |
| `insert <html> --after <offset|#id> --file F` | 블록 끝 오프셋(또는 id 블록) 뒤에 HTML 조각 삽입 |
| `wrap <html> --start S --end E --open '<mark …>' --close '</mark>'` | 원본 오프셋 구간을 태그로 감싼다(형광펜 표시용). 태그 경계를 넘으면 오류 |
| `backup <html>` | `<폴더>/.backup/<이름>_<YYYYMMDD-HHMMSS>.html`로 복사하고 경로 출력 |
| `fragments <html> [--main NAME] [--check]` | 공용 조각을 넣거나 최신으로 갈아 끼운다. CSS(toc·viz·math)는 `</style>` 앞, HTML 조각(jump → glossary → pageidx|tocidx → reader)은 `</body>` 앞 순서. 문서 종류(generator/research)와 viz·math 사용 여부는 문서에서 자동 판별. `--check`는 수정 없이 버전표만 출력 |
| `clip <pdf> <page> [--box x0,y0,x1,y1] [--width 1200] [--out F] [--tag]` | 페이지를 렌더링해 자르고(박스는 0~1 비율) 폭 1200 JPEG q80 → data URI 또는 `<img>` 태그. `--preview`는 비율 눈금이 그려진 저해상도 PNG를 만들어 박스를 고르게 한다 |
| `shot <html> --id ID [--dark] [--width 820] [--out F]` | 문서에서 요소 하나를 문서 CSS와 함께 미리보기 HTML로 뽑아 헤드리스 Chrome으로 캡처. Chrome이 없으면 건너뛴다고 알리고 exit 0 |
| `hub [--dir 출력폴더]` | 출력 폴더의 `*_학습자료.html`·`*_퀴즈.html`을 훑어 `index.html`(제목, 원자료, 분할 부 번호, 보충·예시·시각화 수, 퀴즈 링크, 수정일) 생성 |
| `stats <html>` | 글자 수, 예상 읽기 시간, 섹션·예시·시각화·보충 수 |

구현 메모(빌더에게 맡김): 오프셋이 필요한 명령은 `html.parser.HTMLParser`로 원본 오프셋을 보존하는 가벼운 트리를 만든다. `convert_charrefs=False`. 닫히지 않은 `li`/`p`/`td`/`tr`는 관대하게 닫는다. `find`의 유사 검색은 질의에서 긴 토큰을 골라 후보 위치를 모으고 `difflib` 비율로 순위를 매긴다.

## B. 설정 파일 `.ta.json`

**위치(내 결정)**: 출력 폴더명 자체가 설정이므로 `학습자료/.ta.json`에 둘 수 없다. 찾는 순서는 `<작업 디렉터리>/.ta.json` → `~/.ta.json` → 기본값.

```json
{ "level": "middle", "lang": "ko", "out_dir": null, "open": true }
```

- `level`: `middle`(현재 기본: 한국어·영어 되는 중학생, 분야 지식 없음) · `undergrad`(학부생: 고교 수학과 기초 프로그래밍 전제, 용어 카드는 유지, 설명은 더 압축) · 그 외 문자열은 대상 설명문으로 그대로 쓴다.
- `lang`: 본문·UI 언어 `ko`|`en`. 조각(jump/glossary/pageidx/tocidx/reader)은 `<html lang>`을 보고 문자열을 고른다.
- `out_dir`: null이면 `lang`에 따라 `학습자료` / `study-notes`. 파일 접미사도 `_학습자료`·`_퀴즈` / `_notes`·`_quiz`.
- `open`: 생성 후 브라우저로 열지.

`config` 서브커맨드가 합친 값을 내고, 모든 SKILL.md는 첫 단계에서 이것을 읽어 폴더·접미사·대상·언어를 정한다. 기존 문서는 `<html lang>`과 파일명으로 그대로 동작한다.

## C. 조각 버전

- 시작 마커에 버전을 넣는다: `<!--jump:start v2-->`, `/* toc:start v2 … */`, `/*ta-viz:start v2*/`, `/*ta-math:start v2*/`. 끝 마커는 그대로.
- 버전이 없으면 v0. `fragments`는 문서 버전 < 배포 버전이면 교체한다. `pageidx`의 `data-main`은 교체 때 보존한다.
- 이번에 바뀌는 조각은 모두 v2로 올린다(i18n 문자열 추가). 새 조각 `reader.html`은 v1.

## D. eval 스위트 `evals/`

- 레이아웃: `evals/<case>/prompt.md` + `graders/*.md`, 입력 파일은 `evals/fixtures/`(작은 샘플 HTML·짧은 PDF)에 두고 prompt에서 경로로 가리킨다.
- 케이스(각 `runs: 1`): generator-trigger(스킬 발화 + 출력 파일 + 조각 마커 + 본문 `<ol>` 없음), supplement-insert(`details.sup`·`sup-mark` 추가, 원문 보존), math-convert(`<sub>` 수식이 `class="m"`으로), quiz-build(`_퀴즈.html` 생성, `data-type` 문항), fragments-upgrade(스크립트만: 옛 문서가 최신 마커로).
- 채점기는 결정론적인 것(regex·file_exists·tool_used) 위주, llm 채점기는 "중학생 말투·번호 목록 없음" 한 개.
- 스크립트 단위 테스트는 `scripts/tests/`에 `unittest`로 두고 `python3 -m unittest discover scripts/tests`로 돌린다.

## E. generator 보강

- **분할**: 원자료가 약 80쪽을 넘거나 핵심 개념이 15개를 넘으면 장(章) 경계로 2~4부로 나눈다. 파일명 `<원본>_학습자료_1.html`, `_2.html`…(quiz는 `<원본>_1_퀴즈.html`). 각 부는 독립 문서(자기 용어 카드·목차·색인)이고 제목 아래 `<nav class="parts">`로 다른 부 링크, 끝에 이전/다음 링크. 분할 뒤 `hub`로 `index.html`을 만든다.
- **읽음 체크·읽기 시간·인쇄**: 새 조각 `reader.html`(generator 폴더). 각 `h2`/`h3` 오른쪽에 읽음 체크박스(localStorage, 파일명 키), 제목 아래 진행 막대와 "예상 읽기 시간 N분 · 남은 시간"(본문 글자 수 ÷ 분당 500자, 그림·수식 블록당 가산), 인쇄 전에 접힌 `details`를 모두 펼치고 끝나면 복원. 인쇄 CSS(`@media print`: 고정 패널·버튼·체크박스 숨김, 카드 쪽 나눔 방지, 링크 밑줄 제거)는 `toc.css`에 넣는다.

## 빌더에게 맡기는 것

- 트리 파서의 세부 구현과 유사 검색 임계값.
- `reader.html`의 시각 디자인(기존 조각의 톤을 따른다).
- 영어 문자열의 정확한 문구.
