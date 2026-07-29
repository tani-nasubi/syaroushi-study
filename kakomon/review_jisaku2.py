#!/usr/bin/env python3
"""自作ドリルの点検 第2ラウンド。第1回で見ていない観点だけを見る。"""
import json, re, glob, collections
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
M = json.load(open("mondai.json"))
QS = []
for f in sorted(glob.glob("../drill/data/jisaku-*.js")):
    s = open(f).read(); i = s.index("[", s.index("register")); j = s.rindex("]")
    QS += json.loads(s[i:j+1])
R = []
def check(n, t, bad, note=""):
    R.append((n, t, bad)); print(f"\n【{n:2d}】{t}")
    if note: print("      " + note)
    for x in bad[:8]: print("      ■ " + str(x)[:140])
    if len(bad) > 8: print(f"      … 他 {len(bad)-8} 件")
    if not bad: print("      → 指摘なし")
print("═"*72); print(f" 自作ドリル 第2ラウンド（{len(QS)}問）"); print("═"*72)

# 1 前の問題を前提にする表現が残っていないか
# 文中の「この場合」は肢の中に受け先があるので問題ない。冒頭付近だけを見る。
bad = [c[:70] for q in QS for c in q["choices"]
       if re.search(r"本問|前問|上記|前記|後記", c) or re.match(r".{0,12}(この場合|同項|同条)", c)]
check(1, "単独で成立しない肢（前の問題を前提にしている）", sorted(set(bad)))

# 2 指示語の受け先がない
bad = []
for q in QS:
    for c in q["choices"]:
        if re.match(r"(なお|また|この|その|当該|同項|同条|これら)", c.strip()): bad.append(c[:70])
check(2, "指示語で始まり、受け先が肢の中にない", sorted(set(bad)))

# 3 改変後の語が文中で自然か（助詞の食い違い）
bad = [c[:80] for q in QS for c in q["choices"]
       if re.search(r"することができるならない|しなければならないことができ|ができるが、ができ", c)]
check(3, "改変によって助詞や語尾が壊れている", sorted(set(bad)))

# 4 同一問題内で似すぎている肢（実質同じ内容が2つ）
bad = []
for q in QS:
    n = [NOSP(c) for c in q["choices"]]
    for a in range(5):
        for b in range(a+1, 5):
            s = len(set(n[a][:60]) & set(n[b][:60])) / max(len(set(n[a][:60])), 1)
            if n[a][:25] == n[b][:25]: bad.append(q["tag"] + " " + n[a][:40])
check(4, "同じ問題の中に、書き出しが同一の肢が2つある", sorted(set(bad)))

# 5 「正しいもの」型で、誤り肢4本の改変種別が全て同じ（作りが単調）
bad = []
for q in QS:
    if "正しいもの" not in q["q"]: continue
    k = re.findall(r"の(主体|数値|義務と裁量)を変更", q["exp"])
    if len(k) == 4 and len(set(k)) == 1 and k[0] == "義務と裁量": bad.append(q["tag"])
check(5, "「正しいもの」型で誤り肢4本がすべて義務と裁量の改変", bad,
      f"該当すると語尾を見るだけで解けてしまう")

# 6 出典の年度が偏っていないか
y = collections.Counter(re.search(r"（((?:令和|平成)[^ ]*) 問", q["src"]).group(1) for q in QS
                        if re.search(r"（((?:令和|平成)[^ ]*) 問", q["src"]))
mx, mn = max(y.values()), min(y.values())
check(6, "素材の年度の偏り", [] if mx <= mn*3 else [f"最多{mx} 最少{mn}"],
      "／".join(f"{k}{v}" for k, v in sorted(y.items())))

# 7 科目とタグの整合
SUBJ_OK = {"労基・安衛","労災・徴収","雇用・徴収","一般常識","健保","厚年","国年"}
bad = [q["tag"] for q in QS if q["tag"].split("/")[0] not in SUBJ_OK]
check(7, "科目のタグが不正", sorted(set(bad)))

# 8 設問文と選択肢の科目が合っているか
LAW = {"労基・安衛":"労働基準法及び労働安全衛生法","労災・徴収":"労働者災害補償保険法",
       "雇用・徴収":"雇用保険法","一般常識":"一般常識","健保":"健康保険法",
       "厚年":"厚生年金保険法","国年":"国民年金法"}
bad = [q["tag"] for q in QS if LAW[q["tag"].split("/")[0]] not in q["q"]]
check(8, "設問文の法令名が科目と合っていない", sorted(set(bad)))

# 9 解説に挙げた出典の数が肢の数と合っているか
bad = []
for q in QS:
    n = len(re.findall(r"(?:令和|平成)[^ ]* 問\d+", q["exp"]))
    if n != 5: bad.append(f'{q["tag"]} 出典{n}件')
check(9, "解説の出典が5肢ぶんそろっていない", sorted(set(bad)))

# 10 改変の記述と実際の肢が一致しているか
bad = []
for q in QS:
    wt = "誤っているもの" in q["q"]
    for m in re.finditer(r"([A-E])：誤り。「(.+?)」ではなく", q["exp"]):
        L, after = m.group(1), m.group(2)
        c = q["choices"]["ABCDE".index(L)]
        if after not in c: bad.append(f'{q["tag"]} {L}に「{after}」がない')
    m = re.match(r"正解は([A-E])", q["exp"])
    if m and "ABCDE".index(m.group(1)) != q["a"]: bad.append(f'{q["tag"]} 正解表示の不一致')
check(10, "解説の記述と実際の選択肢が食い違う", sorted(set(bad)))

print("\n" + "═"*72)
ng = [n for n, _, b in R if b]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(b) for _,_,b in R)}件" + (f"　観点{ng}" if ng else ""))
print("═"*72)
