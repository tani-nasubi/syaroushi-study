#!/usr/bin/env python3
"""正答（seitou.json）と問題（mondai.json）を結合し、ドリル用のJSデータを科目別に出力する。

出力形式:
  abc    … 択一式5肢択一（本試験そのまま）
  sel20  … 選択式・20語の共通語群から5空欄
  selpb  … 選択式・空欄ごとの選択肢
  ox     … 択一式の各肢を○×に分解した派生問題
           （「正しいものはどれか」「誤っているものはどれか」型のみ。
             組合せ問題・個数問題は各肢の正誤が確定しないため除外）
"""
import json, os, re, collections

SEITOU = json.load(open("seitou.json"))
MONDAI = json.load(open("mondai.json"))
OUT = "../drill/data"

# 出力ファイル: (ファイル名, 表示名, 択一科目, [選択科目])
FILES = [
    ("kako-1-roukianei", "労基・安衛", "労基安衛", ["労基安衛"]),
    ("kako-2-rousai",    "労災・徴収", "労災",     ["労災"]),
    ("kako-3-koyou",     "雇用・徴収", "雇用",     ["雇用"]),
    ("kako-4-ippan",     "一般常識",   "一般常識", ["労一", "社一"]),
    ("kako-5-kenpo",     "健保",       "健保",     ["健保"]),
    ("kako-6-kounen",    "厚年",       "厚年",     ["厚年"]),
    ("kako-7-kokunen",   "国年",       "国年",     ["国年"]),
]
KAI2YEAR = {49: "平成29", 50: "平成30", 51: "令和元", 52: "令和2",
            53: "令和3", 54: "令和4", 55: "令和5", 56: "令和6", 57: "令和7"}

# 各肢の正誤が確定できる設問文のパターン
POS = re.compile(r"正しいもの(は|の)?どれか")          # 正答肢=正しい／他=誤り
NEG = re.compile(r"(誤っているもの|誤りであるもの)(は|の)?どれか")


def js(v):
    return json.dumps(v, ensure_ascii=False)


def build():
    tak_bank = collections.defaultdict(list)   # 択一（＋派生肢別）
    sel_bank = collections.defaultdict(list)   # 選択式
    stats = collections.Counter()

    for kai in sorted(MONDAI, key=int):
        k = int(kai)
        year = KAI2YEAR.get(k, f"第{k}回")
        sei = SEITOU[str(k)]

        # ---------- 択一式 ----------
        for q in MONDAI[kai]["takuitsu"]:
            subj, no = q["subject"], q["num"]
            ans = sei["takuitsu"][subj][no - 1]
            src = f"{year}年度(第{k}回) {subj} 択一 問{no}"
            note = ""
            if ans is None:
                note = "この問題は全員正解として取り扱われた（没問）。"
            elif isinstance(ans, list):
                note = "複数の選択肢が正答として取り扱われた。"
            tak_bank[subj].append({
                "type": "abc", "src": src, "year": k, "no": no,
                "q": q["stem"], "choices": q["choices"], "a": ans, "note": note,
            })
            stats["abc"] += 1

            # ---------- 派生：肢別○× ----------
            if ans is None or isinstance(ans, list):
                continue
            if POS.search(q["stem"]):
                truth = [i == ans for i in range(5)]
            elif NEG.search(q["stem"]):
                truth = [i != ans for i in range(5)]
            else:
                stats["ox_skip"] += 1
                continue
            head = re.sub(r"に関する次の記述のうち.*$", "", q["stem"])[:60]
            for i, c in enumerate(q["choices"]):
                tak_bank[subj].append({
                    "type": "ox", "src": f"{src} 肢{'ABCDE'[i]}", "year": k, "no": no,
                    "q": c, "a": truth[i], "topic": head,
                })
                stats["ox"] += 1

        # ---------- 選択式 ----------
        for q in MONDAI[kai]["sentaku"]:
            subj, no = q["subject"], q["num"]
            raw = sei["sentaku"][subj]          # 1始まり（perblankは各空欄内の番号）
            src = f"{year}年度(第{k}回) {subj} 選択式"
            if q["format"] == "pool20":
                a = [(v[0] if isinstance(v, list) else v) - 1 for v in raw]
                sel_bank[subj].append({"type": "sel20", "src": src, "year": k,
                                    "q": q["body"], "choices": q["choices"], "a": a})
                stats["sel20"] += 1
            else:
                a = [(v[0] if isinstance(v, list) else v) - 1 for v in raw]
                sel_bank[subj].append({"type": "selpb", "src": src, "year": k,
                                    "q": q["body"], "groups": q["choices"], "a": a})
                stats["selpb"] += 1

    # ---------- 出力 ----------
    os.makedirs(OUT, exist_ok=True)
    for fname, label, tak, sels in FILES:
        qs = list(tak_bank[tak]) + [x for s in sels for x in sel_bank[s]]
        qs.sort(key=lambda x: (-x["year"], {"sel20": 0, "selpb": 0, "abc": 1, "ox": 2}[x["type"]],
                               x.get("no", 0), x["src"]))
        body = ",\n".join(js(x) for x in qs)
        with open(f"{OUT}/{fname}.js", "w") as f:
            f.write(f"/* 本試験過去問 {label}｜第49回(平成29年度)〜第57回(令和7年度)\n"
                    f" * 出典: 社会保険労務士試験オフィシャルサイト等で公表された本試験問題・正答\n"
                    f" * 個人の学習用。解説は付いていない（正答のみ）。\n"
                    f" */\nDRILL.register({js('過去問 ' + label)}, [\n{body}\n]);\n")
        n = collections.Counter(x["type"] for x in qs)
        print(f"{fname:20s} {label:8s} 計{len(qs):4d}問 "
              f"(択一{n['abc']:3d} 選択{n['sel20']+n['selpb']:2d} 肢別{n['ox']:4d})")
    print(f"\n合計: 択一{stats['abc']}問 / 選択{stats['sel20']+stats['selpb']}問 "
          f"/ 派生肢別{stats['ox']}問（正誤確定できず除外した設問 {stats['ox_skip']}問）")


if __name__ == "__main__":
    build()
