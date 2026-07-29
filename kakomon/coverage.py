#!/usr/bin/env python3
"""「この資料だけで合格できるか」を、過去問630問の論点カバー率で測る。

各設問の5肢から論点語を抽出し、対応する科目ノートに載っているかを判定する。
カバー率が低い設問を集め、その論点を「加筆すべきリスト」として出力する。
"""
import json, re, collections, os, sys

N = "../notes"
M = json.load(open("mondai.json"))
S = json.load(open("seitou.json"))
NOSP = lambda s: re.sub(r"[\s　,，、。「」（）()・]", "", str(s))
FILES = sorted(f for f in os.listdir(N) if f.endswith(".md"))
FLAT = {f: NOSP(open(f"{N}/{f}").read()) for f in FILES}

COMMON = ["90-横断整理.md","91-数値暗記.md","92-選択式の解き方.md","93-判例.md",
          "94-計算問題の解法.md","00-法改正-令和8年度.md"]
MAP = {"労基安衛":["01-労働基準法.md","02-労働安全衛生法.md"],
       "労災":["03-労災保険法.md","05-徴収法.md"],
       "雇用":["04-雇用保険法.md","05-徴収法.md"],
       "一般常識":["06-労働一般常識.md","07-社会保険一般常識.md"],
       "労一":["06-労働一般常識.md"],"社一":["07-社会保険一般常識.md"],
       "健保":["08-健康保険法.md"],"厚年":["10-厚生年金保険法.md"],"国年":["09-国民年金法.md"]}
TEXT = {s: "".join(FLAT[f] for f in fs + COMMON) for s, fs in MAP.items()}

# 論点語＝3〜10字の漢字・カタカナ連続。制度名・要件語を拾う
TERM = re.compile(r"[一-鿿ヲ-ヴー]{3,10}")
STOP = set("""労働者使用者事業主被保険者厚生労働大臣厚生労働省令都道府県労働基準監督署長
当該労働者当該事業主当該事業当該被保険者以下本問本問において場合とき規定法律施行
することができるしなければならない厚生労働省次のうち記述正しい誤っているもの
労働基準法労働安全衛生法労災保険法雇用保険法健康保険法厚生年金保険法国民年金法
労働保険徴収法社会保険労務士法都道府県労働局長公共職業安定所長""".split())

def terms(text):
    return {w for w in TERM.findall(NOSP(text)) if w not in STOP and len(w) >= 3}

rows = []; uncovered = collections.defaultdict(collections.Counter)
for kai, v in M.items():
    for q in v["takuitsu"]:
        subj = q["subject"]
        nt = TEXT.get(subj, "")
        ts = terms(q["stem"] + "".join(q["choices"]))
        if not ts: continue
        hit = sum(1 for w in ts if w in nt)
        cov = hit / len(ts)
        rows.append((subj, int(kai), q["num"], cov, len(ts)))
        if cov < 0.55:
            for w in ts:
                if w not in nt: uncovered[subj][w] += 1

print("═"*74)
print(" 過去問630問の論点カバー率（この資料に載っている割合）")
print("═"*74)
bysub = collections.defaultdict(list)
for s, k, n, c, t in rows: bysub[s].append(c)
order = ["労基安衛","労災","雇用","一般常識","健保","厚年","国年"]
tot = []
for s in order:
    cs = bysub[s]; tot += cs
    low = sum(1 for c in cs if c < 0.55)
    bar = "▉" * round(sum(cs)/len(cs)*30)
    print(f"  {s:<6} 平均カバー率 {sum(cs)/len(cs)*100:5.1f}%  {bar}")
    print(f"         55%未満の設問 {low}/{len(cs)}問（{low/len(cs)*100:.0f}%）")
print(f"\n  全体平均 {sum(tot)/len(tot)*100:.1f}%　／　55%未満 {sum(1 for c in tot if c<0.55)}/{len(tot)}問")

print()
print("═"*74)
print(" カバー率が低い設問に頻出する未収録の論点語（加筆候補）")
print("═"*74)
for s in order:
    c = uncovered[s]
    top = [(w, n) for w, n in c.most_common(60) if n >= 3][:14]
    if top:
        print(f"\n■ {s}")
        print("   " + "、".join(f"{w}({n})" for w, n in top))
