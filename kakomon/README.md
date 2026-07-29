# kakomon — 過去問データの生成

本試験のPDFから問題・正答を取り出し、アプリ用のデータと資料を組み立てる。

## 元データの取得

`pdf/` と `txt/` はリポジトリに含めていない。
[社会保険労務士試験オフィシャルサイト](https://www.sharosi-siken.or.jp/) から
第49〜57回の「択一式」「選択式」「合格基準及び正答」のPDFを `pdf/` に置き、
`extract.py` でテキスト化してから以下を実行する。

## 生成の順番

| スクリプト | 出力 | 内容 |
|---|---|---|
| `parse_seitou.py` | `seitou.json` | 正答表。列座標＋DPで欠けたセルを補う |
| `parse_mondai.py` | `mondai.json` | 問題文と選択肢 |
| `gen_data.py` | `drill/data/kako-*.js` | 択一630問・選択式72問・肢別○×2,580問 |
| `gen_tokuten.py` | `notes/96-得点源リスト.md` | 論点のS/A/B/Cランクと出題傾向の分析 |
| `gen_hikkake.py` | `notes/97-引っかけの型.md` | 誤り肢の改変パターン |
| `gen_seibun.py` | `notes/A0-正文集.md` | 正誤が確定した正しい肢 |
| `gen_kosuu.py` | `notes/A1-個数・組合せ問題の解き方.md` | 選択肢構造の解析 |
| `gen_genbun.py` | `notes/95-条文素読.md` | 選択式の原文（正答を埋め戻したもの） |
| `gen_trend.py` | `notes/0*.md`, `10-*.md` | 各科目ノートの「出題傾向」節 |
| `gen_stats.py` | `drill/data/stats.js` | 傾向タブ用の統計 |
| `gen_notes.py` | `drill/data/notes.js` | `notes/*.md` をアプリに埋め込む |

**`notes/` のうち 95・96・97・A0・A1 と、各科目ノートの `<!-- TREND -->` 節は自動生成。**
直接編集しても再生成で消えるので、生成スクリプト側を直すこと。

## 検査

`review_notes.py` `review2.py` `review3.py` `review4.py` `review5.py`
資料の穴を別々の観点から機械的に洗い出す。
