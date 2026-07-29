#!/usr/bin/env python3
"""条文穴埋めを、法令そのもの（e-Gov）から作る。

選択式の原文だけでは300問にしかならなかったので、条文本体を素材にする。
法令は著作権の対象外（著作権法13条）なので、一次資料をそのまま使える。

やること
 1. e-Gov から取った法令XMLから「条・項」の本文を取り出す
 2. 過去問で参照された条文を優先する（出題実績のあるところから覚える）
 3. 語の切れ目で挟まれた語を1つ隠し、4択にする
 4. 誤答は、同じ法令の条文に出てくる同じ種類の語から採る
"""
import json, re, glob, os, random, collections
import xml.etree.ElementTree as ET

NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
OUT  = "../drill/data/anaume2.js"
LAWS = {
 # ── 択一の7科目 ──
 "322AC0000000049":"労働基準法", "347AC0000000057":"労働安全衛生法",
 "322AC0000000050":"労働者災害補償保険法", "349AC0000000116":"雇用保険法",
 "344AC0000000084":"労働保険徴収法", "211AC0000000070":"健康保険法",
 "329AC0000000115":"厚生年金保険法", "334AC0000000141":"国民年金法",
 # ── 労務管理その他の労働に関する一般常識（労一）──
 "419AC0000000128":"労働契約法", "324AC0000000174":"労働組合法",
 "321AC0000000025":"労働関係調整法", "334AC0000000137":"最低賃金法",
 "360AC0000000088":"労働者派遣法", "347AC0000000113":"男女雇用機会均等法",
 "403AC0000000076":"育児・介護休業法", "405AC0000000076":"パートタイム・有期雇用労働法",
 "346AC0000000068":"高年齢者雇用安定法", "335AC0000000123":"障害者雇用促進法",
 "322AC0000000141":"職業安定法", "341AC0000000132":"労働施策総合推進法",
 "413AC0000000112":"個別労働関係紛争解決促進法", "351AC0000000034":"賃金支払確保法",
 "345AC0000000060":"家内労働法", "344AC0000000064":"職業能力開発促進法",
 "404AC0000000090":"労働時間等設定改善法", "334AC0000000160":"中小企業退職金共済法",
 "416AC0000000045":"労働審判法",
 # ── 社会保険に関する一般常識（社一）──
 "333AC0000000192":"国民健康保険法", "409AC0000000123":"介護保険法",
 "357AC0000000080":"高齢者医療確保法", "343AC1000000089":"社会保険労務士法",
 "346AC0000000073":"児童手当法", "413AC0000000088":"確定拠出年金法",
 "413AC0000000050":"確定給付企業年金法", "314AC0000000073":"船員保険法",
 "328AC0000000206":"社会保険審査官及び社会保険審査会法",
 # ── 施行令・施行規則 ──
 # 本試験は「労働基準法施行規則第◯条」からも出る。分量が多いので、
 # 過去問で参照された条を優先して拾う（下の並べ替えで担保している）。
 "322M40000100023":"労働基準法施行規則", "347CO0000000318":"労働安全衛生法施行令",
 "347M50002000032":"労働安全衛生規則", "347M50002000036":"有機溶剤中毒予防規則",
 "347M50002000039":"特定化学物質障害予防規則", "347M50002000037":"鉛中毒予防規則",
 "354M50002000018":"粉じん障害防止規則", "417M60000100021":"石綿障害予防規則",
 "347M50002000041":"電離放射線障害防止規則", "347M50002000043":"事務所衛生基準規則",
 "330M50002000022":"労災保険法施行規則", "352CO0000000033":"労災保険法施行令",
 "350M50002000003":"雇用保険法施行規則", "350CO0000000025":"雇用保険法施行令",
 "347M50002000008":"労働保険徴収法施行規則", "347CO0000000046":"労働保険徴収法施行令",
 "215M10000008036":"健康保険法施行規則", "215IO0000000243":"健康保険法施行令",
 "329M50000100037":"厚生年金保険法施行規則", "329CO0000000110":"厚生年金保険法施行令",
 "335M50000100012":"国民年金法施行規則", "334CO0000000184":"国民年金法施行令",
 "343M50002100001":"社会保険労務士法施行規則", "411M50000100036":"介護保険法施行規則",
 "333M50000100053":"国民健康保険法施行規則",
}

# ── 過去問で参照された条文（出題実績のあるところを優先する）──
M = json.load(open("mondai.json"))
LAWRE = re.compile(r"(労働基準法|労働安全衛生法|労働者災害補償保険法|労災保険法|雇用保険法|"
                   r"労働保険徴収法|健康保険法|厚生年金保険法|国民年金法|労働契約法|労働組合法|"
                   r"労働関係調整法|最低賃金法|労働者派遣法|男女雇用機会均等法|育児・介護休業法|"
                   r"高年齢者雇用安定法|障害者雇用促進法|職業安定法|労働施策総合推進法|"
                   r"賃金支払確保法|家内労働法|職業能力開発促進法|中小企業退職金共済法|"
                   r"国民健康保険法|介護保険法|社会保険労務士法|児童手当法|確定拠出年金法|"
                   r"確定給付企業年金法|船員保険法|高齢者の医療の確保に関する法律|労働基準法施行規則|労働安全衛生法施行令|労働安全衛生規則|有機溶剤中毒予防規則|特定化学物質障害予防規則|鉛中毒予防規則|粉じん障害防止規則|石綿障害予防規則|電離放射線障害防止規則|事務所衛生基準規則|労働者災害補償保険法施行規則|雇用保険法施行規則|労働保険徴収法施行規則|健康保険法施行規則|厚生年金保険法施行規則|国民年金法施行規則)第?([0-9]{1,3})条")
CITED = collections.Counter()
for kai, v in M.items():
    for q in v["takuitsu"] + v["sentaku"]:
        t = NOSP(q.get("stem", "") + "".join(q.get("choices", []) if isinstance(q.get("choices"), list) and q.get("choices") and isinstance(q["choices"][0], str) else []) + q.get("body", ""))
        for m in LAWRE.finditer(t):
            law = m.group(1).replace("労働者災害補償保険法施行規則", "労災保険法施行規則") \
                            .replace("労災保険法", "労働者災害補償保険法") \
                            .replace("高齢者の医療の確保に関する法律", "高齢者医療確保法")
            CITED[(law, m.group(2))] += 1

# ── 条文を取り出す ────────────────────────────────
def art_label(num):
    """「115の45」を「第115条の45」と読める形にする。"""
    p = str(num).split("の")
    return "第" + p[0] + "条" + "".join("の" + x for x in p[1:])

def clean(s):
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"(?<=[぀-ヿ一-鿿、。」）])\s+(?=[぀-ヿ一-鿿「（])", "", s)
    return s.strip()

units = []          # {law, art, cap, text}
for p in sorted(glob.glob("hourei/*.xml")):
    lid = os.path.basename(p)[:-4]
    law = LAWS.get(lid)
    if not law: continue
    root = ET.parse(p).getroot()
    main = root.find(".//MainProvision")      # 附則・経過措置は対象外
    if main is None: continue
    for a in main.iter("Article"):
        # Num は「115_45」のように枝番を持つ。落とすと第115条の45が
        # 「第115条」と表示され、別の条文が同じ出典に見えてしまう。
        # Num は「115_45」のような枝番。そのまま「第115の45条」とすると
        # 条文の呼び方として不自然なので「第115条の45」に組み直す。
        raw = (a.get("Num") or "").split("_")
        num = raw[0] + "".join("の" + x for x in raw[1:])
        cap = clean(a.findtext("ArticleCaption") or "").strip("（）()")
        for para in a.findall("Paragraph"):
            # 号（Item）まで含めて連結すると、境界の語がくっついて
            #「法律三厚生年金保険」のような存在しない語ができる。
            # 項の本文（ParagraphSentence）だけを取る。
            ps = para.find("ParagraphSentence")
            if ps is None: continue
            txt = clean("".join(ps.itertext()))
            txt = re.sub(r"^[0-9０-９一二三四五六七八九十]+\s*", "", txt)   # 項番号を落とす
            if not (60 <= len(NOSP(txt)) <= 195): continue   # 秒で読める長さに収める
            if re.search(r"削除|附則|様式|別表|経過措置", txt) or re.search(r"経過措置", cap): continue
            units.append({"law": law, "art": num, "cap": cap, "text": txt,
                          "cited": CITED.get((law, num), 0)})

print(f"取り出した条文（項）: {len(units):,}件")
c = collections.Counter(u["law"] for u in units)
print("  " + " ".join(f"{k}{v}" for k, v in c.most_common()))
print(f"  うち過去問で参照された条: {sum(1 for u in units if u['cited']):,}件")

# ── 語彙を集める（誤答の素材）──────────────────────
def cat(w):
    t = NOSP(w)
    if re.fullmatch(r"[0-9０-９]+(年|月|日|週間|時間|歳|人|円|％|か月|分の[0-9]+)?", t): return "数値"
    if re.search(r"(大臣|署長|安定所長|局長|知事|機構|協会|組合|政府|市町村|審査会|審査官|委員会|事業主|保険者)$", t): return "主体"
    if re.search(r"(以内|以上|以下|未満|を超え)$", t): return "範囲"
    return "用語"

TERM = re.compile(r"[一-鿿ァ-ヴ]{2,12}(?:者|人|金|料|額|期間|日数|月数|給付|保険|事業|事業所|"
                  r"組合|大臣|署長|所長|局長|知事|機構|協会|委員会|審査会|審査官|届出|申請|認定|"
                  r"決定|通知|報告|命令|規則|規約|定款|承認|許可|認可|免除|猶予|徴収|納付|還付|"
                  r"控除|加算|減額|停止|喪失|取得|変更|継続|標準報酬|被保険者|受給権|受給資格)")
NUM  = re.compile(r"[0-9０-９]{1,4}(?:年|月|日|週間|時間|歳|人|円|％|か月)")
# 語彙は法令ごとに持つが、省令のように条数が少ないものは誤答が3つ作れない。
# 同じ分野の法令をひとまとめにした語彙も用意して、足りないときはそちらを使う。
GROUP = {}
for _l in ["労働安全衛生法","労働安全衛生規則","労働安全衛生法施行令","有機溶剤中毒予防規則",
           "特定化学物質障害予防規則","鉛中毒予防規則","粉じん障害防止規則","石綿障害予防規則",
           "電離放射線障害防止規則","事務所衛生基準規則"]: GROUP[_l] = "安衛"
for _l in ["労働基準法","労働基準法施行規則"]: GROUP[_l] = "労基"
for _l in ["労働者災害補償保険法","労災保険法施行規則","労災保険法施行令",
           "労働保険徴収法","労働保険徴収法施行規則","労働保険徴収法施行令"]: GROUP[_l] = "労災徴収"
for _l in ["雇用保険法","雇用保険法施行規則","雇用保険法施行令"]: GROUP[_l] = "雇用"
for _l in ["健康保険法","健康保険法施行規則","健康保険法施行令","船員保険法"]: GROUP[_l] = "健保"
for _l in ["厚生年金保険法","厚生年金保険法施行規則","厚生年金保険法施行令",
           "国民年金法","国民年金法施行規則","国民年金法施行令"]: GROUP[_l] = "年金"
vocab = collections.defaultdict(collections.Counter)
gvocab = collections.defaultdict(collections.Counter)
for u in units:
    for m in list(TERM.finditer(u["text"])) + list(NUM.finditer(u["text"])):
        w = m.group()
        # 「二　内閣総理大臣」が連結されて「二内閣総理大臣」になることがある。
        # 号番号や接続語が頭に付いた断片は語として扱わない。
        if re.match(r"^(一|二|三|四|五|六|七|八|九|十|他|又|及|若|前|同|当該|この|その)(?=[一-鿿]{2})", w):
            continue
        if 2 <= len(NOSP(w)) <= 14:
            vocab[u["law"]][w] += 1
            gvocab[GROUP.get(u["law"], u["law"])][w] += 1

EDGE = "、。，．「」『』（）()［］〔〕・：；\n はがのにをでともへやから"
def standalone(t, p, w):
    b = t[p-1] if p > 0 else "。"
    a = t[p+len(w)] if p+len(w) < len(t) else "。"
    ok = lambda ch: ch in EDGE or re.match(r"[ぁ-ん\s]", ch)
    return ok(b) and ok(a)

# 金額は政令や告示で改定される。e-Gov は現在施行の内容を返すので、
# 試験の法令基準日（令和8年4月10日）とずれる可能性がある。
# 数値の暗記は検証済みの資料（91-数値暗記）に任せ、ここでは答えにしない。
MONEY = re.compile(r"[0-9０-９，,]+\s*円|[0-9０-９]+\s*万円|[0-9０-９]+分の[0-9０-９]+|"
                   r"千分の[0-9０-９]+|[0-9０-９]+(?:\.[0-9])?\s*パーセント|[0-9０-９]+\s*％")

def unit_of(w):
    m = re.search(r"(年|か月|月|週間|日|時間|歳|人|円|％)$", NOSP(w))
    return m.group(1) if m else ""

# 法令ごとの上限。省令は条数が多く、機械の構造基準のような
# 試験に出ない細部まで拾ってしまう。過去問での参照実績に応じて配分する。
ans_use = collections.Counter()      # 同じ語ばかり正答になるのを防ぐ
cited_by_law = collections.Counter()
for u in units:
    if u["cited"]: cited_by_law[u["law"]] += 1
CORE = {"労働基準法","労働安全衛生法","労働者災害補償保険法","雇用保険法","労働保険徴収法",
        "健康保険法","厚生年金保険法","国民年金法"}
def cap_of(law):
    """本試験の比重に合わせる。択一は7科目×10問なので、その本体を厚くする。
    一般常識の個別法と施行令・規則は薄くてよい。"""
    base = max(30, min(260, cited_by_law[law] * 5))
    if law in CORE: return int(base * 1.8)
    # 有機則・特化則などは作業環境測定や作業主任者で頻出するので薄くしすぎない
    ANEI = ("有機溶剤","特定化学物質","鉛中毒","粉じん","石綿","電離放射線","事務所衛生")
    if any(k in law for k in ANEI): return max(35, int(base * 0.9))
    if "規則" in law or "施行令" in law: return max(25, int(base * 0.6))
    return max(25, int(base * 0.6))

random.seed(20260823)
qs, seen = [], set()
combo_seen = collections.defaultdict(set)
made_by_law = collections.Counter()
# 出題実績のある条文から先に作る
units.sort(key=lambda u: -u["cited"])
for u in units:
    t = u["text"]
    words = [m.group() for m in list(TERM.finditer(t)) + list(NUM.finditer(t))]
    words = [w for w in dict.fromkeys(words)
             if 2 <= len(NOSP(w)) <= 14 and t.count(w) == 1
             and not re.match(r"^(一|二|三|四|五|六|七|八|九|十|他|又|及|若|前|同|当該|この|その)(?=[一-鿿]{2})", w)
             and not MONEY.search(NOSP(w))]
    random.shuffle(words)
    if made_by_law[u["law"]] >= cap_of(u["law"]): continue
    made = 0
    for w in words:
        if made >= (3 if u["cited"] else 1): break
        if made_by_law[u["law"]] >= cap_of(u["law"]): break
        key = (u["law"], u["art"], NOSP(w))
        if key in seen: continue
        p = t.index(w)
        if not standalone(t, p, w): continue
        c, uu, L = cat(w), unit_of(w), len(NOSP(w))
        pick_from = lambda src: [x for x in src
                if x != w and cat(x) == c and unit_of(x) == uu
                and NOSP(x) not in NOSP(w) and NOSP(w) not in NOSP(x)
                and x not in t and max(2, L//3) <= len(NOSP(x)) <= max(L*3, L+8)]
        alts = pick_from(vocab[u["law"]])
        if len(alts) < 3:                       # 省令など語彙が薄い法令は同じ分野から借りる
            alts = pick_from(gvocab[GROUP.get(u["law"], u["law"])])
        if len(alts) < 3: continue
        # 「厚生労働大臣」が何百回も正答になると、条文を読まずに当てられる
        if ans_use[NOSP(w)] >= 25: continue
        alts.sort(key=lambda x: (abs(len(NOSP(x)) - L), -gvocab[GROUP.get(u["law"], u["law"])][x]))
        band = alts[:max(10, len(alts)//4)]
        random.shuffle(band)
        ch = band[:3] + [w]
        if len({NOSP(x) for x in ch}) < 4: continue
        sig = tuple(sorted(NOSP(x) for x in ch))
        if sig in combo_seen[u["law"]]: continue
        combo_seen[u["law"]].add(sig)
        random.shuffle(ch)
        seen.add(key); made += 1; made_by_law[u["law"]] += 1; ans_use[NOSP(w)] += 1
        qs.append({"type":"ana", "law":u["law"],
                   "head":t[:p], "tail":t[p+len(w):],
                   "choices":ch, "a":ch.index(w), "cat":c,
                   "real": u["cited"] > 0,
                   "src": f'{u["law"]}{art_label(u["art"])}',
                   "cap": u["cap"],
                   # 間違えたときに何を確認すればよいかを1行で示す
                   "exp": f'**{w}** が正しい。{u["law"]}{art_label(u["art"])}'
                          + (f'（{u["cap"]}）' if u["cap"] else "") + "の文言です。"
                          + ("この条文は過去問で参照されています。" if u["cited"] else "")})     # 見出しは答えたあとに見せる（正答が入っていることがある）

random.shuffle(qs)
qs.sort(key=lambda q: not q["real"])
with open(OUT, "w") as f:
    f.write('/* 条文穴埋め（法令本体）\n'
            ' * e-Gov の法令データから条・項を取り出し、1語を隠したもの。\n'
            ' * 法令は著作権の対象外（著作権法13条）。kakomon/gen_anaume2.py が生成。\n */\n')
    f.write('DRILL.register("条文穴埋め", ' +
            json.dumps(qs, ensure_ascii=False, separators=(",", ":")) + ');\n')
print(f"\n→ {OUT}  {len(qs):,}問")
print(f"   過去問で参照された条から: {sum(1 for q in qs if q['real']):,}問")
print("   " + " ".join(f"{k}{v}" for k, v in collections.Counter(q["law"] for q in qs).most_common()))
