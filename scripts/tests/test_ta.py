"""scripts/ta.py 단위 테스트.  실행: python3 -m unittest discover -s scripts/tests -v"""
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import ta  # noqa: E402

DOC = """<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><title>T</title>
<style>:root{--bg:#fff}</style>
</head>
<body><main>
<h1>Transfer Learning</h1>
<p>원자료: 7_Lecture.pdf</p>
<nav class="toc"><ol><li><a href="#s1">기본 용어</a></li></ol></nav>
<details class="gloss" id="s1" open><summary><h2 data-noidx>0. 기본 용어</h2></summary>
<div class="gl-grid"><div class="tcard" id="t-head"><p class="tc-def">Head는 출력층이다.</p></div></div></details>
<h2 id="s2">1. 개념 설명</h2>
<h3 id="c1">1.1 Head</h3>
<ul class="pts">
<li><b>새 Head</b> 1280개 숫자를 받아 10개 점수를 내는 층이다. <span class="src">p.18</span>
<li><b>다음</b> 두 번째 항목 &amp; 기호
</ul>
<div class="ex" id="ex1"><div class="exh">예시 ① Head는 출력 형식만 바꾼다</div><p>본문 <a class="term" href="#t-head">Head</a> 설명.</p></div>
<p>식 <span class="m" data-tex="\\lambda_p" role="img"><svg><text>λ</text></svg></span> 끝.</p>
<img src="data:image/jpeg;base64,AAAA" alt="x">
<table><tr><td>a<td>b<tr><td>c</table>
</main>
<script>var x=1;</script>
</body></html>
"""


class ParseTests(unittest.TestCase):
    def setUp(self):
        self.p = ta.parse(DOC)

    def test_offsets_match_raw(self):
        n = self.p.by_id["ex1"]
        self.assertTrue(DOC[n.start:].startswith('<div class="ex" id="ex1">'))
        self.assertTrue(DOC[:n.end].endswith("</div>"))
        self.assertEqual(DOC[n.close_start():n.end], "</div>")

    def test_implicit_close_li_td(self):
        lis = [n for n in self.p.all if n.tag == "li" and n.parent.classes == ["pts"]]
        self.assertEqual(len(lis), 2)
        self.assertLessEqual(lis[0].end, lis[1].start)
        tds = [n for n in self.p.all if n.tag == "td"]
        self.assertEqual(len(tds), 3)
        self.assertTrue(all(t.end is not None for t in tds))

    def test_visible_text_markers(self):
        t = ta.visible_text(self.p)
        self.assertIn("[id=c1] <h3> 1.1 Head", t)
        self.assertIn("⟦src: p.18⟧", t)
        self.assertIn("⟦tex: \\lambda_p⟧", t)
        self.assertIn("⟦img⟧", t)
        self.assertNotIn("var x=1", t)
        self.assertNotIn("--bg", t)
        self.assertIn("& 기호", t)


class FindTests(unittest.TestCase):
    def setUp(self):
        self.p = ta.parse(DOC)

    def test_exact_ignores_whitespace(self):
        r = ta.find_matches(self.p, "1280개 숫자를   받아\n10개 점수")
        self.assertEqual(r[0]["score"], 1.0)
        self.assertEqual(r[0]["block"]["tag"], "li")
        m = r[0]["match"]
        self.assertEqual(DOC[m["start"]:m["end"]], "1280개 숫자를 받아 10개 점수")

    def test_smallest_block_and_nearest_id(self):
        r = ta.find_matches(self.p, "Head는 출력 형식만 바꾼다")[0]
        self.assertEqual(r["block"]["path"].split(" > ")[-1], "div.exh")
        self.assertEqual(r["block"]["nearest_id"], "ex1")

    def test_fuzzy(self):
        r = ta.find_matches(self.p, "1280 개 숫자 를 받아서 10 개 점수를 내는 층")
        self.assertTrue(r)
        self.assertEqual(r[0]["block"]["tag"], "li")
        self.assertLess(r[0]["score"], 1.0)

    def test_tex_searchable(self):
        r = ta.find_matches(self.p, "\\lambda_p")
        self.assertEqual(r[0]["block"]["tag"], "p")

    def test_no_match(self):
        self.assertEqual(ta.find_matches(self.p, "전혀 없는 문장 zzzz qqqq"), [])


class WrapTests(unittest.TestCase):
    def test_wrap_ok_across_balanced_inline(self):
        p = ta.parse(DOC)
        r = ta.find_matches(p, "본문 Head 설명.")[0]["match"]
        ok, _ = ta.wrap_ok(p, r["start"], r["end"])
        self.assertTrue(ok)

    def test_wrap_rejects_partial_element(self):
        p = ta.parse(DOC)
        a = DOC.index("본문 <a")
        b = DOC.index("Head</a>") + 2  # <a> 안에서 끝남
        ok, why = ta.wrap_ok(p, a, b)
        self.assertFalse(ok)


class FragmentTests(unittest.TestCase):
    def test_apply_generator(self):
        new, changed, kind = ta.apply_fragments(DOC)
        self.assertEqual(kind, "generator")
        for name in ("toc.css", "jump.html", "glossary.html", "pageidx.html", "reader.html"):
            self.assertIn(name, changed)
        self.assertIn("math.css", changed)  # class="m" 있음
        self.assertNotIn("viz.css", changed)
        self.assertNotIn("tocidx.html", changed)
        self.assertIn('data-main="7_Lecture.pdf"', new)
        body = new.index("</body>")
        order = [new.index(f"<!--{n}:start") for n in ("jump", "glossary", "pageidx", "reader")]
        self.assertEqual(order, sorted(order))
        self.assertTrue(all(o < body for o in order))
        self.assertLess(new.index("/* toc:start"), new.index("</style>"))
        # 두 번째 적용은 변화 없음
        again, changed2, _ = ta.apply_fragments(new)
        self.assertEqual(changed2, [])
        self.assertEqual(again, new)

    def test_upgrade_old_marker_and_keep_main(self):
        old = DOC.replace("</body>", '<!--pageidx:start--><script data-main="OLD.pdf">old</script><!--pageidx:end-->\n</body>')
        kind, rows = ta.fragments_status(old)
        st = {r["fragment"]: r["status"] for r in rows}
        self.assertEqual(st["pageidx.html"], "outdated")
        new, changed, _ = ta.apply_fragments(old)
        self.assertNotIn(">old<", new)
        self.assertIn('data-main="OLD.pdf"', new)
        self.assertEqual(new.count("<!--pageidx:start"), 1)

    def test_v3d_only_when_used(self):
        new, changed, _ = ta.apply_fragments(DOC)
        self.assertNotIn("v3d.css", changed)
        self.assertNotIn("<!--v3d:start", new)
        doc = DOC.replace("</main>", '<div class="viz" id="viz1"><div class="v3d" data-label="x"></div>'
                          '<div class="v3d-fb" hidden></div></div><script>(window.TA3D_Q=window.TA3D_Q||[]).push({})</script></main>')
        new, changed, _ = ta.apply_fragments(doc)
        self.assertIn("v3d.css", changed)
        self.assertIn("v3d.html", changed)
        self.assertLess(new.index("<!--reader:start"), new.index("<!--v3d:start"))
        self.assertLess(new.index("<!--v3d:end-->"), new.index("</body>"))
        again, changed2, _ = ta.apply_fragments(new)
        self.assertEqual(changed2, [])
        # 3D 그림을 지우면 조각도 빠진다(런타임 안의 문자열이 스스로를 붙잡지 않는다)
        gone = re.sub(r'<div class="v3d"[^>]*></div>', "", new)
        new2, changed3, _ = ta.apply_fragments(gone)
        self.assertIn("-v3d.html", changed3)
        self.assertNotIn("<!--v3d:start", new2)

    def test_eqlink_only_when_linked(self):
        new, changed, _ = ta.apply_fragments(DOC)
        self.assertNotIn("eqlink.html", changed)
        doc = DOC.replace("</main>", '<table class="eqx" id="eqx-1"><tr class="t1"><td>W</td></tr></table>'
                          '<div class="viz" id="viz1" data-eq="eqx-1"><svg><text data-t="t1">W</text></svg></div></main>')
        new, changed, _ = ta.apply_fragments(doc)
        self.assertIn("eqlink.html", changed)
        self.assertLess(new.index("<!--reader:start"), new.index("<!--eqlink:start"))
        again, changed2, _ = ta.apply_fragments(new)
        self.assertEqual(changed2, [])
        unlinked = new.replace(' data-eq="eqx-1"', "")
        _, changed3, _ = ta.apply_fragments(unlinked)
        self.assertIn("-eqlink.html", changed3)

    def test_research_kind(self):
        doc = DOC.replace("</main>", '<h2 id="s9">참고문헌</h2><ol id="refs"><li id="ref-1">x</li></ol></main>')
        new, changed, kind = ta.apply_fragments(doc)
        self.assertEqual(kind, "research")
        self.assertIn("tocidx.html", changed)
        self.assertNotIn("pageidx.html", changed)


class ConfigTests(unittest.TestCase):
    def test_defaults_and_file(self):
        with tempfile.TemporaryDirectory() as d:
            cfg = ta.load_config(d)
            self.assertEqual(cfg["out_dir"], "학습자료")
            self.assertEqual(cfg["suffix_quiz"], "_퀴즈")
            self.assertTrue(cfg["level_preset"])
            Path(d, ".ta.json").write_text(json.dumps({"lang": "en", "level": "undergrad"}), encoding="utf-8")
            cfg = ta.load_config(d)
            self.assertEqual(cfg["out_dir"], "study-notes")
            self.assertEqual(cfg["suffix_notes"], "_notes")
            self.assertIn("undergraduate", cfg["level_text"])
            Path(d, ".ta.json").write_text(json.dumps({"level": "박사과정 신입생", "out_dir": "notes"}), encoding="utf-8")
            cfg = ta.load_config(d)
            self.assertEqual(cfg["level_text"], "박사과정 신입생")
            self.assertFalse(cfg["level_preset"])
            self.assertEqual(cfg["out_dir"], "notes")


class HubStatsTests(unittest.TestCase):
    def test_stats_and_hub(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d, "학습자료")
            out.mkdir()
            (out / "7_Lecture.pdf_학습자료.html").write_text(DOC, encoding="utf-8")
            (out / "7_Lecture.pdf_학습자료_2.html").write_text(DOC.replace("Transfer Learning", "Part 2"), encoding="utf-8")
            (out / "7_Lecture.pdf_퀴즈.html").write_text("<html><body>q</body></html>", encoding="utf-8")
            st = ta.do_stats(out / "7_Lecture.pdf_학습자료.html")
            self.assertEqual(st["examples"], 1)
            self.assertEqual(st["terms"], 1)
            self.assertGreaterEqual(st["read_minutes"], 1)
            self.assertEqual(st["main"], "7_Lecture.pdf")
            idx, notes = ta.do_hub(out)
            html = idx.read_text(encoding="utf-8")
            self.assertEqual(len(notes), 2)
            self.assertIn("7_Lecture.pdf_퀴즈.html", html)
            self.assertIn("2부", html)
            self.assertIn("Part 2", html)

    def test_hub_nfd_filenames(self):
        import unicodedata
        with tempfile.TemporaryDirectory() as d:
            out = Path(d, "학습자료")
            out.mkdir()
            nfd = unicodedata.normalize("NFD", "주제_학습자료.html")
            (out / nfd).write_text(DOC, encoding="utf-8")
            (out / unicodedata.normalize("NFD", "주제_퀴즈.html")).write_text("<html></html>", encoding="utf-8")
            idx, notes = ta.do_hub(out)
            self.assertEqual(len(notes), 1)
            self.assertIsNotNone(notes[0]["quiz"])


class MathScanTests(unittest.TestCase):
    def test_scan(self):
        doc = DOC.replace("끝.</p>", "끝.</p><p>w<sub>1</sub>x + Σ a_i ≤ b</p><p>단위 m<sup>2</sup></p>")
        p = ta.parse(doc)
        hits = ta.math_scan(p)
        kinds = {h["kind"] for h in hits}
        self.assertIn("subsup", kinds)
        self.assertIn("unicode", kinds)
        self.assertTrue(all("rendered" not in h["kind"] for h in hits))


if __name__ == "__main__":
    unittest.main()
