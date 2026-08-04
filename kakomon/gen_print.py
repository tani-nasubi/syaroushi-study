#!/usr/bin/env python3
"""紙で読むための印刷版を作る。

画面ではリンクを押せばよいが、紙では押せない。そこで資料に通し番号を振り、
リンクを「→ 資料23 平均賃金」のように、番号で引ける形に置き換える。
巻頭に番号つきの目次を置き、資料ごとに改ページする。

  出力
    drill/print.html        全99資料（通し）
    drill/print-労基.html   科目ごと（分けて印刷したいとき）
"""
import os, re, glob, html, json

HERE  = os.path.dirname(os.path.abspath(__file__))
ROOT  = os.path.dirname(HERE)
NOTES = os.path.join(ROOT, "notes")
OUTDIR = os.path.join(ROOT, "drill")

# ── 資料の並びと、科目のまとまり ──────────────────────────────
# 深掘りページは本体のすぐ後ろに置く。紙では前後に並んでいるほうが引きやすい。
GROUPS = [
 ("はじめに",   ["00-法改正-令和8年度.md"]),
 ("労基・安衛", ["01-労働基準法.md", "B", "C", "02-労働安全衛生法.md", "D"]),
 ("労災・徴収", ["03-労災保険法.md", "E", "05-徴収法.md", "G"]),
 ("雇用",       ["04-雇用保険法.md", "F"]),
 ("一般常識",   ["06-労働一般常識.md", "H", "07-社会保険一般常識.md", "I"]),
 ("健保",       ["08-健康保険法.md", "J"]),
 ("年金",       ["09-国民年金法.md", "K", "10-厚生年金保険法.md", "L"]),
 ("横断・直前", ["90-横断整理.md", "91-数値暗記.md", "92-選択式の解き方.md", "93-判例.md",
                 "94-計算問題の解法.md", "95-条文素読（選択式の原文）.md",
                 "96-得点源リスト.md", "97-引っかけの型.md",
                 "A0-正文集（択一の正しい肢）.md", "A1-個数・組合せ問題の解き方.md",
                 "99-白書・統計.md", "98-最終確認シート.md"]),
]

def order():
    """並び順を決めて (科目, ファイル名) の一覧を返す。"""
    files = {os.path.basename(p) for p in glob.glob(os.path.join(NOTES, "*.md"))}
    out, used = [], set()
    for g, items in GROUPS:
        for it in items:
            if it.endswith(".md"):
                if it in files:
                    out.append((g, it)); used.add(it)
            else:                                  # 接頭辞（深掘りページ群）
                for f in sorted(f for f in files
                                if re.match(r"^" + it + r"\d-", f)):
                    out.append((g, f)); used.add(f)
    for f in sorted(files - used):                 # 取りこぼしは末尾に
        out.append(("その他", f))
    return out

# ── Markdown → HTML（アプリの md2html と同じ範囲を扱う）──────
def esc(s):
    return html.escape(str(s), quote=False)

def inline(s, link):
    s = esc(s)
    # 資料名がリンクではなくコード表記で書かれていることがある
    # （「`91-数値暗記.md` と対で使う」）。紙では番号で引けないと困るので同じ扱いにする。
    s = re.sub(r"`([^`]+\.md)`", lambda m: link(m.group(1), m.group(1)), s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: link(m.group(1), m.group(2)), s)
    return s

def md2html(src, link):
    lines = src.split("\n")
    out, i, incode, code = [], 0, False, []
    while i < len(lines):
        l = lines[i]
        if l.startswith("```"):
            if incode:
                out.append("<pre><code>" + esc("\n".join(code)) + "</code></pre>")
                code, incode = [], False
            else:
                incode = True
            i += 1; continue
        if incode:
            code.append(l); i += 1; continue
        if not l.strip():
            i += 1; continue
        if l.lstrip().startswith("<!--"):
            while i < len(lines) and "-->" not in lines[i]:
                i += 1
            i += 1; continue
        if re.fullmatch(r"-{3,}", l.strip()):
            out.append("<hr>"); i += 1; continue
        m = re.match(r"^(#{1,4})\s+(.*)$", l)
        if m:
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2), link)}</h{n}>")
            i += 1; continue
        if l.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            cells = lambda r: [c.strip() for c in r.strip().strip("|").split("|")]
            head = cells(rows[0])
            body = rows[2:] if len(rows) > 1 and re.fullmatch(r"[\s|:-]+", rows[1]) else rows[1:]
            out.append("<table><thead><tr>"
                       + "".join(f"<th>{inline(c, link)}</th>" for c in head)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c, link)}</td>" for c in cells(r))
                                 + "</tr>" for r in body)
                       + "</tbody></table>")
            continue
        if re.match(r"^>\s?", l):
            buf = []
            while i < len(lines) and re.match(r"^>\s?", lines[i]):
                buf.append(re.sub(r"^>\s?", "", lines[i])); i += 1
            out.append("<blockquote>" + md2html("\n".join(buf), link) + "</blockquote>")
            continue
        if re.match(r"^\s*[-*]\s+", l):
            buf = []
            while i < len(lines) and re.match(r"^\s*[-*]\s+", lines[i]):
                buf.append(re.sub(r"^\s*[-*]\s+", "", lines[i])); i += 1
            if all(re.match(r"^\[[ xX]\]\s*", b) for b in buf):
                # 紙のチェックリストは□。手で塗れるようにする
                strip = lambda b: re.sub(r"^\[[ xX]\]\s*", "", b)
                out.append("<ul class=\"chk\">"
                           + "".join("<li>" + inline(strip(b), link) + "</li>" for b in buf)
                           + "</ul>")
            else:
                out.append("<ul>" + "".join(f"<li>{inline(b, link)}</li>" for b in buf) + "</ul>")
            continue
        if re.match(r"^\s*\d+\.\s+", l):
            buf = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                buf.append(re.sub(r"^\s*\d+\.\s+", "", lines[i])); i += 1
            out.append("<ol>" + "".join(f"<li>{inline(b, link)}</li>" for b in buf) + "</ol>")
            continue
        buf = []
        while (i < len(lines) and lines[i].strip()
               and not re.match(r"^[|>#`]", lines[i])
               and not re.fullmatch(r"-{3,}", lines[i].strip())
               and not re.match(r"^\s*[-*]\s+", lines[i])
               and not re.match(r"^\s*\d+\.\s+", lines[i])):
            buf.append(lines[i]); i += 1
        if buf:
            out.append("<p>" + inline("\n".join(buf), link) + "</p>")
        else:
            i += 1
    return "\n".join(out)

# ── 印刷用のスタイル ──────────────────────────────────────────
CSS = """
/* 2ページを1枚に並べて刷る想定。余白は詰める。 */
@page { size: A4 portrait; margin: 10mm 9mm 11mm; }
*{box-sizing:border-box}
html{-webkit-print-color-adjust:exact; print-color-adjust:exact}
body{margin:0; color:#111; background:#fff;
  font-family:"Hiragino Kaku Gothic ProN","Yu Gothic","Noto Sans JP",sans-serif;
  font-size:9.6pt; line-height:1.72; text-align:justify;
  font-feature-settings:"palt" 1;}
.wrap{max-width:none; margin:0; padding:0}
/* ── 巻頭 ── */
.cover{text-align:center; padding:24mm 0 0; break-after:page; page-break-after:always}
.cover h1{font-size:22pt; letter-spacing:.06em; margin:0 0 6mm}
.cover .sub{font-size:10pt; color:#555; line-height:2}
.howto{margin:12mm auto 0; max-width:132mm; text-align:left;
  border:1pt solid #bbb; padding:6mm 7mm; font-size:9pt; line-height:1.8}
.howto b{font-size:9.6pt}
/* ── 目次 ── */
.toc h2{font-size:13pt; margin:0 0 4mm; padding-bottom:2mm; border-bottom:1.4pt solid #111}
.toc .grp{margin:3.5mm 0 1.5mm; font-weight:700; font-size:10.5pt;
  border-left:3pt solid #111; padding-left:3mm}
.toc ol{list-style:none; margin:0; padding:0; columns:2; column-gap:10mm}
.toc li{break-inside:avoid; font-size:9pt; line-height:1.85;
  display:flex; gap:2mm; align-items:baseline}
.toc .no{display:inline-block; min-width:9mm; font-weight:700; font-variant-numeric:tabular-nums}
.toc .dots{flex:1; border-bottom:.4pt dotted #999; transform:translateY(-2px)}
/* ── 各資料 ── */
/* 資料ごとに改ページすると、2ページ組みでは半端な余白が積み上がる。
   改ページはやめて、太い区切り線で切れ目を示す。 */
.doc + .doc{margin-top:9mm; padding-top:6mm; border-top:2.2pt solid #111}
.doc.toc{break-after:page; page-break-after:always}
.doc > .head{border-bottom:1.2pt solid #111; padding-bottom:2mm; margin:0 0 3.5mm;
  break-after:avoid; page-break-after:avoid; break-inside:avoid; page-break-inside:avoid}
.doc > .head .no{font-size:8.5pt; letter-spacing:.14em; color:#666}
.doc > .head h1{font-size:16pt; margin:1mm 0 0; letter-spacing:-.01em}
.doc > .head .desc{font-size:8.5pt; color:#555; margin:1.5mm 0 0}
h2{font-size:12pt; margin:5mm 0 2mm; padding:1mm 0 1mm 3mm;
  border-left:3.5pt solid #111; break-after:avoid; page-break-after:avoid}
h3{font-size:10.6pt; margin:3.6mm 0 1.5mm; padding-bottom:.8mm;
  border-bottom:.6pt solid #ccc; break-after:avoid; page-break-after:avoid}
h4{font-size:9.8pt; margin:3mm 0 1.2mm; break-after:avoid; page-break-after:avoid}
p{margin:0 0 2.4mm}
ul,ol{margin:0 0 2.8mm; padding-left:6mm}
li{margin:0 0 .8mm}
ul.chk{list-style:none; padding-left:0}
ul.chk li::before{content:"☐"; margin-right:2mm; font-size:11pt; line-height:1}
strong{font-weight:700}
code{font-family:"SFMono-Regular",Consolas,"Noto Sans Mono",monospace;
  font-size:8.6pt; background:#f2f2f2; padding:.2mm 1mm; border-radius:1mm}
pre{background:#f6f6f6; border:.5pt solid #ddd; padding:3mm 4mm; margin:0 0 3mm;
  break-inside:avoid; page-break-inside:avoid; overflow:visible}
pre code{background:none; padding:0; font-size:8.6pt; line-height:1.6; white-space:pre-wrap}
blockquote{margin:0 0 3mm; padding:2mm 3mm; background:#f7f7f7;
  border-left:2.5pt solid #888; break-inside:avoid; page-break-inside:avoid}
blockquote p:last-child{margin-bottom:0}
hr{border:0; border-top:.6pt solid #ddd; margin:3.5mm 0}
table{border-collapse:collapse; width:100%; margin:0 0 3.5mm; font-size:8.6pt;
  break-inside:avoid; page-break-inside:avoid}
th,td{border:.5pt solid #999; padding:1.4mm 2mm; text-align:left; vertical-align:top;
  line-height:1.55}
th{background:#ececec; font-weight:700; white-space:nowrap}
thead{display:table-header-group}
/* 大きい表は途中で切れてよい。切れないと1ページに収まらず消える */
table.big{break-inside:auto; page-break-inside:auto}
table.big tr{break-inside:avoid; page-break-inside:avoid}
/* ── 参照（紙ではリンクを押せないので番号で引く）── */
.ref{white-space:nowrap; font-weight:600}
.ref .n{font-size:8pt; border:.6pt solid #666; border-radius:1mm;
  padding:0 1mm; margin-right:.8mm; font-variant-numeric:tabular-nums}
.ref .sec{font-weight:400; color:#444}
/* ── 画面で見るときだけの操作 ── */
.bar{position:sticky; top:0; background:#fff; border-bottom:1pt solid #ddd;
  padding:8px 12px; display:flex; gap:10px; align-items:center; font-size:13px; z-index:9}
.bar a{color:#1a4fd6}
.bar button{font:inherit; padding:5px 12px; border:1px solid #999; background:#fff;
  border-radius:5px; cursor:pointer}
@media print{ .bar{display:none} .wrap{padding:0} }
"""

HOWTO = """
<div class="howto">
<b>紙で読むときの約束ごと</b>
<p style="margin:2mm 0 0">本文中の <span class="ref"><span class="n">23</span>平均賃金</span>
のような表示は、ほかの資料への参照です。頭の番号が資料の通し番号なので、
目次か各ページ右上の番号から引いてください。</p>
<p style="margin:2mm 0 0"><span class="ref"><span class="n">5</span>労働基準法
<span class="sec">「4. 労働時間・休憩・休日」</span></span> のように節名が付いているものは、
その資料の中の該当する節を指します。</p>
<p style="margin:2mm 0 0">□ は手で塗るためのものです。</p>
</div>
"""

def build(pages, title, subtitle, path, allpages=None):
    """pages: [(通し番号, 科目, ファイル名, タイトル, 説明, 本文)]

    参照の番号は「全体版の通し番号」で振る。科目ごとに分けて刷っても、
    番号の意味が変わらないようにするため（allpages に全体を渡す）。"""
    ref = allpages or pages
    num_of = {f: n for n, _, f, _, _, _ in ref}
    title_of = {f: t for _, _, f, t, _, _ in ref}
    here = {f for _, _, f, _, _, _ in pages}

    def link(text, href):
        f = href.split("#")[0]
        frag = href.split("#")[1] if "#" in href else ""
        if f.startswith("http"):
            return f"{esc(text)}<span class=\"sec\">（{esc(f)}）</span>"
        if f in num_of:
            sec = f"<span class=\"sec\">「{esc(frag)}」</span>" if frag else ""
            # この冊子に入っていない資料は、全体版を見る必要があると分かるようにする
            out = f"<span class=\"n\">{num_of[f]}</span>{esc(title_of[f])}{sec}"
            if f not in here:
                out += "<span class=\"sec\">（全体版）</span>"
            return f'<span class="ref">{out}</span>'

        if not f and frag:                       # 同じ資料の中の節
            return f'<span class="ref"><span class="sec">本資料「{esc(frag)}」</span></span>'
        return esc(text)

    body = []
    # 表紙
    body.append(f'<div class="cover"><h1>{esc(title)}</h1>'
                f'<div class="sub">{subtitle}</div>{HOWTO}</div>')
    # 目次
    toc = ['<div class="doc toc"><h2>目次</h2>']
    last = None
    for n, g, f, t, d, _ in pages:
        if g != last:
            toc.append(f'<div class="grp">{esc(g)}</div><ol>')
            if last is not None:
                toc.insert(-1, "</ol>")
            last = g
        toc.append(f'<li><span class="no">{n}</span><span>{esc(t)}</span>'
                   f'<span class="dots"></span></li>')
    toc.append("</ol></div>")
    body.append("".join(toc))
    # 本文
    for n, g, f, t, d, src in pages:
        # 先頭のH1は見出しとして別に出すので本文からは落とす
        src = re.sub(r"^# .*\n", "", src, count=1)
        html_body = md2html(src, link)
        # 行数の多い表は途中で改ページしてよい
        html_body = re.sub(r"<table>(?=(?:(?!</table>).)*?(?:<tr>.*?){12,})",
                           '<table class="big">', html_body, flags=re.S)
        body.append(f'<div class="doc"><div class="head">'
                    f'<div class="no">資料 {n} ／ {esc(g)}</div>'
                    f'<h1>{esc(t)}</h1>'
                    + (f'<div class="desc">{esc(d)}</div>' if d else "")
                    + f'</div>{html_body}</div>')

    doc = f"""<!doctype html>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}</style>
<div class="bar">
  <button onclick="print()">印刷する</button>
  <span>A4縦・{len(pages)}資料。1枚に2ページ並べて刷る想定です。
  ブラウザの印刷から「背景のグラフィック」を入にすると表の罫線が出ます。</span>
</div>
<div class="wrap">{''.join(body)}</div>
"""
    open(path, "w", encoding="utf-8").write(doc)
    return len(doc)

def main():
    # 資料の説明はアプリと同じものを使う
    meta = {}
    g = open(os.path.join(HERE, "gen_notes.py"), encoding="utf-8").read()
    for m in re.finditer(r'"([^"]+\.md)":\s*\("([^"]*)",\s*"([^"]*)"\)', g):
        meta[m.group(1)] = (m.group(2), m.group(3))

    pages = []
    for i, (grp, f) in enumerate(order(), 1):
        src = open(os.path.join(NOTES, f), encoding="utf-8").read()
        t, d = meta.get(f, (f[:-3], ""))
        pages.append((i, grp, f, t, d, src))

    n = build(pages, "社会保険労務士試験 2026 学習資料",
              "令和8年度（第58回）本試験 2026年8月23日<br>"
              f"全{len(pages)}資料　過去9年の本試験データから作成",
              os.path.join(OUTDIR, "print.html"))
    print(f"→ drill/print.html  {len(pages)}資料 / {n:,} bytes")

    # 科目ごとにも出す。全部まとめて印刷すると重いので分けて刷れるように。
    for grp in dict.fromkeys(g for _, g, _, _, _, _ in pages):
        sub = [p for p in pages if p[1] == grp]
        name = f"print-{grp}.html"
        # 番号は通し番号のままにする（目次と参照が全体版と一致する）
        n = build(sub, f"社労士2026 学習資料｜{grp}",
                  f"全体版の資料 {sub[0][0]}〜{sub[-1][0]}　"
                  "（本文中の参照番号は全体版と共通です）",
                  os.path.join(OUTDIR, name), allpages=pages)
        print(f"   {name}  {len(sub)}資料")

if __name__ == "__main__":
    main()
