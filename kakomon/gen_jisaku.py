#!/usr/bin/env python3
"""自作ドリル（本試験形式・解説つき）を、検証済みの材料だけから組み立てる。

方針は「私が法令を書き起こさない」こと。誤りの混入を防ぐため、
・正しい肢は本試験で正答と確定した記述の**原文そのまま**
・誤り肢はその原文を**1か所だけ**、記録に残る形で改変したもの
とし、解説には「どこを何から何へ変えたか」と出典を必ず書く。

安全策
 ①法改正で変わった論点・年度依存の数値を含む肢は使わない
 ②改変対象が文中に1回だけ現れる肢に限る（どこを変えたか一意に定まる）
 ③「」でくくられた条文の引用部分は改変しない
 ④改変後の文が、9年分の「正しい」と確定した記述のどれとも一致しないことを照合
 ⑤1問につき誤りはちょうど1つ。残り4つは原文のまま
"""
import json, re, collections, random, sys

M = json.load(open("mondai.json")); S = json.load(open("seitou.json"))
NOSP = lambda s: re.sub(r"[\s　]", "", str(s))
KAI2Y = {57:"令和7",56:"令和6",55:"令和5",54:"令和4",53:"令和3",
         52:"令和2",51:"令和元",50:"平成30",49:"平成29"}
SUBJ  = ["労基安衛","労災","雇用","一般常識","健保","厚年","国年"]
OUT   = {"労基安衛":("../drill/data/jisaku-1-roukianei.js","労基・安衛"),
         "労災":("../drill/data/jisaku-2-rousai.js","労災・徴収"),
         "雇用":("../drill/data/jisaku-3-koyou.js","雇用・徴収"),
         "一般常識":("../drill/data/jisaku-4-ippan.js","一般常識"),
         "健保":("../drill/data/jisaku-5-kenpo.js","健保"),
         "厚年":("../drill/data/jisaku-6-kounen.js","厚年"),
         "国年":("../drill/data/jisaku-7-kokunen.js","国年")}

LAWNAME = {"労基安衛":"労働基準法及び労働安全衛生法","労災":"労働者災害補償保険法（徴収法を含む）",
           "雇用":"雇用保険法（徴収法を含む）","一般常識":"労務管理その他の労働及び社会保険に関する一般常識",
           "健保":"健康保険法","厚年":"厚生年金保険法","国年":"国民年金法"}
ns = {}; exec(open("gen_tokuten.py").read().split("stat = {}")[0], ns)
KEYS = ns["KEYS"]

# ── ① 使ってはいけない肢（法改正・年度依存） ─────────────────
STALE = [
 (r"支給停止調整額|在職老齢年金",      "令和8年4月から65万円に改正"),
 (r"[0-9０-９]+\s*/\s*1,?000|保険料率",  "料率は年度ごとに改定される"),
 (r"保険料の額は.*円|月額.*[0-9]{2},[0-9]{3}\s*円", "年度ごとに改定される額"),
 (r"給付制限",                        "自己都合退職の給付制限が1か月に改正"),
 (r"教育訓練休暇給付金|出生後休業支援|育児時短就業", "令和7〜8年度の新設給付"),
 (r"標準報酬月額の.*(上限|最高)|等級",   "等級・上限は改定される"),
 (r"老齢基礎年金の額は|満額",           "年金額は毎年度改定される"),
 (r"高年齢雇用継続給付.*[0-9]+\s*％",   "給付率が改正された"),
 (r"拠出限度額|確定拠出年金.*円",        "令和8年12月に改正予定"),
 (r"介護保険料率|子ども・子育て",        "料率・新設拠出金"),
]
def stale_reason(t):
    for pat, why in STALE:
        if re.search(pat, t): return why
    return None

# 文脈に依存して単独では成立しない肢も外す
# 元の問題文で定義された語を受ける肢は、単独で出すと主語が分からない。
CTX = re.compile(r"本問において|前問|上記|なお、本問|この場合|当該事案|事例において")
HEAD_REF = re.compile(r"^(当該|その|この|同[項条法条]|これら|なお|また)")

# ── 正しいと確定した肢を集める ────────────────────────────
def qtype(s):
    s = NOSP(s)
    if "いくつあるか" in s: return "個数"
    if "組合せ" in s:       return "組合せ"
    if re.search(r"誤っているもの|誤りである", s): return "誤り"
    if re.search(r"正しいもの|適切なもの", s):     return "正しい"
    return "その他"

TRUE = collections.defaultdict(list)     # 科目 → [(回, 問, 本文)]
ALL_TRUE_NOSP = set()
for kai, v in M.items():
    for q in v["takuitsu"]:
        a = S[kai]["takuitsu"][q["subject"]][q["num"]-1]
        if a is None or isinstance(a, list): continue
        t = qtype(q["stem"])
        if t == "誤り":
            picks = [(i, c) for i, c in enumerate(q["choices"]) if i != a]
        elif t == "正しい":
            picks = [(a, q["choices"][a])]
        else:
            continue
        for _, c in picks:
            TRUE[q["subject"]].append((int(kai), q["num"], c))
            ALL_TRUE_NOSP.add(NOSP(c))

# ── ③ 引用符の内側を避けるための位置判定 ──────────────────
def in_quote(text, pos):
    return text.count("「", 0, pos) > text.count("」", 0, pos)

# ── 改変の定義 ────────────────────────────────────────
# 「厚生労働大臣↔都道府県労働局長」「日本年金機構↔厚生労働大臣」は権限が委任されており、
# 入れ替えても正しいままになる場面がある。誤りと言い切れないので使わない。
# 残すのは、所掌する機関がはっきり別のものだけ。
ACTOR = [("労働基準監督署長","公共職業安定所長"),("公共職業安定所長","労働基準監督署長"),
         ("全国健康保険協会","健康保険組合"),("健康保険組合","全国健康保険協会")]
# 「努めなければならない→しなければならない」は「〜するよう努めなければならない」に当たると
# 「〜するようしなければならない」となり日本語が壊れるので使わない。
DUTY  = [("しなければならない","することができる"),("することができる","しなければならない"),
         ("してはならない","することができる")]
NEAR  = {"日":[3,5,7,10,14,20,30,60],"年":[1,2,3,5,10,20,25],
         "か月":[1,2,3,6,12],"箇月":[1,2,3,6,12],"月":[1,2,3,6,12],
         "週間":[1,2,4,6,8],"時間":[8,40,45,60,100],"歳":[18,20,40,60,65,70,75]}

def mutate(text):
    """1か所だけ変える。変えられなければ None。(改変後, 種別, 変更前, 変更後) を返す。"""
    cands = []
    for before, after in ACTOR:
        if text.count(before) != 1: continue
        p = text.index(before)
        if in_quote(text, p): continue
        # 「国民健康保険組合」の一部として「健康保険組合」を拾わないよう、直前を見る。
        head_ch = text[p-1] if p > 0 else "、"
        if head_ch not in "、。（「』】はがのにをも及並又・　 ": continue
        # 「労働基準監督署長又は公共職業安定所長」の片方を変えると同じ語が並ぶ。
        if after in text: continue
        tail = text[p+len(before):p+len(before)+6]
        # 「全国健康保険協会管掌健康保険において」のように制度の呼び名として出てくる場合は、
        # 入れ替えても取扱いが変わらず、誤りと言い切れない。行為の主体のときだけ変える。
        if re.match(r"管掌|が管掌|の管掌", tail): continue
        if not re.match(r"は|が|に|へ|に対|を|の権限|が行", tail): continue
        cands.append(("主体", before, after))
    for before, after in DUTY:
        if text.count(before) != 1: continue
        p = text.index(before)
        if in_quote(text, p): continue
        tail = text[p+len(before):p+len(before)+8]
        head = text[max(0,p-4):p]
        # 「自走することができるもの」「特別加入をすることができる者」は能力や定義の記述で、
        # 義務に変えると意味を成さない。「〜ための措置」も同じ。
        if re.match(r"もの|者|ため|こと|とき|場合", tail): continue
        # 「必ずしも〜しなければならないものではない」の中を変えると、かえって正しい文になる。
        if re.search(r"ものではない|わけではない|とは限らない", text[p:p+30]): continue
        if re.search(r"必ずしも", text[max(0,p-60):p]): continue
        # 「〜するよう努めなければならない」の直前が「よう」のときは文が壊れる。
        if head.endswith("よう") or head.endswith("ように"): continue
        # 「配慮することができるとの責務」のように、直後に義務を表す語が続くと矛盾する。
        if re.search(r"との?(責務|義務|規定|旨)", tail): continue
        cands.append(("義務と裁量", before, after))
    # 数値はしきい値だけを対象にする。
    # 「58 歳の被保険者は…」のような事例の中の数字を変えても法令の誤りにはならず、
    # 単に別の事案になるだけで、正誤が判定できない。
    # そこで「以上・以下・未満・以内・を超え・間・ごと」など、規範を表す語が
    # 直後に続く数値に限定する。西暦の下3桁を拾わないよう桁の境界も見る。
    # 事例（人物の設定）や統計の記述に含まれる数字は、変えても法令の誤りにならない。
    # 「20 歳から60 歳までの40 年間」を25年に変えると、文が自己矛盾するだけで問題にならない。
    CASE = re.compile(r"例えば|具体的には|とする。|であるものとする|と仮定|"
                      r"(昭和|平成|令和)\s*[0-9]{1,2}\s*年\s*[0-9]{1,2}\s*月\s*[0-9]{1,2}\s*日")
    STAT = re.compile(r"白書|によると|によれば|調査結果|統計|率は|割合は|雇用者|就業者|非正規|職員・従業員|労働力|世帯")
    skip_num = bool(CASE.search(text) or STAT.search(text))
    # 同じ単位の数字が2つ以上あると、片方だけ変えたとき前後が食い違う
    for u in ("歳","年","日","時間"):
        if len(re.findall(r"[0-9]{1,3}\s*"+u, text)) >= 2: skip_num = True
    THRESH = re.compile(r"^\s*(以上|以下|未満|以内|を超え|を限度|ごと|以後|以前|を経過)")
    for m in ([] if skip_num else re.finditer(r"(?<![0-9０-９])([0-9]{1,3})\s*(日|年|か月|箇月|月|週間|時間|歳)(?![0-9０-９])", text)):
        n, unit = int(m.group(1)), m.group(2)
        if unit not in NEAR or in_quote(text, m.start()): continue
        if text.count(m.group(0)) != 1: continue
        if not THRESH.match(text[m.end():]): continue           # しきい値でなければ触らない
        head = text[max(0, m.start()-14):m.start()]
        if re.search(r"(令和|平成|昭和|大正)\s*[0-9]{0,3}\s*(年|年度)?\s*$", head): continue
        if re.search(r"[0-9]\s*(年|月)\s*$", head): continue
        if unit in ("年","月") and re.search(r"(令和|平成|昭和)", text[max(0,m.start()-24):m.end()+8]): continue
        alt = [x for x in NEAR[unit] if x != n]
        if not alt: continue
        pick = min(alt, key=lambda x: (abs(x-n) == 0, abs(x-n)))
        cands.append(("数値", m.group(0), f"{pick}{unit}"))
    if not cands: return None
    kind, before, after = cands[0]
    out = text.replace(before, after, 1)
    # ④ 改変後が既知の正しい記述と一致しないか
    if NOSP(out) in ALL_TRUE_NOSP: return None
    return out, kind, before, after

# ── 論点の判定（同じ論点で5肢そろえるため） ──────────────
def topic_of(subj, text):
    t = NOSP(text); best, blen = None, 0
    for kw in KEYS.get(subj, []):
        k = NOSP(kw)
        if k in t and len(k) > blen: best, blen = kw, len(k)
    return best

def clean(t):
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"(?<=[぀-ヿ一-鿿、。」）])\s+(?=[぀-ヿ一-鿿「（])", "", t)
    return t.strip()

TARGET = 100
random.seed(20260823)          # 生成を再現できるようにする
report = []

for subj in SUBJ:
    fname, label = OUT[subj]
    # 使える肢を選別する
    pool, dropped = [], collections.Counter()
    for kai, num, c in TRUE[subj]:
        t = clean(c); n = len(NOSP(t))
        if not (55 <= n <= 230):        dropped["長さ"] += 1; continue
        # 別表の断片は「）、張出し足場又は…」のように文の途中から始まり、句点で終わらない。
        if not re.search(r"[。」）]$", t):     dropped["文が未完結"] += 1; continue
        if re.match(r"[）」、。]", t):         dropped["文が未完結"] += 1; continue
        if CTX.search(t):               dropped["文脈依存"] += 1; continue
        if HEAD_REF.match(t):           dropped["受け先のない指示語"] += 1; continue
        why = stale_reason(t)
        if why:                         dropped["法改正・年度依存"] += 1; continue
        pool.append({"kai":kai,"num":num,"t":t,"topic":topic_of(subj,t)})
    # 同じ本文が複数年に出ることがあるので重複を落とす
    seen, uniq = set(), []
    for p in pool:
        k = NOSP(p["t"])[:40]
        if k in seen: continue
        seen.add(k); uniq.append(p)
    pool = uniq

    mutables = []
    for p in pool:
        m = mutate(p["t"])
        if m: mutables.append({**p, "wrong":m[0], "kind":m[1], "before":m[2], "after":m[3]})

    by_topic = collections.defaultdict(list)
    for p in pool: by_topic[p["topic"]].append(p)

    qs = []
    used_ans = collections.Counter()   # 正解として使った回数
    used_dis = collections.Counter()   # ダミーとして使った回数
    # 素材が少ない科目では再利用の上限を上げないと100問に届かない。
    CAP_ANS = max(6, -(-TARGET // max(len(mutables), 1)) + 2)
    CAP_DIS = max(16, -(-TARGET * 4 // max(len(mutables), 1)) + 4)
    by_key = {NOSP(p["t"])[:40]: p for p in pool}
    mut_by_key = {NOSP(p["t"])[:40]: p for p in mutables}
    cite = lambda p: f'{KAI2Y[p["kai"]]}年度 問{p["num"]}'
    NOTE = ('\n\n> この問題は過去問データから機械的に組み立てています（`kakomon/gen_jisaku.py`）。\n'
            '> **正しい肢は本試験の原文そのまま**なので、その形をそのまま覚えて構いません。')

    def pick_similar(cands, target_len, n):
        """正解肢だけ長さが突出しないよう、近い長さのものから選ぶ。"""
        random.shuffle(cands)
        if len(cands) < n: return cands
        band = [p for p in cands if abs(len(NOSP(p["t"])) - target_len) <= max(40, target_len*0.45)]
        src = band if len(band) >= n else cands
        # 書き出しが同じ肢を並べると重複して見えるので、頭25字が重ならないように選ぶ
        out, heads = [], set()
        for p in src:
            h = NOSP(p["t"])[:25]
            if h in heads: continue
            heads.add(h); out.append(p)
            if len(out) == n: break
        return out if len(out) == n else src[:n]

    def build_wrong(src):
        """誤っているものを1つ選ばせる問題。正しい肢4本は原文のまま。"""
        key = NOSP(src["t"])[:40]
        L = len(NOSP(src["wrong"]))
        same = [p for p in by_topic.get(src["topic"], []) if NOSP(p["t"])[:40] != key]
        rest = [p for p in pool if NOSP(p["t"])[:40] != key and p not in same]
        others = pick_similar(same + rest, L, 4)
        if len(others) < 4: return None
        items = [{"t":src["wrong"], "bad":True, "src":src}] + [{"t":p["t"], "bad":False, "src":p} for p in others]
        items, ai = place(items, 0)
        exp = (f'正解は{"ABCDE"[ai]}（誤っているもの）。\n\n'
               f'**{"ABCDE"[ai]}：誤り。**「{src["after"]}」ではなく「**{src["before"]}**」が正しい。\n'
               f'（{cite(src)} で正しいと確定した記述の{src["kind"]}を1か所だけ変えたもの）\n\n'
               f'ほかの4つは**本試験で正しいと確定した記述の原文**です。\n'
               + "\n".join(f'- {"ABCDE"[i]}　{cite(x["src"])}' for i, x in enumerate(items) if not x["bad"])
               + NOTE)
        return items, ai, exp, "誤っているものはどれか", src

    def build_right(correct, wrongs):
        """正しいものを1つ選ばせる問題。誤り肢4本はいずれも改変を記録してある。"""
        items = [{"t":correct["t"], "good":True, "src":correct}] + \
                [{"t":w["wrong"], "good":False, "src":w} for w in wrongs]
        items, ai = place(items, 0)
        exp = (f'正解は{"ABCDE"[ai]}（正しいもの）。\n\n'
               f'**{"ABCDE"[ai]}：正しい。** {cite(correct)} で正しいと確定した記述の原文です。\n\n'
               f'ほかの4つは、いずれも本試験の正しい記述を**1か所だけ**変えたものです。\n'
               + "\n".join(
                   f'- {"ABCDE"[i]}：誤り。「{x["src"]["after"]}」ではなく「**{x["src"]["before"]}**」'
                   f'（{cite(x["src"])} の{x["src"]["kind"]}を変更）'
                   for i, x in enumerate(items) if not x["good"])
               + NOTE)
        return items, ai, exp, "正しいものはどれか", correct

    combos = set()          # 同じ5肢の組合せを繰り返さない
    slot = [0]              # 正解の位置を順に割り当てて偏りをなくす

    def place(items, correct_idx):
        """正解を巡回させた位置に置く。残りは長さ順が偏らないよう混ぜる。"""
        ans = items[correct_idx]
        rest = [x for i, x in enumerate(items) if i != correct_idx]
        random.shuffle(rest)
        pos = slot[0] % 5; slot[0] += 1
        out = rest[:pos] + [ans] + rest[pos:]
        return out, pos

    def emit(built):
        items, ai, exp, kind, src = built
        sig = tuple(sorted(NOSP(x["t"])[:30] for x in items))
        if sig in combos: return False
        combos.add(sig)
        qs.append({"type":"abc", "tag":f'{label}/{src["topic"] or subj}',
                   "q":f'{LAWNAME[subj]}に関する次の記述のうち、{kind}。',
                   "choices":[x["t"] for x in items], "a":ai, "exp":exp,
                   "src":f'自作（{cite(src)}の肢を素材に構成）'})
        return True

    # 本試験の比率に近づけ、「誤っているもの」と「正しいもの」を交互に作る
    idx = 0
    while len(qs) < TARGET and mutables:
        idx += 1
        if idx > len(mutables) * 30: break
        if len(qs) % 2 == 0:
            src = mutables[idx % len(mutables)]
            key = NOSP(src["t"])[:40]
            if used_ans[key] >= CAP_ANS: continue
            b2 = build_wrong(src)
            if not b2: continue
            if emit(b2): used_ans[key] += 1
        else:
            correct = pool[idx % len(pool)]
            ck = NOSP(correct["t"])[:40]
            if used_ans[ck] >= CAP_ANS: continue
            pickable = [m for m in mutables
                        if NOSP(m["t"])[:40] != ck and used_dis[NOSP(m["t"])[:40]] < CAP_DIS]
            if len(pickable) < 4: continue
            random.shuffle(pickable)
            L = len(NOSP(correct["t"]))
            ranked = sorted(pickable, key=lambda m: (used_dis[NOSP(m["t"])[:40]],
                                                     abs(len(NOSP(m["wrong"])) - L)))
            # 4本すべてが語尾の改変だと、語尾を見るだけで解けてしまう。
            # 種別が2つ以上になるよう選ぶ。
            ws, kinds = [], collections.Counter()
            for m in ranked:
                if len(ws) == 4: break
                if kinds[m["kind"]] >= 2 and len(ranked) > 12: continue
                ws.append(m); kinds[m["kind"]] += 1
            if len(ws) < 4: continue
            if len(kinds) < 2 and len(ranked) > 12: continue
            if emit(build_right(correct, ws)):
                used_ans[ck] += 1
                for w in ws: used_dis[NOSP(w["t"])[:40]] += 1

    # 同じ素材から作った問題が並ぶと単調なので、出題順を混ぜる
    random.shuffle(qs)
    for _ in range(3):
        for i in range(len(qs)-1):
            if qs[i]["src"] == qs[i+1]["src"] and i+2 < len(qs):
                qs[i+1], qs[i+2] = qs[i+2], qs[i+1]

    with open(fname, "w") as f:
        f.write(f'/* 自作ドリル {label}｜本試験形式（5肢択一・解説つき）\n'
                f' * 本試験で正しいと確定した記述を素材に、1か所だけ変えた肢を1つ混ぜている。\n'
                f' * 正しい肢は原文のまま。kakomon/gen_jisaku.py が生成。\n */\n')
        f.write(f'DRILL.register("自作 {label}", ' +
                json.dumps(qs, ensure_ascii=False, separators=(",", ":")) + ');\n')
    report.append((label, len(pool), len(mutables), len(qs), dropped))

print(f"{'科目':<12}{'使える肢':>8}{'改変可':>7}{'生成':>7}   除外の内訳")
for label, np_, nm, nq, dr in report:
    print(f"{label:<12}{np_:>8}{nm:>7}{nq:>7}   " +
          " ".join(f"{k}{v}" for k, v in dr.most_common()))
print(f"\n合計 {sum(r[3] for r in report)}問")
