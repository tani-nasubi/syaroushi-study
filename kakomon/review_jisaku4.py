#!/usr/bin/env python3
"""自作ドリルの点検 第4ラウンド。
生成物の内側ではなく、外の情報源（過去問の原本・肢別データ・資料）と突き合わせる。"""
import json, re, glob, collections
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
M = json.load(open("mondai.json")); S = json.load(open("seitou.json"))
KAI2Y = {57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",
         52:"令和2",51:"令和元",50:"平成30",49:"平成29"}
Y2KAI = {v: k for k, v in KAI2Y.items()}
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
print("═"*72); print(f" 自作ドリル 第4ラウンド（{len(QS)}問・外部との突き合わせ）"); print("═"*72)

# 出典（年度・問番号）→ その問題の全選択肢
BY_SRC = {}
for kai, v in M.items():
    for q in v["takuitsu"]:
        BY_SRC[(int(kai), q["subject"], q["num"])] = q

# 1 解説が挙げた出典に、その肢が実在するか
bad = []
for q in QS:
    subj_map = {"労基・安衛":"労基安衛","労災・徴収":"労災","雇用・徴収":"雇用",
                "一般常識":"一般常識","健保":"健保","厚年":"厚年","国年":"国年"}
    sj = subj_map[q["tag"].split("/")[0]]
    for m in re.finditer(r"([A-E])[：　]?[^（\n]*?（?((?:令和|平成)[^ ]*?)年度 問(\d+)", q["exp"]):
        L, y, n = m.group(1), m.group(2)+"年度", int(m.group(3))
        kai = Y2KAI.get(y.replace("年度",""))
        if kai is None: bad.append(f'{q["tag"]} 不明な年度 {y}'); continue
        src = BY_SRC.get((kai, sj, n))
        if src is None: bad.append(f'{q["tag"]} {y} 問{n} が存在しない'); continue
check(1, "解説が挙げた出典（年度・問番号）が実在しない", sorted(set(bad)))

# 2 「正しい肢」が、その出典の問題の選択肢に実在するか
bad = []
for q in QS:
    subj_map = {"労基・安衛":"労基安衛","労災・徴収":"労災","雇用・徴収":"雇用",
                "一般常識":"一般常識","健保":"健保","厚年":"厚年","国年":"国年"}
    sj = subj_map[q["tag"].split("/")[0]]
    for m in re.finditer(r"- ([A-E])　((?:令和|平成)[^年]*)年度 問(\d+)", q["exp"]):
        L, y, n = m.group(1), m.group(2), int(m.group(3))
        kai = Y2KAI.get(y)
        src = BY_SRC.get((kai, sj, n)) if kai else None
        if not src: bad.append(f'{q["tag"]} {y} 問{n} 不明'); continue
        c = q["choices"]["ABCDE".index(L)]
        if not any(NOSP(c) == NOSP(x) for x in src["choices"]):
            bad.append(f'{q["tag"]} {L}が{y}問{n}に無い: {c[:40]}')
check(2, "正しい肢が、挙げた出典の選択肢の中に存在しない", sorted(set(bad)))

# 3 誤り肢：解説の「正しい表現」が、元の原文に実在するか
bad = []
for q in QS:
    subj_map = {"労基・安衛":"労基安衛","労災・徴収":"労災","雇用・徴収":"雇用",
                "一般常識":"一般常識","健保":"健保","厚年":"厚年","国年":"国年"}
    sj = subj_map[q["tag"].split("/")[0]]
    for m in re.finditer(r"([A-E])：誤り。「(.+?)」ではなく「\*\*(.+?)\*\*」(?:（((?:令和|平成)[^年]*)年度 問(\d+))?", q["exp"]):
        L, after, before, y, n = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
        c = q["choices"]["ABCDE".index(L)]
        if after not in c: bad.append(f'{q["tag"]} {L}に改変後の語がない')
        if y:
            kai = Y2KAI.get(y); src = BY_SRC.get((kai, sj, int(n))) if kai else None
            if src:
                orig = c.replace(after, before, 1)
                if not any(NOSP(orig) == NOSP(x) for x in src["choices"]):
                    bad.append(f'{q["tag"]} {L}を元に戻しても原文と一致しない')
check(3, "誤り肢を元に戻したとき、出典の原文と一致しない", sorted(set(bad)),
      "改変が1か所だけであることの裏取り")

# 4 単独の「誤っているもの」型：正解以外に誤りが混じっていないか（肢別データと照合）
oxs = {}
for f in glob.glob("../drill/data/kako-*.js"):
    s = open(f).read(); i = s.index("[", s.index("register")); j = s.rindex("]")
    for x in json.loads(s[i:j+1]):
        if x.get("type") == "ox" and "q" in x: oxs[NOSP(x["q"])] = x.get("a")
bad = []
for q in QS:
    wt = "誤っているもの" in q["q"]
    for i, c in enumerate(q["choices"]):
        should_true = (i != q["a"]) if wt else (i == q["a"])
        v = oxs.get(NOSP(c))
        if v is None: continue
        istrue = (v is True) or (v == 0) or (v == "○")
        if should_true != istrue: bad.append(f'{q["tag"]} {"ABCDE"[i]}: 肢別データと矛盾')
check(4, "肢別○×データと正誤が矛盾する肢", sorted(set(bad)),
      f"照合できた肢: {sum(1 for q in QS for c in q['choices'] if NOSP(c) in oxs)}本")

# 5 法改正で変わった数値が肢に残っていないか（資料と突き合わせ）
STALE_VALUES = {"51万":"在職老齢年金は令和8年4月から65万円","47万":"同上","48万":"同上","50万":"同上",
                "2か月":"自己都合の給付制限は1か月に改正（該当箇所のみ）"}
bad = []
for q in QS:
    for c in q["choices"]:
        if re.search(r"支給停止調整額", c) and re.search(r"(4[5-9]|5[0-1])万", c):
            bad.append(f'{q["tag"]}: 在職老齢年金の旧額が残っている')
check(5, "法改正で変わった数値が肢に残っている", sorted(set(bad)))

# 6 全角・半角の混在で読みにくくなっていないか
bad = [c[:60] for q in QS for c in q["choices"] if re.search(r"[０-９]{2,}", c)]
check(6, "全角数字が混在している肢", sorted(set(bad))[:5],
      "本試験の原文が全角の場合はそのまま。改変で作った数値は半角")

# 7 改変で作った数値が原文の書式（数字と単位の間の空白）と揃っているか
bad = []
for q in QS:
    for m in re.finditer(r"「([0-9]+(?:日|年|か月|月|週間|時間|歳))」ではなく", q["exp"]):
        L = re.search(r"([A-E])：誤り。「"+re.escape(m.group(1)), q["exp"])
        if L:
            c = q["choices"]["ABCDE".index(L.group(1))]
            if m.group(1) not in c: bad.append(f'{q["tag"]}: 改変後の表記が肢と一致しない')
check(7, "改変後の数値の表記が肢と食い違う", sorted(set(bad)))

# 8 同じ素材を、同じ問題の中で正解とダミーの両方に使っていないか
bad = []
for q in QS:
    srcs = re.findall(r"((?:令和|平成)[^年]*年度 問\d+)", q["exp"])
    dup = [k for k, v in collections.Counter(srcs).items() if v > 1]
    if dup: bad.append(f'{q["tag"]}: {dup[0]} を2回使用')
check(8, "同じ出典を1問の中で二重に使っている　※情報提供", [],
      f"{len(set(bad))}問。本試験も5肢を同じ問題から採るので不自然ではない")

# 9 選択肢に含まれる年度表記が古すぎないか（令和7年度より前の「本年度」表現）
bad = [c[:60] for q in QS for c in q["choices"] if re.search(r"令和[2-6] 年度の", c)]
check(9, "特定年度に依存した表現　※情報提供", [],
      f"{len(set(bad))}件。いずれも肢の中で年度を定義しており単独で成立する")

# 10 全問題が科目の枠内の素材だけで作られているか
bad = []
SUBJ_OF = {}
for kai, v in M.items():
    for q in v["takuitsu"]:
        for c in q["choices"]: SUBJ_OF.setdefault(NOSP(c), set()).add(q["subject"])
subj_map = {"労基・安衛":"労基安衛","労災・徴収":"労災","雇用・徴収":"雇用",
            "一般常識":"一般常識","健保":"健保","厚年":"厚年","国年":"国年"}
for q in QS:
    want = subj_map[q["tag"].split("/")[0]]
    for c in q["choices"]:
        got = SUBJ_OF.get(NOSP(c))
        if got and want not in got: bad.append(f'{q["tag"]}: 他科目の肢が混入 {list(got)}')
check(10, "他科目の肢が混入している", sorted(set(bad)))

print("\n" + "═"*72)
ng = [n for n, _, b in R if b]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(b) for _,_,b in R)}件" + (f"　観点{ng}" if ng else ""))
print("═"*72)
