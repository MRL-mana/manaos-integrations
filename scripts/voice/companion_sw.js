// ManaOS コンパニオン用 簡易サービスワーカー（オフラインキャッシュ）
const CACHE = 'manaos-companion-v1';
self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(CACHE).then(function (cache) {
    return cache.addAll(['/companion']);
  }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) { return k !== CACHE; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener('fetch', function (e) {
  if (e.request.url.indexOf('/companion') !== -1 && e.request.mode === 'navigate') {
    e.respondWith(fetch(e.request).catch(function () {
      return caches.match('/companion');
    }));
  }
});
