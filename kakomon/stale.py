#!/usr/bin/env python3
"""改正で答えが変わってしまった過去問を洗い出す。

過去問は9年分あるが、社労士試験は改正が多い。出題時は正しかった肢でも、
今は誤りになっているものがある。それを知らずに繰り返すと、間違いを
覚え込むことになる。

  施行より前の回の問題で、その論点に触れているものを拾う。
  出力: ../drill/data/stale.js  { 問題ID: "注意書き" }

第49回=平成29年 … 第57回=令和7年。試験は8月なので、その年の4月施行の
改正はその回から対象になる。
"""
import json, re, os, glob, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_qref import js_array

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(os.path.dirname(HERE), "drill", "data")
OUT  = os.path.join(DATA, "stale.js")

# (この回から新しい扱い, 科目の限定, 語, 何がどう変わったか)
# 語は素朴に書くと取り違える。数字は前に数字が来ないこと（150万円の中の50万円を
# 拾わない）、語は改正が関わる文脈と一緒に出ることを条件にする。
D = r"(?<![0-9０-９,，.．])"          # 数字の途中で切り出さない
CHANGES = [
 (51, "労基", r"限度時間|特別条項|時間外労働の上限|" + D + r"45時間|" + D + r"360時間|複数月平均|単月100時間",
      "時間外労働の上限規制は平成31年4月（中小は令和2年4月）から。それ以前の回は限度基準告示が前提で、いまとは扱いが違う"),
 (51, "労基", r"時季を定めることにより与え|" + D + r"5日について.{0,20}時季",
      "年休の年5日の時季指定義務は平成31年4月から。それ以前の回には無い義務"),
 (52, "一般", r"労働契約法第20条|労働契約法第二十条",
      "労働契約法20条は令和2年4月に削除され、パート・有期法8条・9条へ移った"),
 (52, "健保", r"被扶養者.{0,80}(国内に住所|国内居住)|(国内に住所|国内居住).{0,80}被扶養者",
      "被扶養者の国内居住要件は令和2年4月から。それ以前の回にはこの要件が無い"),
 (53, "一般", r"70歳までの就業確保|創業支援等措置",
      "70歳までの就業確保措置（努力義務）は令和3年4月から"),
 (54, "厚年", r"支給停止調整開始額|" + D + r"28万円",
      "60歳台前半の在職老齢年金の基準額は令和4年4月に28万円から47万円へ。令和8年4月からは65万円"),
 (54, "国年|厚年", r"(繰下げ|繰上げ).{0,60}(申出|限度|上限|減額|増額|" + D + r"75歳|" + D + r"0\.[457])",
      "繰下げの上限は令和4年4月から75歳。繰上げの減額率は昭和37年4月2日以後生まれが1月あたり0.4％"),
 (54, "健保", r"傷病手当金.{0,60}(1年6|一年六)",
      "傷病手当金の支給期間の通算化は令和4年1月から。それ以前は暦の上での1年6か月"),
 (54, "健保", r"任意継続被保険者.{0,40}(2年|二年)|(2年|二年).{0,24}任意継続被保険者",
      "任意継続被保険者は令和4年1月から申出により脱退できる。それ以前は原則2年間抜けられなかった"),
 (55, "雇用", r"育児休業給付金.{0,80}(1回|一回|分割|回数)|(1回|一回|分割).{0,40}育児休業給付金",
      "育児休業給付は令和4年10月から分割取得ができ、出生時育児休業給付金が加わった"),
 (57, "健保|厚年", D + r"(501|101|100|51|50)人|特定適用事業所.{0,60}" + D + r"\d+人",
      "短時間労働者の適用拡大の人数要件は、平成28年10月に501人超、令和4年10月に101人超、令和6年10月に51人超と変わってきた。出題年で数字が違う"),
 (55, "一般", r"後期高齢者.{0,60}(1割|一割)",
      "後期高齢者医療の2割負担（一定以上所得者）は令和4年10月から"),
 (57, "雇用", r"給付制限.{0,24}(2箇月|2か月|3箇月|3か月)|(2箇月|3箇月)間.{0,16}給付制限",
      "自己都合離職の給付制限は令和7年4月から原則1か月。過去問はすべて旧法（2か月・3か月）"),
 (57, "雇用", r"高年齢雇用継続.{0,80}(100分の15|" + D + r"15％|" + D + r"15%)",
      "高年齢雇用継続基本給付金の給付率の上限は令和7年4月から10％。過去問はすべて旧法（15％）"),
 (58, "", r"懲役|禁錮|禁こ",
      "令和7年6月から拘禁刑に一本化。条文の「懲役」「禁錮」はいまは「拘禁刑」"),
 (58, "厚年", r"(分割|按分割合).{0,60}(2年を経過|請求すべき期限)|(2年を経過|請求すべき期限).{0,60}分割",
      "離婚時分割の請求期限は令和8年4月から5年（旧2年）"),
 (58, "労災", r"315,000|三十一万五千|" + D + r"31万5",
      "労災の葬祭料（葬祭給付）の定額部分は330,000円。旧315,000円"),
 (58, "厚年", r"支給停止調整額",
      "在職老齢年金の支給停止調整額は令和8年4月から65万円"),
]

def main():
    out, cnt, sample = {}, collections.Counter(), {}
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
        for i, q in enumerate(arr):
            src = str(q.get("src", ""))
            mm = re.search(r"第(\d+)回", src)
            if not mm:
                continue
            kai = int(mm.group(1))
            body = " ".join(str(q.get(k, "")) for k in ("q", "stem", "head", "tail"))
            body += " ".join(str(x) for x in (q.get("choices") or []))
            body = re.sub(r"\s+", "", body)
            subj = m.group(1)
            hits = [(note, re.search(pat, body)) for since, sub, pat, note in CHANGES
                    if kai < since and (not sub or re.search(sub, subj))
                    and re.search(pat, body)]
            if hits:
                out[f"{subj}#{i}"] = hits[0][0]
                cnt[hits[0][0][:26]] += 1
                sample.setdefault(hits[0][0][:26], []).append(
                    (src, hits[0][1].group(0), body[max(0, hits[0][1].start() - 26):hits[0][1].start() + 34]))
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("/* 改正で答えが変わった過去問。kakomon/stale.py が作る。 */\n")
        fh.write("window.STALE = " + json.dumps(out, ensure_ascii=False, indent=0) + ";\n")
    print(f"→ {OUT}  {len(out)}問に注意書きを付けた / {os.path.getsize(OUT):,} bytes")
    for k, v in cnt.most_common():
        print(f"   {v:4d}問  {k}…")
    if "-v" in sys.argv:                    # 取り違えていないか、当たった箇所を見る
        for k, rows in sample.items():
            print(f"\n■ {k}…")
            for src, got, ctx in rows[:3]:
                print(f"   [{src[:26]}] 「{got}」 …{ctx}…")

if __name__ == "__main__":
    main()
