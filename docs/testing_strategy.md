# Views 測試策略（提升覆蓋率 27-47% → 70%+）

## 現況分析（2026-04-03）

| 模組 | 總行數 | 未測試行數 | 覆蓋率 | 主要缺口 |
|------|--------|------------|--------|----------|
| accounts/views.py | 132 | 96 | 27% | 使用者設定、個人檔案、停權申訴 |
| books/views.py | 332 | 188 | 43% | 書籍詳情、時間線、願望清單、照片上傳 |
| deals/views.py | 346 | 182 | 47% | 交易列表、通知、延長借閱、評價 |

**總計：** 810 行程式碼，466 行未測試（42% 覆蓋率）

## 目標

將三個 views 模組的覆蓋率提升至 **70%+**：

1. accounts/views.py：27% → 70%+
2. books/views.py：43% → 70%+
3. deals/views.py：47% → 70%+

## 測試策略

### 1. 測試優先級（P0 最高）

#### P0 - 核心功能（必須有測試）
- **accounts/views.py**：`profile_update`, `settings`, `appeal_*`（停權申訴）
- **books/views.py**：`book_detail`, `timeline`, `wishlist_*`
- **deals/views.py**：`deal_list`, `notification_*`, `extension_*`

#### P1 - 次要功能（重要但不緊急）
- **books/views.py**：`book_photos`, `book_search`, `my_bookshelf`
- **deals/views.py**：`rating_create`, `deal_message_*`

#### P2 - 輔助功能（可延後）
- 靜態頁面、表單 GET 請求、簡單的重導向

### 2. 測試模式

#### Django Test Client 模式
```python
class TestBookDetailView(TestCase):
    def test_get_authenticated(self):
        self.client.login(email="user@example.com", password="password")
        response = self.client.get(reverse("books:book_detail", args=[book_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "書籍詳情")
```

#### FactoryBoy + Fixture 模式
```python
@pytest.fixture
def test_user():
    return UserFactory()

@pytest.mark.django_db
def test_profile_update_authenticated(client, test_user):
    client.force_login(test_user)
    response = client.post(
        reverse("accounts:profile_update"),
        {"nickname": "新暱稱"},
    )
    assert response.status_code == 302  # 重導向
    test_user.profile.refresh_from_db()
    assert test_user.profile.nickname == "新暱稱"
```

#### HTMX 請求測試模式
```python
def test_timeline_htmx_request(self):
    response = self.client.get(
        reverse("books:book_timeline", args=[book_id]),
        HTTP_HX_REQUEST="true",
    )
    # 只返回部分模板，不包含完整頁面
    self.assertTemplateUsed(response, "books/partials/timeline.html")
    self.assertNotContains(response, "<html>")
```

### 3. 測試類別設計

#### accounts/views.py
```python
# 1. ProfileView 測試
class TestProfileView:
    - test_get_authenticated()
    - test_get_unauthenticated_redirects()
    - test_post_update_nickname()
    - test_post_update_availability()
    - test_invalid_form_returns_errors()

# 2. SettingsView 測試  
class TestSettingsView:
    - test_get_authenticated()
    - test_post_update_notification_preferences()
    - test_post_update_privacy_settings()

# 3. Appeal 相關測試
class TestAppealViews:
    - test_appeal_list_authenticated()
    - test_appeal_create_get()
    - test_appeal_create_post()
    - test_appeal_detail_owner_access()
    - test_appeal_detail_non_owner_denied()
    - test_appeal_cancel_owner()
```

#### books/views.py
```python
# 1. BookDetailView 測試
class TestBookDetailView:
    - test_get_authenticated()
    - test_get_with_timeline_htmx()
    - test_get_with_photos_htmx()
    - test_get_wishlist_status_htmx()
    - test_unauthenticated_access()

# 2. TimelineView 測試
class TestTimelineView:
    - test_htmx_request_returns_partial()
    - test_non_htmx_request_redirects()
    - test_timeline_events_ordering()

# 3. Wishlist 相關測試
class TestWishlistViews:
    - test_wishlist_add_authenticated()
    - test_wishlist_remove_authenticated()
    - test_wishlist_list_authenticated()
    - test_wishlist_unauthenticated_redirects()

# 4. BookPhotosView 測試
class TestBookPhotosView:
    - test_get_authenticated()
    - test_photo_upload_post()
    - test_photo_delete_owner()
    - test_photo_delete_non_owner_denied()
```

#### deals/views.py
```python
# 1. DealListView 測試
class TestDealListView:
    - test_get_authenticated()
    - test_filter_by_status()
    - test_tab_switching_htmx()
    - test_search_functionality()

# 2. Notification 相關測試
class TestNotificationViews:
    - test_notification_list_authenticated()
    - test_notification_count_htmx()
    - test_mark_as_read_htmx()
    - test_mark_all_as_read_htmx()

# 3. Extension 相關測試
class TestExtensionViews:
    - test_extension_request_get()
    - test_extension_request_post()
    - test_extension_approve_responder()
    - test_extension_approve_non_responder_denied()
    - test_extension_reject_responder()

# 4. Rating 相關測試
class TestRatingViews:
    - test_rating_create_get()
    - test_rating_create_post()
    - test_rating_create_non_participant_denied()
    - test_rating_create_already_rated_denied()
```

### 4. 特殊案例處理

#### 停權使用者
```python
def test_profile_update_suspended_user(self):
    user = UserFactory()
    user.profile.is_suspended = True
    user.profile.save()
    
    self.client.force_login(user)
    response = self.client.get(reverse("accounts:profile_update"))
    
    # 停權使用者應被重導向到申訴頁面或錯誤頁面
    self.assertEqual(response.status_code, 403)
```

#### 無效 UUID
```python
def test_book_detail_invalid_uuid(self):
    self.client.login(email="user@example.com", password="password")
    response = self.client.get(reverse("books:book_detail", args=["invalid-uuid"]))
    self.assertEqual(response.status_code, 404)
```

#### HTMX 與非 HTMX 請求
```python
def test_deal_list_htmx_vs_normal(self):
    # HTMX 請求
    htmx_response = self.client.get(
        reverse("deals:deal_list"),
        HTTP_HX_REQUEST="true",
    )
    self.assertTemplateUsed(htmx_response, "deals/partials/deal_list.html")
    
    # 正常請求
    normal_response = self.client.get(reverse("deals:deal_list"))
    self.assertTemplateUsed(normal_response, "deals/deal_list.html")
```

### 5. 實施計畫

#### 階段 1：建立基礎測試架構
1. 建立 `accounts/tests/test_views.py`
2. 建立 `books/tests/test_views.py` 
3. 建立 `deals/tests/test_views.py`
4. 建立共用的測試工具函數

#### 階段 2：核心功能測試
1. 實作 P0 測試（每個 view 至少 5-10 個測試）
2. 驗證 authentication/authorization
3. 測試 HTMX 互動

#### 階段 3：覆蓋率提升
1. 針對 coverage 報告中的 missing lines 逐行補齊測試
2. 測試邊界條件和錯誤處理
3. 測試表單驗證

#### 階段 4：整合與驗證
1. 執行完整測試套件
2. 驗證覆蓋率達到 70%+
3. 修復任何測試失敗

### 6. 預期成果

完成後應有：
- **400+ 個新增的 view 測試**
- **覆蓋率從 42% 提升至 70%+**
- **完整的 authentication/authorization 測試**
- **HTMX 互動測試**
- **邊界條件測試**

### 7. 質量檢查清單

- [ ] 每個 view 函數至少有 1 個測試
- [ ] 每個條件分支都有測試覆蓋
- [ ] HTTP 方法（GET/POST）都有測試
- [ ] HTMX 與非 HTMX 請求都有測試
- [ ] 錯誤處理（404, 403, 400）都有測試
- [ ] 表單驗證錯誤都有測試
- [ ] 重導向路徑正確驗證
- [ ] 模板使用正確驗證
- [ ] 上下文資料正確傳遞

---

## 進度追蹤

### 已完成
- [x] 技術債分析
- [x] 核心 constants.py 建立
- [x] Timeline 邏輯萃取到 service
- [x] 違規處理服務單元測試
- [x] 統一例外處理架構
- [x] Deal service 拆分
- [x] 測試套件執行與分析
- [x] 測試檔案格式錯誤修復
- [x] Service 函式型別提示
- [x] 關鍵未測試模組識別
- [x] Deal services 單元測試
- [x] BookTimelineService 單元測試

### 進行中
- [ ] Views 測試策略規劃與實施
- [ ] 所有重構工作驗證

### 預估工作量
- accounts/views.py：96 行未測試 → 需要 20-30 個測試
- books/views.py：188 行未測試 → 需要 40-50 個測試  
- deals/views.py：182 行未測試 → 需要 40-50 個測試
- **總計：約 100-130 個測試需要撰寫**

---

**最後更新：** 2026-04-03  
**負責人：** Sisyphus (AI Agent)  
**狀態：** 策略規劃完成，準備實施