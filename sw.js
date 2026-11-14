'use strict';
// 電波が弱い場所でも開けるよう、アプリ本体・マニュアル・標準マップ画像を端末に保存する。
// 位置共有(Firebase)と動画(guide.mp4)は対象外で、そのまま通信する。
const APP = 'fm-app-v1', MAP = 'fm-map-v1';
const SHELL = ['./', 'quick.html', 'manual.html', 'guide-poster.jpg'];
const NET_WAIT = 2500; // 通信がこの時間(ms)で返らなければ、保存済みの版を表示する

self.addEventListener('install', e => {
  e.waitUntil(caches.open(APP).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== APP && k !== MAP).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) {
    // 標準マップ画像: 保存済みならそれを使う(URLに版番号が入っており、中身は変わらない前提)
    if (req.destination === 'image') e.respondWith(caches.open(MAP).then(c => c.match(req.url)).then(r => r || fetch(req)));
    return;
  }
  if (url.pathname.endsWith('.mp4') || url.pathname.endsWith('/sw.js')) return;
  e.respondWith(netFirst(e, req, url.origin + url.pathname.replace(/index\.html$/, '')));
});

// 通信を優先し、遅いか失敗したら保存済みの版を返す。成功した応答は保存し直す
async function netFirst(e, req, key) {
  const cache = await caches.open(APP);
  const cached = await cache.match(key);
  const net = fetch(req).then(r => {
    if (r.ok) e.waitUntil(cache.put(key, r.clone()));
    return r;
  });
  if (!cached) return net;
  const r = await Promise.race([net.catch(() => null), new Promise(res => setTimeout(res, NET_WAIT))]);
  return (r && r.ok) ? r : cached;
}

// アプリ側で「画像を正しく表示できた」と確認できたときだけ、マップ画像を保存する
async function saveMap(url) {
  const c = await caches.open(MAP);
  if (await c.match(url)) return true;
  try {
    await c.put(url, await fetch(url, { mode: 'no-cors' }));
    for (const k of await c.keys()) if (k.url !== url) await c.delete(k);
    return true;
  } catch (_) { return false; }
}
self.addEventListener('message', e => {
  const d = e.data || {};
  if (typeof d.url !== 'string') return;
  if (d.type === 'map-ok') e.waitUntil(saveMap(d.url).then(ok => { if (e.source) e.source.postMessage({ type: 'map-saved', ok }); }));
  else if (d.type === 'map-bad') e.waitUntil(caches.open(MAP).then(c => c.delete(d.url)));
});
