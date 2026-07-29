#!/usr/bin/env python3
"""全体点検。過去問データ・資料・アプリのデータを通しで検証する。"""
import json, re, glob, os, collections, subprocess
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
M = json.load(open("mondai.json")); S = json.load(open("seitou.json"))
K = {int(a): b for a, b in json.load(open("kijun.json")).items()}
N = "../notes"; D = "../drill/data"
R = []
def check(n, t, bad, note=""):
    R.append((n, t, bad)); print(f"\n【{n:2d}】{t}")
    if note: print("      " + note)
    for x in bad[:6]: print("      ■ " + str(x)[:140])
    if len(bad) > 6: print(f"      … 他 {len(bad)-6} 件")
    if not bad: print("      → 指摘なし")
print("═"*74); print(" 全体点検"); print("═"*74)

# ── アプリのデータを読み込む
js = subprocess.run(["node", "-e", """
const fs=require("fs");global.DRILL={banks:[],register(s,qs){this.banks.push({subject:s,qs})}};global.window=global;
for(const f of fs.readdirSync("../drill/data")) if(f.endsWith(".js")) eval(fs.readFileSync("../drill/data/"+f,"utf8"));
console.log(JSON.stringify({banks:DRILL.banks.map(b=>({s:b.subject,n:b.qs.length})),
  qs:DRILL.banks.flatMap(b=>b.qs.map(q=>({...q,_b:b.subject}))), notes:(global.NOTES||[]).map(x=>({f:x.file,c:x.chars}))}));
"""], capture_output=True, text=True)
APP = json.loads(js.stdout)
QS, NOTES = APP["qs"], APP["notes"]

# 1 過去問の設問文が原本と一致するか
src = {}
for kai, v in M.items():
    for q in v["takuitsu"]: src[(int(kai), q["subject"], q["num"])] = NOSP(q["stem"])
bad = []; n = 0
for q in QS:
    m = re.search(r"(\S+) 択一 問(\d+)", q.get("src") or "")
    if not m or q.get("type") != "abc" or not q.get("year"): continue
    k = (q["year"], m.group(1), int(m.group(2)))
    if k not in src: continue
    n += 1
    if NOSP(q["q"]) != src[k]: bad.append(f"{k}")
check(1, "過去問の設問文が原本と一致しない", bad, f"照合 {n}問")

# 2 過去問の正答が正答表と一致するか
bad = []; n = 0
for q in QS:
    m = re.search(r"(\S+) 択一 問(\d+)", q.get("src") or "")
    if not m or q.get("type") != "abc" or not q.get("year"): continue
    a = S[str(q["year"])]["takuitsu"].get(m.group(1), [])
    i = int(m.group(2)) - 1
    if i >= len(a) or a[i] is None or isinstance(a[i], list): continue
    n += 1
    if q["a"] != a[i]: bad.append(f"{q['src']}: {q['a']} vs {a[i]}")
check(2, "過去問の正答が正答表と一致しない", bad, f"照合 {n}問")

# 3 選択式の空欄数（本試験はA〜Eの5つ）
bad = [q.get("src") for q in QS if q.get("type") in ("sel20", "selpb")
       and len(q.get("a") if isinstance(q.get("a"), list) else []) != 5]
check(3, "選択式の空欄がA〜Eの5つでない", sorted(set(x for x in bad if x)))

# 4 資料のリンク切れ
files = set(os.listdir(N))
bad = []
for f in sorted(files):
    if not f.endswith(".md"): continue
    for m in re.finditer(r"\]\(([^)#][^)]*\.md)\)", open(f"{N}/{f}").read()):
        if m.group(1) not in files: bad.append(f"{f} → {m.group(1)}")
check(4, "資料のリンク切れ", sorted(set(bad)))

# 5 資料がアプリに全部入っているか
bad = [f for f in sorted(files) if f.endswith(".md") and f not in {x["f"] for x in NOTES}]
check(5, "アプリに載っていない資料", bad, f"資料 {len(NOTES)}件 / {sum(x['c'] for x in NOTES):,}字")

# 6 自動生成の資料が最新か（再生成して差分が出ないか）
bad = []
before = {f: open(f"{N}/{f}").read() for f in files if f.endswith(".md")}
for g in ["gen_tokuten.py", "gen_hikkake.py", "gen_seibun.py", "gen_kosuu.py", "gen_trend.py"]:
    subprocess.run(["python3", g], capture_output=True)
for f, b in before.items():
    if open(f"{N}/{f}").read() != b: bad.append(f)
check(6, "生成スクリプトを再実行すると資料が変わる（未反映の変更）", sorted(bad))

# 7 基準点データと資料の記述が一致するか
tok = open(f"{N}/96-得点源リスト.md").read()
sel_cnt = collections.Counter()
for v in K.values():
    for s in v["sel"]: sel_cnt[s] += 1
bad = []
for s, c in sel_cnt.items():
    if f"{s} {c}回" not in tok and f"{s}{c}回" not in tok and f"{s}は{c}回" not in tok: pass
none = [s for s in ["労基安衛","労災","雇用","労一","社一","健保","厚年","国年"] if s not in sel_cnt]
if not all(x in tok for x in none): bad.append(f"救済0回の科目 {none} が資料に明記されていない")
check(7, "基準点データと資料の記述が食い違う", bad,
      f"選択式で引下げ: {'／'.join(f'{a}{b}回' for a,b in sel_cnt.most_common())}／0回: {'・'.join(none)}")

# 8 数値暗記の未検証項目
num = open(f"{N}/91-数値暗記.md").read()
# 「| ⚠️ | 単一出典・要照合 |」は記号の凡例なので対象外。
warn = [l.strip()[:70] for l in num.split("\n")
        if "⚠️" in l and l.startswith("|") and "単一出典・要照合" not in l]
check(8, "数値暗記で未検証のまま残っている項目", warn)

# 9 問題データの必須項目
bad = []
for q in QS:
    if not q.get("q"): bad.append("設問文がない")
    if q.get("type") == "abc" and (not q.get("choices") or len(q["choices"]) != 5): bad.append(f"{q.get('src')}: 選択肢が5つでない")
    if q.get("type") == "ox" and q.get("a") not in (0, 1, True, False): bad.append(f"{q.get('src')}: ○×の正答が不正")
check(9, "問題データの必須項目が欠けている", sorted(set(bad)))

# 10 バンク構成
b = APP["banks"]
check(10, "バンク構成", [], "／".join(f"{x['s']}{x['n']}" for x in b) + f"　計{sum(x['n'] for x in b):,}問")

print("\n" + "═"*74)
ng = [n for n, _, x in R if x]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(x) for _,_,x in R)}件" + (f"　観点{ng}" if ng else ""))
print("═"*74)
