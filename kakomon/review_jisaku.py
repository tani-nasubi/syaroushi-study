#!/usr/bin/env python3
"""自作ドリルの点検。観点を変えて繰り返し掛ける。"""
import json, re, glob, collections
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
M = json.load(open("mondai.json")); S = json.load(open("seitou.json"))

def qt(s):
    s = NOSP(s)
    if "いくつあるか" in s or "組合せ" in s: return "x"
    if re.search(r"誤っているもの|誤りである", s): return "誤り"
    if re.search(r"正しいもの|適切なもの", s): return "正しい"
    return "x"
TRUE = set()
for kai, v in M.items():
    for q in v["takuitsu"]:
        a = S[kai]["takuitsu"][q["subject"]][q["num"]-1]
        if a is None or isinstance(a, list): continue
        t = qt(q["stem"])
        if t == "誤り":   [TRUE.add(NOSP(c)) for i, c in enumerate(q["choices"]) if i != a]
        elif t == "正しい": TRUE.add(NOSP(q["choices"][a]))

QS = []
for f in sorted(glob.glob("../drill/data/jisaku-*.js")):
    s = open(f).read(); i = s.index("[", s.index("register")); j = s.rindex("]")
    QS += json.loads(s[i:j+1])

R = []
def check(n, title, bad, note=""):
    R.append((n, title, bad))
    print(f"\n【{n:2d}】{title}")
    if note: print("      " + note)
    if bad:
        for x in bad[:8]: print("      ■ " + str(x)[:150])
        if len(bad) > 8: print(f"      … 他 {len(bad)-8} 件")
    else: print("      → 指摘なし")

print("═"*72); print(f" 自作ドリルの点検（{len(QS)}問）"); print("═"*72)

# 1 正しい肢が本試験の原文と一致するか
bad = []
for q in QS:
    wt = "誤っているもの" in q["q"]
    for i, c in enumerate(q["choices"]):
        should_be_true = (i != q["a"]) if wt else (i == q["a"])
        if should_be_true and NOSP(c) not in TRUE: bad.append(c[:70])
check(1, "正しいはずの肢が本試験の原文と一致しない", bad)

# 2 誤り肢が既知の正しい記述と一致していないか
bad = []
for q in QS:
    wt = "誤っているもの" in q["q"]
    for i, c in enumerate(q["choices"]):
        should_be_false = (i == q["a"]) if wt else (i != q["a"])
        if should_be_false and NOSP(c) in TRUE: bad.append(c[:70])
check(2, "誤りのはずの肢が、実は正しい記述と一致する", bad)

# 3 文が途中で切れていないか
bad = [c[-40:] for q in QS for c in q["choices"]
       if not re.search(r"[。」）\)]$", c.strip())]
check(3, "文が途中で終わっている肢", sorted(set(bad)))

# 4 同じ語が並ぶ・語の切り出し誤り
bad = [c[:70] for q in QS for c in q["choices"]
       if re.search(r"(労働基準監督署長|公共職業安定所長|健康保険組合|全国健康保険協会)(又は|及び|、)\1", c)
       or re.search(r"国民全国健康保険協会|全国健康保険組合|するようしなければ|しなければならないための", c)]
check(4, "同じ語が並ぶ／語の切り出し誤り", sorted(set(bad)))

# 5 二重否定・定義の中を変えていないか
bad = []
for q in QS:
    wt = "誤っているもの" in q["q"]
    for i, c in enumerate(q["choices"]):
        mutated = (i == q["a"]) if wt else (i != q["a"])
        if not mutated: continue                      # 原文はそのまま正しいので対象外
        for pat in (r"必ずしも[^。]{0,60}(しなければならない|することができる)[^。]{0,20}ものではない",
                    r"(しなければならない|することができる)(もの|者|ため)の",
                    r"するようしなければ|しなければならないための"):
            if re.search(pat, c): bad.append(c[:80])
check(5, "二重否定や定義の中を改変している", sorted(set(bad)))

# 6 設問の重複（同じ5肢の組合せ）
seen = collections.Counter(tuple(sorted(NOSP(c)[:30] for c in q["choices"])) for q in QS)
check(6, "選択肢の組合せが完全に重複している問題", [f"{v}回" for k, v in seen.items() if v > 1])

# 7 正解の位置の偏り
d = collections.Counter("ABCDE"[q["a"]] for q in QS)
mx, mn = max(d.values()), min(d.values())
check(7, "正解の位置の偏り", [] if (mx-mn)/len(QS)*100 < 6 else [f"最多{mx} 最少{mn}"],
      f"A{d['A']} B{d['B']} C{d['C']} D{d['D']} E{d['E']}（差 {(mx-mn)/len(QS)*100:.1f}ポイント）")

# 8 正解肢だけ極端に長い／短い（見た目で分かってしまう）
bad = []
for q in QS:
    L = [len(NOSP(c)) for c in q["choices"]]
    others = [L[i] for i in range(5) if i != q["a"]]
    if L[q["a"]] > max(others)*1.6 or L[q["a"]] < min(others)*0.55: bad.append(q["tag"])
check(8, "正解肢の長さが突出していて見た目で分かる", bad)

# 9 解説に出典と差分が書かれているか
bad = [q["tag"] for q in QS if "年度 問" not in q["exp"] or "ではなく" not in q["exp"]]
check(9, "解説に出典または差分の記載がない", bad)

# 10 形式
bad = [q["tag"] for q in QS if q["type"] != "abc" or len(q["choices"]) != 5 or not (0 <= q["a"] < 5)]
check(10, "本試験の形式（5肢択一）になっていない", bad)

print("\n" + "═"*72)
ng = [n for n, _, b in R if b]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(b) for _, _, b in R)}件" + (f"　観点{ng}" if ng else ""))
print("═"*72)
