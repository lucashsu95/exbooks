/**
 * Exbooks PWA Service Worker
 * 處理快取策略與 Web Push 通知
 */

const CACHE_NAME = 'exbooks-v2';
const STATIC_CACHE_NAME = 'exbooks-static-v2';
const DYNAMIC_CACHE_NAME = 'exbooks-dynamic-v2';

// 靜態資源（安裝時預先快取）
const STATIC_ASSETS = [
  '/',
  '/static/manifest.json',
  'https://cdn.tailwindcss.com',
  'https://fonts.googleapis.com/css2?family=Work+Sans:wght@300;400;500;600;700&display=swap',
  'https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght@100..700,0..1&display=swap',
  'https://unpkg.com/htmx.org@2.0.4',
];

// 安裝事件 - 預先快取靜態資源
self.addEventListener('install', (event) => {
  console.log('[SW] 安裝中...');
  event.waitUntil(
    caches.open(STATIC_CACHE_NAME).then((cache) => {
      console.log('[SW] 預先快取靜態資源');
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// 啟用事件 - 清理舊快取
self.addEventListener('activate', (event) => {
  console.log('[SW] 啟用中...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((name) => name !== STATIC_CACHE_NAME && name !== DYNAMIC_CACHE_NAME)
          .map((name) => {
            console.log('[SW] 清理舊快取:', name);
            return caches.delete(name);
          })
      );
    })
  );
  self.clients.claim();
});

// 請求攔截 - 網路優先策略（動態內容）+ 快取優先策略（靜態資源）
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // API 請求 - 網路優先
  if (url.pathname.startsWith('/api/') || url.pathname.startsWith('/deals/') || url.pathname.startsWith('/books/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // 靜態資源 - 快取優先
  if (request.destination === 'style' || request.destination === 'script' || request.destination === 'font') {
    event.respondWith(cacheFirst(request));
    return;
  }

  // 其他請求 - 網路優先
  event.respondWith(networkFirst(request));
});

// 快取優先策略
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(STATIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[SW] 快取優先策略失敗:', error);
    return new Response('離線中', { status: 503 });
  }
}

// 網路優先策略
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok && request.method === 'GET') {
      const cache = await caches.open(DYNAMIC_CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    console.error('[SW] 網路優先策略失敗:', error);
    return new Response('離線中', { status: 503 });
  }
}

// ============================================
// Web Push 通知處理
// ============================================

// 接收 Push 訊息
self.addEventListener('push', (event) => {
  console.log('[SW] 收到 Push 訊息');

  let notificationData = {
    title: 'Exbooks 通知',
    body: '您有新訊息',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/badge-72.png',
    tag: 'exbooks-notification',
    data: {
      url: '/',
    },
  };

  // 解析伺服器傳來的資料
  if (event.data) {
    try {
      const data = event.data.json();
      notificationData = {
        title: data.title || notificationData.title,
        body: data.message || data.body || notificationData.body,
        icon: notificationData.icon,
        badge: notificationData.badge,
        tag: `exbooks-${data.notification_type || 'default'}`,
        data: {
          url: data.url || '/',
          dealId: data.deal_id,
          bookId: data.book_id,
        },
      };
    } catch (e) {
      console.error('[SW] 解析 Push 資料失敗:', e);
    }
  }

  const options = {
    body: notificationData.body,
    icon: notificationData.icon,
    badge: notificationData.badge,
    tag: notificationData.tag,
    vibrate: [100, 50, 100], // 震動模式
    requireInteraction: true, // 需要用戶互動才關閉
    actions: [
      { action: 'view', title: '查看' },
      { action: 'dismiss', title: '忽略' },
    ],
    data: notificationData.data,
  };

  event.waitUntil(self.registration.showNotification(notificationData.title, options));
});

// 通知點擊事件
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] 通知被點擊:', event.action);
  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  // 預設行為：跳轉到相關頁面
  const urlToOpen = event.notification.data?.url || '/';

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // 檢查是否已有開啟的視窗
      for (const client of windowClients) {
        if (client.url.includes(self.location.origin) && 'focus' in client) {
          client.navigate(urlToOpen);
          return client.focus();
        }
      }
      // 沒有開啟的視窗，開啟新視窗
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen);
      }
    })
  );
});

// 通知關閉事件
self.addEventListener('notificationclose', (event) => {
  console.log('[SW] 通知被關閉');
  // 可以在這裡追蹤用戶關閉通知的行為
});

// ============================================
// 推播訂閱管理
// ============================================

// 訂閱過期或失效時的處理
self.addEventListener('pushsubscriptionchange', (event) => {
  console.log('[SW] Push 訂閱變更');
  // 重新訂閱的邏輯會在前端處理
});
