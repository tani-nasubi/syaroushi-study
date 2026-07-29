#!/usr/bin/env python3
"""択一の「正しい肢」から正文集を作る。

選択式は 95-条文素読 で原文を読めるようにした。択一側は科目別ノート（私の要約）
しかなかったので、本試験で『正しい』と確定した肢を、論点別に並べて読めるようにする。
文言は本試験の原文そのまま。
"""
import json, re, collections

M = json.load(open("mondai.json")); S = json.load(open("seitou.json"))
OUT = "../notes/A0-正文集（択一の正しい肢）.md"
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
KAI2Y = {57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",52:"令和2",51:"令和元",50:"平成30",49:"平成29"}
ORDER = ["労基安衛","労災","雇用","一般常識","健保","厚年","国年"]
LABEL = {"労基安衛":"労基・安衛","労災":"労災・徴収","雇用":"雇用・徴収",
         "一般常識":"一般常識（労一・社一）","健保":"健康保険法","厚年":"厚生年金保険法","国年":"国民年金法"}

# 論点キーワード（96-得点源リスト と同じ体系）
ns = {}
exec(open("gen_tokuten.py").read().split("stat = {}")[0], ns)
KEYS = ns["KEYS"]

def qtype(s):
    s = NOSP(s)
    if "いくつあるか" in s: return "個数"
    if "組合せ" in s: return "組合せ"
    if re.search(r"誤っているもの|誤りである", s): return "誤り選び"
    if re.search(r"正しいもの|適切なもの", s): return "正しい選び"
    return "その他"

def clean(t):
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(?<=[぀-ヿ一-鿿、。」）])\s+(?=[぀-ヿ一-鿿「（])", "", t)
    t = re.sub(r"^(なお|また)、", "", t)
    return t.strip()

# 正しい肢を集める
RIGHT = collections.defaultdict(list)
for kai, v in M.items():
    k = int(kai)
    for q in v["takuitsu"]:
        a = S[kai]["takuitsu"][q["subject"]][q["num"]-1]
        if a is None or isinstance(a, list): continue
        t = qtype(q["stem"])
        if t == "誤り選び":
            RIGHT[q["subject"]] += [(k, q["num"], c) for i, c in enumerate(q["choices"]) if i != a]
        elif t == "正しい選び":
            RIGHT[q["subject"]].append((k, q["num"], q["choices"][a]))

# （旧）最長一致で論点を1つに決める方式
def topic_of(subj, text):
    t = NOSP(text); best = None; blen = 0
    for kw in KEYS.get(subj, []):
        kk = NOSP(kw)
        if kk in t and len(kk) > blen: best, blen = kw, len(kk)
    return best

# 論点ごとに独立して選ぶ。
# 以前は「最長一致の論点1つ」に割り当てていたため、「保険者」が「被保険者」に飲まれて
# 出題9年の論点なのに1本も載らない、という取りこぼしが起きていた。
def years_of(subj, kw):
    kk = NOSP(kw); ys = set()
    for kai, v in M.items():
        for q in v["takuitsu"]:
            if q["subject"] != subj: continue
            if kk in NOSP(q["stem"]) or sum(1 for c in q["choices"] if kk in NOSP(c)) >= 3:
                ys.add(int(kai))
    return len(ys)

picked = collections.defaultdict(lambda: collections.defaultdict(list))
for subj, arr in RIGHT.items():
    arr = [x for x in sorted(arr, key=lambda x: -x[0]) if 55 <= len(NOSP(x[2])) <= 230]
    used = set()
    # 出題年数の多い論点から先に取る（頻出論点を確実に埋める）
    for kw in sorted(KEYS.get(subj, []), key=lambda k: -years_of(subj, k)):
        kk = NOSP(kw)
        for k, n, c in arr:
            if len(picked[subj][kw]) >= 3: break
            key = (k, n, NOSP(c)[:30])
            if key in used or kk not in NOSP(c): continue
            if any(NOSP(c)[:30] == NOSP(x[2])[:30] for x in picked[subj][kw]): continue
            picked[subj][kw].append((k, n, c)); used.add(key)
        if not picked[subj][kw]:
            # 55〜230字の条件で1本も取れない論点は、条件をゆるめて拾い直す
            for k, n, c in [x for x in sorted(RIGHT[subj], key=lambda x: -x[0])
                            if 40 <= len(NOSP(x[2])) <= 300]:
                if len(picked[subj][kw]) >= 2: break
                if kk not in NOSP(c): continue
                if any(NOSP(c)[:30] == NOSP(x[2])[:30] for x in picked[subj][kw]): continue
                picked[subj][kw].append((k, n, c))
        if not picked[subj][kw]: del picked[subj][kw]

with open(OUT, "w") as f:
    w = f.write
    total = sum(len(v) for d in picked.values() for v in d.values())
    w(f"""# 正文集｜択一で「正しい」と確定した肢

| 項目 | 内容 |
|---|---|
| 収録 | 過去9年の択一から、**正誤が確定した正しい肢 {total}本**を論点別に整理 |
| 意味 | 科目別ノートは私の要約。**この資料は本試験の原文そのまま** |
| 使い方 | 論点ごとに読み、**「そう書いてあったか」を確認する**。誤りを探す読み方はしない |

> `95-条文素読` が選択式の原文なら、こちらは**択一の原文**です。
> 過去問データから機械的に生成しているので（`kakomon/gen_seibun.py`）、文言は正確です。

---

## なぜ正文を読むのか

択一の勉強は「誤りを見つける」訓練に偏りがちですが、**誤りを見つけるには正しい形を知っていることが前提**です。

- 誤り肢は**正しい記述の一部を書き換えて**作られます（→ [`97-引っかけの型.md`](97-引っかけの型.md)）
- **正しい形が頭に入っていれば、書き換えられた瞬間に違和感が出ます**
- 要約された解説では、この「違和感」は育ちません

### 読み方

1. 論点の見出しを見て、**自分で内容を思い出してから**本文を読む
2. 思い出せなかった論点に印をつける
3. 2周目以降は**印をつけた論点だけ**
4. [`96-得点源リスト.md`](96-得点源リスト.md) のS・Aランク論点を優先する

---

""")
    for subj in ORDER:
        d = picked.get(subj)
        if not d: continue
        # 論点は収録数の多い順（＝頻出順）
        tps = sorted(d.items(), key=lambda x: -len(x[1]))
        w(f"## {LABEL[subj]}\n\n")
        for tp, arr in tps:
            w(f"### {tp}\n\n")
            for k, n, c in sorted(arr, reverse=True):
                w(f"- {clean(c)}　<span style=\"opacity:.55\">（{KAI2Y[k]}年度 問{n}）</span>\n")
            w("\n")
        w("---\n\n")
    w("""## 次に読むもの

| 資料 | 用途 |
|---|---|
| [`97-引っかけの型.md`](97-引っかけの型.md) | この正しい形が、どう書き換えられて誤り肢になるか |
| [`96-得点源リスト.md`](96-得点源リスト.md) | どの論点を優先して読むか |
| [`95-条文素読（選択式の原文）.md`](95-条文素読（選択式の原文）.md) | 選択式の原文 |
""")

print(f"→ {OUT}  {len(open(OUT).read()):,}字")
for subj in ORDER:
    if subj in picked:
        print(f"   {LABEL[subj]:<18} 論点{len(picked[subj]):3d}件 / 正文{sum(len(v) for v in picked[subj].values()):4d}本")
