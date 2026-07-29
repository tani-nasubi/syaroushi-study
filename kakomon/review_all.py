#!/usr/bin/env python3
"""資料全体を10の観点で検査する。深掘りページを全科目に広げたあとの点検用。

出題実績との突き合わせ（cover_all.py）とは別に、資料そのものの体裁・
整合・事実関係を見る。指摘は候補であり、最後は条文で確かめる。
"""
import os, re, glob, sys, ast, collections
import xml.etree.ElementTree as ET

HERE  = os.path.dirname(os.path.abspath(__file__))
NOTES = os.path.join(os.path.dirname(HERE), "notes")
HOUREI = os.path.join(HERE, "hourei")
LAWS = ast.literal_eval(re.search(r"LAWS\s*=\s*(\{.*?\n\})",
        open(os.path.join(HERE, "gen_anaume2.py"), encoding="utf-8").read(), re.S).group(1))

DOCS = {os.path.basename(p): open(p, encoding="utf-8").read()
        for p in sorted(glob.glob(os.path.join(NOTES, "*.md")))}
DEEP = {k: v for k, v in DOCS.items() if re.match(r"^[B-L]\d-", k)}

hits = collections.defaultdict(list)
def bad(n, msg):
    hits[n].append(msg)

# ── 1. リンク切れ・孤立ページ ────────────────────────────────
def v1():
    linked = set()
    for f, s in DOCS.items():
        for m in re.finditer(r"\]\(([^)#]+\.md)(?:#[^)]*)?\)", s):
            t = m.group(1)
            if t not in DOCS:
                bad(1, f"リンク切れ {f} → {t}")
            else:
                linked.add(t)
    for f in DEEP:
        if f not in linked:
            bad(1, f"どこからも辿れない {f}")

# ── 2. 見出し・体裁 ──────────────────────────────────────────
def v2():
    for f, s in DOCS.items():
        if not s.startswith("# "):
            bad(2, f"H1で始まっていない {f}")
        if "\n---\n\n---\n" in s or "\n---\n---\n" in s:
            bad(2, f"区切り線が連続 {f}")
        if re.search(r"\n#{1,6}[^ #]", s):
            bad(2, f"見出しの#の後に空白がない {f}")
        for m in re.finditer(r"^\|.*\|$", s, re.M):
            pass
        if f in DEEP and "## 次に読むもの" not in s:
            bad(2, f"戻り導線がない {f}")

# ── 3. 表の列数がそろっているか ──────────────────────────────
def v3():
    for f, s in DOCS.items():
        rows, head = [], None
        for line in s.split("\n"):
            if line.startswith("|") and line.rstrip().endswith("|"):
                n = line.count("|") - 1
                if head is None:
                    head = n
                elif re.match(r"^\|[\s:|-]+\|$", line):
                    if n != head:
                        bad(3, f"区切り行の列数が違う {f}: {line[:40]}")
                else:
                    if n != head:
                        bad(3, f"列数が違う {f}: {line[:46]}")
            else:
                head = None

# ── 4. 外国語文字の混入 ──────────────────────────────────────
# 本文で使ってよい略語。これ以外のラテン語が日本語に直接くっついていたら
# 生成時の取り違えを疑う（「labor関係」「treatment用装具」のような事故）。
OKWORD = {"MBA","IT","ITSS","SDS","ICD","BMI","LDL","HDL","iDeCo","ADR","DC","DB",
          "GDP","km","ILO","OECD","NPO","PDF","URL","AI","DX"}
def v4():
    for f, s in DOCS.items():
        for m in re.finditer(r"[Ѐ-ӿ가-힣؀-ۿ฀-๿]+", s):
            bad(4, f"日本語以外の文字 {f}: {s[max(0,m.start()-20):m.end()+10]!r}")
        t = re.sub(r"`[^`]*`", "`", s)
        t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
        t = re.sub(r"\[[^\]]*\]\([^)]*\)", "", t)
        for m in re.finditer(r"(?:(?<=[ぁ-んァ-ヴ一-鿿])[A-Za-z]{2,}"
                             r"|[A-Za-z]{2,}(?=[ぁ-んァ-ヴ一-鿿]))", t):
            if m.group(0) not in OKWORD:
                bad(4, f"日本語に紛れた英単語 {f}: {t[max(0,m.start()-20):m.end()+10]!r}")

# ── 5. 引用した条番号が実在するか ────────────────────────────
_arts = {}
def arts_of(law):
    if law not in _arts:
        lid = next((k for k, v in LAWS.items() if v == law), None)
        p = os.path.join(HOUREI, f"{lid}.xml") if lid else None
        got = None
        if p and os.path.exists(p):
            got = set()
            for a in ET.parse(p).getroot().iter("Article"):
                q = a.get("Num", "").split(":")[0].split("_")
                if q[0].isdigit():
                    lab = f"第{int(q[0])}条"
                    if len(q) > 1 and q[1].isdigit():
                        lab += f"の{int(q[1])}"
                    got.add(lab)
        _arts[law] = got
    return _arts[law]

# 深掘りページの接頭辞 → 既定の法令
PRE2LAW = {"B": "労働基準法", "C": "労働基準法", "D": "労働安全衛生法",
           "E": "労働者災害補償保険法", "F": "雇用保険法", "G": "労働保険徴収法",
           "J": "健康保険法", "K": "国民年金法", "L": "厚生年金保険法"}

def v5():
    for f, s in DEEP.items():
        law = PRE2LAW.get(f[0])
        if not law:
            continue                      # 労一・社一は法令が混ざるので対象外
        real = arts_of(law)
        if real is None:
            continue
        body = re.sub(r"\[[^\]]*\]\([^)]*\)", "", s)      # リンクは除く
        for m in re.finditer(r"(?<![0-9])(\d{1,3})条(?:の(\d{1,2}))?", body):
            # 直前に他の法令名があるものは対象外
            head = body[max(0, m.start() - 16):m.start()]
            # 「◯◯法」「◯◯則」「同令」など、別の法令を指しているものは対象外
            if re.search(r"(法|規則|令|則)\s*$", head):
                continue
            if re.search(r"[〜～~－ー]\s*第?$", head):     # 「644条〜662条」の後半
                continue
            lab = f"第{int(m.group(1))}条" + (f"の{int(m.group(2))}" if m.group(2) else "")
            if lab not in real:
                bad(5, f"{law}に無い条 {f}: {body[max(0,m.start()-16):m.end()+6]}")

# ── 6. 数値の表記ゆれ ────────────────────────────────────────
# 本試験の原文をそのまま収めた資料は、表記を原文どおりにしておく
RAWDOC = {"95-条文素読（選択式の原文）.md", "A0-正文集（択一の正しい肢）.md"}
def v6():
    for f, s in DOCS.items():
        if f in RAWDOC:
            continue
        for m in re.finditer(r"[０-９]+", s):
            bad(6, f"全角数字 {f}: {s[max(0,m.start()-14):m.end()+8]!r}")
        for m in re.finditer(r"(?<![0-9,./])\d{4,}(?![0-9,]*[円日月年人条項号級歳％%度回分年])", s):
            t = s[max(0, m.start()-12):m.end()+10]
            # 「◯/1000」の分母、元号、金額は桁区切りしない
            if re.match(r"\d+(?![,\d])", s[m.start():]) and s[max(0,m.start()-1)] in "/.":
                continue
            if any(k in t for k in ("円", "年度", "昭和", "平成", "令和", "/1000", "分の")):
                continue
            bad(6, f"桁区切りのない数 {f}: {t!r}")

# ── 7. 科目間で食い違う数値 ──────────────────────────────────
FACTS = [
  ("延滞金の率", r"年\*?\*?14[\.．]6"),
  ("督促の指定期限", r"10日以上"),
  ("障害等級の境目", r"第?7級"),
]
def v7():
    # 同じ語に別々の数字を当てていないか（代表的なものだけ）
    pat = {
      "傷病手当金の支給期間": (r"傷病手当金.{0,40}?通算(?:して)?(\d+年\d*か?月?)", "1年6か月"),
      "介護休業の日数":       (r"介護休業.{0,60}?通算(\d+日)", "93日"),
      "出産手当金の産前":     (r"出産(?:の日)?.{0,20}?以前(\d+日)", "42日"),
    }
    for key, (rx, want) in pat.items():
        seen = set()
        for f, s in DOCS.items():
            for m in re.finditer(rx, s):
                seen.add(m.group(1))
        wrong = {x for x in seen if x.replace("箇", "か") != want}
        if wrong:
            bad(7, f"{key}: 想定「{want}」と違う表記 {sorted(wrong)}")

# ── 8. 深掘りページの分量 ────────────────────────────────────
def v8():
    for f, s in DEEP.items():
        n = len(re.sub(r"\s", "", s))
        if n < 900:
            bad(8, f"内容が薄い {f}（{n}字）")
        if n > 6000:
            bad(8, f"1ページが長すぎる {f}（{n}字）")

# ── 9. 太字・強調の壊れ ──────────────────────────────────────
def v9():
    for f, s in DOCS.items():
        for i, line in enumerate(s.split("\n"), 1):
            if line.count("**") % 2:
                bad(9, f"太字の対応が合わない {f}:{i} {line[:50]}")
            if line.count("`") % 2 and not line.startswith("```"):
                bad(9, f"バッククォートの対応が合わない {f}:{i} {line[:50]}")

# ── 10. 資料の登録漏れ ───────────────────────────────────────
def v10():
    g = open(os.path.join(HERE, "gen_notes.py"), encoding="utf-8").read()
    for f in DOCS:
        if f'"{f}"' not in g:
            bad(10, f"gen_notes.py のMETAに無い {f}")
    js = os.path.join(os.path.dirname(HERE), "drill", "data", "notes.js")
    j = open(js, encoding="utf-8").read()
    for f in DOCS:
        if f not in j:
            bad(10, f"notes.js に入っていない {f}")

TITLES = ["リンク切れ・孤立", "見出しと体裁", "表の列数", "外国語文字の混入",
          "条番号の実在", "数値の表記", "科目間の食い違い", "分量", "強調の壊れ", "登録漏れ"]

def main():
    for i, fn in enumerate([v1, v2, v3, v4, v5, v6, v7, v8, v9, v10], 1):
        fn()
    ng = 0
    for i, t in enumerate(TITLES, 1):
        h = hits[i]
        print(f"【{i:2}】{t}　{'■ ' + str(len(h)) + '件' if h else 'OK'}")
        for m in h[:8]:
            print("      " + m)
        if len(h) > 8:
            print(f"      … 他{len(h)-8}件")
        ng += bool(h)
    print(f"\n要改善: {ng}観点 / 指摘 {sum(len(v) for v in hits.values())}件"
          f" / 資料 {len(DOCS)}件（うち深掘り {len(DEEP)}件）")

if __name__ == "__main__":
    main()
