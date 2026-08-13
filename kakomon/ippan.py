#!/usr/bin/env python3
"""一般常識（労一・社一）が、法令と統計のどちらをどれだけ聞いているかを数える。

はじめ択一だけを見て「社一の統計は6%」と出したが、これは測り方が悪かった。
選択式は科目名が「労一」「社一」で入っていて「一般常識」では拾えず、
また統計問題でも「◯◯調査を参照」の但し書きが付かないものがある。
両方を入れて数え直す。

  出力: 年度ごとに、択一と選択式それぞれの 法令／統計 の内訳
"""
import json, re, os, glob, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_qref import js_array

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "drill", "data")

# 但し書きが無くても統計とわかる語。白書・調査の名前と、統計特有の言い回し。
STAT = re.compile(
    r"調査（|白書（|統計等を利用|統計局|統計トピックス|"
    r"労働力調査|毎月勤労統計|賃金構造基本統計|就労条件総合調査|雇用動向調査|"
    r"能力開発基本調査|雇用均等基本調査|労働組合基礎調査|労働安全衛生調査|"
    r"労使間の交渉|実態調査|人口動態統計|国民生活基礎調査|国民医療費|"
    r"社会保障費用統計|人口推計|将来推計人口|加入・保険料納付状況|"
    r"割合が最も高|次いで|構成割合|推移をみると|年平均|概況|"
    # 但し書きも調査名も無いまま白書の記述を引く問題がある（令和7年度 問10）
    r"年頃を見通す|生産年齢人口|85歳以上人口")
LAW = re.compile(r"第\d+条|法第|規則第|政令で定める|条例で定める")

# 択一の各問が労一か社一かは、設問文の中身で決める（問番号は年で動く）
SHA = re.compile(
    r"社会保険|社会保障|国民健康保険|介護保険|高齢者医療|確定拠出|確定給付|"
    r"企業年金|船員保険|児童手当|社会保険労務士|審査官|審査会|国民年金|厚生年金|"
    r"医療費|年金制度|後期高齢者")

def load():
    out = []
    for f in sorted(glob.glob(os.path.join(DATA, "*.js"))):
        s = open(f, encoding="utf-8").read()
        m = re.search(r'DRILL\.register\(\s*"([^"]+)"', s)
        if not m:
            continue
        tail = s[m.end():]
        try:
            arr = json.loads(tail[tail.index("["):tail.rindex("]") + 1])
        except Exception:
            arr = js_array(tail[tail.index("["):tail.rindex("]") + 1])
        if arr is None:
            continue
        for q in arr:
            src = str(q.get("src", ""))
            if "年度" not in src or "自作" in src or "肢" in src:
                continue
            if not re.search(r"一般常識|労一|社一", src):
                continue
            st = re.sub(r"\s+", "", str(q.get("q") or q.get("stem") or ""))
            if not st:                       # 選択式は問題文の無い枝が混じる
                continue
            ch = "".join(str(x) for x in (q.get("choices") or []))
            out.append((src, st, ch))
    return out

def main():
    rows = load()
    tbl = collections.defaultdict(lambda: collections.Counter())
    detail = collections.defaultdict(list)
    for src, st, ch in rows:
        y = re.search(r"(令和\d|令和元|平成\d+)年度", src).group(1)
        sel = "選択式" in src
        body = st + ch
        if sel:
            who = "社一" if "社一" in src else "労一"
        else:
            who = "社一" if SHA.search(st[:80]) else "労一"
        kind = "統計" if STAT.search(body) else "法令"
        tbl[(y, who, "選択式" if sel else "択一")][kind] += 1
        detail[(y, who, "選択式" if sel else "択一")].append((kind, st[:44]))
    YS = ["令和7", "令和6", "令和5", "令和4", "令和3", "令和2", "令和元", "平成30", "平成29"]
    for form in ("択一", "選択式"):
        print(f"\n■ {form}　（統計 / 全体）")
        print("年度     労一        社一")
        ta = tb = sa = sb = 0
        for y in YS:
            a = tbl[(y, "労一", form)]; b = tbl[(y, "社一", form)]
            na, nb = sum(a.values()), sum(b.values())
            print(f"{y:6}   {a['統計']}/{na:<10} {b['統計']}/{nb}")
            ta += na; tb += nb; sa += a["統計"]; sb += b["統計"]
        f = lambda s, t: f"{s}/{t}（{s/t*100:.0f}%）" if t else "—"
        print(f"合計     労一 {f(sa,ta)}    社一 {f(sb,tb)}")
    if "-v" in sys.argv:
        for k in sorted(detail):
            print(f"\n{k}")
            for kind, st in detail[k]:
                print(f"   [{kind}] {st}")

if __name__ == "__main__":
    main()
