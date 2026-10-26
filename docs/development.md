# 개발 안내

README에 없는 내부 구조와 개발 절차입니다.

## 저장소 구조

```
plugin.json                        이식 가능한 플러그인 매니페스트(agent-plugins.org 스키마) — Codex가 읽음
.codex-plugin/plugin.json          Codex 호환 매니페스트(구버전용)
.agents/plugins/marketplace.json   Codex 마켓플레이스 정의
.claude-plugin/plugin.json         Claude Code 매니페스트
.claude-plugin/marketplace.json    Claude Code 마켓플레이스 정의
package.json                       MathJax 의존성(skills/math/tex2svg.js가 씀), `build:v3d` 스크립트
scripts/
  ta.py                            공용 스크립트(아래)
  tests/test_ta.py                 단위 테스트
skills/
  generator/   SKILL.md + toc.css, jump.html, glossary.html, pageidx.html, reader.html
  research/    SKILL.md + tocidx.html
  supplement/
  example/
  regenerate/
  viz/         SKILL.md + viz.css, v3d.css, v3d.html(빌드 결과), 3d/(entry.js, runtime.js, build.mjs)
  math/        SKILL.md + tex2svg.js, math.css
  quiz/
evals/<케이스>/                      claude plugin eval 케이스(prompt.md, graders/, fixtures/, scaffold.sh, case.yaml)
docs/superpowers/specs/            설계 문서
```

SKILL.md 안의 파일 참조는 모두 **그 SKILL.md가 있는 폴더 기준 상대 경로**(`../math/math.css`, `../../scripts/ta.py`)입니다. `${CLAUDE_PLUGIN_ROOT}` 같은 변수는 Codex가 치환하지 않으므로 쓰지 않습니다. 호출 이름과 도구 이름이 에이전트마다 다른 곳은 본문에 두 가지를 함께 적습니다(`/ta:math` · `$math`, WebSearch · 그 환경의 검색 도구).

## 공용 스크립트 `scripts/ta.py`

스킬이 즉석 코드를 짜는 대신 부르는 결정론적 도구입니다. Python 3 표준 라이브러리만 쓰고 `clip`만 Pillow가 필요합니다. `python3 scripts/ta.py <명령> --help`.

| 명령 | 하는 일 |
|---|---|
| `config [--dir D]` | `.ta.json`을 기본값과 합쳐 출력(출력 폴더·파일 접미사·학습 대상 설명 포함) |
| `text <html> [--out F]` | style/script/svg/base64를 떼고 태그를 벗긴 텍스트. 블록 id는 `[id=c3]`, 출처는 `⟦src: p.18⟧`, 수식은 `⟦tex: …⟧` |
| `find <html> "<문장>" [--json]` | 공백 차이를 무시하고(없으면 유사 문장으로) 그 문장을 담는 가장 작은 블록과 원본 오프셋 |
| `insert <html> --after <오프셋|#id> --file F` | 블록 뒤에 HTML 조각 삽입(자동 백업) |
| `wrap <html> --start S --end E --open '<mark …>' --close '</mark>'` | 구간을 태그로 감싸기. 태그에 걸치면 거부 |
| `replace <html> --id ID(또는 --start S --end E) --file F [--dry-run]` | 블록을 조각으로 교체(자동 백업). 제목 id면 다음 같은 급 제목 전까지의 절 전체. 원래 구간에 있던 id 중 새 조각에 없는 것(`missing_ids`)을 보고하고, 구간 밖 id와 겹치면 거부. `--dry-run`은 구간·id·텍스트만 |
| `backup <html>` | `<폴더>/.backup/<이름>_<일시>.html`로 복사 |
| `fragments <html> [--main 원자료] [--check] [--force]` | 공용 조각을 넣거나 구버전을 교체. 문서 종류(generator/research)와 viz·math·3D·수식 연동 사용 여부는 자동 판별 |
| `clip <pdf> <쪽> [--box x0,y0,x1,y1] [--tag] [--preview]` | 페이지를 렌더링해 비율 박스로 자르고 폭 1200 JPEG data URI(또는 `<img>`)로. `--preview`는 눈금 그린 미리보기 |
| `shot <html> --id ID [--dark] [--width W] [--step N]` | 요소 하나를 문서 CSS와 함께 헤드리스 Chrome으로 캡처. 3D 시각화면 런타임·장면 정의를 함께 넣고 소프트웨어 WebGL로 그리며, `--step`으로 그 단계(0부터)를 찍음. Chrome이 없으면 건너뜀(`TA_CHROME`으로 지정 가능) |
| `hub [--dir 폴더]` | 출력 폴더의 학습자료·퀴즈를 모은 `index.html` 생성 |
| `stats <html>` | 글자 수, 예상 읽기 시간, 예시·시각화·보충 수, 원자료 파일명 |
| `mathscan <html>` | 아직 SVG로 안 바뀐 수식 후보(`<sub>/<sup>`, 유니코드 기호, monospace 식) |

## 공용 조각과 버전

학습자료에 들어가는 공용 CSS·스크립트는 시작·끝 주석으로 감싸고 시작 주석에 버전을 적습니다.

| 조각 | 마커 | 하는 일 |
|---|---|---|
| `generator/toc.css` | `/* toc:start v2 … */` | 목차 번호, 본문 공통 스타일, 인쇄 CSS |
| `viz/viz.css` | `/*ta-viz:start v1*/` | 도식 색·범례 |
| `viz/v3d.css` | `/*ta-v3d:start v1*/` | 3D 시각화의 무대·단계 버튼·라벨(문서에 `class="v3d"`가 있을 때만) |
| `math/math.css` | `/*ta-math:start v1*/` | 수식 블록, 항 색 짝짓기 표 |
| `generator/jump.html` | `<!--jump:start v2-->` | 문서 안 링크 이동과 "읽던 곳으로" 되돌아가기 |
| `generator/glossary.html` | `<!--glossary:start v3-->` | 용어 카드 패널, 약자의 원래 단어(`tc-full`) |
| `generator/pageidx.html` | `<!--pageidx:start v2-->` | 왼쪽 슬라이드 쪽수 색인(generator 문서) |
| `research/tocidx.html` | `<!--tocidx:start v2-->` | 왼쪽 절 목차(research 문서) |
| `generator/reader.html` | `<!--reader:start v1-->` | 절별 읽음 체크, 진행 막대와 읽기 시간, 인쇄 전 펼치기 |
| `math/eqlink.html` | `<!--eqlink:start v1-->` | 수식 표 줄 ↔ 식의 항 ↔ 그림(`data-eq`, `data-t`) 함께 강조, 표 아래 안내 문장. 문서에 `data-eq`가 있을 때만 |
| `viz/v3d.html` | `<!--v3d:start v1-->` | three.js 일부(약 550KB) + 3D 런타임. `npm run build:v3d`로 `viz/3d/`에서 만든다. 버전은 `3d/build.mjs`의 `VERSION` |

조각 파일을 고치면 시작 주석의 버전을 올립니다. 그러면 `ta.py fragments <파일>`이 옛 문서의 그 조각만 교체합니다. 버전이 없는 옛 마커는 v0으로 봅니다. 조각 스크립트는 `<html lang>`이 `en`이면 영어 문자열을 씁니다.

## 검사와 테스트

```bash
claude plugin validate . --strict                 # 매니페스트·스킬 검사
python3 -m unittest discover -s scripts/tests     # 공용 스크립트 단위 테스트
claude --plugin-dir .                             # Claude Code에서 로컬 로드
codex plugin marketplace add .                    # Codex에 로컬 마켓플레이스로 등록
```

### eval (실제 모델을 돌리므로 비용이 듭니다)

```bash
claude plugin eval . --scaffold --trust-plugin \
  --allow-tools Bash Write Edit Read Glob Grep Skill --no-publish
claude plugin eval . --case 'math-*' --ablation none ...   # 케이스 하나, 기준선 없이
```

- 케이스는 `evals/<이름>/`에 `prompt.md`(프롬프트와 runs·max_turns 등), `graders/*.md`(채점기), `fixtures/`(입력 파일), `scaffold.sh`, `case.yaml`로 구성됩니다.
- 실행은 빈 샌드박스 폴더에서 시작합니다. `scaffold.sh`가 그 폴더에 `fixtures/`를 복사하므로 **`--scaffold`가 꼭 필요**합니다. 채점기의 파일 경로는 그 폴더 기준 상대 경로여야 합니다.
- 채점기는 결정론적인 것 위주입니다: `tool_used`(스킬 발화, 스크립트 사용), `file_exists`, 만들어진 파일에 대한 `regex`. `llm` 채점기는 응답 형태 확인 하나뿐입니다.
- 케이스당 1회 실행 기준 약 $0.5~1이 듭니다(generator는 더 큽니다).

## 릴리스

1. 네 매니페스트(`plugin.json`, `.codex-plugin/plugin.json`, `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`)의 `version`을 올립니다.
2. 위 검사·테스트를 돌립니다.
3. 커밋·푸시 후 `claude plugin tag .`로 `ta--v<버전>` 태그를 만들고 `git push origin --tags`.
