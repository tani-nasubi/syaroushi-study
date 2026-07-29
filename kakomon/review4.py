#!/usr/bin/env python3
"""資料レビュー 第4ラウンド。
第1回=過去問の語の網羅、第2回=合否を分ける要素、第3回=運用と密度。
今回は「本試験の1点に直結するか」という観点で、これまで見ていない角度だけを見る。
"""
import json, re, collections, os

N="../notes"
M=json.load(open("mondai.json")); S=json.load(open("seitou.json"))
K={int(a):b for a,b in json.load(open("kijun.json")).items()}
NOSP=lambda s: re.sub(r"[\s　,，、。「」（）()・]","",str(s))
FILES=sorted(f for f in os.listdir(N) if f.endswith(".md"))
RAW={f:open(f"{N}/{f}").read() for f in FILES}
strip=lambda b: re.sub(r"<!-- TREND:BEGIN -->.*?<!-- TREND:END -->","",b,flags=re.S)
BODY={f:strip(b) for f,b in RAW.items()}
FLAT={f:NOSP(b) for f,b in BODY.items()}
ALL=NOSP("".join(BODY.values()))
SUBJ_FILE={"労基安衛":["01-労働基準法.md","02-労働安全衛生法.md"],"労災":["03-労災保険法.md","05-徴収法.md"],
 "雇用":["04-雇用保険法.md","05-徴収法.md"],"一般常識":["06-労働一般常識.md","07-社会保険一般常識.md"],
 "健保":["08-健康保険法.md"],"厚年":["10-厚生年金保険法.md"],"国年":["09-国民年金法.md"]}
R=[]
def rep(n,t,lines,summary="",info=False):
    R.append((n,t,lines,info))
    print(f"\n【{n:2d}】{t}"+("　※情報提供" if info else ""))
    if summary: print("      "+summary)
    for l in lines[:14]: print("      "+l)
    if len(lines)>14: print(f"      … 他 {len(lines)-14} 件")
    if not lines: print("      → 指摘なし")

print("═"*76); print(" 資料レビュー 第4ラウンド（1点に直結するかの観点）"); print("═"*76)

LAWRE=re.compile(r"(労働基準法|労働安全衛生法|労働者災害補償保険法|労災保険法|雇用保険法|健康保険法|"
 r"厚生年金保険法|国民年金法|社会保険労務士法|労働契約法|労働組合法|最低賃金法|労働者派遣法)第?([0-9]{1,3})条")

# 1 ── 選択式で出た条文が素読集にあるか（＝選択式の直撃対策の穴）
gen=FLAT.get("95-条文素読（選択式の原文）.md","")
need=collections.Counter()
for kai,v in M.items():
    for q in v["sentaku"]:
        for m in LAWRE.finditer(NOSP(q["body"])): need[f"{m.group(1)}{m.group(2)}条"]+=1
def has_art(a):
    law, num = re.match(r"(.+?)([0-9]{1,3})条$", a).groups()
    # 「労働基準法114条」「労働基準法第114条」「第114条」いずれの表記でも拾う
    return any(x in ALL for x in (f"{law}{num}条", f"{law}第{num}条"))
miss=[a for a,c in need.most_common() if not has_art(a)]
rep(1,"選択式の根拠条文なのに、資料のどこにも条文番号がない",
    [f"{a}（{need[a]}回）" for a in miss],
    f"選択式で参照された条文 {len(need)}種のうち {len(miss)}種が資料に不在")

# 2 ── S/Aランク論点に対して正文集の収録がゼロ
ns={}; exec(open("gen_tokuten.py").read().split("stat = {}")[0], ns); KEYS=ns["KEYS"]
sei=FLAT.get("A0-正文集（択一の正しい肢）.md","")
lines=[]
for s,keys in KEYS.items():
    for kw in keys:
        ys=set()
        for kai,v in M.items():
            for q in v["takuitsu"]:
                if q["subject"]!=s: continue
                if NOSP(kw) in NOSP(q["stem"]) or sum(1 for c in q["choices"] if NOSP(kw) in NOSP(c))>=3:
                    ys.add(int(kai))
        if len(ys)>=5 and f"### {kw}" not in BODY.get("A0-正文集（択一の正しい肢）.md",""):
            lines.append(f"{s}／{kw}（{len(ys)}年出題）")
rep(2,"S/Aランク論点なのに正文集に見出しがない",lines,
    "毎年出るのに『正しい形』を原文で読めない論点")

# 3 ── 計算問題の類型を網羅しているか
calc=collections.Counter()
PATC={"平均賃金":r"平均賃金","給付基礎日額":r"給付基礎日額","賃金日額":r"賃金日額|基本手当の日額",
 "標準報酬":r"標準報酬(月額|日額)","傷病手当金":r"傷病手当金の額","高額療養費":r"高額療養費",
 "老齢厚生年金":r"報酬比例部分|老齢厚生年金の額","在職老齢":r"在職老齢年金|支給停止基準額",
 "遺族厚生":r"遺族厚生年金の額|300月","老齢基礎":r"老齢基礎年金の額|保険料納付済期間",
 "保険料":r"一般保険料額|保険料の額","労働時間":r"割増賃金|時間外労働.*時間"}
for kai,v in M.items():
    for q in v["takuitsu"]:
        t=NOSP(q["stem"]+"".join(q["choices"]))
        if not re.search(r"いくらか|額はいくら|何円|日額は",NOSP(q["stem"])): continue
        for k,p in PATC.items():
            if re.search(p,t): calc[k]+=1
cal=BODY.get("94-計算問題の解法.md","")
lines=[f"{k}（過去9年で{c}問）" for k,c in calc.most_common() if NOSP(k) not in NOSP(cal)]
rep(3,"過去に計算問題が出た類型なのに、計算資料に解法がない",lines,
    f"計算問題で問われた類型 {len(calc)}種")

# 4 ── 直近3年に新出した語が資料にあるか（法改正・新制度の取り込み）
old=set(); new=collections.Counter()
for kai,v in M.items():
    txt=NOSP("".join(q["stem"]+"".join(q["choices"]) for q in v["takuitsu"])+
             "".join(q["body"] for q in v["sentaku"]))
    for w in re.findall(r"[一-鿿ァ-ヴ]{4,10}(?:給付金?|手当金?|一時金|加算|保険料|届|認定|休業|支援金)",txt):
        if int(kai)>=55: new[w]+=1
        else: old.add(w)
lines=[f"{w}（直近3年で{c}回）" for w,c in new.most_common(40) if w not in old and NOSP(w) not in ALL][:14]
rep(4,"直近3年で新しく出た用語なのに資料にない",lines,
    "制度改正で新設された給付・手当は狙われやすい")

# 5 ── 択一で「〜以内」「〜以上」の期間・回数が資料にあるか（数値の穴）
num=collections.Counter()
for kai,v in M.items():
    for q in v["takuitsu"]:
        a=S[kai]["takuitsu"][q["subject"]][q["num"]-1]
        if a is None or isinstance(a,list): continue
        st=NOSP(q["stem"])
        wrong_pick = bool(re.search(r"誤っているもの|誤りである",st))
        ok=[c for i,c in enumerate(q["choices"]) if (i!=a) == wrong_pick]
        for c in ok:
            for m in re.finditer(r"([0-9]{1,4})(年|か月|箇月|月|日|週間|時間|回|人|分の[0-9]+)(以内|以上|以下|未満|を超え|間)",NOSP(c)):
                num[m.group(0)]+=1
lines=[f"{k}（正しい肢に{c}回）" for k,c in num.most_common(60) if c>=3 and NOSP(k) not in ALL][:14]
rep(5,"正しい肢に3回以上出た期間・数値なのに資料にない",lines,
    f"正しい肢から抽出した期間表現 {len(num)}種")

# 6 ── 科目間で同じ数値が食い違っていないか
lines=[]
PAIR=[("被保険者期間","1年以上"),("時効","2年"),("時効","5年"),("不服申立て","3か月"),
      ("届出","5日以内"),("届出","10日以内"),("端数処理","50銭")]
seen=collections.defaultdict(set)
for f,b in BODY.items():
    for m in re.finditer(r"(時効|消滅時効)[^\n]{0,40}?([0-9]+)年",b): seen[m.group(1)].add((f,m.group(2)))
for k,v in seen.items():
    yr=collections.Counter(x[1] for x in v)
    if len(yr)>2: lines.append(f"「{k}」の年数が資料間で {sorted(yr)} と分かれている")
rep(6,"同じ概念の数値が資料間で食い違う",lines,"矛盾があると本番で迷う",info=True)

# 7 ── 各資料に「直前チェック」があるか（当日使えるか）
lines=[f for f in FILES if f[0] in "01" and "直前チェック" not in BODY[f]]
rep(7,"科目資料に直前チェックリストがない",lines)

# 8 ── 択一の個数・組合せ問題への専用の解き方があるか
has=any(re.search(r"個数(・組合せ)?問題[^\n]{0,80}(解き方|手順|対処|飛ば)",b) for b in BODY.values())
n_ko=sum(1 for kai,v in M.items() for q in v["takuitsu"]
         if re.search(r"いくつあるか|組合せ",NOSP(q["stem"])))
rep(8,"個数・組合せ問題の解き方",
    [] if has else [f"9年で{n_ko}問（全630問の{n_ko/630*100:.0f}%）出ているが、専用の解き方の記述がない"])

# 9 ── 判例資料が直近の判例増加に追いついているか
han=[]
for kai,v in M.items():
    for q in v["takuitsu"]:
        if re.search(r"最高裁判所",NOSP(q["stem"]+"".join(q["choices"]))):
            han.append((int(kai),q["subject"]))
hb=BODY.get("93-判例.md","")
cnt=collections.Counter(s for k,s in han if k>=55)
lines=[f"{s}：直近3年の択一で{c}問 判例が出ているが、判例資料に{s}の節がない"
       for s,c in cnt.items() if c>=2 and s not in ("労基安衛",) and NOSP(s) not in NOSP(hb)]
rep(9,"直近3年に判例が出た科目で、判例資料に節がない",lines,
    f"択一の判例言及 直近3年で{sum(cnt.values())}問")

# 10 ── 白書・統計の出題語が資料にあるか
stat_words=collections.Counter()
for kai,v in M.items():
    for q in v["sentaku"]:
        b=NOSP(q["body"])
        if not re.search(r"白書|調査|統計|によれば",b): continue
        raw=S[kai]["sentaku"][q["subject"]]
        for i,a in enumerate(raw):
            a0=a[0] if isinstance(a,list) else a
            if a0 is None: continue
            w=(q["choices"][a0-1] if q["format"]=="pool20"
               else (q["choices"][i][a0-1] if a0-1<len(q["choices"][i]) else ""))
            if w: stat_words[NOSP(w)]+=1
hb=FLAT.get("99-白書・統計.md","")
miss=[w for w in stat_words if w not in hb and w not in ALL]
rep(10,"統計・白書の選択式で正答になった語のうち、資料にないもの",
    miss[:14], f"統計由来の正答語 {len(stat_words)}語中 {len(miss)}語が不在")

print("\n"+"═"*76)
ng=[n for n,_,l,i in R if l and not i]
print(f" 要改善: {len(ng)}観点 / 指摘 {sum(len(l) for n,_,l,i in R if l and not i)}件"+(f"　観点{ng}" if ng else ""))
print("═"*76)
