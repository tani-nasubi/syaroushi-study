#!/usr/bin/env python3
"""資料レビュー 第3ラウンド。
第1回＝「過去問の語が資料にあるか」、第2回＝「合否を分ける要素があるか」。
今回は「実際に使い切れるか・穴はどこか」という運用と密度の観点で見る。
"""
import json, re, collections, os

N = "../notes"
M = json.load(open("mondai.json"))
S = json.load(open("seitou.json"))
NOSP = lambda s: re.sub(r"[\s　,，、。「」（）()・]", "", str(s))
FILES = sorted(f for f in os.listdir(N) if f.endswith(".md"))
RAW = {f: open(f"{N}/{f}").read() for f in FILES}
def strip_trend(b): return re.sub(r"<!-- TREND:BEGIN -->.*?<!-- TREND:END -->", "", b, flags=re.S)
BODY = {f: strip_trend(b) for f, b in RAW.items()}
FLAT = {f: NOSP(b) for f, b in BODY.items()}
SUBJ_FILE = {"労基安衛":["01-労働基準法.md","02-労働安全衛生法.md"],"労災":["03-労災保険法.md","05-徴収法.md"],
  "雇用":["04-雇用保険法.md","05-徴収法.md"],"一般常識":["06-労働一般常識.md","07-社会保険一般常識.md"],
  "健保":["08-健康保険法.md"],"厚年":["10-厚生年金保険法.md"],"国年":["09-国民年金法.md"]}

R=[]; INFO={2,3,4,7,10}   # 統計を出すだけの観点
def rep(n,t,lines,summary=""):
    R.append((n,t,lines))
    print(f"\n【{n:2d}】{t}" + ("　※情報提供" if n in INFO else ""))
    if summary: print("      "+summary)
    for l in lines[:12]: print("      "+l)
    if len(lines)>12: print(f"      … 他 {len(lines)-12} 件")
    if not lines: print("      → 指摘なし")

print("═"*74); print(" 資料レビュー 第3ラウンド（運用と密度の観点）"); print("═"*74)

def qtype(s):
    s=NOSP(s)
    if "いくつあるか" in s: return "個数"
    if "組合せ" in s: return "組合せ"
    if re.search(r"誤っているもの|誤りである",s): return "誤り選び"
    if re.search(r"正しいもの|適切なもの",s): return "正しい選び"
    return "その他"

# 1 ── S/Aランク論点に対して資料の記述が薄いもの
KEYS=json.load(open("tokuten_keys.json")) if os.path.exists("tokuten_keys.json") else None
import importlib.util
spec=importlib.util.spec_from_file_location("gt","gen_tokuten.py")
gt=importlib.util.module_from_spec(spec)
import sys as _s; _s.argv=["x"]
try:
    src=open("gen_tokuten.py").read()
    ns={}
    exec(src.split("stat = {}")[0], ns)     # KEYS だけ取り出す
    KEYS=ns["KEYS"]
except Exception as e:
    KEYS={}
lines=[]
for subj,keys in KEYS.items():
    nt="".join(FLAT[f] for f in SUBJ_FILE.get(subj,[]))
    d={k:set() for k in keys}
    for kai,v in M.items():
        for q in v["takuitsu"]:
            if q["subject"]!=subj: continue
            stem=NOSP(q["stem"]); chs=[NOSP(c) for c in q["choices"]]
            for k in keys:
                kk=NOSP(k)
                if kk in stem or sum(1 for c in chs if kk in c)>=3: d[k].add(int(kai))
    for k,y in d.items():
        if len(y)>=5:                                   # S/Aランク
            n=FLAT_count=nt.count(NOSP(k))
            if n<=2: lines.append(f"{subj}／{k}（{len(y)}年出題）… 資料中の言及 {n}回")
rep(1,"S/Aランク論点なのに資料での言及が2回以下",lines,
    "毎年出るのに記述が薄い＝取りこぼしの温床")

# 2 ── 誤り肢に頻出する「改変のしかた」
wrong=collections.defaultdict(list); right=collections.defaultdict(list)
for kai,v in M.items():
    for q in v["takuitsu"]:
        a=S[kai]["takuitsu"][q["subject"]][q["num"]-1]
        if a is None or isinstance(a,list): continue
        t=qtype(q["stem"])
        if t=="誤り選び":
            wrong[q["subject"]].append(q["choices"][a])
            right[q["subject"]] += [c for i,c in enumerate(q["choices"]) if i!=a]
        elif t=="正しい選び":
            right[q["subject"]].append(q["choices"][a])
            wrong[q["subject"]] += [c for i,c in enumerate(q["choices"]) if i!=a]
PAT={"数値":r"[0-9０-９]+\s*(年|月|日|時間|人|円|％|分の[0-9])",
     "主体":r"(厚生労働大臣|都道府県労働局長|労働基準監督署長|公共職業安定所長|市町村長|保険者|政府|裁判所)",
     "義務／裁量":r"(しなければならない|することができる|するものとする|してはならない|努めなければならない)",
     "範囲":r"(以上|以下|超え|未満|以内|を限度)"}
lines=[]
for s in ["労基安衛","労災","雇用","健保","厚年","国年","一般常識"]:
    ws=wrong[s]; tot=len(ws)
    if not tot: continue
    c={k:sum(1 for w in ws if re.search(p,NOSP(w)))/tot*100 for k,p in PAT.items()}
    lines.append(f"{s}：数値{c['数値']:.0f}% 主体{c['主体']:.0f}% 義務裁量{c['義務／裁量']:.0f}% 範囲{c['範囲']:.0f}%")
rep(2,"誤り肢に含まれる要素の割合（＝改変されやすい箇所）",lines,
    f"誤り肢 計{sum(len(v) for v in wrong.values())}肢／正しい肢 計{sum(len(v) for v in right.values())}肢")

# 3 ── 資料の読了時間 vs 残り日数
tot=sum(len(BODY[f]) for f in FILES)
rep(3,"資料の総量と読了時間",
    [f"総字数 {tot:,}字",
     f"通読の目安 {tot/600/60:.1f}時間（600字/分）／表が多いので実質 {tot/300/60:.1f}時間",
     f"残り26日・1日4〜5時間なら、通読は全体の {tot/300/60/120*100:.0f}% 程度の時間"],
    "読み切れる量かどうか")

# 4 ── 各資料の位置づけ（読む順序が示されているか）
lines=[]
for f in FILES:
    if "## 次に読むもの" not in BODY[f] and f[:2] not in ("90","91"): lines.append(f"{f}：次に読むものの導線なし")
rep(4,"資料間の読む順序",lines)

# 5 ── 直前期（前日・当日）に読む圧縮版があるか
has_final = any(re.search(r"(前日|当日|最終確認|直前確認)", BODY[f]) and len(BODY[f])<8000 for f in FILES)
lines=[] if has_final else ["8/22（前日）と当日朝に読む『圧縮版』がない。209,000字は前日に読めない"]
rep(5,"前日・当日に読む圧縮版",lines,"直前に何を見るかが決まっていないと、当日に迷って消耗する")

# 6 ── 同じ内容の重複（メンテナンスのリスク）
lines=[]; seen=collections.defaultdict(list)
for f in FILES:
    for m in re.finditer(r"^\| \*\*([^|*]{3,20})\*\* \|", BODY[f], re.M):
        seen[m.group(1)].append(f)
for k,fs in seen.items():
    u=sorted(set(fs))
    if len(u)>=4: lines.append(f"「{k}」が {len(u)}資料に重複: {'、'.join(x[:2] for x in u)}")
rep(6,"同一項目が4資料以上に重複",lines,"片方だけ直すと矛盾する。1か所に集約すべき")

# 7 ── 白書・統計の出題実態
n_stat=0; kinds=collections.Counter()
for kai,v in M.items():
    for q in v["takuitsu"]+v["sentaku"]:
        t=NOSP(q.get("stem") or q.get("body",""))
        if re.search(r"(白書|労働経済の分析|調査|統計|厚生労働省の.*によれば)",t):
            n_stat+=1
            for k in ["労働力調査","毎月勤労統計","賃金構造基本統計","就労条件総合調査","能力開発基本調査",
                      "労働組合基礎調査","国民医療費","社会保障費用統計","人口動態","雇用動向調査","労働経済の分析","厚生労働白書"]:
                if NOSP(k) in t: kinds[k]+=1
rep(7,"白書・統計からの出題",
    [f"過去9年で {n_stat} 問が白書・統計に言及"]+[f"  {k}：{c}回" for k,c in kinds.most_common(8)],
    "この資料では『順位と傾向』しか扱えていない領域")

# 8 ── 通達・行政解釈からの出題
n_tsu=0
for kai,v in M.items():
    for q in v["takuitsu"]:
        if re.search(r"(通達|とされている|と解されている|行政解釈)",NOSP(q["stem"]+"".join(q["choices"]))): n_tsu+=1
# 通達由来の記述をまとめた資料があるかを見る
has_tsu = any("通達・行政解釈からの出題" in BODY[f] for f in FILES)
lines=[] if has_tsu else [f"通達・行政解釈に基づく記述が {n_tsu} 問（全630問中 {n_tsu/630*100:.0f}%）に登場するが、まとめた資料がない"]
rep(8,"通達・行政解釈からの出題",lines)

# 9 ── 選択式の科目別カバー（条文素読で埋まったか）
gen=FLAT.get("95-条文素読（選択式の原文）.md","")
lines=[]
for s in ["労基安衛","労災","雇用","労一","社一","健保","厚年","国年"]:
    n=sum(1 for kai,v in M.items() for q in v["sentaku"] if q["subject"]==s)
    if n<9: lines.append(f"{s}：素読集に {n}/9年分しかない")
rep(9,"条文素読集の年度網羅",lines)

# 10 ── アプリのドリルとの役割分担
lines=[f"ドリル 3,524問（過去問3,282＋自作242）／資料 {len(FILES)}件 {tot:,}字",
       "肢別○× 2,674問は『誤り肢の型』を体で覚える装置。資料の読解と併用する設計"]
rep(10,"ドリルと資料の役割分担",lines)

print("\n"+"═"*74)
ng=[n for n,_,l in R if l and n not in INFO]
print(f" 要改善: {len(ng)}観点 / 指摘{sum(len(l) for n,_,l in R if l and n not in INFO)}件"
      + (f"（観点 {ng}）" if ng else ""))
print("═"*74)
