/* オフラインでも開けるようにする。
 * 電車内など回線がないところで開いても、問題も資料も出る状態にしたい。
 *
 * 方針
 *  - HTML は「通信を先に試す」。更新がすぐ届くようにする
 *  - データ（約3.9MB）と画像は「キャッシュを先に返し、裏で取り直す」。
 *    表示は即座に、次に開いたときには最新になる
 *  - バージョンが変わったら古いキャッシュを消す
 */
const VERSION = "9dc81978e502";
const CACHE   = "sharoushi-" + VERSION;

self.addEventListener("install", () => self.skipWaiting());

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)));
    await self.clients.claim();
  })());
});

const isAsset = url => /\/data\/.*\.js$/.test(url.pathname) || /\/icon\//.test(url.pathname);

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  if (url.pathname.startsWith("/api/")) return;        // 同期は必ず通信する

  if (isAsset(url)) {
    e.respondWith((async () => {
      const cache = await caches.open(CACHE);
      const hit = await cache.match(req);
      const net = fetch(req).then(res => {
        if (res && res.ok) cache.put(req, res.clone());
        return res;
      }).catch(() => null);
      return hit || (await net) || new Response("", { status: 504 });
    })());
    return;
  }

  e.respondWith((async () => {
    const cache = await caches.open(CACHE);
    try {
      const res = await fetch(req);
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    } catch (err) {
      return (await cache.match(req)) || (await cache.match("./")) ||
             new Response("オフラインです", { status: 503 });
    }
  })());
});
