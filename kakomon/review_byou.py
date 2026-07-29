#!/usr/bin/env python3
"""全体のブラッシュアップ検討。今回は速答（条文穴埋め）と学習設計の観点で見る。"""
import json, re, glob, os, collections, subprocess
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
R = []
def check(n, t, bad, note=""):
    R.append((n, t, bad)); print(f"\n【{n:2d}】{t}")
    if note: print("      " + note)
    for x in bad[:7]: print("      ■ " + str(x)[:150])
    if len(bad) > 7: print(f"      … 他 {len(bad)-7} 件")
    if not bad: print("      → 指摘なし")
print("═"*74); print(" ブラッシュアップの検討"); print("═"*74)

ANA = []
for f in ["../drill/data/anaume.js", "../drill/data/anaume2.js"]:
    s = open(f).read(); i = s.index("[", s.index("register")); j = s.rindex("]")
    ANA += json.loads(s[i:j+1])
APP = open("../drill/index.html").read()

# 1 条文の見出しが答えを漏らしていないか
bad = []
for q in ANA:
    m = re.search(r"（(.+?)）$", q.get("src", ""))
    if not m: continue
    cap = NOSP(m.group(1)); a = NOSP(q["choices"][q["a"]])
    if len(a) >= 3 and (a in cap or cap in a): bad.append(f'{q["src"]} ← 正答「{q["choices"][q["a"]]}」')
check(1, "条文の見出しに正答が入っていて、読めば分かる", bad,
      f"見出しつき {sum(1 for q in ANA if re.search(chr(65288)+'.+'+chr(65289)+'$', q.get('src','')))}問")

# 2 速答のセッションがリロードで消えないか
has = "K_BSESS" in APP or re.search(r"save\(K_[A-Z]*SESS[^)]*\).*B\b", APP)
check(2, "速答が出題中にリロードすると消える", [] if has else
      ["ドリルと模試は保存しているが、速答は保存していない"])

# 3 法令ごとの配分が試験の比重と合っているか
w = collections.Counter(q["law"] for q in ANA)
CORE = {"労働基準法","労働安全衛生法","労働者災害補償保険法","雇用保険法","労働保険徴収法",
        "健康保険法","厚生年金保険法","国民年金法"}
core = sum(v for k, v in w.items() if k in CORE)
sub  = sum(v for k, v in w.items() if k not in CORE and "規則" not in k and "施行令" not in k)
rule = sum(v for k, v in w.items() if "規則" in k or "施行令" in k)
tot = sum(w.values())
bad = []
if core / tot < 0.40: bad.append(f"択一7科目の法律本体が {core/tot*100:.0f}% しかない（本試験の択一は7科目×10問）")
check(3, "法令ごとの配分が本試験の比重と合っていない", bad,
      f"択一7科目の本体 {core}問({core/tot*100:.0f}%) / 一般常識の個別法 {sub}問({sub/tot*100:.0f}%) / 施行令・規則 {rule}問({rule/tot*100:.0f}%)")

# 4 同じ条文から作りすぎていないか
c = collections.Counter(q["src"] for q in ANA)
bad = [f"{k} から {v}問" for k, v in c.most_common() if v > 8]
check(4, "同じ条文から作りすぎ", bad, f"条文 {len(c)}種から {len(ANA)}問")

# 5 配信データの大きさ（スマホでの初回読み込み）
# 実測すると gzip で 1/6 になる（anaume2.js は 2.4MB → 417KB）。
# 判定は圧縮後の見込みで行う。
import gzip as _gz
tot_b = sum(os.path.getsize(p) for p in glob.glob("../drill/data/*.js"))
gz_b = sum(len(_gz.compress(open(p,"rb").read(), 6)) for p in glob.glob("../drill/data/*.js"))
bad = [] if gz_b < 2_500_000 else [f"圧縮後 {gz_b/1048576:.1f}MB。回線が細いと初回が重い"]
check(5, "配信データが大きい", bad,
      f"data/ 生 {tot_b/1048576:.1f}MB → 圧縮後 {gz_b/1048576:.1f}MB（{len(glob.glob('../drill/data/*.js'))}ファイル）")

# 6 残り日数で回せる量か
days = 25
n_all = 0
for f in glob.glob("../drill/data/*.js"):
    s = open(f).read()
    if "register" not in s: continue
    i = s.index("[", s.index("register")); j = s.rindex("]")
    try: n_all += len(json.loads(s[i:j+1]))
    except Exception: n_all += s.count('"type"')
check(6, "残り日数に対する問題数", [], f"総 {n_all:,}問。25日で1日 {n_all//25:,}問は非現実的。"
      "→ 優先順位（出題実績あり・間違えたものだけ）で絞る設計になっているかが要点")

# 7 速答に解説がない
has_exp = sum(1 for q in ANA if q.get("exp"))
check(7, "速答に解説がない", [] if has_exp else
      ["間違えたときに『なぜその語か』が分からない。条文の出典は出ているが、意味の説明はない"],
      f"解説あり {has_exp}/{len(ANA)}問")

# 8 同じ語ばかり正答になっていないか
a = collections.Counter(q["choices"][q["a"]] for q in ANA)
bad = [f"「{k}」が {v}回" for k, v in a.most_common(6) if v > 40]
check(8, "同じ語が正答になりすぎ", bad, f"正答の種類 {len(a)}種")

# 9 選択肢の重複度（同じ4択の組合せ）
c2 = collections.Counter(tuple(sorted(NOSP(x) for x in q["choices"])) for q in ANA)
bad = [f"{v}回" for k, v in c2.items() if v > 3]
check(9, "同じ4択の組合せが繰り返される", bad)

# 10 学習記録との連携
bad = []
if "grade(q.id" not in APP: bad.append("速答の結果が学習記録に入っていない")
if 'type === "ana"' not in APP and "type==='ana'" not in APP: pass
check(10, "速答の結果が記録に反映されるか", bad)

print("\n" + "═"*74)
ng = [n for n, _, b in R if b]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(b) for _,_,b in R)}件" + (f"　観点{ng}" if ng else ""))
print("═"*74)
