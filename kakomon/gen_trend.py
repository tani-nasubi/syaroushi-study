#!/usr/bin/env python3
"""過去問9年分から抽出した出題傾向を、各科目ノートの冒頭に「出題傾向」節として挿入する。
すでに挿入済みの場合は最新の内容で置き換える。"""
import json, re, collections, os

MONDAI = json.load(open("mondai.json"))
SEITOU = json.load(open("seitou.json"))
NOTES = "../notes"
KAI2Y = {57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",
         52:"令和2",51:"令和元",50:"平成30",49:"平成29"}
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))

def qtype(stem):
    s = NOSP(stem)
    if "いくつあるか" in s: return "個数問題"
    if "組合せ" in s: return "組合せ問題"
    if re.search(r"誤っているもの|誤りである", s): return "誤りを選ぶ"
    if re.search(r"正しいもの|適切なもの", s): return "正しいものを選ぶ"
    return "その他"

LAW = re.compile(r"(労働基準法|労働安全衛生法|労働者災害補償保険法|労災保険法|雇用保険法|"
                 r"労働保険の保険料の徴収等に関する法律|労働保険徴収法|健康保険法|厚生年金保険法|"
                 r"国民年金法|介護保険法|国民健康保険法|社会保険労務士法|労働契約法|労働組合法|"
                 r"最低賃金法|労働者派遣法|確定拠出年金法)(?:施行規則)?(?:第([0-9]{1,3})条)?")

D = collections.defaultdict(lambda: {"t":collections.Counter(),"a":collections.Counter(),"s":[],
                                     "y":collections.defaultdict(collections.Counter)})
for kai, v in MONDAI.items():
    k = int(kai)
    for q in v["takuitsu"]:
        d = D[q["subject"]]
        d["t"][qtype(q["stem"])] += 1
        # 年度別の設問形式（傾向の推移を見るため）
        y = d["y"][k]; y[qtype(q["stem"])] += 1; y["問数"] += 1
        y["字数計"] += sum(len(NOSP(c)) for c in q["choices"])
        y["肢数"]  += len(q["choices"])
        if re.search(r"最高裁判所|判示|判例", NOSP(q["stem"] + "".join(q["choices"]))): y["判例"] += 1
        for m in LAW.finditer(NOSP(q["stem"] + "".join(q["choices"]))):
            if m.group(2): d["a"][f"{m.group(1)}{m.group(2)}条"] += 1
    for q in v["sentaku"]:
        d = D[q["subject"]]
        body = NOSP(q["body"])
        laws = sorted({f"{m.group(1)}{m.group(2)}条" for m in LAW.finditer(body) if m.group(2)})
        raw = SEITOU[kai]["sentaku"][q["subject"]]
        ws = []
        for i, a in enumerate(raw):
            a = a[0] if isinstance(a, list) else a
            if a is None: continue
            w = (q["choices"][a-1] if q["format"]=="pool20"
                 else (q["choices"][i][a-1] if a-1 < len(q["choices"][i]) else ""))
            if w: ws.append(re.sub(r"\s+", " ", w).strip())
        d["s"].append((k, laws[:3], ws))

# ノート → (択一の集計に使う科目, 選択式に使う科目, 条文の絞り込み)
TARGET = {
 "01-労働基準法.md":       (["労基安衛"], ["労基安衛"], "労働基準法"),
 "02-労働安全衛生法.md":   (["労基安衛"], ["労基安衛"], "労働安全衛生法"),
 "03-労災保険法.md":       (["労災"],     ["労災"],     "労災保険法"),
 "04-雇用保険法.md":       (["雇用"],     ["雇用"],     "雇用保険法"),
 "05-徴収法.md":           (["労災","雇用"], [],        "労働保険徴収法"),
 "06-労働一般常識.md":     (["一般常識"], ["労一"],     None),
 "07-社会保険一般常識.md": (["一般常識"], ["社一"],     None),
 "08-健康保険法.md":       (["健保"],     ["健保"],     "健康保険法"),
 "09-国民年金法.md":       (["国年"],     ["国年"],     "国民年金法"),
 "10-厚生年金保険法.md":   (["厚年"],     ["厚年"],     "厚生年金保険法"),
}

# ── 基準点補正（合格基準PDFの「ただし〜点以上」から抽出）
KIJUN = json.load(open("kijun.json"))
KIJUN = {int(k): v for k, v in KIJUN.items()}

def shift_table(subs):
    """年度別の設問形式の推移。作問方針が変わったかを見る。"""
    ys = collections.defaultdict(collections.Counter)
    for s in subs:
        for k, c in D[s]["y"].items(): ys[k].update(c)
    if not ys: return [], None
    rows = ["| 年度 | 個数・組合せ | 誤りを選ぶ | 正しいものを選ぶ | 肢の平均字数 | 判例に言及 |",
            "|---|---:|---:|---:|---:|---:|"]
    for k in sorted(ys, reverse=True):
        c = ys[k]; ko = c["個数問題"] + c["組合せ問題"]
        rows.append(f"| {KAI2Y[k]} | {ko} | {c['誤りを選ぶ']} | {c['正しいものを選ぶ']} | "
                    f"{c['字数計']/max(c['肢数'],1):.0f} | {c['判例']} |")
    # 前期（第49〜53回）と後期（第54〜57回）の平均を比べる
    def avg(keys, f):
        cs = [ys[k] for k in keys if k in ys]
        return sum(f(c) for c in cs) / max(len(cs), 1)
    old, new = range(49, 54), range(54, 58)
    g = lambda ks, key: avg(ks, lambda c: c[key])
    d = {"個数": (g(old,"個数問題")+g(old,"組合せ問題"), g(new,"個数問題")+g(new,"組合せ問題")),
         "正": (g(old,"正しいものを選ぶ"), g(new,"正しいものを選ぶ")),
         "判例": (g(old,"判例"), g(new,"判例")),
         "字数": (avg(old, lambda c: c["字数計"]/max(c["肢数"],1)),
                  avg(new, lambda c: c["字数計"]/max(c["肢数"],1)))}
    msg = []
    if d["個数"][1] - d["個数"][0] >= .8:
        msg.append(f"**個数・組合せ問題が増えています**（前期 平均{d['個数'][0]:.1f}問 → 直近4年 平均{d['個数'][1]:.1f}問）。"
                   "全肢の判断が必要なので、1問あたりの時間が伸びます")
    elif d["個数"][0] - d["個数"][1] >= .8:
        msg.append(f"個数・組合せ問題は減っています（前期 平均{d['個数'][0]:.1f}問 → 直近4年 平均{d['個数'][1]:.1f}問）")
    if d["正"][1] - d["正"][0] >= 1:
        msg.append(f"**「正しいものを選べ」が増えています**（{d['正'][0]:.1f}問 → {d['正'][1]:.1f}問）。"
                   "誤りを探すより、**正しい形を知っているか**が問われる方向です")
    if d["判例"][1] - d["判例"][0] >= .5:
        msg.append(f"**判例への言及が増えています**（{d['判例'][0]:.1f}問 → {d['判例'][1]:.1f}問）")
    if d["字数"][0] - d["字数"][1] >= 5:
        msg.append(f"肢が短くなっています（平均{d['字数'][0]:.0f}字 → {d['字数'][1]:.0f}字）")
    return rows, msg

def kijun_lines(sel_subj, tak_subj):
    """この科目で基準点が下がった年。＝救済が期待できるかどうか。"""
    sel = [(k, v["sel"][sel_subj]) for k, v in sorted(KIJUN.items(), reverse=True)
           if sel_subj and sel_subj in v["sel"]]
    tak = [(k, v["tak"][tak_subj]) for k, v in sorted(KIJUN.items(), reverse=True)
           if tak_subj and tak_subj in v["tak"]]
    out = ["### 基準点補正の履歴（この科目が救済された年）", ""]
    if sel:
        out.append("**選択式**　" + "／".join(f"{KAI2Y[k]}年度 **{p}点**に引下げ" for k, p in sel))
    else:
        out.append("**選択式**　過去9年で**一度も引下げなし**")
    if tak:
        out.append("")
        out.append("**択一式**　" + "／".join(f"{KAI2Y[k]}年度 **{p}点**に引下げ" for k, p in tak))
    out.append("")
    n = len(sel)
    if n >= 3:
        out.append(f"> 選択式は9年で**{n}回**引下げられています。難問が出れば救済される可能性はありますが、"
                   "**救済を前提にした学習計画は組めません**。3点は自力で取る前提で。")
    elif n >= 1:
        out.append(f"> 選択式の引下げは9年で{n}回。**例外的**です。基準点は自力で超える前提で臨んでください。")
    else:
        out.append("> **選択式は一度も救済されていません。** ここで3点を割ると、"
                   "他がどれだけ良くてもその時点で不合格です。**取りこぼせない科目**です。"
                   + ("択一も引下げは1回だけです。" if tak else ""))
    out.append("")
    return out
BEGIN, END = "<!-- TREND:BEGIN -->", "<!-- TREND:END -->"

for f, (tsubs, ssubs, lawfilter) in TARGET.items():
    types = collections.Counter(); arts = collections.Counter()
    for s in tsubs:
        types.update(D[s]["t"]); arts.update(D[s]["a"])
    if lawfilter:
        arts = collections.Counter({a:c for a,c in arts.items() if a.startswith(lawfilter)})
    tot = sum(types.values())

    out = [BEGIN, "## 出題傾向（過去9年・第49〜57回の実データ）", ""]
    if tot:
        out += ["### 択一の設問形式", "", "| 形式 | 問数 | 割合 |", "|---|---:|---:|"]
        for t, c in types.most_common():
            out.append(f"| {t} | {c} | {c/tot*100:.0f}% |")
        kosuu = types.get("個数問題",0); kumi = types.get("組合せ問題",0); ko = kosuu + kumi
        out += ["", f"**{tsubs[0] if len(tsubs)==1 else '労災・雇用'}枠 計{tot}問**のうち、"
                    f"**個数問題{kosuu}問・組合せ問題{kumi}問（合わせて{ko/tot*100:.0f}%）**。"
                    + (f"組合せのほうが多い科目です。組合せは**2肢の正誤が分かれば99%正解が決まる**ので、"
                       "時間はかかりません。飛ばす候補は個数問題だけです。"
                       if kumi > kosuu else
                       f"個数問題が多い科目です。個数は**5肢すべての判断が必要**で時間を食います。"
                       "2肢以上分からなければ飛ばしてください。")
                    + "（→ [`A1-個数・組合せ問題の解き方.md`](A1-個数・組合せ問題の解き方.md)）", ""]
    # ── 年度別の推移（作問方針が変わったか）
    rows, msg = shift_table(tsubs)
    if rows:
        out += ["### 設問形式の推移（作問方針の変化）", ""] + rows + [""]
        out += [("\n".join("- " + m for m in msg) if msg
                 else "- 9年を通じて設問形式に大きな変化はありません。過去問の解き方がそのまま通用します。"), ""]

    # ── 基準点補正（救済が期待できる科目か）
    SEL_OF = {"01":"労基安衛","02":"労基安衛","03":"労災","04":"雇用",
              "06":"労一","07":"社一","08":"健保","09":"国年","10":"厚年"}
    TAK_OF = {"01":"労基安衛","02":"労基安衛","03":"労災","04":"雇用",
              "06":"一般常識","07":"一般常識","08":"健保","09":"国年","10":"厚年"}
    pre = f[:2]
    if pre in SEL_OF:
        out += kijun_lines(SEL_OF[pre], TAK_OF[pre])
    elif pre == "05":
        out += ["### 基準点補正の履歴", "",
                "徴収法は独立した科目ではなく、**労災の択一10問中3問・雇用の択一10問中3問**として出題されます。",
                "したがって徴収法単独の基準点はなく、労災・雇用の基準点に組み込まれます。", "",
                "> 択一で**計6問**＝全70問の**9%**。ここは条文数が少なく得点しやすいので、"
                "**6問中5問**を目標にしてください。労災・雇用の基準点割れを防ぐ最大の保険になります。", ""]

    if arts:
        out += ["### 頻出条文（択一で参照された回数）", "",
                "　".join(f"**{a}**({c})" for a, c in arts.most_common(10)), ""]
    for s in ssubs:
        if not D[s]["s"]: continue
        out += [f"### 選択式が9年間で問うたこと（{s}）", "",
                "| 年度 | 根拠条文 | 正答となった語 |", "|---|---|---|"]
        for k, laws, ws in sorted(D[s]["s"], reverse=True):
            out.append(f"| {KAI2Y[k]} | {'／'.join(laws) if laws else '—'} | "
                       + " ／ ".join(w[:20] for w in ws) + " |")
        out.append("")
    out += ["> この節は `kakomon/gen_trend.py` が過去問データから自動生成しています。", END, ""]

    body = open(f"{NOTES}/{f}").read()
    block = "\n".join(out)
    if BEGIN in body:
        body = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", block, body, flags=re.S)
    else:
        i = body.index("\n---\n")          # 冒頭の説明表の直後に差し込む
        body = body[:i+5] + "\n" + block + body[i+5:]
    open(f"{NOTES}/{f}", "w").write(body)
    print(f"{f:26s} 択一{tot:3d}問 / 条文{len(arts):2d}種 / 選択式{sum(len(D[s]['s']) for s in ssubs)}年分")
