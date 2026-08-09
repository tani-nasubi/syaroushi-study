#!/usr/bin/env python3
"""過去問の肢から割り出した根拠の条を、資料が扱っているか一つずつ見る。

年度や語ではなく**条**を単位にした総当たり。gen_qref.py が 2,061問について
割り出した根拠の条（930条）を、その科目の資料と突き合わせる。

  1. 条番号がそのまま資料にあるか
  2. なければ、条見出し（法令XMLのArticleCaption）の語が資料にあるか

どちらも無いものだけを残す。qref の割り出しは総当たりの一致なので
取り違えも混じる。残ったものは肢の本文を見て判断する。
"""
import json, re, os, sys, ast, collections
import xml.etree.ElementTree as ET
sys.argv = ["artgap"]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cover_all as C

HERE = os.path.dirname(os.path.abspath(__file__))
LAWS = ast.literal_eval(re.search(r"LAWS\s*=\s*(\{.*?\n\})",
        open(os.path.join(HERE, "gen_anaume2.py"), encoding="utf-8").read(), re.S).group(1))

# 法令 → 科目。cover_all の対応に、施行規則と一般常識の個別法を足す。
EXTRA = {"労働基準法施行規則": "労基", "労働安全衛生規則": "安衛",
         "労災保険法施行規則": "労災", "雇用保険法施行規則": "雇用",
         "労働保険徴収法施行規則": "徴収", "健康保険法施行規則": "健保",
         "国民年金法施行規則": "国年", "厚生年金保険法施行規則": "厚年",
         "労働契約法": "労一", "労働組合法": "労一", "最低賃金法": "労一",
         "労働者派遣法": "労一", "社会保険労務士法": "社一",
         "国民健康保険法": "社一", "介護保険法": "社一", "高齢者医療確保法": "社一",
         "確定拠出年金法": "社一", "確定給付企業年金法": "社一", "船員保険法": "社一"}

_cap = {}
def caption(law, lab):
    if law not in _cap:
        lid = next((k for k, v in LAWS.items() if v == law), None)
        p = os.path.join(HERE, "hourei", f"{lid}.xml") if lid else None
        out = {}
        if p and os.path.exists(p):
            root = ET.parse(p).getroot()
            for a in (root.find(".//MainProvision") or root).iter("Article"):
                q = a.get("Num", "").split(":")[0].split("_")
                if not q[0].isdigit():
                    continue
                k = f"第{int(q[0])}条" + (f"の{int(q[1])}" if len(q) > 1 and q[1].isdigit() else "")
                if k in out:
                    continue
                c = a.find("ArticleCaption")
                out[k] = re.sub(r"[（）]", "", "".join(c.itertext()).strip()) if c is not None else ""
        _cap[law] = out
    return _cap[law].get(lab, "")

def numrx(lab):
    a, b = re.match(r"第(\d+)条(?:の(\d+))?$", lab).groups()
    return re.compile(r"第?\s*" + a + r"\s*条" + (r"\s*の\s*" + b if b else r"(?!\s*の\s*\d)"))

def frag_in(word, hay):
    """語そのもの、または4字以上の部分が資料にあるか。"""
    for n in range(len(word), 3, -1):
        for i in range(len(word) - n + 1):
            if word[i:i + n] in hay:
                return True
    return False

def main():
    raw = open(os.path.join(os.path.dirname(HERE), "drill", "data", "qref.js"), encoding="utf-8").read()
    cnt = collections.Counter(k for ks in json.loads(raw.split("=", 1)[1].rsplit(";", 1)[0]).values()
                              for k in ks)
    txt = {s: C.notes_text(s) for s in C.SUBJ}
    l2s = {d["law"]: s for s, d in C.SUBJ.items() if d["law"]}
    l2s.update(EXTRA)

    gap, n_num, n_cap = [], 0, 0
    for key, n in cnt.items():
        m = re.match(r"^(.+?)(第\d+条(?:の\d+)?)$", key)
        if not m:
            continue
        law, lab = m.groups()
        s = l2s.get(law)
        if not s:
            continue
        if numrx(lab).search(txt[s]):
            n_num += 1
            continue
        cap = caption(law, lab)
        if cap and frag_in(cap, txt[s]):
            n_cap += 1
            continue
        gap.append((n, key, cap, s))

    gap.sort(key=lambda x: (-x[0], x[1]))
    print(f"過去問の肢から割り出した根拠の条 {len(cnt)}条")
    print(f"   条番号が資料にある      {n_num}条")
    print(f"   条見出しの語が資料にある {n_cap}条")
    print(f"合計 番号も見出しも見当たらない {len(gap)}条")
    for n, k, c, s in gap:
        print(f"   {n}問 [{s}] {k}　{c or '（見出しなし）'}")

if __name__ == "__main__":
    main()
