#!/usr/bin/env python3
"""資料の整合性と、計画の現在性を見る。機能を足すたびに古くなる箇所を洗う。"""
import json, re, glob, os, collections, datetime
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
R = []
def check(n, t, bad, note=""):
    R.append((n, t, bad)); print(f"\n【{n:2d}】{t}")
    if note: print("      " + note)
    for x in bad[:7]: print("      ■ " + str(x)[:150])
    if len(bad) > 7: print(f"      … 他 {len(bad)-7} 件")
    if not bad: print("      → 指摘なし")
print("═"*74); print(" 資料の整合性と計画の現在性"); print("═"*74)

N = {os.path.basename(p): open(p).read() for p in glob.glob("../notes/*.md")}
APP = open("../drill/index.html").read()
TODAY = datetime.date(2026, 7, 29)
EXAM  = datetime.date(2026, 8, 23)

# 1 同じ項目に違う数値が書かれていないか
FACTS = {
  "在職老齢年金の支給停止調整額": (r"支給停止調整額[^\n]{0,40}?([0-9]{2})万円", {"65"}),
  "選択式の基準点":             (r"各科目\s*\*?\*?([0-9])点以上", {"3"}),
  "択一の基準点":               (r"択一[^\n]{0,20}?各科目\s*\*?\*?([0-9])点", {"4"}),
  # A1資料には「1肢/2肢を無作為に選んだとき確定する割合（38%）」と
  # 「最適に2肢を選べば確定する割合（98.5%）」の2つがある。後者だけを見る。
  "組合せ問題が2肢で決まる割合":  (r"2肢(?:で|の正誤が分かれば)[^\n]{0,14}?([0-9]{2}\.?[0-9]?)%", {"98.5"}),
  "翌年も出た割合":             (r"翌年も出た割合\s*([0-9]{2}\.[0-9])%", {"44.7","44.8"}),
}
bad = []
for name, (pat, ok) in FACTS.items():
    got = collections.Counter()
    for f, b in N.items():
        for m in re.finditer(pat, b): got[m.group(1)] += 1
    wrong = {v for v in got if v not in ok}
    if wrong: bad.append(f"{name}: {dict(got)} ← 想定は {ok}")
check(1, "同じ項目に違う数値が書かれている", bad,
      "／".join(f"{k}:{'・'.join(v[1])}" for k, v in FACTS.items()))

# 2 直前期スケジュールが今日以降を指しているか
seg = APP[APP.index("const PLAN"):]
days = sorted(re.findall(r'"(\d{4}-\d{2}-\d{2})"', seg[:9000]))
past = [d for d in days if datetime.date.fromisoformat(d) < TODAY]
left = [d for d in days if datetime.date.fromisoformat(d) >= TODAY]
bad = [] if len(left) >= 20 else [f"残り {len(left)}日ぶんしか予定がない"]
check(2, "直前期スケジュールの残り", bad,
      f"登録 {len(days)}日（済 {len(past)}日／これから {len(left)}日）本試験まで {(EXAM-TODAY).days}日")

# 3 資料の相互リンク（行き止まりがないか）
bad = [f for f, b in N.items() if "## 次に読むもの" not in b and f[:2] not in ("90", "91")]
check(3, "次に読むものの導線がない資料", bad, f"資料 {len(N)}件")

# 4 法改正資料の記述と、取得した条文が矛盾しないか
kaisei = N.get("00-法改正-令和8年度.md", "")
bad = []
if "65万円" in kaisei and "51万円" in kaisei and "引下げ" not in kaisei:
    pass
for pat, why in [(r"支給停止調整額[^\n]*51万円(?!から)", "旧額が残っている"),
                 (r"給付制限[^\n]{0,6}(2)\s*か月(?!→)", "旧の給付制限が残っている")]:
    for f, b in N.items():
        if re.search(pat, b): bad.append(f"{f}: {why}")
check(4, "法改正前の数値が資料に残っている", sorted(set(bad)))

# 5 生成資料が最新のデータと一致しているか
import subprocess
before = {f: N[f] for f in N}
for g in ["gen_tokuten.py", "gen_hikkake.py", "gen_seibun.py", "gen_kosuu.py", "gen_trend.py", "gen_genbun.py"]:
    subprocess.run(["python3", g], capture_output=True)
after = {os.path.basename(p): open(p).read() for p in glob.glob("../notes/*.md")}
bad = [f for f in before if before[f] != after.get(f)]
check(5, "生成資料が古い（再生成で変わる）", bad)

# 6 アプリの既定設定
bad = []
m = re.search(r'<select id="limit">(.*?)</select>', APP, re.S)
if m and 'selected' not in m.group(1): bad.append("ドリルの出題数に既定が指定されていない")
m2 = re.search(r'<select id="byouN">(.*?)</select>', APP, re.S)
if m2 and 'selected' not in m2.group(1): bad.append("速答の出題数に既定が指定されていない")
check(6, "既定の設定", bad)

# 7 選択式そのものを練習する手段があるか
has_sel = 'sel20' in APP and 'rPool' in APP
bad = [] if has_sel else ["選択式（A〜E5空欄・語群20）の練習ができない"]
check(7, "選択式の練習手段", bad,
      "ドリルで sel20/selpb を出題、模試で本番形式、速答で条文の穴埋め")

# 8 キーボード操作
bad = []
if "keydown" not in APP: bad.append("キーボード操作に対応していない")
if 't-byou' in APP and not re.search(r'byou.*keydown|keydown.*byou', APP, re.S):
    bad.append("速答タブがキーボードに対応していない（数字キーで選べない）")
check(8, "キーボード操作", bad)

# 9 傾向タブの数値が最新の過去問データと一致しているか
st = open("../drill/data/stats.js").read()
o = json.loads(st[st.index("{"):st.rstrip().rstrip(";").rindex("}")+1])
M = json.load(open("mondai.json"))
n_tak = sum(len(v["takuitsu"]) for v in M.values())
n_sel = sum(len(v["sentaku"]) for v in M.values())
bad = []
if len(o["selDetail"]) != n_sel: bad.append(f"選択式 {len(o['selDetail'])} vs {n_sel}")
tot = sum(c.get("問数", 0) for y in o["style"].values() for c in y.values())
if tot != n_tak: bad.append(f"択一 {tot} vs {n_tak}")
check(9, "傾向タブの統計が過去問データとずれている", bad,
      f"択一{n_tak}問・選択式{n_sel}問")

# 10 残り日数で現実的に回せるか
n_all = 0
for f in glob.glob("../drill/data/*.js"):
    s = open(f).read()
    if "register" not in s: continue
    i = s.index("[", s.index("register")); j = s.rindex("]")
    try: n_all += len(json.loads(s[i:j+1]))
    except Exception: n_all += s.count('"type"')
d = (EXAM - TODAY).days
check(10, "残り日数に対する現実性", [],
      f"総 {n_all:,}問／残り {d}日。1日100問なら {d*100:,}問＝全体の {d*100/n_all*100:.0f}%。"
      "優先順位（出題実績あり・間違えたものだけ・弱点科目）で絞る設計が要")

print("\n" + "═"*74)
ng = [n for n, _, b in R if b]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(b) for _,_,b in R)}件" + (f"　観点{ng}" if ng else ""))
print("═"*74)
