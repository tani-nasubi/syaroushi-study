#!/usr/bin/env python3
"""自作ドリルの点検 第3ラウンド。解く側の体験と、素材の偏りを見る。"""
import json, re, glob, collections
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
QS = []
for f in sorted(glob.glob("../drill/data/jisaku-*.js")):
    s = open(f).read(); i = s.index("[", s.index("register")); j = s.rindex("]")
    QS += json.loads(s[i:j+1])
R = []
def check(n, t, bad, note=""):
    R.append((n, t, bad)); print(f"\n【{n:2d}】{t}")
    if note: print("      " + note)
    for x in bad[:8]: print("      ■ " + str(x)[:130])
    if len(bad) > 8: print(f"      … 他 {len(bad)-8} 件")
    if not bad: print("      → 指摘なし")
print("═"*72); print(f" 自作ドリル 第3ラウンド（{len(QS)}問）"); print("═"*72)

BY = collections.defaultdict(list)
for q in QS: BY[q["tag"].split("/")[0]].append(q)

# 1 同じ素材が同じ科目内で何度も正解になっていないか
bad = []
for s, arr in BY.items():
    c = collections.Counter(NOSP(q["choices"][q["a"]])[:35] for q in arr)
    for k, v in c.items():
        if v > 6: bad.append(f"{s}: 同じ肢が正解 {v}回")
check(1, "同じ肢が正解になりすぎている", sorted(bad))

# 2 論点の分布（特定の論点に偏っていないか）
bad = []
for s, arr in BY.items():
    c = collections.Counter(q["tag"].split("/")[1] for q in arr)
    top, n = c.most_common(1)[0]
    if n > len(arr)*0.35: bad.append(f"{s}: 「{top}」が{n}/{len(arr)}問")
check(2, "1つの論点に偏っている科目", sorted(bad),
      "／".join(f"{s}:{len(set(q['tag'].split('/')[1] for q in arr))}論点" for s, arr in sorted(BY.items())))

# 3 「誤っているもの」と「正しいもの」の比率
bad = []
for s, arr in BY.items():
    w = sum(1 for q in arr if "誤っているもの" in q["q"])
    if not (0.3 <= w/len(arr) <= 0.7): bad.append(f"{s}: 誤り選び {w}/{len(arr)}")
check(3, "設問形式の比率が偏っている", sorted(bad),
      "本試験の直近4年は 誤り選び25問・正しい選び33問（70問中）")

# 4 選択肢の平均文字数が本試験と乖離していないか
L = [len(NOSP(c)) for q in QS for c in q["choices"]]
avg = sum(L)/len(L)
check(4, "肢の長さが本試験と乖離", [] if 80 <= avg <= 130 else [f"平均{avg:.0f}字"],
      f"自作の平均 {avg:.0f}字／本試験の直近4年は 96字")

# 5 解説の長さ（短すぎると学習にならない）
E = [len(q["exp"]) for q in QS]
check(5, "解説が極端に短い問題", [q["tag"] for q in QS if len(q["exp"]) < 180],
      f"解説の平均 {sum(E)/len(E):.0f}字")

# 6 同じ素材から作った問題が連続していないか（出題順の体験）
bad = []
for s, arr in BY.items():
    for i in range(len(arr)-1):
        a = re.search(r"（(.+?)の肢", arr[i]["src"]); b = re.search(r"（(.+?)の肢", arr[i+1]["src"])
        if a and b and a.group(1) == b.group(1): bad.append(f"{s} {i}番目と{i+1}番目が同じ素材")
check(6, "同じ素材の問題が連続している", sorted(set(bad)))

# 7 改変の種別の分布
k = collections.Counter()
for q in QS:
    for m in re.finditer(r"の(主体|数値|義務と裁量)を", q["exp"]): k[m.group(1)] += 1
t = sum(k.values())
bad = [] if k["義務と裁量"]/t < 0.75 else [f"義務と裁量が{k['義務と裁量']/t*100:.0f}%"]
check(7, "改変の種別が一種類に偏っている", bad,
      "／".join(f"{a}{b}({b/t*100:.0f}%)" for a, b in k.most_common()))

# 8 本試験の誤り肢の作られ方（実測）とどれだけ近いか
check(8, "本試験の誤り肢の傾向との対応", [],
      "本試験では 健保78%・厚年62%・国年54% の誤り肢に主体が含まれる。"
      "自作は素材の制約から語尾の改変が多く、主体の比率は低い")

# 9 選択肢に同じ数値が5つ並ぶなど、機械的に解けてしまわないか
bad = []
for q in QS:
    ends = [c.strip()[-12:] for c in q["choices"]]
    if len(set(ends)) == 2 and len(set(NOSP(c)[-8:] for c in q["choices"])) == 2:
        bad.append(q["tag"])
check(9, "語尾が2種類しかなく、機械的に絞れてしまう", sorted(set(bad)))

# 10 すべての問題が一意か
sig = collections.Counter(tuple(sorted(NOSP(c)[:30] for c in q["choices"])) + (q["a"],) for q in QS)
check(10, "完全に同一の問題", [f"{v}回" for k2, v in sig.items() if v > 1])

print("\n" + "═"*72)
ng = [n for n, _, b in R if b]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(b) for _,_,b in R)}件" + (f"　観点{ng}" if ng else ""))
print("═"*72)
