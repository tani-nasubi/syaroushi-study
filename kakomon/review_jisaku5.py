#!/usr/bin/env python3
"""自作ドリルの点検 第5ラウンド。解答者が「正解を選べるか」という観点で見る。"""
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
    for x in bad[:6]: print("      ■ " + str(x)[:140])
    if len(bad) > 6: print(f"      … 他 {len(bad)-6} 件")
    if not bad: print("      → 指摘なし")
print("═"*72); print(f" 自作ドリル 第5ラウンド（{len(QS)}問）"); print("═"*72)

# 1「正しいもの」型で、誤り肢の語尾がすべて同じ → 語尾を見るだけで正解が浮く
bad = []
for q in QS:
    if "正しいもの" not in q["q"]: continue
    ends = [NOSP(c)[-9:] for i, c in enumerate(q["choices"]) if i != q["a"]]
    ans  = NOSP(q["choices"][q["a"]])[-9:]
    # 5つとも同じ語尾なら手がかりにならない。正解だけ違うときが問題。
    if len(set(ends)) == 1 and ans != ends[0]:
        bad.append(f'{q["tag"]}: 誤り肢の語尾が全て「{ends[0]}」')
check(1, "誤り肢の語尾がすべて同一で、正解が浮いて見える", sorted(set(bad)))

# 2 逆に「誤っているもの」型で、誤り肢だけ語尾が違う
bad = []
for q in QS:
    if "誤っているもの" not in q["q"]: continue
    ans = NOSP(q["choices"][q["a"]])[-9:]
    oth = [NOSP(c)[-9:] for i, c in enumerate(q["choices"]) if i != q["a"]]
    if len(set(oth)) == 1 and ans != oth[0]: bad.append(f'{q["tag"]}: 誤り肢だけ語尾が違う')
check(2, "誤り肢だけ語尾が違い、見た目で分かる", sorted(set(bad)))

# 3 数値の改変で、同じ問題に同じ単位の数値が並び比較で解けてしまう
bad = []
for q in QS:
    # 「正しいもの」型では、単位の偏りは正解の手がかりにならない
    # （正解は改変されていない肢の側なので）。誤っているもの型だけを見る。
    if "誤っているもの" not in q["q"]: continue
    m = re.search(r"「([0-9]+ ?(?:日|年|か月|月|週間|時間|歳))」ではなく", q["exp"])
    if not m: continue
    unit = re.sub(r"[0-9 ]", "", m.group(1))
    cnt = sum(1 for c in q["choices"] if re.search(r"[0-9]+\s*"+unit, c))
    if cnt == 1: bad.append(f'{q["tag"]}: {unit}を含む肢が1つだけ')
check(3, "改変した単位を含む肢が1つしかなく、そこだけ浮く", sorted(set(bad))[:6],
      "同じ単位の数値が複数あれば比較の余地が生まれる")

# 4 素材の年度が1問の中で1年に集中していないか
bad = []
for q in QS:
    y = re.findall(r"((?:令和|平成)[^年]*)年度 問", q["exp"])
    if len(y) >= 4 and len(set(y)) == 1: bad.append(f'{q["tag"]}: 全て{y[0]}年度')
check(4, "1問の素材がすべて同じ年度", sorted(set(bad)))

# 5 解説の中で同じ肢記号が2回説明されていないか
bad = []
for q in QS:
    ls = re.findall(r"^- ([A-E])", q["exp"], re.M) + re.findall(r"^\*\*([A-E])：", q["exp"], re.M)
    d = [k for k, v in collections.Counter(ls).items() if v > 1]
    if d: bad.append(f'{q["tag"]}: {d}')
check(5, "解説で同じ肢が二重に説明されている", sorted(set(bad)))

# 6 解説に登場する肢記号が5つそろっているか
bad = []
for q in QS:
    ls = set(re.findall(r"[A-E](?=：|　)", q["exp"]))
    if len(ls) < 5: bad.append(f'{q["tag"]}: {sorted(ls)}')
check(6, "解説で触れられていない肢がある", sorted(set(bad)))

# 7 タグの論点が肢の内容と関係しているか
bad = []
for q in QS:
    t = q["tag"].split("/")[1]
    # 論点が特定できなかったときは科目名を入れている。これは見出しなので対象外。
    if t in ("労基安衛","労災","雇用","一般常識","健保","厚年","国年"): continue
    if not any(NOSP(t) in NOSP(c) for c in q["choices"]): bad.append(f'{q["tag"]}: 肢に語がない')
check(7, "タグの論点が肢に含まれていない", sorted(set(bad)))

# 8 問題文が全て同じ文面になっていないか（本試験は論点を書く場合もある）
f = collections.Counter(q["q"] for q in QS)
check(8, "設問文の種類", [], "／".join(f"{k[:18]}…{v}問" for k, v in f.most_common(4)))

# 9 選択肢の中に解答のヒントになる語が入っていないか
# 「申告書の記載に誤りがあるとき」は法令用語なので対象外。
# 解答を示す使い方（〜は誤りである等）だけを見る。
bad = [f'{q["tag"]}' for q in QS for c in q["choices"]
       if re.search(r"(記述|肢|本問)は(誤り|正しい)|誤りである。$|正しい。$", c)]
check(9, "肢の中に正誤を示す語が入っている", sorted(set(bad)))

# 10 極端に短い／長い肢
L = [(len(NOSP(c)), q["tag"]) for q in QS for c in q["choices"]]
bad = [f"{t}: {n}字" for n, t in L if n < 50 or n > 250]
check(10, "極端に短い・長い肢", sorted(set(bad)),
      f"平均 {sum(n for n,_ in L)/len(L):.0f}字／最短 {min(n for n,_ in L)}／最長 {max(n for n,_ in L)}")

print("\n" + "═"*72)
ng = [n for n, _, b in R if b]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(b) for _,_,b in R)}件" + (f"　観点{ng}" if ng else ""))
print("═"*72)
