// Remi Dashboard - Service Worker
// オフライン対応 + PWAインストール強化
const CACHE_NAME = 'remi-v2';
const CACHE_URLS = ['/dashboard', '/manifest.json'];

self.addEventListener('install', e => {
    e.waitUntil(
        caches.open(CACHE_NAME).then(c => c.addAll(CACHE_URLS)).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', e => {
    e.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        ).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', e => {
    const url = new URL(e.request.url);
    // API calls: network only (status, actions, etc.)
    if (url.pathname.startsWith('/status') || url.pathname.startsWith('/task') ||
        url.pathname.startsWith('/action') || url.pathname.startsWith('/chat') ||
        url.pathname.startsWith('/notif') || url.pathname.startsWith('/tts') ||
        url.pathname.startsWith('/health') || url.pathname.startsWith('/emergency')) {
        return;
    }
    // Dashboard & manifest: network first, fallback to cache
    e.respondWith(
        fetch(e.request).then(res => {
            const clone = res.clone();
            caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
            return res;
        }).catch(() => caches.match(e.request))
    );
});
