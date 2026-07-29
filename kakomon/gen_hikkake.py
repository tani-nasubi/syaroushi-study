#!/usr/bin/env python3
"""「引っかけの型」資料を生成する。

過去9年の択一から、正誤が確定する肢を 誤り1,326肢／正しい1,269肢 に分解し、
 ① 科目ごとに「どこが改変されやすいか」を統計で出す
 ② 同じ論点を扱う『誤り肢 × 正しい肢』のペアを機械的に見つけて対比表示する
 ③ 通達・行政解釈に基づく記述（条文だけでは解けない知識）を抽出する
すべて過去問データ由来なので、文言は本試験の原文そのまま。
"""
import json, re, collections

M = json.load(open("mondai.json")); S = json.load(open("seitou.json"))
OUT = "../notes/97-引っかけの型.md"
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
ORDER = ["労基安衛","労災","雇用","一般常識","健保","厚年","国年"]
LABEL = {"労基安衛":"労基・安衛","労災":"労災・徴収","雇用":"雇用・徴収",
         "一般常識":"一般常識（労一・社一）","健保":"健康保険法","厚年":"厚生年金保険法","国年":"国民年金法"}
KAI2Y = {57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",52:"令和2",51:"令和元",50:"平成30",49:"平成29"}

def qtype(s):
    s = NOSP(s)
    if "いくつあるか" in s: return "個数"
    if "組合せ" in s: return "組合せ"
    if re.search(r"誤っているもの|誤りである", s): return "誤り選び"
    if re.search(r"正しいもの|適切なもの", s): return "正しい選び"
    return "その他"

W = collections.defaultdict(list); R = collections.defaultdict(list)
for kai, v in M.items():
    for q in v["takuitsu"]:
        a = S[kai]["takuitsu"][q["subject"]][q["num"]-1]
        if a is None or isinstance(a, list): continue
        t = qtype(q["stem"])
        if t == "誤り選び":
            W[q["subject"]].append((int(kai), q["num"], q["choices"][a]))
            R[q["subject"]] += [(int(kai), q["num"], c) for i, c in enumerate(q["choices"]) if i != a]
        elif t == "正しい選び":
            R[q["subject"]].append((int(kai), q["num"], q["choices"][a]))
            W[q["subject"]] += [(int(kai), q["num"], c) for i, c in enumerate(q["choices"]) if i != a]

PAT = {"数値": r"[0-9０-９]+\s*(年|月|日|時間|人|円|％|分の[0-9])",
       "主体": r"(厚生労働大臣|都道府県労働局長|労働基準監督署長|公共職業安定所長|市町村長|保険者|政府|裁判所|実施機関)",
       "義務／裁量": r"(しなければならない|することができる|するものとする|してはならない|努めなければならない)",
       "範囲": r"(以上|以下|超え|未満|以内|を限度)"}

def grams(s, n=3):
    s = NOSP(s); return {s[i:i+n] for i in range(len(s)-n+1)}
def jac(a, b): return len(a & b) / len(a | b) if a and b else 0

def clean(t):
    t = re.sub(r"\s+", " ", t)
    return re.sub(r"(?<=[぀-ヿ一-鿿、。」）])\s+(?=[぀-ヿ一-鿿「（])", "", t).strip()

with open(OUT, "w") as f:
    w = f.write
    w("""# 引っかけの型｜出題者はどこを改変するか

| 項目 | 内容 |
|---|---|
| 根拠 | 過去9年の択一630問を、**誤り1,326肢／正しい1,269肢**に分解して実測 |
| 目的 | 「なんとなく正しそう」で選ばない。**疑うべき箇所を科目ごとに決めておく** |
| 使い方 | 肢を読むとき、その科目で改変されやすい箇所に**先に目を向ける** |

> 掲載している肢は**本試験の原文そのまま**です（`kakomon/gen_hikkake.py` が過去問データから生成）。

---

## 1. 科目ごとに「疑うべき箇所」が違う

誤り肢に何が含まれているかを数えると、科目ごとにはっきり傾向が出ます。

| 科目 | 数値 | **主体** | 義務／裁量 | 範囲（以上・未満） |
|---|---:|---:|---:|---:|
""")
    stats = {}
    for s in ORDER:
        ws = [c for _, _, c in W[s]]
        if not ws: continue
        c = {k: sum(1 for x in ws if re.search(p, NOSP(x)))/len(ws)*100 for k, p in PAT.items()}
        stats[s] = c
        w(f"| {LABEL[s]} | {c['数値']:.0f}% | **{c['主体']:.0f}%** | {c['義務／裁量']:.0f}% | {c['範囲']:.0f}% |\n")
    w("""
### 読み取れること

- **健保78%・厚年62%・国年54%** — 社会保険3科目の誤り肢は**「主体」を含む割合が突出**。
  「**誰が**（厚生労働大臣／保険者／実施機関／市町村長）行うのか」が改変の主戦場です。
- **労基安衛は数値29%・義務裁量23%・範囲24%** と分散。特定の型に偏らないので、
  条文の**文言そのもの**を覚えていないと切れません。
- **雇用は主体41%・数値36%** の両方が高い。給付の名称と支給要件の数値を正確に。
- 全科目で**「範囲」（以上／未満／以内／を超え）** が15〜36%。**境界値の言い換えは定番**です。

### 肢を読むときの順序

1. **主体**を確認（社会保険科目では最優先）
2. **数値と範囲**を確認（「以上」か「超え」か、「以内」か「未満」か）
3. **文末**を確認（義務／裁量／努力義務／禁止）
4. そのうえで内容の当否を判断

---

## 2. 実例｜同じ論点の「誤り肢 × 正しい肢」

出題者は、**過去に正しい肢として出した記述の一部を書き換えて**誤り肢を作ります。
機械的に類似ペアを探すと、どこが改変されたかがそのまま見えます。

""")
    for s in ORDER:
        ws = [(k, n, c, grams(c)) for k, n, c in W[s] if 60 < len(NOSP(c)) < 420]
        rs = [(k, n, c, grams(c)) for k, n, c in R[s] if 60 < len(NOSP(c)) < 420]
        pairs = []
        for k, n, c, g in ws:
            best = max(((jac(g, g2), k2, n2, c2) for k2, n2, c2, g2 in rs if not (k2 == k and n2 == n)),
                       default=(0, 0, 0, ""))
            if best[0] >= 0.34: pairs.append((best[0], k, n, c, best[1], best[2], best[3]))
        pairs.sort(reverse=True)
        seen = set(); out = []
        for p in pairs:
            key = (p[1], p[2])
            if key in seen: continue
            seen.add(key); out.append(p)
            if len(out) >= 6: break
        if not out: continue
        w(f"### {LABEL[s]}\n\n")
        for sim, k, n, wc, k2, n2, rc in out:
            w(f"**{KAI2Y[k]}年度 問{n}（誤り）** ／ **{KAI2Y[k2]}年度 問{n2}（正しい）**　類似度 {sim:.2f}\n\n")
            w(f"> ✗ {clean(wc)}\n\n")
            w(f"> ○ {clean(rc)}\n\n")
            w("---\n\n")

    # ── 通達・行政解釈 ──
    w("""## 3. 通達・行政解釈からの出題

条文だけでは解けない記述が、**630問中156問（25%）**に登場します。
「〜とされている」「〜と解されている」で終わる記述は、条文ではなく**通達・行政解釈**が根拠です。

過去問で**正しい肢**として出題された通達ベースの記述を、科目別に抜き出します。
条文を読んでも出てこない知識なので、ここは**そのまま覚えるしかありません**。

""")
    TSU = re.compile(r"(とされている|と解されている|と解するのが相当|취급)")
    for s in ORDER:
        cand = [(k, n, c) for k, n, c in R[s]
                if TSU.search(NOSP(c)) and 50 < len(NOSP(c)) < 260]
        cand.sort(key=lambda x: len(NOSP(x[2])))
        if not cand: continue
        w(f"### {LABEL[s]}（該当 {len(cand)}肢のうち代表例）\n\n")
        for k, n, c in cand[:8]:
            w(f"- {clean(c)}　<span style=\"opacity:.6\">（{KAI2Y[k]}年度 問{n}）</span>\n")
        w("\n")

    w("""---

## 4. 直前チェック（引っかけ）

- [ ] 社会保険3科目（健保・厚年・国年）は**「主体」を最優先で疑う**
- [ ] 「以上／超え」「以内／未満」の**境界値の言い換え**（全科目15〜36%）
- [ ] 文末の**義務／裁量／努力義務**の入替え
- [ ] 労基安衛は特定の型に偏らない → **条文の文言そのもの**で勝負
- [ ] 「〜とされている」で終わる肢は**通達根拠**。条文を探しても出てこない

---

## 次に読むもの

| 資料 | 用途 |
|---|---|
| [`96-得点源リスト.md`](96-得点源リスト.md) | どの論点を優先するか |
| [`90-横断整理.md`](90-横断整理.md) | 主体（誰が）の一覧は第9節 |
| [`95-条文素読（選択式の原文）.md`](95-条文素読（選択式の原文）.md) | 条文の文言そのもの |
""")

print(f"→ {OUT}  {len(open(OUT).read()):,}字")
