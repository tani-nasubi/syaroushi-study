/* 学習データの同期。
 * 端末をまたいで進捗を持ち歩くための最小限の置き場。DBスキーマは持たない。
 * 「同期コード」1つに対して JSON を丸ごと1件、読み書きするだけ。
 *
 * 保存先は Vercel の KV（Upstash Redis）を REST 経由で叩く。
 * 依存パッケージなし。Vercel で KV ストアを作れば環境変数は自動で入る。
 * 未設定のときは 501 を返し、アプリ側は同期機能を出さずローカル保存のまま動く。 */
const URL_  = process.env.KV_REST_API_URL;
const TOKEN = process.env.KV_REST_API_TOKEN;

const redis = async (...cmd) => {
  const r = await fetch(URL_, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify(cmd),
  });
  if (!r.ok) throw new Error(`KV ${r.status}`);
  return (await r.json()).result;
};

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");

  if (!URL_ || !TOKEN) {
    return res.status(501).json({ error: "同期用の保存先が未設定です" });
  }

  // 同期コードは利用者が決める合言葉。推測されにくい長さを求める。
  const code = String(req.query.code || "").trim();
  if (!/^[\w-]{8,64}$/.test(code)) {
    return res.status(400).json({ error: "同期コードは英数字・ハイフン・アンダースコアで8〜64文字にしてください" });
  }
  const key = `sharoushi2026:${code}`;

  try {
    if (req.method === "GET") {
      const v = await redis("GET", key);
      return res.status(200).json(v ? JSON.parse(v) : { empty: true });
    }

    if (req.method === "PUT" || req.method === "POST") {
      const body = typeof req.body === "string" ? JSON.parse(req.body) : req.body;
      if (!body || typeof body !== "object") {
        return res.status(400).json({ error: "保存する内容がありません" });
      }
      const payload = JSON.stringify({ ...body, savedAt: Date.now() });
      if (payload.length > 4_000_000) {
        return res.status(413).json({ error: "データが大きすぎます" });
      }
      // 90日で自動的に消える。置きっぱなしにしない。
      await redis("SET", key, payload, "EX", 60 * 60 * 24 * 90);
      return res.status(200).json({ ok: true, savedAt: Date.now() });
    }

    res.setHeader("Allow", "GET, PUT");
    return res.status(405).json({ error: "対応していないメソッドです" });
  } catch (e) {
    return res.status(500).json({ error: "保存先にアクセスできませんでした" });
  }
}
