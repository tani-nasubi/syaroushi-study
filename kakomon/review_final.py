#!/usr/bin/env python3
"""全体のブラッシュアップ検討。今回はまだ見ていない角度を見る。"""
import json, re, glob, os, collections
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
R = []
def check(n, t, bad, note=""):
    R.append((n, t, bad)); print(f"\n【{n:2d}】{t}")
    if note: print("      " + note)
    for x in bad[:7]: print("      ■ " + str(x)[:150])
    if len(bad) > 7: print(f"      … 他 {len(bad)-7} 件")
    if not bad: print("      → 指摘なし")
print("═"*74); print(" ブラッシュアップの検討（新しい観点）"); print("═"*74)

ANA = []
for f in ["../drill/data/anaume.js", "../drill/data/anaume2.js"]:
    s = open(f).read(); i = s.index("[", s.index("register")); j = s.rindex("]")
    ANA += json.loads(s[i:j+1])
APP = open("../drill/index.html").read()
NOTES = {os.path.basename(p): open(p).read() for p in glob.glob("../notes/*.md")}

# 1 年度で変わる数値を穴埋めにしていないか（法令の版と試験の基準日がずれる）
# 「年金額」「加給年金額」は用語であって数値ではない。実際の値だけを見る。
VOL = re.compile(r"[0-9０-９，,]+\s*円|[0-9０-９]+\s*万円|[0-9０-９]+分の[0-9０-９]+|"
                 r"千分の[0-9０-９]+|[0-9０-９]+(?:\.[0-9])?\s*パーセント|[0-9０-９]+\s*％")
bad = []
for q in ANA:
    a = q["choices"][q["a"]]
    if VOL.search(NOSP(a)): bad.append(f'{q["src"]} ← 正答「{a}」')
check(1, "年度で変わる数値を正答にしている", bad,
      "e-Gov は現在施行の内容を返す。試験は令和8年4月10日現在施行の法令が基準なので、"
      "改定される数値は答えにしないほうが安全")

# 2 学習計画に速答が入っているか
bad = [] if "byou" in APP[APP.index("const PLAN"):APP.index("const PLAN")+9000] else \
      ["直前期スケジュールが速答タブを案内していない"]
check(2, "学習計画が新しいモードを案内していない", bad)

# 3 検索が条文穴埋めを拾うか
seg = APP[APP.index("function runSearch"):APP.index("function runSearch")+1800]
bad = [] if ("head" in seg or "ana" in seg) else ["検索の対象に条文穴埋めの本文が入っていない"]
check(3, "横断検索が条文穴埋めを拾わない", bad)

# 4 傾向タブが新しいコンテンツを反映しているか
bad = [] if "条文穴埋め" in APP[APP.index("function stMe"):APP.index("function stMe")+2500] else \
      ["自分の穴（傾向タブ）に条文穴埋めの成績が出ない"]
check(4, "傾向タブに速答の成績が出ない", bad)

# 5 資料と条文穴埋めの重なり
gen = NOTES.get("95-条文素読（選択式の原文）.md", "")
same = sum(1 for q in ANA if q.get("head") and len(NOSP(q["head"])) > 30
           and NOSP(q["head"])[-30:] in NOSP(gen))
check(5, "資料と条文穴埋めの重なり", [],
      f"素読集と同じ文が出るもの {same}問（重なり自体は復習になるので問題ない）")

# 6 過去問の肢別と条文穴埋めの重複
bad = []
check(6, "肢別○×と条文穴埋めの重複", bad, "形式が違うので重複とはみなさない")

# 7 モバイルでの操作（タップ領域）
bad = []
m = re.search(r"\.bopts button\{[^}]*padding:([^;]+)", APP)
if m and "15px" not in m.group(1) and "16px" not in m.group(1): bad.append("速答の選択肢のタップ領域が小さい")
if "font-size:16px" not in APP and "--fs:16px" not in APP: bad.append("既定の文字サイズが16px未満（iOSで拡大される）")
check(7, "スマホでの操作性", bad,
      "iOSは16px未満の入力欄で自動拡大する。タップ領域は44px相当が目安")

# 8 SRSの設計が残り日数に合っているか
m = re.search(r"const IVL\s*=\s*\[([^\]]*)\]", APP)
check(8, "復習間隔の設計", [], f"間隔: {m.group(1) if m else '（定義を確認できず）'}　"
      "本試験まで25日なので、最長間隔が25日を超えると1度も戻ってこない")

# 9 オフラインの実効性
sw = open("../drill/sw.js").read()
bad = []
# sw.js では正規表現内で \/data\/ とエスケープされている
if not re.search(r"data.*\.js", sw): bad.append("条文穴埋めのデータがキャッシュ対象に入っていない")
check(9, "オフラインで速答が使えるか", bad,
      "data/ 配下を対象にしているので、一度開けばオフラインでも動く")

# 10 ホームが次の行動を示しているか
seg = APP[APP.index("function renderHero"):APP.index("function renderHero")+2200]
bad = []
if "模試" not in seg and "moshi" not in seg: bad.append("ホームに模試の未受験が出ていない")
check(10, "ホームが次の行動を示しているか", bad,
      "残り日数・収録数・着手・正答率・復習待ちを表示している")

print("\n" + "═"*74)
ng = [n for n, _, b in R if b]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(b) for _,_,b in R)}件" + (f"　観点{ng}" if ng else ""))
print("═"*74)
