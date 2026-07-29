#!/usr/bin/env python3
"""資料レビュー 第5ラウンド。第4回までに見ていない観点だけを見る。"""
import json, re, collections, os
N="../notes"
M=json.load(open("mondai.json")); S=json.load(open("seitou.json"))
NOSP=lambda s: re.sub(r"[\s　,，、。「」（）()・]","",str(s))
FILES=sorted(f for f in os.listdir(N) if f.endswith(".md"))
RAW={f:open(f"{N}/{f}").read() for f in FILES}
strip=lambda b: re.sub(r"<!-- TREND:BEGIN -->.*?<!-- TREND:END -->","",b,flags=re.S)
BODY={f:strip(b) for f,b in RAW.items()}
ALL=NOSP("".join(BODY.values()))
KAI2Y={57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",52:"令和2",51:"令和元",50:"平成30",49:"平成29"}
R=[]
def rep(n,t,lines,summary="",info=False):
    R.append((n,t,lines,info))
    print(f"\n【{n:2d}】{t}"+("　※情報提供" if info else ""))
    if summary: print("      "+summary)
    for l in lines[:14]: print("      "+l)
    if len(lines)>14: print(f"      … 他 {len(lines)-14} 件")
    if not lines: print("      → 指摘なし")
print("═"*76); print(" 資料レビュー 第5ラウンド"); print("═"*76)

LAWRE=re.compile(r"(労働基準法|労働安全衛生法|労働者災害補償保険法|労災保険法|雇用保険法|健康保険法|"
 r"厚生年金保険法|国民年金法|社会保険労務士法|労働契約法|労働組合法|最低賃金法|労働者派遣法)第?([0-9]{1,3})条")

# 1 ── 選択式で複数年出ている条文（＝また出る可能性が高い）
art=collections.defaultdict(set)
for kai,v in M.items():
    for q in v["sentaku"]:
        for m in LAWRE.finditer(NOSP(q["body"])): art[f"{m.group(1)}{m.group(2)}条"].add(int(kai))
multi={a:sorted(y,reverse=True) for a,y in art.items() if len(y)>=2}
has=lambda a:(a in ALL) or (re.sub(r"([0-9]+条)",r"第\1",a) in ALL)
rep(1,"選択式で2年以上出た条文のうち、資料に条文番号がないもの",
    [f"{a}（{'・'.join(KAI2Y[k] for k in y)}）" for a,y in sorted(multi.items(),key=lambda x:-len(x[1])) if not has(a)],
    f"選択式で2年以上出た条文は {len(multi)}種。ここは再出題の本命")

# 2 ── 択一の正解番号の偏り（時間切れ時のマーク戦略になるか）
pos=collections.Counter(); byS=collections.defaultdict(collections.Counter)
for kai,v in M.items():
    for q in v["takuitsu"]:
        a=S[kai]["takuitsu"][q["subject"]][q["num"]-1]
        if a is None or isinstance(a,list): continue
        pos["ABCDE"[a]]+=1; byS[q["subject"]]["ABCDE"[a]]+=1
t=sum(pos.values())
rep(2,"択一の正解番号の分布",
    [f"{k}: {v}問 ({v/t*100:4.1f}%)" for k,v in sorted(pos.items())]
    +[f"→ 最多{max(pos,key=pos.get)} と 最少{min(pos,key=pos.get)} の差 {(pos[max(pos,key=pos.get)]-pos[min(pos,key=pos.get)])/t*100:.1f}ポイント"],
    f"全{t}問。偏りがあれば時間切れ時のマーク戦略になる",info=True)

# 3 ── 数値暗記の未検証項目
num=BODY.get("91-数値暗記.md","")
warn=[l.strip() for l in num.split("\n") if "⚠️" in l and l.startswith("|") and "単一出典・要照合" not in l]
rep(3,"数値暗記で未検証（⚠️）のまま残っている項目",
    [re.sub(r"\s+"," ",w)[:88] for w in warn],
    f"⚠️ {len(warn)}件。本番で使う数値が未確認のまま")

# 4 ── 資料内のリンク切れ
lines=[]
for f,b in BODY.items():
    for m in re.finditer(r"\]\(([^)#][^)]*\.md)\)", b):
        tgt=m.group(1)
        if tgt not in FILES: lines.append(f"{f} → {tgt}（存在しない）")
rep(4,"資料間リンクの切れ",sorted(set(lines)))

# 5 ── 目的条文の網羅（選択式で出た実績がある）
obj=[]
for kai,v in M.items():
    for q in v["sentaku"]:
        b=NOSP(q["body"])
        if re.search(r"この法律は|目的とする",b): obj.append((int(kai),q["subject"]))
lines=[]
for f in [x for x in FILES if x[0] in "01"]:
    if "目的" not in BODY[f]: lines.append(f"{f}：目的条文の記述がない")
rep(5,"目的条文",lines,f"選択式で目的条文が題材になった実績 {len(obj)}件"
    +("（"+"・".join(f"{KAI2Y[k]}{s}" for k,s in sorted(obj,reverse=True)[:6])+"）" if obj else ""))

# 6 ── 選択式pool20 の20語がどんな構成か（絞り込み技術の裏づけ）
grp=[]
for kai,v in M.items():
    for q in v["sentaku"]:
        if q["format"]!="pool20": continue
        ws=[NOSP(c) for c in q["choices"]]
        L=[len(w) for w in ws]
        grp.append((max(L)-min(L), sum(L)/len(L)))
rep(6,"選択式20語プールの構成",
    [f"語の長さの平均 {sum(x[1] for x in grp)/len(grp):.1f}字／最長と最短の差 平均 {sum(x[0] for x in grp)/len(grp):.1f}字",
     "→ 長さがそろっていない＝『種類で切る』技術が効く裏づけ"],info=True)

# 7 ── 直前期スケジュールと資料の対応（アプリのPLAN）
app=open("../drill/index.html").read()
plan=re.findall(r'"(\d{4}-\d{2}-\d{2})":\s*\{([^}]*)\}', app)
nofile=[d for d,body in plan if ".md" not in body and "sel" not in body]
rep(7,"直前期スケジュールで読む資料が指定されていない日",
    [f"{d}" for d in nofile], f"登録日数 {len(plan)}日")

# 8 ── 横断整理に載せるべき「科目間で違う」項目
pairs={"時効":r"時効","不服申立て":r"審査請求|再審査請求","端数処理":r"端数","届出の期限":r"以内に届け出",
       "被保険者資格":r"資格の取得|資格の喪失","給付制限":r"給付制限","一部負担":r"一部負担金"}
yoko=BODY.get("90-横断整理.md","")
rep(8,"横断整理で扱っていない対比項目",
    [k for k,p in pairs.items() if k not in yoko],
    f"横断整理 {len(yoko):,}字")

# 9 ── 各科目資料の分量バランス（出題数は全科目同じ10問）
sizes={f:len(BODY[f]) for f in FILES if f[0] in "01"}
avg=sum(sizes.values())/len(sizes)
rep(9,"科目資料の分量が平均から大きく外れているもの",
    [f"{f}：{v:,}字（平均比 {v/avg*100:.0f}%）" for f,v in sorted(sizes.items(),key=lambda x:x[1]) if v<avg*.6 or v>avg*1.6],
    f"択一は全科目10問ずつ。平均 {avg:,.0f}字")

# 10 ── 過去問で「正しい肢」が0本の論点（正文集の空白）
ns={}; exec(open("gen_tokuten.py").read().split("stat = {}")[0], ns); KEYS=ns["KEYS"]
sei=BODY.get("A0-正文集（択一の正しい肢）.md","")
lines=[]
for s,keys in KEYS.items():
    for kw in keys:
        ys=set()
        for kai,v in M.items():
            for q in v["takuitsu"]:
                if q["subject"]!=s: continue
                if NOSP(kw) in NOSP(q["stem"]) or sum(1 for c in q["choices"] if NOSP(kw) in NOSP(c))>=3: ys.add(int(kai))
        if len(ys)>=3 and f"### {kw}" not in sei: lines.append(f"{s}／{kw}（{len(ys)}年）")
rep(10,"3年以上出題された論点で正文集に見出しがない",lines)

print("\n"+"═"*76)
ng=[n for n,_,l,i in R if l and not i]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(l) for n,_,l,i in R if l and not i)}件"+(f"　観点{ng}" if ng else ""))
print("═"*76)
