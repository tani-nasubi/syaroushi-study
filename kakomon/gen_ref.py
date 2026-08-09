#!/usr/bin/env python3
"""「この条文はどの資料を読めばよいか」の対応表を作る。

問題を解いて間違えたとき、その論点の解説へ1タップで行けるようにする。
対応づけは手書きせず、深掘りページの本文と見出しから自動で決める
（gen_trend.py と同じ考え方）。

  出力: ../drill/data/ref.js
    REF.art  = { "労働基準法第32条の3": ["B9-変形労働時間制.md", "変形労働時間制"] , ... }
    REF.tag  = { "労基・安衛/解雇予告手当": ["B4-解雇.md", "解雇"], ... }
"""
import re, os, glob, json, collections

NOTES = "../notes"
OUT   = "../drill/data/ref.js"

# 深掘りページの接頭辞 → その資料が扱う法令
PRE_LAW = {
 "B": "労働基準法", "C": "労働基準法", "D": "労働安全衛生法",
 "E": "労働者災害補償保険法", "F": "雇用保険法", "G": "労働保険徴収法",
 "J": "健康保険法", "K": "国民年金法", "L": "厚生年金保険法",
}
# 労一・社一は1ページ1法令なので、表題から引く
MULTI = ("H", "I")

OTHER = re.compile(
    r"(労働契約法|民法|労働組合法|労働関係調整法|労働施策総合推進法|男女雇用機会均等法|"
    r"育児・介護休業法|パートタイム・有期雇用労働法|高年齢者雇用安定法|障害者雇用促進法|"
    r"最低賃金法|労働者派遣法|職業安定法|労働審判法|賃金支払確保法|"
    r"労働基準法|労働安全衛生法|労災保険法|労働者災害補償保険法|雇用保険法|労働保険徴収法|"
    r"健康保険法|厚生年金保険法|国民年金法|国民健康保険法|介護保険法|高齢者医療確保法|"
    r"社会保険労務士法|船員保険法|確定拠出年金法|確定給付企業年金法|"
    r"安衛則|労基則|労災則|徴収則|施行規則|施行令|憲法)")

ART   = re.compile(r"(?<![0-9])([0-9]{1,3})条(?:の([0-9]{1,2}))?")
RANGE = re.compile(r"(?<![0-9])([0-9]{1,3})条(?:の[0-9]{1,2})?\s*[〜～~－ー-]\s*([0-9]{1,3})条")
lab_of = lambda m: f"第{int(m.group(1))}条" + (f"の{int(m.group(2))}" if m.group(2) else "")

def collect():
    """深掘りページを読み、(法令名, 条ラベル) → ページ の点数表を作る。"""
    score = collections.defaultdict(collections.Counter)
    title = {}
    for path in sorted(glob.glob(f"{NOTES}/*.md")):
        b = os.path.basename(path)
        if not re.match(r"^[B-L]\d-", b):
            continue
        body = open(path, encoding="utf-8").read()
        title[b] = re.sub(r"｜.*$", "", body.split("\n", 1)[0].lstrip("# ").strip())
        own = PRE_LAW.get(b[0])
        if own is None:                      # 労一・社一は表題の法令名を使う
            m = re.search(r"[一-鿿・]{2,20}?(?:法|規則|令)", title[b])
            own = m.group(0) if m else None
        cur = ""
        for line in body.split("\n"):
            hm = re.match(r"^#{2,4} (.+)$", line)
            if hm:
                cur = hm.group(1)
                mo = OTHER.search(cur)
                law = mo.group(1) if mo else own
                if law is None:
                    continue
                for rg in RANGE.finditer(cur):
                    a, z = int(rg.group(1)), int(rg.group(2))
                    if 0 < z - a < 40:
                        for i in range(a, z + 1):
                            score[(law, f"第{i}条")][b] += 1
                for mm in ART.finditer(cur):
                    score[(law, lab_of(mm))][b] += 3    # 見出しに出るものは重い
                continue
            mo = OTHER.search(line)
            law = mo.group(1) if mo else (OTHER.search(cur).group(1)
                                          if OTHER.search(cur) else own)
            if law is None:
                continue
            for rg in RANGE.finditer(line):
                a, z = int(rg.group(1)), int(rg.group(2))
                if 0 < z - a < 40:
                    for i in range(a, z + 1):
                        score[(law, f"第{i}条")][b] += 1
            for mm in ART.finditer(line):
                score[(law, lab_of(mm))][b] += 1
    return score, title

ALIAS = {"労災保険法": "労働者災害補償保険法",
         "労働保険の保険料の徴収等に関する法律": "労働保険徴収法"}

def main():
    score, title = collect()
    art = {}
    for (law, lab), c in score.items():
        b, n = c.most_common(1)[0]
        if n < 2:
            continue
        art[f"{ALIAS.get(law, law)}{lab}"] = [b, title[b]]

    # 自作問題のタグ（「労基・安衛/解雇予告手当」）→ 資料
    tag = {}
    tags = set()
    for f in sorted(glob.glob("../drill/data/jisaku-*.js")):
        s = open(f, encoding="utf-8").read()
        for q in json.loads(s[s.index("["):s.rindex("]") + 1]):
            if q.get("tag"):
                tags.add(q["tag"])
    bodies = {}
    for path in sorted(glob.glob(f"{NOTES}/*.md")):
        b = os.path.basename(path)
        if re.match(r"^[B-L]\d-", b):
            bodies[b] = re.sub(r"[\s*`>|]", "", open(path, encoding="utf-8").read())
    for t in sorted(tags):
        topic = t.split("/")[-1]
        best, cnt = None, 0
        for b, body in bodies.items():
            n = body.count(topic)
            if title[b] == topic:            n += 20
            elif title[b].startswith(topic): n += 12
            elif topic in title[b]:          n += 6
            if n > cnt:
                best, cnt = b, n
        if best and cnt >= 2:
            tag[t] = [best, title[best]]

    # ── 法令名 → 資料（条が対応づかないときの受け皿）──────────
    # 速答は施行規則や一般常識の周辺法令からも出るので、条で当たらなくても
    # 「その法律ならここ」までは必ず案内できるようにする。
    LAW2NOTE = {
     "労働基準法": "01-労働基準法.md", "労働安全衛生法": "02-労働安全衛生法.md",
     "労働者災害補償保険法": "03-労災保険法.md", "雇用保険法": "04-雇用保険法.md",
     "労働保険徴収法": "05-徴収法.md", "健康保険法": "08-健康保険法.md",
     "厚生年金保険法": "10-厚生年金保険法.md", "国民年金法": "09-国民年金法.md",
    }
    law = {}
    # ① ページの表題に法令名があるもの（「介護保険法」など）
    for b, t in title.items():
        # 「国民健康保険法と高齢者医療確保法」のように2つ並ぶ表題があるので全部拾う
        for nm in re.findall(r"[一-鿿・]{2,20}?(?:法|規則|令)", t):
            law.setdefault(nm, [b, t])
    # ② 表題に無くても、見出しが法令名そのものなら、そのページを充てる
    #    （「企業年金と社会保険審査」の中の「## 船員保険法」など）
    for path in sorted(glob.glob(f"{NOTES}/*.md")):
        b = os.path.basename(path)
        if not re.match(r"^[B-L]\d-", b):
            continue
        for h in re.findall(r"^#{2,3} (.+)$", open(path, encoding="utf-8").read(), re.M):
            h = re.sub(r"（[^）]*）\s*$", "", h).strip()
            if re.fullmatch(r"[一-鿿・]{3,24}(?:法|規則|令)", h):
                law.setdefault(h, [b, title[b]])
    # ③ 見出しにも無い法令は、その名をいちばん多く扱っている深掘りページへ
    import collections as _c
    cnt = _c.defaultdict(_c.Counter)
    for path in sorted(glob.glob(f"{NOTES}/*.md")):
        b = os.path.basename(path)
        if not re.match(r"^[B-L]\d-", b):
            continue
        body = re.sub(r"[\s*`>|]", "", open(path, encoding="utf-8").read())
        for nm in set(re.findall(r"[一-鿿・]{3,24}?(?:法|規則|令)(?=[第。、（にはがをのでとやも])", body)):
            cnt[nm][b] = body.count(nm)
    for nm, c in cnt.items():
        b, n = c.most_common(1)[0]
        if n >= 4:                      # ついでに出てくる程度の言及では充てない
            law.setdefault(nm, [b, title[b]])

    for nm, note in LAW2NOTE.items():
        law.setdefault(nm, [note, note[3:-3]])
    # 一般常識の周辺法令は、その法令を扱う深掘りページか本体ノートへ
    for nm, note in [("労働契約法", "06-労働一般常識.md"), ("労働組合法", "06-労働一般常識.md"),
                     ("労働関係調整法", "06-労働一般常識.md"), ("最低賃金法", "06-労働一般常識.md"),
                     ("労働者派遣法", "06-労働一般常識.md"), ("男女雇用機会均等法", "06-労働一般常識.md"),
                     ("育児・介護休業法", "06-労働一般常識.md"), ("職業安定法", "06-労働一般常識.md"),
                     ("高年齢者雇用安定法", "06-労働一般常識.md"), ("障害者雇用促進法", "06-労働一般常識.md"),
                     ("労働施策総合推進法", "06-労働一般常識.md"), ("労働審判法", "06-労働一般常識.md"),
                     ("賃金支払確保法", "06-労働一般常識.md"), ("家内労働法", "06-労働一般常識.md"),
                     ("職業能力開発促進法", "06-労働一般常識.md"), ("中小企業退職金共済法", "06-労働一般常識.md"),
                     ("労働時間等設定改善法", "06-労働一般常識.md"),
                     ("個別労働関係紛争解決促進法", "06-労働一般常識.md"),
                     ("パートタイム・有期雇用労働法", "06-労働一般常識.md"),
                     ("社会保険労務士法", "07-社会保険一般常識.md"), ("国民健康保険法", "07-社会保険一般常識.md"),
                     ("介護保険法", "07-社会保険一般常識.md"), ("高齢者医療確保法", "07-社会保険一般常識.md"),
                     ("確定拠出年金法", "07-社会保険一般常識.md"), ("確定給付企業年金法", "07-社会保険一般常識.md"),
                     ("船員保険法", "07-社会保険一般常識.md"), ("児童手当法", "07-社会保険一般常識.md"),
                     ("社会保険審査官及び社会保険審査会法", "07-社会保険一般常識.md")]:
        law.setdefault(nm, [note, note[3:-3]])
    # 施行規則・施行令は本法の資料へ寄せる
    for nm in list(law):
        pass
    for k in ["労働基準法", "労働安全衛生法", "労働者災害補償保険法", "雇用保険法",
              "労働保険徴収法", "健康保険法", "厚生年金保険法", "国民年金法",
              "社会保険労務士法", "介護保険法", "国民健康保険法"]:
        for suf in ("施行規則", "施行令"):
            law.setdefault(k + suf, law[k])
    for k, v in [("労災保険法施行規則", "労働者災害補償保険法"), ("労災保険法施行令", "労働者災害補償保険法"),
                 ("安衛則", "労働安全衛生法"), ("労働安全衛生規則", "労働安全衛生法")]:
        if v in law:
            law.setdefault(k, law[v])

    # ── 科目 → 本体ノート（条文も法令名も書かれていない問題の受け皿）──
    subj = {"労基": ["01-労働基準法.md", "労働基準法"],
            "安衛": ["02-労働安全衛生法.md", "労働安全衛生法"],
            "労基安衛": ["01-労働基準法.md", "労働基準法"],
            "労災": ["03-労災保険法.md", "労災保険法"],
            "雇用": ["04-雇用保険法.md", "雇用保険法"],
            "徴収": ["05-徴収法.md", "徴収法"],
            "労一": ["06-労働一般常識.md", "労働一般常識"],
            "社一": ["07-社会保険一般常識.md", "社会保険一般常識"],
            "一般常識": ["06-労働一般常識.md", "労働一般常識"],
            "健保": ["08-健康保険法.md", "健康保険法"],
            "国年": ["09-国民年金法.md", "国民年金法"],
            "厚年": ["10-厚生年金保険法.md", "厚生年金保険法"]}

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("/* 条文・論点 → 読むべき資料。kakomon/gen_ref.py が自動生成する。 */\n")
        f.write("window.REF = " + json.dumps({"art": art, "tag": tag, "law": law, "subj": subj},
                                             ensure_ascii=False, indent=0) + ";\n")
    print(f"→ {OUT}  条文 {len(art):,}件 / タグ {len(tag)}件 / "
          f"法令 {len(law)}件 / 科目 {len(subj)}件")

if __name__ == "__main__":
    main()
