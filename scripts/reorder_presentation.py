#!/usr/bin/env python3
"""
Reorder presentation-0701.md sections and fix heading levels.
"""

import re
from pathlib import Path

SRC = Path("docs/presentation-0701.md")

# Read file
content = SRC.read_text(encoding="utf-8")
lines = content.splitlines(keepends=True)

# Find all h1 section boundaries
sections = []
current_start = 0
for i, line in enumerate(lines):
    if line.startswith("# ") and i > 0:
        sections.append((current_start, i))
        current_start = i
sections.append((current_start, len(lines)))

# Extract section texts
section_texts = []
for start, end in sections:
    section_texts.append("".join(lines[start:end]))

# Map: index -> (title, text)
index_map = {}
for idx, text in enumerate(section_texts):
    title = text.strip().split("\n")[0]
    index_map[idx] = (title, text)

# Fix heading levels in specific sections
def fix_heading_level(text, old_prefix, new_prefix):
    """Replace old_prefix headings with new_prefix, but only standalone lines."""
    result = []
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        if stripped.startswith(old_prefix) and not stripped.startswith(old_prefix + "-"):
            line = line.replace(old_prefix, new_prefix, 1)
        result.append(line)
    return "".join(result)

# New order:
# 0: Front matter (keep first)
# 1: Lead title (keep)
# 2: TOC (will regenerate)
# 3: 執行摘要
# 4: AI 聊天機器人
# 5: AI 核心技術細節
# 6: 企業級觀測性與日誌
# 7: 三層日誌怎麼分流？ -> fix sub-headings to h2
# 8: 這行決定... -> h2
# 9: 寫入時自動... -> h2
# 10: 生產環境... -> h2
# 11: 一圖看懂
# 12: 可觀測性證據
# 13: 效能與架構改善 (moved before k6)
# 14: Celery
# 15: 壓力測試 k6 (moved after Celery)
# 16: 資安與合規強化
# 17: nginx -> h2
# 18: exbook/settings.py -> h2
# 19: exbook/prod_settings.py -> h2
# 20: 架構總覽圖
# 21: 媒體雙軌
# 22: book_photo.py -> h2
# 23: views.py -> h2
# 24: 物件儲存選型
# 25: Mailpit
# 26: 問題與討論

# Fix sub-headings in observability section (sections 8,9,10)
for idx in [8, 9, 10]:
    section_texts[idx] = fix_heading_level(section_texts[idx], "# ", "### ")

# Fix sub-headings in security section (sections 17,18,19)
for idx in [17, 18, 19]:
    section_texts[idx] = fix_heading_level(section_texts[idx], "# ", "### ")

# Fix sub-headings in media section (sections 22,23)
for idx in [22, 23]:
    section_texts[idx] = fix_heading_level(section_texts[idx], "# ", "### ")

# Create the new Django mail section
new_mail_section = """<!-- _note: Exbooks 的通知系統採用 Django + Celery 的非同步郵件發送。當交易狀態改變、到期提醒、註冊驗證時，系統不會阻塞主執行緒，而是把郵件任務丟進 Redis，由 Celery Worker 在背景發送。 -->

# Django 怎麼發信？

**Celery + Django send_mail，非同步不阻塞**

### 發信流程

<div class="columns">
<div class="card">
<h3>1️⃣ 觸發事件</h3>
<p>交易建立、到期提醒、註冊驗證</p>
</div>
<div class="card">
<h3>2️⃣ 通知服務</h3>
<p><code>notify()</code> 檢查用戶設定</p>
<p>決定要不要發 Email</p>
</div>
<div class="card">
<h3>3️⃣ Celery 排隊</h3>
<p><code>send_email.delay()</code></p>
<p>任務進 Redis，立即回傳</p>
</div>
<div class="card">
<h3>4️⃣ Worker 發送</h3>
<p>Django <code>send_mail()</code></p>
<p>透過 Mailpit / SMTP</p>
</div>
</div>

---

### 程式碼：通知服務層

```python
# deals/services/notification_service.py
def notify(recipient, title, message, send_email=True, ...):
    # 1. 寫入資料庫（通知列表）
    notification = Notification.objects.create(...)
    
    # 2. 檢查用戶是否啟用 Email 通知
    if send_email and profile.email_notifications_enabled:
        # 3. 丟進 Celery，不阻塞
        send_email_notification_task.delay(
            user_id=recipient.pk,
            title=title,
            message=message,
        )
```

---

### 程式碼：Celery 郵件任務

```python
# deals/tasks.py
@shared_task(
    name="deals.send_email_notification",
    bind=True,
    max_retries=3,          # 失敗重試 3 次
    default_retry_delay=10,  # 每次間隔 10 秒
)
def send_email_notification_task(self, user_id, title, message):
    """非同步發送 Email 通知。"""
    user = User.objects.get(pk=user_id)
    
    if not user.email:
        return
    
    try:
        send_mail(
            subject=f"[Exbooks] {title}",
            message=message or title,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
    except Exception as exc:
        # 發送失敗 → 自動重試
        raise self.retry(exc=exc)
```

---

### 設定：Django Email

```python
# exbook/settings.py
EMAIL_BACKEND = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",  # 開發：印到終端
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "mailpit")   # Docker: mailpit
DEFAULT_FROM_EMAIL = "Exbooks <noreply@exbook.example.com>"
```

---

### 何時會收到信？

| 事件 | 收件人 | 內容 |
|------|--------|------|
| 交易被接受 | 申請人 | 「對方已同意你的借閱申請」 |
| 3 天後到期 | 借閱人 | 「書籍即將到期，請安排歸還」 |
| 註冊驗證 | 新用戶 | 「點擊連結完成信箱驗證」 |
| 信任分變動 | 用戶 | 「你的信任分數已更新」 |

> **失敗重試**：郵件發不出去時自動重試 3 次，確保重要通知不遺失。

---

"""

# New order
new_order = [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 13, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26]

# Insert new mail section after AI 核心技術細節 (index 5 in original = position 5 in new_order)
# Actually: new_order positions: 0=front, 1=lead, 2=exec_summary, 3=ai, 4=ai_detail, 5=obs, ...
# Wait, I need to insert the new section. Let me build the new content piece by piece.

ordered_sections = []
for idx in new_order:
    ordered_sections.append(section_texts[idx])

# Insert mail section after AI 核心技術細節 (which is at position 4 in ordered_sections)
# Actually the new section should go between AI core tech and observability
# In the new_order: [..., 4(ai_detail), 5(obs), ...]
# So I insert after position 4 in the ordered list
ordered_sections.insert(5, new_mail_section)

# Regenerate TOC section
new_toc = """# 目錄

<div class="columns">
<div>

### 上半場：新功能與基礎設施

1. **執行摘要**
2. **AI 聊天機器人** — Gemini 整合
3. **Django 發信機制** — Celery 非同步郵件
4. **觀測性與日誌**
   - 三層日誌分流
   - E2E 驗證儀表板

</div>
<div>

### 下半場：效能、架構與安全

5. **效能與架構改善**
6. **Celery 非同步任務**
7. **壓力測試** — k6 腳本
8. **資安與合規強化**
9. **架構總覽**
   - 全系統視角
   - 媒體雙軌存取
   - MinIO 選型
10. **開發工具 Mailpit**

</div>
</div>

---

"""

# Replace TOC (section 2 in original = position 1 in ordered_sections since 0=front matter, 1=lead)
# Actually front matter (0) + lead (1) + TOC (2) -> in new order: [0, 1, 3, ...]
# So TOC is at position 1 in ordered_sections (index 2 from original)
ordered_sections[1] = new_toc

# Combine
new_content = "".join(ordered_sections)

# Write back
SRC.write_text(new_content, encoding="utf-8")
print(f"✅ Reordered {len(ordered_sections)} sections into {SRC}")
