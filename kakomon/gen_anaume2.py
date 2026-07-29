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
M = json.load(open("mondai.json")); S = json.load(open("seitou.json"))
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
def order_key(num):
    """「115の45」を (115, 45) のような組にして、条文の順に並べられるようにする。"""
    return tuple(int(x) if x.isdigit() else 0 for x in str(num).split("の"))

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
    # 条がどの章に属するかを控える。条文は前後のつながりで意味が決まるので、
    # 「いまどのあたりの話か」が分からないと真ん中だけ抜かれて意味を成さない。
    chap_of = {}
    for ch in main.findall(".//Chapter"):
        ct = clean(ch.findtext("ChapterTitle") or "")
        for a in ch.iter("Article"): chap_of[id(a)] = ct
    for a in main.iter("Article"):
        chap = chap_of.get(id(a), "")
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
            # 労基法4条（男女同一賃金）48字、6条（中間搾取の排除）44字のように、
            # 短くても頻出の条文がある。下限を下げて取りこぼさないようにする。
            if not (34 <= len(NOSP(txt)) <= 195): continue
            if re.search(r"削除|附則|様式|別表|経過措置", txt) or re.search(r"経過措置", cap): continue
            units.append({"law": law, "art": num, "cap": cap, "text": txt,
                          "chap": chap, "order": order_key(num),
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

# 語の抽出。以前は「者・金・料…」で終わる語に限っていたため、
# 「労働条件」「労働契約」「利益」のような基本的な語を取りこぼしていた。
# 漢字・カタカナの連なりを広く拾い、語として切り出せるか（前後が助詞や句読点か）は
# あとの standalone で判定する。
TERM = re.compile(r"[一-鿿ァ-ヴー]{2,12}")
# 「就業規則及び」の「及」のように、接続詞の頭の一字を巻き込むことがある。
# その一字を落としてから語として扱う。落とすと2字未満になるものは捨てる。
TAIL_CUT = re.compile(r"(及|又|若|並|且|かつ|及び|又は)$")
HEAD_CUT = re.compile(r"^(及|又|若|並|且|同|前|当|各|其|この|その)")
# 「第三項中」「項第二号」のように、条項の指し示しを切り取った断片は語ではない。
# 「第三項中」「項第二号」「政法人法」のように、条項の指し示しや
# 固有名詞の途中を切り取った断片は語ではない。
REFFRAG = re.compile(r"[条項号款章節]|[一二三四五六七八九十百千]")
LEADFRAG = re.compile(r"^(政|独立行|行政法|法人|等|該|記|掲|至|係|基|定|得|受|有|要)(?=[一-鿿]{2})")
def norm_term(w):
    w = TAIL_CUT.sub("", w)
    if HEAD_CUT.match(w) and len(w) > 3: w = HEAD_CUT.sub("", w)
    if len(w) < 2: return ""
    if REFFRAG.search(w): return ""
    if LEADFRAG.match(w): return ""
    return w
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
        w = norm_term(m.group()) if not NUM.fullmatch(m.group()) else m.group()
        if not w: continue
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


# ── 法令を社労士試験の科目に割り当てる ──
# 一覧が法令名だけで60種並ぶと、どれがどの科目か分からない。
SUBJ_OF = {
 "労基・安衛": ["労働基準法","労働基準法施行規則","労働安全衛生法","労働安全衛生法施行令",
              "労働安全衛生規則","有機溶剤中毒予防規則","特定化学物質障害予防規則",
              "鉛中毒予防規則","粉じん障害防止規則","石綿障害予防規則",
              "電離放射線障害防止規則","事務所衛生基準規則"],
 "労災":     ["労働者災害補償保険法","労災保険法施行規則","労災保険法施行令"],
 "雇用":     ["雇用保険法","雇用保険法施行規則","雇用保険法施行令"],
 "徴収":     ["労働保険徴収法","労働保険徴収法施行規則","労働保険徴収法施行令"],
 "労一":     ["労働契約法","労働組合法","労働関係調整法","最低賃金法","労働者派遣法",
              "男女雇用機会均等法","育児・介護休業法","パートタイム・有期雇用労働法",
              "高年齢者雇用安定法","障害者雇用促進法","職業安定法","労働施策総合推進法",
              "個別労働関係紛争解決促進法","賃金支払確保法","家内労働法","職業能力開発促進法",
              "労働時間等設定改善法","中小企業退職金共済法","労働審判法","労働一般常識"],
 "社一":     ["国民健康保険法","国民健康保険法施行規則","介護保険法","介護保険法施行規則",
              "高齢者医療確保法","社会保険労務士法","社会保険労務士法施行規則","児童手当法",
              "確定拠出年金法","確定給付企業年金法","船員保険法",
              "社会保険審査官及び社会保険審査会法","社会保険一般常識"],
 "健保":     ["健康保険法","健康保険法施行規則","健康保険法施行令"],
 "厚年":     ["厚生年金保険法","厚生年金保険法施行規則","厚生年金保険法施行令"],
 "国年":     ["国民年金法","国民年金法施行規則","国民年金法施行令"],
}
LAW2SUBJ = {l: s for s, ls in SUBJ_OF.items() for l in ls}


# ── 穴にする語の価値づけ ──
# 「事項」「場合」「規定」「前項」を隠しても法令の理解にならない。
# 本試験で実際に空欄にされた語と、過去問の論点キーワードを優先する。
BLANKED = set()          # 選択式で実際に空欄にされた語
for _kai, _v in M.items():
    for _q in _v["sentaku"]:
        _raw = S[_kai]["sentaku"][_q["subject"]]
        for _i, _a in enumerate(_raw):
            _a0 = _a[0] if isinstance(_a, list) else _a
            if _a0 is None: continue
            _w = (_q["choices"][_a0-1] if _q["format"] == "pool20"
                  else (_q["choices"][_i][_a0-1] if _a0-1 < len(_q["choices"][_i]) else ""))
            if _w: BLANKED.add(NOSP(_w))
_ns = {}
exec(open("gen_tokuten.py").read().split("stat = {}")[0], _ns)
TOPICS = {NOSP(k) for v in _ns["KEYS"].values() for k in v}

# 条文の骨組みを指すだけで、隠しても意味のない語
STOP = {"事項","場合","法律","前項","規定","必要","同項","各号","以下","当該","その他",
        "前条","次項","本条","この法律","前号","次条","もの","こと","とき","ため",
        "第一項","第二項","第三項","第四項","第五項","前二項","前三項","各項",
        "政令","厚生労働省令","省令","命令","準用","適用","該当","前段","後段",
        "定め","範囲","内容","方法","状況","状態","事情","事由","限度","程度"}

def blank_score(w):
    """穴にする価値。高いものから選ぶ。"""
    t = NOSP(w)
    if t in STOP: return -1
    if re.fullmatch(r"[0-9０-９]+.*", t): return 3        # 数値はしきい値になりやすい
    if t in BLANKED: return 5                            # 本試験で実際に空欄になった語
    if any(k == t for k in TOPICS): return 4             # 論点そのもの
    if any(k in t or t in k for k in TOPICS): return 3   # 論点に関わる語
    if re.search(r"(大臣|署長|所長|局長|知事|機構|協会|組合|市町村|審査会|審査官|委員会|事業主|保険者|被保険者)$", t):
        return 3                                          # 主体は誤り肢の定番
    if len(t) >= 4: return 1
    return 0


random.seed(20260823)
qs, seen = [], set()
combo_seen = collections.defaultdict(set)
made_by_law = collections.Counter()
made_by_art = collections.Counter()
# 出題実績のある条文から先に作る
units.sort(key=lambda u: -u["cited"])
for u in units:
    t = u["text"]
    words = [(norm_term(m.group()) if not NUM.fullmatch(m.group()) else m.group())
             for m in list(TERM.finditer(t)) + list(NUM.finditer(t))]
    words = [w for w in words if w]
    # 価値の高い語から穴にする。価値0以下は使わない。
    words = sorted({w for w in words if blank_score(w) > 0},
                   key=lambda w: -blank_score(w))
    words = [w for w in dict.fromkeys(words)
             if 2 <= len(NOSP(w)) <= 14 and t.count(w) == 1
             and not re.match(r"^(一|二|三|四|五|六|七|八|九|十|他|又|及|若|前|同|当該|この|その)(?=[一-鿿]{2})", w)
             and not MONEY.search(NOSP(w))]
    if made_by_law[u["law"]] >= cap_of(u["law"]): continue
    art_key = (u["law"], u["art"])
    if made_by_art[art_key] >= (6 if u["cited"] else 3): continue
    made = 0
    for w in words:
        # 定義規定（介護保険法8条など）は項が多く、放っておくと1条から
        # 数十問できてしまう。1条あたりの上限を掛ける。
        if made >= (3 if u["cited"] else 1): break
        if made_by_law[u["law"]] >= cap_of(u["law"]): break
        if made_by_art[art_key] >= (6 if u["cited"] else 3): break
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
        seen.add(key); made += 1; made_by_law[u["law"]] += 1
        made_by_art[art_key] += 1; ans_use[NOSP(w)] += 1
        qs.append({"type":"ana", "law":u["law"],
                   "subj": LAW2SUBJ.get(u["law"], "その他"),
                   "head":t[:p], "tail":t[p+len(w):],
                   "choices":ch, "a":ch.index(w), "cat":c,
                   "real": u["cited"] > 0,
                   "src": f'{u["law"]}{art_label(u["art"])}',
                   "cap": u["cap"], "chap": u["chap"], "ord": list(u["order"]),
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
