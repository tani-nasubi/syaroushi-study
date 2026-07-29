#!/usr/bin/env python3
"""選択式の本文に正答を埋め戻して「出題された条文の原文」を復元し、素読用の資料を生成する。

選択式は条文・判示からの出題が中心なので、正答を埋めた完成文はそのまま
出題実績のある条文の原文になる。過去問データから機械的に作るので、
私（生成AI）の記憶に依存せず、文言が正確。
"""
import json, re, collections

M = json.load(open("mondai.json"))
S = json.load(open("seitou.json"))
OUT = "../notes/95-条文素読（選択式の原文）.md"
KAI2Y = {57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",
         52:"令和2",51:"令和元",50:"平成30",49:"平成29"}
ORDER = ["労基安衛","労災","雇用","労一","社一","健保","厚年","国年"]
LABEL = {"労基安衛":"労働基準法・労働安全衛生法","労災":"労働者災害補償保険法","雇用":"雇用保険法",
         "労一":"労務管理その他の労働に関する一般常識","社一":"社会保険に関する一般常識",
         "健保":"健康保険法","厚年":"厚生年金保険法","国年":"国民年金法"}

def clean(t):
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(?<=[぀-ヿ一-鿿、。」）])\s+(?=[぀-ヿ一-鿿「（])", "", t)
    return t.strip()

def para(t):
    """本文中の項番号（1 2 3 …）の前で改行し、読める形にする。"""
    t = re.sub(r"(?<=[。」])\s*([1-9]) ", r"\n\n\1　", t)
    t = re.sub(r"^([1-9]) ", r"\1　", t)
    return t

items = collections.defaultdict(list)   # 科目 -> [(回, 完成文, 正答リスト)]
for kai, v in M.items():
    k = int(kai)
    for q in v["sentaku"]:
        raw = S[kai]["sentaku"][q["subject"]]
        ans = []
        for i, a in enumerate(raw):
            a = a[0] if isinstance(a, list) else a
            if a is None: ans.append(None); continue
            w = (q["choices"][a-1] if q["format"]=="pool20"
                 else (q["choices"][i][a-1] if a-1 < len(q["choices"][i]) else ""))
            ans.append(clean(w))
        bl = sorted(set(re.findall(r"【([A-E])】", q["body"])))
        body = q["body"]
        for L in bl:
            i = bl.index(L)
            w = ans[i] if i < len(ans) and ans[i] else "—"
            body = body.replace(f"【{L}】", f"**{w}**")   # 空欄に正答を埋め戻す
        items[q["subject"]].append((k, para(clean(body)),
                                    [a for a in ans if a]))

with open(OUT, "w") as f:
    w = f.write
    w("""# 条文素読｜選択式で実際に出題された原文

| 項目 | 内容 |
|---|---|
| 収録 | 過去9年（第49〜57回）の選択式**72問**の本文に、**正答を埋め戻した完成文** |
| 意味 | 選択式は条文・判示からの出題が中心。埋め戻せば**出題された条文の原文**になる |
| 使い方 | **太字が実際に空欄だった語**。声に出して読み、太字が言えるか確認する |

> この資料は過去問データから機械的に生成しています。**文言は本試験の原文そのまま**です。
> 生成にあたって内容を要約・改変していません（`kakomon/gen_genbun.py`）。

---

## なぜ素読が効くのか

選択式の正答語のうち、**それ以前の過去問に既出だったのは平均47%**です。
つまり**過去に出た条文は繰り返し問われます**。しかも同じ条文の別の箇所が空欄になります。

要約された解説を読むのではなく、**原文をそのまま読む**ことでしか、
「この条文はこういう言い回しをする」という感覚は身につきません。

### 読み方

1. **太字を隠して**読む（指で隠す、印刷して塗る）
2. 太字が出てこなければ、その語をチェック
3. 1周目は全部読む。2周目以降は**出てこなかった語だけ**
4. 同じ条文の**別の箇所**が空欄になりうると意識する

---

""")
    for s in ORDER:
        if s not in items: continue
        w(f"## {LABEL[s]}（{s}）\n\n")
        for k, body, ans in sorted(items[s], reverse=True):
            w(f"### {KAI2Y[k]}年度（第{k}回）\n\n")
            for line in body.split("\n"):
                line = line.strip()
                if line: w(f"{line}\n\n")
            w(f"> **空欄だった語**：{' ／ '.join(ans)}\n\n")
        w("---\n\n")
    w("""## 次に読むもの

| 資料 | 用途 |
|---|---|
| [`92-選択式の解き方.md`](92-選択式の解き方.md) | 初見問題での絞り込み手順 |
| [`93-判例.md`](93-判例.md) | 判示の言い回しの型 |
| [`90-横断整理.md`](90-横断整理.md) | 数値の取りうる範囲 |
""")

n = sum(len(v) for v in items.values())
size = len(open(OUT).read())
print(f"→ {OUT}")
print(f"   {n}問 / {size:,}字")
for s in ORDER:
    if s in items: print(f"   {s:<6} {len(items[s])}問")
