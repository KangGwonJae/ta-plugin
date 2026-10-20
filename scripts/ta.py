#!/usr/bin/env python3
"""ta 플러그인 공용 스크립트 (Python 3 표준 라이브러리만 사용; clip만 Pillow 선택).

사용: python3 ta.py <cmd> [...]   (각 cmd는 --help 지원, 대부분 --json 지원)

  config      .ta.json을 찾아 기본값과 합친 설정과 파생값(출력 폴더·접미사·대상 설명)을 출력
  text        학습자료 HTML에서 style/script/svg/base64를 떼고 태그를 벗긴 텍스트(id·출처·수식 표시 유지)
  find        공백 차이를 무시하고(없으면 유사 문장으로) 질의를 담는 가장 작은 블록과 원본 오프셋을 찾음
  insert      블록 끝(오프셋 또는 #id) 뒤에 HTML 조각 삽입
  wrap        원본 오프셋 구간을 여는/닫는 태그로 감쌈(형광펜 표시용)
  backup      <폴더>/.backup/<이름>_<YYYYMMDD-HHMMSS>.html 로 복사
  fragments   공용 조각(toc/viz/math CSS, jump/glossary/pageidx|tocidx/reader)을 넣거나 최신으로 교체
  clip        PDF 페이지를 렌더링해 비율 박스로 자르고 폭 1200 JPEG data URI(또는 <img>)로 출력
  shot        문서의 요소 하나를 문서 CSS와 함께 헤드리스 Chrome으로 캡처(라이트/다크)
  hub         출력 폴더의 학습자료·퀴즈를 훑어 index.html 생성
  stats       글자 수·예상 읽기 시간·블록 수
"""
import argparse
import base64
import difflib
import html as htmlmod
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"

# ---------------------------------------------------------------- 설정

DEFAULTS = {"level": "middle", "lang": "ko", "out_dir": None, "open": True}

LEVELS = {
    "middle": {
        "ko": "한국어와 영어를 할 줄 아는 중학생. 해당 분야 지식 없음.",
        "en": "A middle-school student who reads English (and Korean). No prior knowledge of the field.",
    },
    "undergrad": {
        "ko": "학부생. 고등학교 수학(함수·벡터·확률 기초)과 기초 프로그래밍은 안다고 전제하되, 해당 분야 전문 지식은 없음. 용어 카드는 유지하고 설명은 더 압축한다.",
        "en": "An undergraduate. Assumes high-school math (functions, vectors, basic probability) and basic programming, but no expertise in the field. Keep term cards; explain more concisely.",
    },
}

NAMES = {
    "ko": {"out_dir": "학습자료", "notes": "_학습자료", "quiz": "_퀴즈", "hub_title": "학습자료"},
    "en": {"out_dir": "study-notes", "notes": "_notes", "quiz": "_quiz", "hub_title": "Study notes"},
}


def load_config(start_dir=None):
    cfg = dict(DEFAULTS)
    found = None
    cands = []
    if start_dir:
        cands.append(Path(start_dir) / ".ta.json")
    cands.append(Path.cwd() / ".ta.json")
    cands.append(Path.home() / ".ta.json")
    for c in cands:
        if c.is_file():
            try:
                data = json.loads(c.read_text(encoding="utf-8"))
            except Exception as e:  # noqa: BLE001
                die(f"{c}: JSON 오류: {e}")
            if not isinstance(data, dict):
                die(f"{c}: 객체(JSON object)여야 합니다")
            cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
            found = str(c)
            break
    lang = cfg["lang"] if cfg["lang"] in NAMES else "ko"
    cfg["lang"] = lang
    names = NAMES[lang]
    level = cfg["level"] or "middle"
    level_text = LEVELS.get(level, {}).get(lang) or (LEVELS[level]["ko"] if level in LEVELS else str(level))
    out = {
        **cfg,
        "config_file": found,
        "out_dir": cfg["out_dir"] or names["out_dir"],
        "suffix_notes": names["notes"],
        "suffix_quiz": names["quiz"],
        "level_text": level_text,
        "level_preset": level in LEVELS,
    }
    return out


# ---------------------------------------------------------------- HTML 트리(원본 오프셋 보존)

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
BLOCK = {
    "p", "li", "td", "th", "tr", "table", "thead", "tbody", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "div",
    "details", "summary", "dd", "dt", "dl", "figure", "figcaption", "pre", "ul", "ol", "section", "article", "nav",
    "aside", "main", "header", "footer", "body", "html",
}
CLOSE_P = {"p", "div", "ul", "ol", "table", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "details",
           "section", "nav", "figure", "hr", "dl", "aside", "main", "header", "footer", "article"}
SKIP_TEXT = {"style", "script", "svg", "template", "noscript", "head"}


class Node:
    __slots__ = ("tag", "attrs", "start", "open_end", "end", "children", "parent", "idx", "_close_start")

    def __init__(self, tag, attrs, start, open_end, parent):
        self.tag, self.attrs, self.start, self.open_end, self.parent = tag, attrs, start, open_end, parent
        self.end = None
        self._close_start = None
        self.children = []
        self.idx = 0

    @property
    def id(self):
        return self.attrs.get("id")

    @property
    def classes(self):
        return (self.attrs.get("class") or "").split()

    def inner(self):
        return (self.open_end, self.close_start())

    def close_start(self):
        """닫는 태그가 시작하는 오프셋(없으면 end)."""
        return self._close_start if self._close_start is not None else self.end


class Text:
    __slots__ = ("start", "end", "text", "parent")

    def __init__(self, start, end, text, parent):
        self.start, self.end, self.text, self.parent = start, end, text, parent


class TreeParser(HTMLParser):
    def __init__(self, raw):
        super().__init__(convert_charrefs=False)
        self.raw = raw
        self.lines = [0]
        for m in re.finditer("\n", raw):
            self.lines.append(m.end())
        self.root = Node("#root", {}, 0, 0, None)
        self.root.end = len(raw)
        self.stack = [self.root]
        self.by_id = {}
        self.all = []

    def off(self):
        line, col = self.getpos()
        return self.lines[line - 1] + col

    @property
    def top(self):
        return self.stack[-1]

    def _close(self, node, at, close_len=0):
        node.end = at + close_len
        node._close_start = at  # type: ignore[attr-defined]
        while self.stack and self.stack[-1] is not node:
            n = self.stack.pop()
            n.end = at
            n._close_start = at  # type: ignore[attr-defined]
        if self.stack:
            self.stack.pop()

    def _implicit(self, tag, at):
        open_tags = [n.tag for n in self.stack]
        if tag == "li":
            for n in reversed(self.stack):
                if n.tag in ("ul", "ol"):
                    break
                if n.tag == "li":
                    self._close(n, at)
                    break
        elif tag in ("td", "th"):
            for n in reversed(self.stack):
                if n.tag == "tr" or n.tag == "table":
                    break
                if n.tag in ("td", "th"):
                    self._close(n, at)
                    break
        elif tag == "tr":
            for n in reversed(self.stack):
                if n.tag in ("table", "tbody", "thead", "tfoot"):
                    break
                if n.tag in ("tr", "td", "th"):
                    self._close(n, at)
                    break
        elif tag in ("dt", "dd"):
            for n in reversed(self.stack):
                if n.tag == "dl":
                    break
                if n.tag in ("dt", "dd"):
                    self._close(n, at)
                    break
        if tag in CLOSE_P and "p" in open_tags:
            for n in reversed(self.stack):
                if n.tag == "p":
                    self._close(n, at)
                    break
                if n.tag in BLOCK:
                    break

    def handle_starttag(self, tag, attrs):
        at = self.off()
        self._implicit(tag, at)
        text = self.get_starttag_text() or ""
        node = Node(tag, dict((k, v if v is not None else "") for k, v in attrs), at, at + len(text), self.top)
        node.idx = len(self.top.children)
        self.top.children.append(node)
        self.all.append(node)
        if node.id and node.id not in self.by_id:
            self.by_id[node.id] = node
        if tag in VOID or text.endswith("/>"):
            node.end = node.open_end
            node._close_start = node.open_end  # type: ignore[attr-defined]
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        at = self.off()
        gt = self.raw.find(">", at)
        close_len = (gt - at + 1) if gt >= 0 else len(tag) + 3
        for n in reversed(self.stack):
            if n.tag == tag:
                self._close(n, at, close_len)
                return

    def _text(self, s):
        at = self.off()
        self.top.children.append(Text(at, at + len(s), s, self.top))

    def handle_data(self, data):
        at = self.off()
        self.top.children.append(Text(at, at + len(data), data, self.top))

    def handle_entityref(self, name):
        at = self.off()
        raw = f"&{name};"
        self.top.children.append(Text(at, at + len(raw), htmlmod.unescape(raw), self.top))

    def handle_charref(self, name):
        at = self.off()
        raw = f"&#{name};"
        self.top.children.append(Text(at, at + len(raw), htmlmod.unescape(raw), self.top))

    def close(self):
        super().close()
        while len(self.stack) > 1:
            n = self.stack.pop()
            n.end = len(self.raw)
            n._close_start = len(self.raw)  # type: ignore[attr-defined]


def parse(raw):
    p = TreeParser(raw)
    p.feed(raw)
    p.close()
    return p


# ---------------------------------------------------------------- 텍스트 추출

TEX_OPEN, TEX_CLOSE = "⟦tex: ", "⟧"


def visible_text(p, node=None, with_ids=True):
    """태그를 벗긴 읽기용 텍스트. 블록마다 줄 바꿈, id는 [id=…], 출처는 ⟦src: …⟧, 수식은 ⟦tex: …⟧, 그림은 ⟦img⟧."""
    out = []

    def walk(n):
        if isinstance(n, Text):
            out.append(n.text)
            return
        if n.tag in SKIP_TEXT:
            return
        cls = n.classes
        if n.tag == "br":
            out.append("\n")
            return
        if n.tag == "img":
            out.append(" ⟦img⟧ ")
            return
        if "m" in cls and "data-tex" in n.attrs:
            out.append(f" {TEX_OPEN}{n.attrs['data-tex']}{TEX_CLOSE} ")
            return
        block = n.tag in BLOCK
        if block:
            out.append("\n")
            if with_ids and n.id:
                out.append(f"[id={n.id}] ")
            if n.tag in ("h1", "h2", "h3", "h4"):
                out.append(f"<{n.tag}> ")
        if "src" in cls and n.tag == "span":
            out.append(" ⟦src: ")
            for c in n.children:
                walk(c)
            out.append("⟧ ")
            return
        for c in n.children:
            walk(c)
        if block:
            out.append("\n")
        elif n.tag in ("td", "th"):
            out.append(" | ")

    walk(node or p.root)
    s = "".join(out)
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r" ?\n ?", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip() + "\n"


def norm_stream(p):
    """공백을 뺀 가시 텍스트와 각 글자의 원본 오프셋. (chars, offsets)"""
    chars, offs = [], []

    def push(s, at):
        for ch in s:
            if not ch.isspace():
                chars.append(ch)
                offs.append(at)

    def walk(n):
        if isinstance(n, Text):
            if n.parent.tag in SKIP_TEXT:
                return
            if len(n.text) == n.end - n.start:
                for i, ch in enumerate(n.text):
                    if not ch.isspace():
                        chars.append(ch)
                        offs.append(n.start + i)
            else:
                push(n.text, n.start)
            return
        if n.tag in SKIP_TEXT:
            return
        if "m" in n.classes and "data-tex" in n.attrs:
            push(n.attrs["data-tex"], n.start)
            return
        for c in n.children:
            walk(c)

    walk(p.root)
    return "".join(chars), offs


def smallest_block(p, s, e):
    """오프셋 구간 [s,e)를 완전히 담는 가장 작은 블록 요소."""
    best = None
    for n in p.all:
        if n.tag not in BLOCK or n.end is None:
            continue
        if n.open_end <= s and e <= n.close_start():
            if best is None or (n.end - n.start) < (best.end - best.start):
                best = n
    return best or p.root


def path_of(n):
    parts = []
    while n is not None and n.tag != "#root":
        seg = n.tag
        if n.id:
            seg += f"#{n.id}"
        elif n.classes:
            seg += "." + ".".join(n.classes[:2])
        parts.append(seg)
        n = n.parent
    return " > ".join(reversed(parts))


def nearest_id(n):
    while n is not None and n.tag != "#root":
        if n.id:
            return n.id
        n = n.parent
    return None


def norm_query(q):
    return "".join(ch for ch in q if not ch.isspace())


def find_matches(p, query, limit=5, min_ratio=0.5):
    stream, offs = norm_stream(p)
    nq = norm_query(query)
    if not nq:
        return []
    results = []
    # 1) 정확히 일치
    i = stream.find(nq)
    while i >= 0:
        results.append((1.0, i, i + len(nq)))
        i = stream.find(nq, i + 1)
        if len(results) >= limit:
            break
    # 2) 유사 문장
    if not results:
        tokens = [t for t in re.split(r"[\s,.;:()\[\]{}\"'“”‘’·…?!/]+", query) if t]
        tokens = [norm_query(t) for t in tokens]
        tokens = [t for t in tokens if len(t) >= (2 if re.search(r"[가-힣]", t) else 4)]
        tokens.sort(key=len, reverse=True)
        seen = set()
        cands = []
        for t in tokens[:8]:
            j = stream.find(t)
            while j >= 0 and len(cands) < 200:
                c = j // 20
                if c not in seen:
                    seen.add(c)
                    cands.append(j)
                j = stream.find(t, j + 1)
        win = int(len(nq) * 1.4) + 8
        for j in cands:
            a = max(0, j - win)
            b = min(len(stream), j + win)
            seg = stream[a:b]
            sm = difflib.SequenceMatcher(None, seg, nq, autojunk=False)
            blocks = [m for m in sm.get_matching_blocks() if m.size > 0]
            if not blocks:
                continue
            s = a + blocks[0].a
            e = a + blocks[-1].a + blocks[-1].size
            covered = sum(m.size for m in blocks)
            ratio = 2 * covered / (len(nq) + (e - s))
            if ratio >= min_ratio:
                results.append((round(ratio, 3), s, e))
        results.sort(key=lambda r: (-r[0], r[1]))
        # 겹치는 후보 제거
        dedup = []
        for r in results:
            if all(r[2] <= d[1] or r[1] >= d[2] for d in dedup):
                dedup.append(r)
        results = dedup[:limit]
    out = []
    for score, s, e in results:
        rs, re_ = offs[s], offs[e - 1] + 1
        blk = smallest_block(p, rs, re_)
        ctx_a = max(0, s - 40)
        ctx_b = min(len(stream), e + 40)
        out.append({
            "score": score,
            "match": {"start": rs, "end": re_},
            "block": {
                "tag": blk.tag, "id": blk.id, "nearest_id": nearest_id(blk), "path": path_of(blk),
                "start": blk.start, "end": blk.end, "inner_start": blk.open_end, "inner_end": blk.close_start(),
            },
            "context": stream[ctx_a:s] + "«" + stream[s:e] + "»" + stream[e:ctx_b],
            "text": visible_text(p, blk, with_ids=False).strip()[:600],
        })
    return out


def wrap_ok(p, s, e):
    """[s,e)를 태그로 감싸도 되는지: 구간에 걸치는(부분적으로만 포함되는) 요소가 없어야 한다."""
    for n in p.all:
        if n.end is None:
            continue
        inside_start = s <= n.start < e
        inside_end = s < n.end <= e
        if inside_start != inside_end and not (n.start >= e or n.end <= s):
            return False, f"{path_of(n)} 요소가 구간에 걸쳐 있습니다 ({n.start}-{n.end})"
        if n.start < s < n.open_end or n.start < e < n.open_end:
            return False, "구간 경계가 태그 안에 있습니다"
    return True, ""


# ---------------------------------------------------------------- 수식 후보 찾기

MATH_CHARS = "∑∏√≤≥≠≈∈∀∃∞∂∇∫±÷⇒αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΦΨΩ"  # ·×→ 는 일반 글에도 흔해 뺀다


def math_scan(p):
    """아직 MathJax SVG(class="m")로 바뀌지 않은 수식 후보: <sub>/<sup>, 유니코드 수식 문자, monospace 식 블록."""
    hits = []
    seen = set()

    def add(node, kind, snippet):
        blk = node if node.tag in BLOCK else smallest_block(p, node.start, node.end)
        key = (blk.start, kind)
        if key in seen:
            return
        seen.add(key)
        hits.append({"kind": kind, "block": {"tag": blk.tag, "id": blk.id, "nearest_id": nearest_id(blk),
                                              "start": blk.start, "end": blk.end, "path": path_of(blk)},
                     "snippet": snippet[:160]})

    for n in p.all:
        if n.tag in SKIP_TEXT or n.end is None:
            continue
        anc = n
        skip = False
        while anc is not None:
            if anc.tag in SKIP_TEXT or ("m" in anc.classes and "data-tex" in anc.attrs) or anc.tag == "code" or anc.tag == "pre":
                skip = True
                break
            anc = anc.parent
        if skip:
            continue
        if n.tag in ("sub", "sup"):
            inner = p.raw[n.open_end:n.close_start()]
            if re.fullmatch(r"\s*(?:\d+|st|nd|rd|th)\s*", inner) and n.tag == "sup":
                continue  # 단위·서수
            par = smallest_block(p, n.start, n.end)
            add(par, "subsup", visible_text(p, par, with_ids=False).strip())
    for n in p.all:
        if n.tag in BLOCK and n.tag not in ("html", "body", "main", "div", "section", "article", "ul", "ol", "table", "tr", "thead", "tbody", "dl", "details", "nav", "summary", "h1"):
            if n.end is None:
                continue
            anc, skip = n.parent, False
            while anc is not None:
                if anc.tag == "nav" or "toc" in anc.classes:
                    skip = True
                    break
                anc = anc.parent
            if skip:
                continue
            txt = visible_text(p, n, with_ids=False)
            txt_wo = re.sub(r"⟦tex:[^⟧]*⟧", "", txt)
            if any(ch in txt_wo for ch in MATH_CHARS):
                add(n, "unicode", txt_wo.strip())
    for n in p.all:
        if n.tag in ("pre", "code") and n.end is not None:
            txt = visible_text(p, n, with_ids=False)
            if re.search(r"[=≤≥<>]\s*\S", txt) and re.search(r"\b(?:sum|min|max|subject to|s\.t\.)\b|[Σ∑]|\^", txt):
                add(n, "mono", txt.strip())
    hits.sort(key=lambda h: h["block"]["start"])
    return hits


# ---------------------------------------------------------------- 공용 조각

FRAG_CSS = [  # (이름, 파일, 시작 마커 정규식, 끝 마커)
    ("toc", SKILLS / "generator" / "toc.css", r"/\*\s*toc:start(?:\s+v(\d+))?[^*]*\*/", "/* toc:end */"),
    ("viz", SKILLS / "viz" / "viz.css", r"/\*ta-viz:start(?:\s+v(\d+))?\*/", "/*ta-viz:end*/"),
    ("math", SKILLS / "math" / "math.css", r"/\*ta-math:start(?:\s+v(\d+))?\*/", "/*ta-math:end*/"),
]
FRAG_HTML = [  # 순서대로 </body> 앞에 들어간다
    ("jump", SKILLS / "generator" / "jump.html"),
    ("glossary", SKILLS / "generator" / "glossary.html"),
    ("pageidx", SKILLS / "generator" / "pageidx.html"),
    ("tocidx", SKILLS / "research" / "tocidx.html"),
    ("reader", SKILLS / "generator" / "reader.html"),
]


def html_marker_re(name):
    return re.compile(rf"<!--{name}:start(?:\s+v(\d+))?-->.*?<!--{name}:end-->\s*", re.S)


def shipped_version(text, name, css=False):
    if css:
        for n, _f, pat, _e in FRAG_CSS:
            if n == name:
                m = re.search(pat, text)
                return int(m.group(1) or 0) if m else 0
    m = re.search(rf"<!--{name}:start(?:\s+v(\d+))?-->", text)
    return int(m.group(1) or 0) if m else 0


def doc_kind(raw):
    if re.search(r'\bid="refs"', raw) or re.search(r'\bid="ref-\d+"', raw) or "<!--tocidx:start" in raw:
        return "research"
    return "generator"


def guess_main(raw):
    m = re.search(r"data-main=\"([^\"]+)\"", raw)
    if m and m.group(1) != "__MAIN__":
        return m.group(1)
    m = re.search(r"(?:원자료|Source)\s*:\s*(?:</?[^>]+>\s*)*([^\s<(,]+\.(?:pdf|ipynb|pptx|docx|md))", raw, re.I)
    return m.group(1) if m else None


def fragments_status(raw):
    kind = doc_kind(raw)
    want = {"toc": True, "viz": 'class="viz' in raw or "class='viz" in raw, "math": bool(re.search(r'class="m(?: m-d)?"', raw))}
    rows = []
    for name, f, pat, _end in FRAG_CSS:
        ship = f.read_text(encoding="utf-8")
        m = re.search(pat, raw)
        have = int(m.group(1) or 0) if m else None
        sv = shipped_version(ship, name, css=True)
        rows.append({"fragment": name + ".css", "needed": want[name], "doc": have, "shipped": sv,
                     "status": _status(want[name], have, sv)})
    for name, f in FRAG_HTML:
        needed = not ((name == "pageidx" and kind == "research") or (name == "tocidx" and kind == "generator"))
        ship = f.read_text(encoding="utf-8")
        m = re.search(rf"<!--{name}:start(?:\s+v(\d+))?-->", raw)
        have = int(m.group(1) or 0) if m else None
        sv = shipped_version(ship, name)
        rows.append({"fragment": name + ".html", "needed": needed, "doc": have, "shipped": sv,
                     "status": _status(needed, have, sv)})
    return kind, rows


def _status(needed, have, shipped):
    if not needed:
        return "n/a" if have is None else "extra"
    if have is None:
        return "missing"
    return "outdated" if have < shipped else "current"


def apply_fragments(raw, main=None, force=False):
    kind, rows = fragments_status(raw)
    changed = []
    # CSS: 기존 블록 제거 후 첫 </style> 앞에 넣는다
    css_add = []
    for (name, f, pat, end), row in zip(FRAG_CSS, rows[:3]):
        m = re.search(pat, raw)
        if m:
            e = raw.find(end, m.end())
            if e >= 0:
                if row["status"] in ("outdated",) or force or row["status"] == "extra":
                    raw = raw[:m.start()] + raw[e + len(end):]
                    raw = re.sub(r"\n{3,}", "\n\n", raw)
                else:
                    continue
            else:
                continue
        if row["needed"]:
            css_add.append(f.read_text(encoding="utf-8").strip())
            changed.append(name + ".css")
    if css_add:
        i = raw.find("</style>")
        if i < 0:
            j = raw.find("</head>")
            if j < 0:
                die("</style>도 </head>도 없습니다")
            raw = raw[:j] + "<style>\n" + "\n".join(css_add) + "\n</style>\n" + raw[j:]
        else:
            raw = raw[:i] + "\n" + "\n".join(css_add) + "\n" + raw[i:]
    # HTML 조각: 모두 떼어낸 뒤 정해진 순서로 </body> 앞에 다시 넣는다
    html_rows = {r["fragment"][:-5]: r for r in rows[3:]}
    existing_main = guess_main(raw)
    need_rebuild = force or any(r["status"] in ("missing", "outdated", "extra") for r in html_rows.values())
    if need_rebuild:
        blocks = []
        for name, f in FRAG_HTML:
            r = html_rows[name]
            mre = html_marker_re(name)
            m = mre.search(raw)
            if m:
                old = m.group(0)
                raw = raw[:m.start()] + raw[m.end():]
            else:
                old = None
            if not r["needed"]:
                if old is not None:
                    changed.append(f"-{name}.html")
                continue
            if old is not None and r["status"] == "current" and not force:
                blocks.append(old.rstrip() + "\n")
                continue
            frag = f.read_text(encoding="utf-8").rstrip() + "\n"
            if name == "pageidx":
                mm = main or existing_main
                if mm:
                    frag = frag.replace("__MAIN__", mm)
            blocks.append(frag)
            changed.append(name + ".html")
        # 옛날 되돌아가기 버튼·펼치기 스크립트 제거
        raw = re.sub(r"<button id=\"backbtn\"[^>]*>.*?</button>\s*", "", raw, flags=re.S)
        i = raw.rfind("</body>")
        if i < 0:
            die("</body>가 없습니다")
        raw = raw[:i].rstrip("\n") + "\n" + "".join(blocks) + raw[i:]
    return raw, changed, kind


# ---------------------------------------------------------------- 유틸

def die(msg, code=1):
    print(msg, file=sys.stderr)
    sys.exit(code)


def read(path):
    return Path(path).read_text(encoding="utf-8")


def write(path, text):
    Path(path).write_text(text, encoding="utf-8")


def emit(obj, as_json, text=None):
    if as_json:
        print(json.dumps(obj, ensure_ascii=False, indent=2))
    else:
        print(text if text is not None else json.dumps(obj, ensure_ascii=False, indent=2))


def do_backup(path):
    p = Path(path)
    bdir = p.parent / ".backup"
    bdir.mkdir(parents=True, exist_ok=True)
    dst = bdir / f"{p.stem}_{datetime.now():%Y%m%d-%H%M%S}{p.suffix}"
    shutil.copy2(p, dst)
    return dst


def latest_notes(out_dir, suffix):
    d = Path(out_dir)
    if not d.is_dir():
        return None
    files = sorted((f for f in d.glob("*.html") if suffix in unicodedata.normalize("NFC", f.name)),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    return files[0] if files else None


# ---------------------------------------------------------------- clip / shot

def find_chrome():
    env = os.environ.get("TA_CHROME")
    cands = [env] if env else []
    cands += [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    for c in cands:
        if c and Path(c).is_file():
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        w = shutil.which(name)
        if w:
            return w
    return None


def render_page(pdf, page, scale_x, out_png_base):
    cmd = ["pdftoppm", "-f", str(page), "-l", str(page), "-scale-to-x", str(scale_x), "-scale-to-y", "-1",
           "-png", "-singlefile", str(pdf), str(out_png_base)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        die(f"pdftoppm 실패: {r.stderr.strip()}")
    return Path(str(out_png_base) + ".png")


def do_clip(args):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        die("Pillow가 없습니다: python3 -m pip install pillow")
    tmp = Path(tempfile.mkdtemp(prefix="ta-clip-"))
    if args.preview:
        png = render_page(args.pdf, args.page, 900, tmp / "prev")
        im = Image.open(png).convert("RGB")
        d = ImageDraw.Draw(im)
        w, h = im.size
        for k in range(1, 10):
            x, y = int(w * k / 10), int(h * k / 10)
            d.line([(x, 0), (x, h)], fill=(255, 0, 0), width=1)
            d.line([(0, y), (w, y)], fill=(255, 0, 0), width=1)
            d.text((x + 2, 2), f"{k/10:.1f}", fill=(255, 0, 0))
            d.text((2, y + 2), f"{k/10:.1f}", fill=(255, 0, 0))
        out = Path(args.out) if args.out else tmp / f"preview_p{args.page}.png"
        im.save(out)
        emit({"preview": str(out), "size": [w, h]}, args.json, str(out))
        return
    png = render_page(args.pdf, args.page, 1800, tmp / "page")
    im = Image.open(png).convert("RGB")
    w, h = im.size
    if args.box:
        try:
            x0, y0, x1, y1 = [float(v) for v in args.box.split(",")]
        except ValueError:
            die("--box는 x0,y0,x1,y1 (0~1 비율) 형식입니다")
        if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
            die("--box 비율이 범위를 벗어났습니다")
        im = im.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1)))
    if im.width > args.width:
        im = im.resize((args.width, int(im.height * args.width / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=args.quality, optimize=True)
    data = buf.getvalue()
    if args.out:
        Path(args.out).write_bytes(data)
    uri = "data:image/jpeg;base64," + base64.b64encode(data).decode()
    alt = args.alt or f"p.{args.page}"
    tag = f'<img src="{uri}" alt="{htmlmod.escape(alt)}" width="{im.width}" height="{im.height}">'
    if args.json:
        emit({"width": im.width, "height": im.height, "bytes": len(data), "out": args.out,
              "img": tag if args.tag else None, "data_uri": None if args.tag else uri}, True)
    else:
        print(tag if args.tag else (args.out or uri))


def extract_styles(p):
    css = []
    for n in p.all:
        if n.tag == "style" and n.end is not None:
            css.append(p.raw[n.open_end:n.close_start()])
    return "\n".join(css)


def do_shot(args):
    raw = read(args.html)
    p = parse(raw)
    if args.snippet:
        body = read(args.snippet)
    else:
        n = p.by_id.get(args.id)
        if not n:
            die(f"id={args.id} 요소가 없습니다")
        body = raw[n.start:n.end]
    lang = re.search(r"<html[^>]*\blang=\"([^\"]+)\"", raw)
    theme = ' data-theme="dark"' if args.dark else ""
    doc = (f'<!doctype html><html lang="{lang.group(1) if lang else "ko"}"{theme}><head><meta charset="utf-8">'
           f'<meta name="viewport" content="width=device-width,initial-scale=1"><style>{extract_styles(p)}\n'
           f'body{{padding:0!important;margin:0}} main{{max-width:760px;margin:0 auto;padding:16px}}</style></head>'
           f'<body><main>{body}</main></body></html>')
    tmp = Path(tempfile.mkdtemp(prefix="ta-shot-"))
    prev = tmp / "preview.html"
    write(prev, doc)
    chrome = find_chrome()
    out = Path(args.out) if args.out else tmp / f"{args.id or 'snippet'}{'-dark' if args.dark else ''}.png"
    if not chrome:
        emit({"skipped": "Chrome을 찾지 못했습니다(TA_CHROME 환경변수로 지정 가능). 캡처를 건너뜁니다.", "preview": str(prev)},
             args.json, f"Chrome 없음 — 캡처 건너뜀. 미리보기: {prev}")
        return
    cmd = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
           f"--user-data-dir={tmp / 'chrome-profile'}", f"--window-size={args.width},{args.height}",
           f"--screenshot={out}", prev.as_uri()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or not out.exists():
        die(f"Chrome 캡처 실패: {r.stderr.strip()[-400:]}")
    emit({"png": str(out), "preview": str(prev)}, args.json, str(out))


# ---------------------------------------------------------------- stats / hub

def count_blocks(raw):
    return {
        "sections": len(re.findall(r"<h2\b", raw)),
        "subsections": len(re.findall(r"<h3\b", raw)),
        "examples": len(re.findall(r'<div class="ex"', raw)),
        "viz": len(re.findall(r'class="viz"', raw)),
        "orig": len(re.findall(r'id="orig-(?:p|r)\d+"', raw)),
        "sup": len(re.findall(r'<details class="sup"', raw)),
        "exm": len(re.findall(r'<details class="exm"', raw)),
        "fix": len(re.findall(r'<details class="fix"', raw)),
        "terms": len(re.findall(r'class="tcard"', raw)),
        "equations": len(re.findall(r'class="m m-d"', raw)),
        "images": len(re.findall(r"<img\b", raw)),
    }


def do_stats(path):
    raw = read(path)
    p = parse(raw)
    main = None
    for n in p.all:
        if n.tag == "main":
            main = n
            break
    txt = visible_text(p, main or p.root, with_ids=False)
    txt = re.sub(r"⟦tex:[^⟧]*⟧|⟦img⟧|⟦src:[^⟧]*⟧|\[id=[^\]]*\]", "", txt)
    chars = len(re.sub(r"\s", "", txt))
    c = count_blocks(raw)
    minutes = chars / 500 + (c["images"] + c["viz"]) * 0.5 + c["equations"] * 0.7
    return {"file": str(path), "chars": chars, "read_minutes": max(1, round(minutes)), **c,
            "kind": doc_kind(raw), "main": guess_main(raw), "bytes": len(raw.encode("utf-8"))}


HUB_CSS = """
:root{--bg:#fff;--fg:#1d2330;--muted:#6b7280;--line:#e3e6ec;--card:#f6f7fb;--accent:#2f3e9e;--soft:#e7eafb}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#14161c;--fg:#e6e8ee;--muted:#9aa1ad;--line:#2c303a;--card:#1c1f27;--accent:#9fb0ff;--soft:#232a4a}}
:root[data-theme="dark"]{--bg:#14161c;--fg:#e6e8ee;--muted:#9aa1ad;--line:#2c303a;--card:#1c1f27;--accent:#9fb0ff;--soft:#232a4a}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;line-height:1.6}
main{max-width:860px;margin:0 auto;padding:28px 16px 60px}h1{font-size:1.6rem;margin:.2em 0 .2em}.sub{color:var(--muted);margin:0 0 20px;font-size:.9rem}
.grp{margin:18px 0 26px}.grp h2{font-size:1.05rem;margin:0 0 8px;color:var(--muted);font-weight:600}
.card{display:grid;grid-template-columns:1fr auto;gap:4px 16px;align-items:center;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin:8px 0;text-decoration:none;color:inherit}
.card:hover{border-color:var(--accent)}.card .t{font-weight:650}.card .m{grid-column:1/-1;color:var(--muted);font-size:.82rem;display:flex;flex-wrap:wrap;gap:4px 12px}
.card .q{font-size:.82rem;color:var(--accent);white-space:nowrap}.pill{display:inline-block;background:var(--soft);color:var(--accent);border-radius:999px;padding:0 .6em;font-size:.78rem;font-weight:600}
.src{font-size:.8rem;color:var(--muted)}
"""

HUB_L = {
    "ko": {"sub": "이 폴더의 학습자료 목록 · 생성 {date}", "quiz": "퀴즈 →", "part": "{n}부", "min": "약 {m}분", "sup": "보충 {n}", "exm": "추가 예시 {n}", "viz": "시각화 {n}", "ex": "예시 {n}", "none": "학습자료가 없습니다.", "src": "원자료"},
    "en": {"sub": "Study notes in this folder · built {date}", "quiz": "Quiz →", "part": "Part {n}", "min": "~{m} min", "sup": "{n} supplements", "exm": "{n} extra examples", "viz": "{n} figures", "ex": "{n} examples", "none": "No study notes yet.", "src": "Source"},
}


def do_hub(out_dir, lang=None):
    cfg = load_config(Path(out_dir).parent)
    lang = lang or cfg["lang"]
    L = HUB_L[lang]
    d = Path(out_dir)
    notes = []
    suffixes = [NAMES["ko"]["notes"], NAMES["en"]["notes"]]
    qsuf = [NAMES["ko"]["quiz"], NAMES["en"]["quiz"]]
    names_nfc = {unicodedata.normalize("NFC", f.name): f.name for f in d.glob("*.html")}
    for f in sorted(d.glob("*.html")):
        if f.name == "index.html":
            continue
        name = unicodedata.normalize("NFC", f.stem)  # macOS 파일명은 NFD일 수 있다
        suf = next((s for s in suffixes if s in name), None)
        if not suf:
            continue
        stem, _, rest = name.partition(suf)
        part = rest.lstrip("_") if rest else ""
        raw = f.read_text(encoding="utf-8", errors="replace")
        t = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.S)
        title = re.sub(r"<[^>]+>", "", t.group(1)).strip() if t else name
        st = do_stats(f)
        quiz = None
        for qs in qsuf:
            for cand in (f"{stem}{('_' + part) if part else ''}{qs}.html", f"{stem}{qs}.html"):
                if cand in names_nfc:
                    quiz = names_nfc[cand]
                    break
            if quiz:
                break
        notes.append({"file": f.name, "stem": stem, "part": part, "title": title, "quiz": quiz, "mtime": f.stat().st_mtime, **st})
    groups = {}
    for n in notes:
        groups.setdefault(n["stem"], []).append(n)
    today = datetime.now().strftime("%Y-%m-%d")
    title_all = htmlmod.escape(NAMES[lang]["hub_title"])
    html_parts = [f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                  f'<title>{title_all}</title><style>{HUB_CSS}</style></head><body><main>'
                  f'<h1>{title_all}</h1><p class="sub">{L["sub"].format(date=today)}</p>']
    if not notes:
        html_parts.append(f"<p>{L['none']}</p>")
    for stem, items in groups.items():
        items.sort(key=lambda n: (int(n["part"]) if n["part"].isdigit() else 0, n["file"]))
        src = items[0]["main"]
        head = htmlmod.escape(stem) + (f' <span class="src">· {L["src"]}: {htmlmod.escape(src)}</span>' if src and src != stem else "")
        html_parts.append(f'<section class="grp"><h2>{head}</h2>')
        for n in items:
            meta = [L["min"].format(m=n["read_minutes"])]
            if n["examples"]:
                meta.append(L["ex"].format(n=n["examples"]))
            if n["viz"]:
                meta.append(L["viz"].format(n=n["viz"]))
            if n["sup"]:
                meta.append(L["sup"].format(n=n["sup"]))
            if n["exm"]:
                meta.append(L["exm"].format(n=n["exm"]))
            meta.append(datetime.fromtimestamp(n["mtime"]).strftime("%Y-%m-%d"))
            part = f' <span class="pill">{L["part"].format(n=n["part"])}</span>' if n["part"] else ""
            q = f'<a class="q" href="{htmlmod.escape(n["quiz"])}">{L["quiz"]}</a>' if n["quiz"] else "<span></span>"
            html_parts.append(f'<div class="card"><a class="t" href="{htmlmod.escape(n["file"])}">{htmlmod.escape(n["title"])}{part}</a>{q}'
                              f'<div class="m">{" · ".join(meta)}</div></div>')
        html_parts.append("</section>")
    html_parts.append("</main></body></html>")
    out = d / "index.html"
    write(out, "\n".join(html_parts))
    return out, notes


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(prog="ta.py", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)

    a = sp.add_parser("config", help="설정 출력")
    a.add_argument("--dir", help="작업 디렉터리(기본: 현재)")
    a.add_argument("--json", action="store_true")

    a = sp.add_parser("text", help="태그를 벗긴 텍스트")
    a.add_argument("html")
    a.add_argument("--out", help="저장할 파일(없으면 stdout)")
    a.add_argument("--no-ids", action="store_true")

    a = sp.add_parser("find", help="질의를 담는 가장 작은 블록 찾기")
    a.add_argument("html")
    a.add_argument("query")
    a.add_argument("--limit", type=int, default=5)
    a.add_argument("--json", action="store_true")

    a = sp.add_parser("insert", help="블록 뒤에 HTML 삽입")
    a.add_argument("html")
    a.add_argument("--after", required=True, help="원본 오프셋 또는 #id")
    a.add_argument("--file", required=True, help="삽입할 HTML 조각 파일")
    a.add_argument("--no-backup", action="store_true")
    a.add_argument("--json", action="store_true")

    a = sp.add_parser("wrap", help="오프셋 구간을 태그로 감싸기")
    a.add_argument("html")
    a.add_argument("--start", type=int, required=True)
    a.add_argument("--end", type=int, required=True)
    a.add_argument("--open", required=True, help='여는 태그, 예: \'<mark class="sup-mark" id="sup-src-1">\'')
    a.add_argument("--close", required=True, help="닫는 태그, 예: </mark>")
    a.add_argument("--no-backup", action="store_true")
    a.add_argument("--json", action="store_true")

    a = sp.add_parser("backup", help=".backup/ 으로 복사")
    a.add_argument("html")
    a.add_argument("--json", action="store_true")

    a = sp.add_parser("fragments", help="공용 조각 넣기/갱신")
    a.add_argument("html")
    a.add_argument("--main", help="pageidx의 원자료 파일명(__MAIN__)")
    a.add_argument("--check", action="store_true", help="수정하지 않고 상태만")
    a.add_argument("--force", action="store_true", help="버전과 상관없이 모두 교체")
    a.add_argument("--no-backup", action="store_true")
    a.add_argument("--json", action="store_true")

    a = sp.add_parser("clip", help="PDF 페이지 자르기 → JPEG data URI")
    a.add_argument("pdf")
    a.add_argument("page", type=int)
    a.add_argument("--box", help="x0,y0,x1,y1 (0~1 비율). 없으면 페이지 전체")
    a.add_argument("--width", type=int, default=1200)
    a.add_argument("--quality", type=int, default=80)
    a.add_argument("--out", help="JPEG(또는 --preview PNG) 저장 경로")
    a.add_argument("--tag", action="store_true", help="<img> 태그로 출력")
    a.add_argument("--alt", help="img alt")
    a.add_argument("--preview", action="store_true", help="비율 눈금이 그려진 미리보기 PNG 생성")
    a.add_argument("--json", action="store_true")

    a = sp.add_parser("shot", help="요소 하나를 헤드리스 Chrome으로 캡처")
    a.add_argument("html")
    a.add_argument("--id", help="캡처할 요소 id")
    a.add_argument("--snippet", help="id 대신 캡처할 HTML 조각 파일")
    a.add_argument("--dark", action="store_true")
    a.add_argument("--width", type=int, default=820)
    a.add_argument("--height", type=int, default=600)
    a.add_argument("--out")
    a.add_argument("--json", action="store_true")

    a = sp.add_parser("hub", help="출력 폴더 index.html 생성")
    a.add_argument("--dir", help="출력 폴더(기본: config의 out_dir)")
    a.add_argument("--lang", choices=["ko", "en"])
    a.add_argument("--json", action="store_true")

    a = sp.add_parser("stats", help="글자 수·읽기 시간·블록 수")
    a.add_argument("html")
    a.add_argument("--json", action="store_true")

    a = sp.add_parser("mathscan", help="SVG로 안 바뀐 수식 후보(<sub>/<sup>, 유니코드 기호, monospace 식)")
    a.add_argument("html")
    a.add_argument("--json", action="store_true")

    args = ap.parse_args(argv)

    if args.cmd == "config":
        cfg = load_config(args.dir)
        emit(cfg, True)
    elif args.cmd == "text":
        p = parse(read(args.html))
        t = visible_text(p, with_ids=not args.no_ids)
        if args.out:
            write(args.out, t)
            print(args.out)
        else:
            sys.stdout.write(t)
    elif args.cmd == "find":
        p = parse(read(args.html))
        res = find_matches(p, args.query, limit=args.limit)
        if args.json:
            emit(res, True)
        else:
            if not res:
                print("일치하는 곳이 없습니다")
                sys.exit(2)
            for i, r in enumerate(res, 1):
                b = r["block"]
                print(f"[{i}] score={r['score']} block=<{b['tag']}> id={b['id']} near={b['nearest_id']} "
                      f"block_end={b['end']} match={r['match']['start']}-{r['match']['end']}\n    {b['path']}\n    …{r['context']}…")
        if not res:
            sys.exit(2)
    elif args.cmd == "insert":
        raw = read(args.html)
        frag = read(args.file)
        if args.after.startswith("#"):
            p = parse(raw)
            n = p.by_id.get(args.after[1:])
            if not n:
                die(f"id={args.after[1:]} 요소가 없습니다")
            at = n.end
        else:
            at = int(args.after)
        if not (0 <= at <= len(raw)):
            die("오프셋이 범위를 벗어났습니다")
        bk = None if args.no_backup else str(do_backup(args.html))
        new = raw[:at] + "\n" + frag.strip("\n") + "\n" + raw[at:]
        write(args.html, new)
        emit({"inserted_at": at, "length": len(frag), "backup": bk}, args.json, f"삽입 완료 @ {at} (백업: {bk})")
    elif args.cmd == "wrap":
        raw = read(args.html)
        p = parse(raw)
        if not (0 <= args.start < args.end <= len(raw)):
            die("구간이 범위를 벗어났습니다")
        ok, why = wrap_ok(p, args.start, args.end)
        if not ok:
            die("감쌀 수 없습니다: " + why)
        bk = None if args.no_backup else str(do_backup(args.html))
        new = raw[:args.start] + args.open + raw[args.start:args.end] + args.close + raw[args.end:]
        write(args.html, new)
        emit({"start": args.start, "end": args.end + len(args.open), "backup": bk}, args.json,
             f"감쌈 완료 {args.start}-{args.end} (백업: {bk})")
    elif args.cmd == "backup":
        dst = do_backup(args.html)
        emit({"backup": str(dst)}, args.json, str(dst))
    elif args.cmd == "fragments":
        raw = read(args.html)
        if args.check:
            kind, rows = fragments_status(raw)
            if args.json:
                emit({"kind": kind, "main": guess_main(raw), "fragments": rows}, True)
            else:
                print(f"kind={kind} main={guess_main(raw)}")
                for r in rows:
                    print(f"  {r['fragment']:<14} {r['status']:<9} doc={r['doc']} shipped={r['shipped']}")
            sys.exit(0 if all(r["status"] in ("current", "n/a") for r in rows) else 3)
        new, changed, kind = apply_fragments(raw, main=args.main, force=args.force)
        if new == raw:
            emit({"kind": kind, "changed": []}, args.json, "이미 최신입니다")
            return
        bk = None if args.no_backup else str(do_backup(args.html))
        write(args.html, new)
        emit({"kind": kind, "changed": changed, "backup": bk, "main": guess_main(new)}, args.json,
             f"갱신: {', '.join(changed)} (kind={kind}, 백업: {bk})")
    elif args.cmd == "clip":
        do_clip(args)
    elif args.cmd == "shot":
        if not args.id and not args.snippet:
            die("--id 또는 --snippet 이 필요합니다")
        do_shot(args)
    elif args.cmd == "hub":
        out_dir = args.dir or load_config()["out_dir"]
        if not Path(out_dir).is_dir():
            die(f"폴더가 없습니다: {out_dir}")
        out, notes = do_hub(out_dir, args.lang)
        emit({"index": str(out), "count": len(notes), "files": [n["file"] for n in notes]}, args.json,
             f"{out} ({len(notes)}개)")
    elif args.cmd == "stats":
        emit(do_stats(args.html), True)
    elif args.cmd == "mathscan":
        hits = math_scan(parse(read(args.html)))
        if args.json:
            emit(hits, True)
        else:
            if not hits:
                print("수식 후보가 없습니다")
            for i, h in enumerate(hits, 1):
                b = h["block"]
                print(f"[{i}] {h['kind']:<7} <{b['tag']}> id={b['id']} near={b['nearest_id']} {b['start']}-{b['end']}\n    {h['snippet']}")


if __name__ == "__main__":
    main()
