#!/usr/bin/env python3
"""過去問9年分の統計を drill/data/stats.js に書き出す（アプリの「傾向」タブ用）。"""
import json, re, collections

M = json.load(open("mondai.json")); S = json.load(open("seitou.json"))
K = {int(a): b for a, b in json.load(open("kijun.json")).items()}
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
KAI2Y = {57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",
         52:"令和2",51:"令和元",50:"平成30",49:"平成29"}
SUBJ = ["労基安衛","労災","雇用","一般常識","健保","厚年","国年"]
SEL  = ["労基安衛","労災","雇用","労一","社一","健保","厚年","国年"]
ns = {}; exec(open("gen_tokuten.py").read().split("stat = {}")[0], ns)
KEYS = ns["KEYS"]

LAWRE = re.compile(r"(労働基準法|労働安全衛生法|労働者災害補償保険法|労災保険法|雇用保険法|"
                   r"労働保険の保険料の徴収等に関する法律|労働保険徴収法|健康保険法|厚生年金保険法|"
                   r"国民年金法|介護保険法|国民健康保険法|社会保険労務士法|労働契約法|労働組合法|"
                   r"最低賃金法|労働者派遣法|確定拠出年金法)(?:施行規則)?(?:第([0-9]{1,3})条)?")

def qtype(s):
    s = NOSP(s)
    if "いくつあるか" in s: return "個数"
    if "組合せ" in s: return "組合せ"
    if re.search(r"誤っているもの|誤りである", s): return "誤り"
    if re.search(r"正しいもの|適切なもの", s): return "正しい"
    return "その他"

# ── 1. 年度×科目の設問形式
style = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
for kai, v in M.items():
    k = int(kai)
    for q in v["takuitsu"]:
        c = style[k][q["subject"]]; t = NOSP(q["stem"] + "".join(q["choices"]))
        c[qtype(q["stem"])] += 1; c["問数"] += 1
        c["字数"] += sum(len(NOSP(x)) for x in q["choices"]); c["肢数"] += len(q["choices"])
        if re.search(r"最高裁判所|判示|判例", t): c["判例"] += 1
        if re.search(r"通達|とされている|と解されている|行政解釈", t): c["通達"] += 1

# ── 2. 選択式の出題ソース
src = collections.defaultdict(collections.Counter)
for kai, v in M.items():
    for q in v["sentaku"]:
        b = NOSP(q["body"])
        kind = ("判例" if re.search(r"最高裁判所|判示", b)
                else "統計" if re.search(r"白書|調査|統計|によれば", b) else "条文")
        src[int(kai)][kind] += 1; src[int(kai)][q["subject"]+"_"+kind] += 1

# ── 3. 論点別の出題年（S/A/B/Cランク）
topic = {}
for s in SUBJ:
    d = {}
    for kw in KEYS.get(s, []):
        kk = NOSP(kw); ys = set()
        for kai, v in M.items():
            for q in v["takuitsu"]:
                if q["subject"] != s: continue
                if kk in NOSP(q["stem"]) or sum(1 for c in q["choices"] if kk in NOSP(c)) >= 3:
                    ys.add(int(kai))
        if ys: d[kw] = sorted(ys, reverse=True)
    topic[s] = sorted(d.items(), key=lambda x: (-len(x[1]), -max(x[1])))

# ── 4. 再出題の間隔
gap = collections.Counter(); nxt = [0, 0]
for s, arr in topic.items():
    for kw, ys in arr:
        ys = sorted(ys)
        for i in range(len(ys) - 1): gap[ys[i+1] - ys[i]] += 1
        for y in ys[:-1] if len(ys) > 1 else []: pass
        for y in ys:
            if y < 57: nxt[1] += 1; nxt[0] += (y + 1) in ys

# ── 5. 誤り肢の改変パターン
PAT = {"数値": r"[0-9０-９]+\s*(年|月|日|時間|人|円|％|分の[0-9])",
       "主体": r"(厚生労働大臣|都道府県労働局長|労働基準監督署長|公共職業安定所長|市町村長|保険者|政府)",
       "義務裁量": r"(しなければならない|することができる|するものとする|してはならない|努めなければならない)",
       "範囲": r"(以上|以下|超え|未満|以内|を限度)"}
mut = {}
for s in SUBJ:
    w = []
    for kai, v in M.items():
        for q in v["takuitsu"]:
            if q["subject"] != s: continue
            a = S[kai]["takuitsu"][s][q["num"]-1]
            if a is None or isinstance(a, list): continue
            t = qtype(q["stem"])
            if t == "誤り": w.append(q["choices"][a])
            elif t == "正しい": w += [c for i, c in enumerate(q["choices"]) if i != a]
    mut[s] = {"n": len(w), **{k: round(sum(1 for x in w if re.search(p, NOSP(x)))/max(len(w),1)*100)
                              for k, p in PAT.items()}}

# ── 6. 選択式の正答語が過去に出ていたか（新語率）
words = collections.defaultdict(set)
for kai, v in M.items():
    for q in v["sentaku"]:
        raw = S[kai]["sentaku"][q["subject"]]
        for i, a in enumerate(raw):
            a = a[0] if isinstance(a, list) else a
            if a is None: continue
            w = (q["choices"][a-1] if q["format"] == "pool20"
                 else (q["choices"][i][a-1] if a-1 < len(q["choices"][i]) else ""))
            if w: words[int(kai)].add(NOSP(w))
novel = {}
for k in sorted(words):
    past = set().union(*[words[j] for j in words if j < k]) if any(j < k for j in words) else set()
    if past: novel[k] = round(len(words[k] - past) / len(words[k]) * 100)


# ── 7. 選択式の1問ごとの中身（年度×科目）
sel_detail = []
for kai, v in M.items():
    for q in v["sentaku"]:
        body = NOSP(q["body"])
        kind = ("判例" if re.search(r"最高裁判所|判示", body)
                else "統計" if re.search(r"白書|調査|統計|によれば", body) else "条文")
        laws = sorted({f"{m.group(1)}{m.group(2)}条" for m in LAWRE.finditer(body) if m.group(2)})
        raw = S[kai]["sentaku"][q["subject"]]
        ws = []
        for i, a in enumerate(raw):
            a0 = a[0] if isinstance(a, list) else a
            if a0 is None: ws.append(None); continue
            w = (q["choices"][a0-1] if q["format"] == "pool20"
                 else (q["choices"][i][a0-1] if a0-1 < len(q["choices"][i]) else ""))
            ws.append(re.sub(r"\s+", " ", w).strip() if w else None)
        sel_detail.append({"kai": int(kai), "subj": q["subject"], "fmt": q["format"],
                           "src": kind, "laws": laws[:3], "w": ws,
                           "len": len(body)})

# ── 8. 選択式の正答語が「過去の正答語」と一致した割合
reuse = {}
for k in sorted(words):
    past = set().union(*[words[j] for j in words if j < k]) if any(j < k for j in words) else set()
    if past: reuse[k] = {"n": len(words[k]), "same": len(words[k] & past)}

out = {
 "years": [{"kai": k, "y": KAI2Y[k],
            "selTot": K[k]["sel_tot"], "takTot": K[k]["tak_tot"],
            "selAdj": K[k]["sel"], "takAdj": K[k]["tak"],
            "src": {x: src[k][x] for x in ("条文","判例","統計")},
            "novel": novel.get(k)} for k in sorted(KAI2Y, reverse=True)],
 "style": {str(k): {s: dict(c) for s, c in v.items()} for k, v in style.items()},
 "subj": SUBJ, "sel": SEL,
 "topic": {s: [{"k": kw, "y": ys} for kw, ys in topic[s][:40]] for s in SUBJ},
 "gap": dict(sorted(gap.items())), "nextYear": nxt,
 "mut": mut,
 "selDetail": sel_detail, "reuse": reuse,
}
open("../drill/data/stats.js", "w").write("window.STATS = " + json.dumps(out, ensure_ascii=False) + ";\n")
print(f"→ ../drill/data/stats.js  {len(open('../drill/data/stats.js').read()):,} bytes")
print(f"   翌年も出題 {nxt[0]}/{nxt[1]} = {nxt[0]/nxt[1]*100:.1f}%")
print(f"   選択式の新語率 {sum(novel.values())/len(novel):.0f}%（{min(novel.values())}〜{max(novel.values())}%）")
