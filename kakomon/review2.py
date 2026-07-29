#!/usr/bin/env python3
"""資料レビュー 第2ラウンド。
前回は「過去問に出た語が資料にあるか」を見た。今回は
「合否を分ける要素が資料に入っているか」という観点で10項目を見る。
"""
import json, re, collections, os, statistics

N = "../notes"
M = json.load(open("mondai.json"))
S = json.load(open("seitou.json"))
NOSP = lambda s: re.sub(r"[\s　,，]", "", str(s))
FILES = sorted(f for f in os.listdir(N) if f.endswith(".md"))
BODY = {f: open(f"{N}/{f}").read() for f in FILES}
FLAT = {f: NOSP(b) for f, b in BODY.items()}
MAP = {"労基安衛":["01-労働基準法.md","02-労働安全衛生法.md","93-判例.md","94-計算問題の解法.md"],
       "労災":["03-労災保険法.md","05-徴収法.md","93-判例.md","94-計算問題の解法.md"],
       "雇用":["04-雇用保険法.md","05-徴収法.md","94-計算問題の解法.md"],
       "一般常識":["06-労働一般常識.md","07-社会保険一般常識.md","93-判例.md"],
       "労一":["06-労働一般常識.md","93-判例.md"],"社一":["07-社会保険一般常識.md"],
       "健保":["08-健康保険法.md","94-計算問題の解法.md"],"厚年":["10-厚生年金保険法.md","94-計算問題の解法.md"],"国年":["09-国民年金法.md","94-計算問題の解法.md"]}
note = lambda s: "".join(FLAT[f] for f in MAP.get(s,[]))

R=[]
INFO={1,2,4,7,9}   # 統計を出すだけの観点（指摘＝改善要求ではない）
def rep(n,t,lines,summary=""):
    R.append((n,t,lines))
    print(f"\n【{n:2d}】{t}" + ("　※情報提供" if n in INFO else ""))
    if summary: print("      "+summary)
    for l in lines[:12]: print("      "+l)
    if len(lines)>12: print(f"      … 他 {len(lines)-12} 件")
    if not lines: print("      → 指摘なし")

print("═"*74); print(" 資料レビュー 第2ラウンド（合否を分ける要素の観点）"); print("═"*74)

# ── 設問の型を判定 ──
def qtype(s):
    s=NOSP(s)
    if "いくつあるか" in s: return "個数"
    if "組合せ" in s: return "組合せ"
    if re.search(r"誤っているもの|誤りである", s): return "誤り選び"
    if re.search(r"正しいもの|適切なもの", s): return "正しい選び"
    return "その他"

# 1 ── 「誤り」とされた肢＝出題者が作る典型的な誤解のカタログ
wrong_by_subj = collections.defaultdict(list)
for kai,v in M.items():
    for q in v["takuitsu"]:
        a = S[kai]["takuitsu"][q["subject"]][q["num"]-1]
        if a is None or isinstance(a,list): continue
        t = qtype(q["stem"])
        if t=="誤り選び":   wrong_by_subj[q["subject"]].append(q["choices"][a])       # 正解肢＝誤り
        elif t=="正しい選び":
            for i,c in enumerate(q["choices"]):
                if i!=a: wrong_by_subj[q["subject"]].append(c)                        # 正解以外＝誤り
tot_wrong = sum(len(v) for v in wrong_by_subj.values())
lines=[f"{s}：{len(v)}肢" for s,v in sorted(wrong_by_subj.items(), key=lambda x:-len(x[1]))]
rep(1,"「誤りの肢」の総数（＝出題者が作った引っかけの実物）",lines,
    f"過去9年で正誤が確定する誤り肢は計 {tot_wrong} 肢。ここに引っかけの型が全部ある")

# 2 ── 個数・組合せ問題の題材（全肢の正誤判断が要る＝理解の深さが要る論点）
lines=[]; kosu=collections.defaultdict(int)
for kai,v in M.items():
    for q in v["takuitsu"]:
        t=qtype(q["stem"])
        if t in ("個数","組合せ"): kosu[q["subject"]]+=1
for s,c in sorted(kosu.items(), key=lambda x:-x[1]):
    lines.append(f"{s}：{c}問 / 90問（{c/90*100:.0f}%）")
rep(2,"個数・組合せ問題の科目別出題数",lines,
    "全肢の正誤判断が必要。ここが多い科目は「なんとなく」では取れない")

# 3 ── 複数年で繰り返し問われた論点（再出題キーワード）
TERM=re.compile(r"[一-鿿ヲ-ヴー]{4,14}")
STOP=set("労働者使用者事業主被保険者厚生労働大臣厚生労働省令都道府県保険給付当該労働者当該事業主".split())
lines=[]
for subj in ["労基安衛","労災","雇用","健保","厚年","国年","一般常識"]:
    byyear=collections.defaultdict(set)
    for kai,v in M.items():
        for q in v["takuitsu"]:
            if q["subject"]!=subj: continue
            for w in set(TERM.findall(NOSP(q["stem"]))):
                if w not in STOP: byyear[w].add(int(kai))
    rec=[(w,len(y)) for w,y in byyear.items() if len(y)>=5]
    nt=note(subj)
    miss=[(w,c) for w,c in sorted(rec,key=lambda x:-x[1]) if w not in nt]
    if miss: lines.append(f"{subj}：" + "、".join(f"{w}({c}年)" for w,c in miss[:6]))
rep(3,"5年以上の年度で繰り返し問われているのに資料に無い論点",lines,
    "毎年出る＝出題者が重視している。ここを落とすのは致命的")

# 4 ── 計算・事例問題（毎年出る確定得点源）
CALC=re.compile(r"(いくらか|額はいくら|計算|に相当する額|円である|日額|支給額)")
lines=[]; calc=collections.defaultdict(list)
for kai,v in M.items():
    for q in v["takuitsu"]:
        if CALC.search(NOSP(q["stem"])) and re.search(r"[0-9０-９]",q["stem"]):
            calc[q["subject"]].append((int(kai),q["num"]))
for s,arr in sorted(calc.items(), key=lambda x:-len(x[1])):
    lines.append(f"{s}：{len(arr)}問（第{'・'.join(str(k) for k,_ in sorted(set(arr),reverse=True)[:6])}回 …）")
rep(4,"計算・事例問題の科目別出題数",lines,
    "解法さえ知っていれば確実に取れる。資料に計算手順があるか")

# 5 ── 判例の判示文言（選択式の長文選択肢はここから出る）
HAN=re.compile(r"最高裁判所|判示|事件")
lines=[]
for subj in ["労基安衛","労一","一般常識"]:
    n=0
    for kai,v in M.items():
        for q in v["takuitsu"]+v["sentaku"]:
            txt=q.get("stem") or q.get("body","")
            if q["subject"]==subj and HAN.search(NOSP(txt)): n+=1
    nt=note(subj)
    has=len(re.findall(r"事件", nt))
    lines.append(f"{subj}：過去問に判例言及 {n}問 ／ 資料の判例名 {has}件")
rep(5,"判例の扱い",lines,"労基・労一は判例からの出題が多い。判示文言が選択式で問われる")

# 6 ── 数値の「取りうる値の範囲」が整理されているか
lines=[]
RANGE_KEY=["時効","割合","端数","待期","年齢","人数"]
cross=FLAT["90-横断整理.md"]
for k in RANGE_KEY:
    if k not in cross: lines.append(f"横断整理に「{k}」の節がない")
if "取りうる" not in FLAT["91-数値暗記.md"] and "取りうる" not in cross:
    lines.append("「取りうる値の範囲」（時効なら2年か5年、割合なら2分の1/3分の2/4分の3…）の一覧がない")
rep(6,"選択式で数値を絞るための「取りうる値」の整理",lines,
    "初見の数値空欄は、制度上ありえない値を切ることでしか絞れない")

# 7 ── 横断比較が問われた設問
CROSS=re.compile(r"(労災保険法|雇用保険法|健康保険法|厚生年金保険法|国民年金法|労働基準法)")
lines=[]; n_cross=0
for kai,v in M.items():
    for q in v["takuitsu"]:
        laws=set(CROSS.findall(NOSP(q["stem"]+"".join(q["choices"]))))
        if len(laws)>=3: n_cross+=1
rep(7,"3つ以上の法律にまたがる設問",[f"過去9年で {n_cross} 問"],
    "横断整理が直接効く設問。90-横断整理.md の充実度が得点に直結")

# 8 ── 直前チェックが「誤り肢ベース」になっているか
lines=[]
for f in FILES:
    if f[:2] in ("00","90","91","92"): continue
    m=re.search(r"## 直前チェック.*", BODY[f], re.S)
    if not m: lines.append(f"{f}：直前チェックの節がない"); continue
    items=re.findall(r"^- \[ \] (.+)$", m.group(0), re.M)
    # 「〜は誤り」「〜ではない」「〜と混同」の形が何割か
    trap=sum(1 for i in items if re.search(
        r"(ではない|でない|と混同|入替|違い|対比|注意|引っかけ|／|＝|→|「.+」.*「.+」|"
        r"\*\*[^*]+\*\*.*\*\*[^*]+\*\*|[0-9]+.*[・／].*[0-9]+)", i))
    if items and trap/len(items) < 0.5:
        lines.append(f"{f}：{len(items)}項目中 対比・引っかけ形式は{trap}項目（{trap/len(items)*100:.0f}%）")
rep(8,"直前チェックリストが「引っかけの対比」形式になっているか",lines,
    "単なる知識の羅列だと直前に読む価値が薄い")

# 9 ── 科目ごとの節数と過去問の論点数の対応
lines=[]
for subj,files in MAP.items():
    if subj in ("労一","社一"): continue
    secs=sum(len(re.findall(r"^## ", BODY[f], re.M)) for f in files)
    qs=sum(1 for kai,v in M.items() for q in v["takuitsu"] if q["subject"]==subj)
    lines.append(f"{subj}：資料の節 {secs} ／ 過去問 {qs}問（1節あたり {qs/secs:.1f}問）")
rep(9,"資料の構成密度",lines,"1節あたりの過去問数が多い科目は、節の粒度が粗い可能性")

# 10 ── 未収録の重要制度（キーワード網羅）
MUST = {
 "01-労働基準法.md":["付加金","割増賃金","裁量労働","事業場外","変形労働時間","解雇予告","年次有給休暇","平均賃金","就業規則","労働者派遣"],
 "02-労働安全衛生法.md":["総括安全衛生管理者","作業主任者","特定機械等","健康診断","面接指導","ストレスチェック","元方事業者","計画の届出"],
 "03-労災保険法.md":["業務起因性","通勤災害","給付基礎日額","傷病補償年金","特別加入","第三者行為","メリット制","二次健康診断"],
 "04-雇用保険法.md":["被保険者期間","所定給付日数","基本手当日額","給付制限","高年齢求職者給付金","就職促進給付","教育訓練給付","育児休業給付"],
 "05-徴収法.md":["概算保険料","確定保険料","延納","メリット制","労働保険事務組合","印紙保険料","一括","賃金総額"],
 "06-労働一般常識.md":["労働契約法","無期転換","パート有期","派遣","育児介護休業","男女雇用機会均等","最低賃金","労働組合","高年齢者雇用","障害者雇用"],
 "07-社会保険一般常識.md":["社会保険労務士法","国民健康保険","後期高齢者","介護保険","確定拠出年金","確定給付企業年金","児童手当","社会保険審査"],
 "08-健康保険法.md":["標準報酬","任意継続","被扶養者","傷病手当金","出産手当金","高額療養費","保険外併用","埋葬料","日雇特例"],
 "09-国民年金法.md":["第1号被保険者","保険料免除","学生納付特例","老齢基礎年金","障害基礎年金","遺族基礎年金","寡婦年金","死亡一時金","付加年金","脱退一時金"],
 "10-厚生年金保険法.md":["標準報酬月額","老齢厚生年金","加給年金","在職老齢年金","障害厚生年金","遺族厚生年金","中高齢寡婦加算","離婚分割","脱退一時金","経過的加算"],
}
lines=[]
for f,ks in MUST.items():
    miss=[k for k in ks if NOSP(k) not in FLAT[f]]
    if miss: lines.append(f"{f}：{ '、'.join(miss) } が未収録")
rep(10,"科目の骨格をなす制度で未収録のもの",lines,"ここが抜けていると体系が崩れる")

print("\n"+"═"*74)
ng=[n for n,_,l in R if l and n not in INFO]
cnt=sum(len(l) for n,_,l in R if l and n not in INFO)
print(f" 要改善: {len(ng)}観点 / 指摘{cnt}件" + (f"（観点 {ng}）" if ng else "")
      + f"　※他5観点は統計の提示")
print("═"*74)
