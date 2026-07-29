#!/usr/bin/env python3
"""条文穴埋めドリルを作る。

選択式の本文（＝条文や判示の原文）に正答を埋め戻したものを素材にして、
そのうちの1語を隠し、4択で当てさせる。同じ条文でも隠す箇所は毎回変わる。

素材の性質
 ・条文そのものは著作権の対象外（著作権法13条）
 ・誤答は「本試験で実際に語群に並んだ語」から採る。もっともらしい誤答になる
 ・隠す語は、本試験で実際に空欄にされた語を優先する（重要度が実証されている）
"""
import json, re, collections, random

M = json.load(open("mondai.json")); S = json.load(open("seitou.json"))
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
KAI2Y = {57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",
         52:"令和2",51:"令和元",50:"平成30",49:"平成29"}
# 条文の穴埋めなので、試験の科目枠ではなく「どの法律の条文か」で分ける。
# 同じ労基安衛枠でも労働基準法と労働安全衛生法は別物なので、そこを分けたい。
LAWS = ["労働基準法","労働安全衛生法","労働者災害補償保険法","労働保険の保険料の徴収等に関する法律",
        "雇用保険法","健康保険法","厚生年金保険法","国民年金法","労働契約法","労働組合法",
        "労働関係調整法","最低賃金法","労働者派遣法","社会保険労務士法","介護保険法",
        "国民健康保険法","高齢者の医療の確保に関する法律","確定拠出年金法","確定給付企業年金法",
        "船員保険法","児童手当法","男女雇用機会均等法","育児・介護休業法","高年齢者等の雇用の安定等に関する法律"]
SHORT = {"労働保険の保険料の徴収等に関する法律":"労働保険徴収法",
         "高齢者の医療の確保に関する法律":"高齢者医療確保法",
         "高年齢者等の雇用の安定等に関する法律":"高年齢者雇用安定法"}
FALLBACK = {"労基安衛":"労働基準法","労災":"労働者災害補償保険法","雇用":"雇用保険法",
            "労一":"労働一般常識","社一":"社会保険一般常識","健保":"健康保険法",
            "厚年":"厚生年金保険法","国年":"国民年金法"}
def law_of(text, subj):
    """文中で引用している法令名を見出しにする。無ければ科目から補う。"""
    hits = [(text.index(L), L) for L in LAWS if L in text]
    if hits:
        L = min(hits)[1]
        return SHORT.get(L, L)
    return FALLBACK.get(subj, subj)
OUT = "../drill/data/anaume.js"

# ── 素材を組み立てる ─────────────────────────────
bodies, pool = [], collections.Counter()
real_answers = set()                     # 本試験で実際に空欄だった語
for kai, v in M.items():
    for q in v["sentaku"]:
        raw = S[kai]["sentaku"][q["subject"]]
        ws = []
        for i, a in enumerate(raw):
            a0 = a[0] if isinstance(a, list) else a
            if a0 is None: ws.append(None); continue
            w = (q["choices"][a0-1] if q["format"] == "pool20"
                 else (q["choices"][i][a0-1] if a0-1 < len(q["choices"][i]) else ""))
            ws.append(re.sub(r"\s+", " ", w).strip() if w else None)
        body = q["body"]
        for i, w in enumerate(ws):
            if w: body = body.replace(f"【{'ABCDE'[i]}】", w)
        bodies.append({"kai": int(kai), "subj": q["subject"], "text": body})
        real_answers.update(w for w in ws if w)
        groups = [q["choices"]] if q["format"] == "pool20" else q["choices"]
        for g in groups:
            for c in g: pool[re.sub(r"\s+", " ", c).strip()] += 1

# ── 語の種類。誤答は同じ種類から選ぶ ───────────────
def cat(w):
    t = NOSP(w)
    if re.fullmatch(r"[0-9０-９]+(\.[0-9]+)?(年|月|日|週間|時間|歳|人|円|％|か月|箇月|分の[0-9]+)?", t): return "数値"
    if re.search(r"(大臣|署長|安定所長|局長|知事|機構|協会|組合|政府|市町村|審査会|審査官|委員会)$", t): return "主体"
    if re.search(r"(以内|以上|以下|未満|を超え)$", t): return "範囲"
    if re.search(r"(なければならない|することができる|するものとする|してはならない)$", t): return "語尾"
    return "用語"

BY_CAT = collections.defaultdict(list)
for w in pool: BY_CAT[cat(w)].append(w)

# ── 使わない素材（年度で変わるもの・法改正で変わったもの）────
SKIP = re.compile(r"白書|によれば|調査によると|完全失業率|有効求人倍率|就業者数|"
                  r"支給停止調整額|保険料率|平均標準報酬")

random.seed(20260823)

# 語の切れ目。ここで挟まれていない語を隠すと、複合語の一部を隠すことになり
#（「［？］労働大臣」のように）残りを見れば答えが分かってしまう。
EDGE = "、。，．「」『』（）()［］〔〕・：；\n はがのにをでともへやから より また ただし"
def standalone(t, p, w):
    before = t[p-1] if p > 0 else "。"
    after  = t[p+len(w)] if p+len(w) < len(t) else "。"
    ok = lambda ch: ch in EDGE or re.match(r"[ぁ-ん\s]", ch)
    return ok(before) and ok(after)

# 数値は「単位が本文に残るか」で形をそろえる。
# 「［？］日以内」の空欄に「4 か月」を並べると、読まずに消せてしまう。
def unit_of(w):
    m = re.search(r"(年|か月|箇月|月|週間|日|時間|歳|人|円|％|分の[0-9]+)$", NOSP(w))
    return m.group(1) if m else ""

qs, seen = [], set()
for b in bodies:
    if SKIP.search(b["text"]): continue
    t = b["text"]
    cands = [w for w in pool
             if len(NOSP(w)) >= 2 and t.count(w) == 1 and not re.fullmatch(r"[0-9０-９]", NOSP(w))]
    cands.sort(key=lambda w: (w not in real_answers, -len(NOSP(w))))
    for w in cands[:16]:
        key = (b["kai"], b["subj"], NOSP(w))
        if key in seen: continue
        p = t.index(w)
        if not standalone(t, p, w): continue          # 複合語の一部は隠さない

        c, u, L = cat(w), unit_of(w), len(NOSP(w))
        alts = [x for x in BY_CAT[c]
                if x != w and NOSP(x) not in NOSP(w) and NOSP(w) not in NOSP(x)
                and x not in t and unit_of(x) == u]    # 単位の形をそろえる
        if len(alts) < 3: continue
        # 長さの近いものを優先する（長さで当てられないように）
        # 長さで当てられないよう、正答と極端に離れたものは外す
        alts = [x for x in alts if len(NOSP(x)) <= max(L*3, L+8) and len(NOSP(x)) >= max(2, L//3)]
        if len(alts) < 3: continue
        alts.sort(key=lambda x: abs(len(NOSP(x)) - L))
        band = alts[:max(8, len(alts)//3)]
        random.shuffle(band)
        choices = band[:3] + [w]
        if len({NOSP(x) for x in choices}) < 4: continue
        random.shuffle(choices)
        seen.add(key)

        # 「秒」で答えるモードなので、前後を長く出さない。
        # 空欄を含む一文だけを切り出す（短すぎるときだけ前の文をひとつ足す）。
        def sentence_span(t, p, end):
            s = t.rfind("。", 0, p)
            s = 0 if s < 0 else s + 1
            e = t.find("。", end)
            e = len(t) if e < 0 else e + 1
            if e - s < 46:                       # 短すぎるときは前の文を足す
                s2 = t.rfind("。", 0, max(0, s - 1))
                s = 0 if s2 < 0 else s2 + 1
            return s, e
        s0, s1 = sentence_span(t, p, p + len(w))
        if s1 - s0 > 190: continue               # 一文が長すぎるものは出さない
        head = t[s0:p].lstrip("\n 　")
        tail = t[p+len(w):s1]

        qs.append({
            "type": "ana", "law": law_of(head + w + tail, b["subj"]),
            "head": head.strip(), "tail": tail.strip(),
            "choices": choices, "a": choices.index(w), "cat": c,
            "real": w in real_answers,
            "src": f'{KAI2Y[b["kai"]]}年度 {b["subj"]} 選択式',
        })

random.shuffle(qs)
# 本試験で実際に空欄だった語を前に出す
qs.sort(key=lambda q: not q["real"])

with open(OUT, "w") as f:
    f.write('/* 条文穴埋め（速答）\n'
            ' * 選択式の本文＝条文・判示の原文に正答を埋め戻し、その1語を隠したもの。\n'
            ' * 誤答は本試験で実際に語群へ並んだ語から採っている。\n'
            ' * kakomon/gen_anaume.py が生成。\n */\n')
    f.write('DRILL.register("条文穴埋め", ' +
            json.dumps(qs, ensure_ascii=False, separators=(",", ":")) + ');\n')

print(f"→ {OUT}  {len(qs):,}問")
print(f"   本試験で実際に空欄だった語: {sum(1 for q in qs if q['real'])}問")
c = collections.Counter(q["cat"] for q in qs)
print("   隠した語の種類:", dict(c.most_common()))
s = collections.Counter(q["law"] for q in qs)
print("   科目:", " ".join(f"{k}{v}" for k, v in s.most_common()))
