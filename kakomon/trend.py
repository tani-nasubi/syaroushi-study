#!/usr/bin/env python3
"""過去問9年分から科目ごとの出題傾向を抽出し、ノートに貼れる形で出力する。

抽出するもの
  ・択一の設問形式の内訳（正誤／個数問題／組合せ問題）… 解答時間の配分に直結する
  ・頻出条文ランキング
  ・選択式が9年間で何を問うたか（年度 → 根拠条文・テーマ）
"""
import json, re, collections

MONDAI = json.load(open("mondai.json"))
SEITOU = json.load(open("seitou.json"))
KAI2Y = {57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",
         52:"令和2",51:"令和元",50:"平成30",49:"平成29"}
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))

# 設問形式の判定
def qtype(stem):
    s = NOSP(stem)
    if re.search(r"いくつあるか", s):            return "個数"
    if re.search(r"組合せ", s):                  return "組合せ"
    if re.search(r"誤っているもの|誤りである", s): return "誤り選び"
    if re.search(r"正しいもの|適切なもの", s):    return "正しい選び"
    return "その他"

LAW = re.compile(r"(労働基準法|労働安全衛生法|労働者災害補償保険法|労災保険法|雇用保険法|"
                 r"労働保険の保険料の徴収等に関する法律|労働保険徴収法|健康保険法|"
                 r"厚生年金保険法|国民年金法|介護保険法|国民健康保険法|社会保険労務士法|"
                 r"労働契約法|労働組合法|最低賃金法|育児・介護休業法|男女雇用機会均等法|"
                 r"労働者派遣法|高齢者の医療の確保に関する法律|確定拠出年金法)"
                 r"(?:施行規則)?(?:第([0-9]{1,3})条)?")

res = collections.defaultdict(lambda: {"types":collections.Counter(),
                                       "arts":collections.Counter(),
                                       "sel":[]})
for kai, v in MONDAI.items():
    k = int(kai)
    for q in v["takuitsu"]:
        r = res[q["subject"]]
        r["types"][qtype(q["stem"])] += 1
        for m in LAW.finditer(NOSP(q["stem"] + "".join(q["choices"]))):
            if m.group(2): r["arts"][f"{m.group(1)}{m.group(2)}条"] += 1
    for q in v["sentaku"]:
        r = res[q["subject"]]
        body = NOSP(q["body"])
        laws = [f"{m.group(1)}{m.group(2)}条" for m in LAW.finditer(body) if m.group(2)]
        # その回の正答語（テーマの手がかり）
        raw = SEITOU[kai]["sentaku"][q["subject"]]
        words = []
        for i, a in enumerate(raw):
            a = a[0] if isinstance(a, list) else a
            if a is None: continue
            w = (q["choices"][a-1] if q["format"]=="pool20"
                 else (q["choices"][i][a-1] if a-1 < len(q["choices"][i]) else ""))
            if w: words.append(re.sub(r"\s+"," ",w).strip()[:14])
        r["sel"].append((k, sorted(set(laws))[:3], words))

ORDER = ["労基安衛","労災","雇用","一般常識","労一","社一","健保","厚年","国年"]
for subj in ORDER:
    if subj not in res: continue
    r = res[subj]
    print("\n" + "="*70)
    print(f"■ {subj}")
    tot = sum(r["types"].values())
    if tot:
        print(f"\n【択一の設問形式】（9年 {tot}問）")
        for t,c in r["types"].most_common():
            print(f"   {t:<6} {c:3d}問 ({c/tot*100:4.1f}%)  " + "▉"*round(c/tot*40))
    if r["arts"]:
        print(f"\n【頻出条文 top10】")
        for a,c in r["arts"].most_common(10):
            print(f"   {a:<22} {c}回")
    if r["sel"]:
        print(f"\n【選択式が問うたもの（9年）】")
        for k, laws, words in sorted(r["sel"], reverse=True):
            print(f"   {KAI2Y[k]}年度 {'／'.join(laws) if laws else '（条文明示なし）'}")
            print(f"        正答: {' / '.join(words)}")
