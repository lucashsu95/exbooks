# Exbooks Web Push 架構圖

> 以文字圖呈現 Web Push 通知在 Exbooks 中的完整資料流與層級架構。

```
═══════════════════════════════════════════════════════════════════════════════
                               前 端 層  (PWA Browser)
═══════════════════════════════════════════════════════════════════════════════
                                                                                
  ┌──────────────────────────────┐        ┌──────────────────────────────────┐
  │       Web App (JS)           │        │     Service Worker (sw.js)       │
  │                              │        │                                  │
  │  • pushManager.subscribe()   │───────▶│  • push 事件                      │
  │  • pushManager.getSub()      │  註冊   │    → registration.showNotif()   │
  │  • subscription.unsubscribe()│        │  • notificationclick 事件         │
  │                              │        │    → clients.openWindow(url)     │
  └──────────────────────────────┘        └──────────────────────────────────┘
            │                                                       ▲
            │ HTTP / HTTPS                                         │ 無線推送
            ▼                                                       │
═══════════════════════════════════════════════════════════════════════════════
                              視 圖 層  (Django Views)
═══════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐
  │ GET /api/push/        │  │ POST /api/push/      │  │ POST /api/push/      │
  │ vapid-public-key/     │  │ subscribe/           │  │ unsubscribe/          │
  ├──────────────────────┤  ├──────────────────────┤  ├──────────────────────┤
  │ 回傳 VAPID            │  │ 儲存 PushSubscription │  │ is_active = False    │
  │ 公開金鑰              │  │ (update_or_create)    │  │ (軟刪除)              │
  └──────────────────────┘  └──────────┬───────────┘  └──────────────────────┘
                                        │
                                        ▼
═══════════════════════════════════════════════════════════════════════════════
                          業 務 觸 發 源
═══════════════════════════════════════════════════════════════════════════════

  ┌────────────────────┐  ┌────────────────────┐  ┌────────────────────────┐
  │   deal_service     │  │   rating_service   │  │   extension_service    │
  │                    │  │                    │  │                        │
  │ • accept_deal()    │  │ • create_rating()  │  │ • request_extension()  │
  │ • complete_meeting │  │                    │  │ • approve_extension()  │
  │ • cancel_deal()    │  │                    │  │                        │
  └────────┬───────────┘  └────────┬───────────┘  └──────────┬─────────────┘
           │                       │                         │
           │        呼叫 notify_*() 系列函式                     │
           └───────────────────────┼─────────────────────────┘
                                   │
                                   ▼
═══════════════════════════════════════════════════════════════════════════════
                              服 務 層  (Services)
═══════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────────────────────────────────────────────────┐
  │                      notification_service.py                            │
  │                                                                          │
  │  notify(recipient, type, title, message, deal, ...)                     │
  │                                                                          │
  │  • 建立 Notification 資料庫記錄                                           │
  │  • 檢查 user.profile.push_enabled / email_notifications_enabled          │
  │  • 非同步觸發 Celery Task → send_push_notification_task.delay(...)       │
  │                              → send_email_notification_task.delay(...)  │
  │                                                                          │
  │  ┌────────────────────────────────────────────────────────────────────┐  │
  │  │  notify_deal_requested()   │  notify_deal_responded()              │  │
  │  │  notify_deal_cancelled()   │  notify_deal_meeted()                 │  │
  │  │  notify_book_due_soon()    │  notify_book_overdue()                │  │
  │  │  notify_book_available()   │  notify_rating_created()              │  │
  │  │  notify_extend_requested() │  notify_extend_result()               │  │
  │  │  notify_violation_created()│  notify_appeal_status_updated()       │  │
  │  └────────────────────────────────────────────────────────────────────┘  │
  └──────────────────────────┬───────────────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              │  .delay()    │              │  .delay()
              ▼              │              ▼
  ┌──────────────────────┐   │   ┌────────────────────────────┐
  │  Celery Tasks        │   │   │  send_email_notification   │
  │  (tasks.py)          │   │   │  _task                     │
  │                      │   │   └────────────────────────────┘
  │  send_push_          │   │
  │  notification_task   │   │
  │  • bind=True         │   │
  │  • max_retries=3     │   │
  └──────────┬───────────┘   │
             │ 呼叫           │
             ▼               │
  ┌─────────────────────────────────────────────────┐
  │              push_service.py                     │
  │                                                  │
  │  send_push_notification(subscription, title,     │
  │                          message, url, ...)      │
  │    → 使用 pywebpush.webpush() 發送加密 Payload    │
  │    → 410 Gone → 自動停用失效訂閱                   │
  │                                                  │
  │  send_push_to_user(user, title, message, ...)    │
  │    → 遍歷用戶所有 is_active 訂閱                   │
  │                                                  │
  │  generate_vapid_keys()                           │
  │    → 產生 P-256 ECDH 金鑰對                       │
  └──────────────────────┬──────────────────────────┘
                         │
                         │ pywebpush (加密 Payload)
                         ▼
═══════════════════════════════════════════════════════════════════════════════
                         外 部  Push  Service
═══════════════════════════════════════════════════════════════════════════════

  ┌──────────────────────────────────────────────────────────────────────────┐
  │                            Browser Push Service                          │
  │                                                                          │
  │    由瀏覽器決定（Chrome → FCM / Firefox → MozPush / Safari → APNs）       │
  │    你的專案不需關心 endpoint 背後是誰，一律用 pywebpush + VAPID 發送       │
  │                                                                          │
  │    • 接收 VAPID 簽署 + 加密的 Push Payload                                │
  │    • 透過裝置端無線推送至對應瀏覽器                                        │
  │    • 訂閱失效時回傳 410 Gone（push_service 會自動停用該訂閱）               │
  │                                                                          │
  └──────────────────────────────────────────────────────────────────────────┘
                         │
                         │ 無線推送（喚醒 Service Worker）
                         ▼
                 ┌──────────────────┐
                 │  用戶收到通知      │
                 └──────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                             資 料 庫 模 型
═══════════════════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────┐  ┌─────────────────────────────────┐
  │        PushSubscription             │  │        WebPushConfig            │
  ├─────────────────────────────────────┤  ├─────────────────────────────────┤
  │  user          → FK(User)           │  │  vapid_public_key  → CharField │
  │  endpoint      → URLField (unique)  │  │  vapid_private_key → TextField │
  │  p256dh        → CharField          │  │  subject           → URLField  │
  │  auth          → CharField          │  │                                  │
  │  user_agent    → CharField          │  │  Singleton (get_config())       │
  │  is_active     → BooleanField       │  │                                  │
  │                                      │  └─────────────────────────────────┘
  │  subscription_data  → property      │
  │    {endpoint, keys: {p256dh, auth}}  │  ┌─────────────────────────────────┐
  │                                      │  │        Notification             │
  │  Index: (user, is_active)            │  ├─────────────────────────────────┤
  │  Index: (endpoint)                   │  │  recipient       → FK(User)     │
  │  Constraint: unique(endpoint)       │  │  notification_type → Enum        │
  └─────────────────────────────────────┘  │  title            → CharField   │
                                           │  message          → TextField   │
  ┌─────────────────────────────────────┐  │  is_read          → BooleanField│
  │  Management Commands                │  │  deal             → FK(Deal)    │
  ├─────────────────────────────────────┤  │  shared_book      → FK(Shared)  │
  │  python manage.py generate_vapid_   │  └─────────────────────────────────┘
  │    keys [--force] [--subject]       │
  │                                     │
  │  → 寫入 WebPushConfig               │
  │  → 輸出 .env 格式                    │
  └─────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
                             關 鍵 流 程
═══════════════════════════════════════════════════════════════════════════════

  ① 管理員初始化:
     python manage.py generate_vapid_keys
     → 產生 P-256 ECDH 金鑰對 → 存入 WebPushConfig

  ② 前端註冊流程 (用戶同意後):
     GET  /api/push/vapid-public-key/   → 取得 publicKey
     pushManager.subscribe({ userVisibleOnly:true, applicationServerKey })
     POST /api/push/subscribe/          → 儲存 subscription

  ③ 觸發通知 (例如借閱申請送出):
     deal_service.create_deal()
       → notification_service.notify_deal_requested()
         → notify(recipient=responder, type=DEAL_REQUESTED, ...)
           → 建立 Notification 記錄
           → send_push_notification_task.delay(...)
             → push_service.send_push_to_user()
               → pywebpush.webpush(subscription, payload, vapid)
                 → 加密 → POST 到 Push Service endpoint
                   → 無線推送 → Service Worker push 事件
                     → showNotification("收到借閱申請", ...)

  ④ 用戶點擊通知:
     notificationclick 事件
       → clients.openWindow("/deals/{deal_id}/")
       → 瀏覽器打開對應交易頁面

  ⑤ 取消訂閱:
     POST /api/push/unsubscribe/
       → PushSubscription.is_active = False
       → 後續不再發送 (send_push_notification 會跳過)
```
