# Google OAuth 2.0 設定指南

本指南說明如何設定 Google OAuth 2.0 以用於 Exbooks 認證。

## 1. 建立 Google Cloud 專案

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)
2. 點擊頂部的專案選擇器，然後點擊「新增專案」
3. 輸入專案名稱（例如：`exbooks-auth`），點擊「建立」

## 2. 設定 OAuth 同意畫面

1. 在左側選單中，前往「API 和服務」→「OAuth 同意畫面」
2. 選擇用戶類型：「外部」（開發階段），點擊「建立」
3. 填寫應用程式資訊：
   - **應用程式名稱**：Exbooks 共享書籍
   - **使用者支援電子郵件**：你的信箱
   - **應用程式標誌**：（可選）
   - **應用程式首頁連結**：`http://localhost:8000`
   - **應用程式隱私權政策連結**：（開發階段可留空）
   - **應用程式服務條款連結**：（開發階段可留空）
   - **授權範圍**：
     - `.../auth/userinfo.email`
     - `.../auth/userinfo.profile`
     - `openid`
4. 點擊「儲存並繼續」

## 3. 建立 OAuth 2.0 憑證

1. 在左側選單中，前往「API 和服務」→「憑證」
2. 點擊上方的「建立憑證」→「OAuth 用戶端 ID」
3. 選擇應用程式類型：「網頁應用程式」
4. 填寫以下資訊：
   - **名稱**：Exbooks 本地開發
   - **已授權的 JavaScript 來源**：
     - `http://localhost:8000`
   - **已授權的重導 URI**：
     - `http://localhost:8000/accounts/google/login/callback/`
5. 點擊「建立」
6. 記下顯示的 **用戶端 ID** 和 **用戶端密碼**

## 4. 設定環境變數

在 `.env` 檔案中填入憑證資訊：

```env
GOOGLE_CLIENT_ID=你的用戶端ID
GOOGLE_CLIENT_SECRET=你的用戶端密碼
```

## 5. 在 Django Admin 設定 Social Application

1. 啟動開發伺服器：
   ```bash
   python manage.py runserver
   ```

2. 前往 Django Admin：http://localhost:8000/admin/

3. 在「Social applications」中點擊「Add」

4. 填寫以下資訊：
   - **Provider**：Google
   - **Name**：Google（或任何識別名稱）
   - **Client id**：你的用戶端 ID
   - **Secret key**：你的用戶端密碼
   - **Key**：留空
   - **Sites**：選擇 `example.com`（或你的站點）

5. 點擊「儲存」

## 6. 測試 Google 登入

1. 前往登入頁面：http://localhost:8000/accounts/login/
2. 點擊「使用 Google 帳號登入」按鈕
3. 應該會重導到 Google 登入頁面
4. 選擇你的 Google 帳號後，會重導回 Exbooks

## 常見問題

### Q: 顯示「重導 URI 不符」錯誤

請確認 Google Cloud Console 中的「已授權的重導 URI」完全符合：
- `http://localhost:8000/accounts/google/login/callback/`

注意結尾的 `/` 是必要的。

### Q: 顯示「存取遭拒」錯誤

請確認：
1. OAuth 同意畫面已正確設定
2. 你的 Google 帳號已加入測試使用者（如果是 Testing 模式）

### Q: 本地開發需要 HTTPS 嗎？

不需要。本地開發可以使用 `http://localhost`。但在正式環境必須使用 HTTPS。

## 正式環境設定

正式環境的設定流程相同，但需注意：

1. **授權 JavaScript 來源**：使用正式網域名稱
   - `https://your-domain.com`

2. **授權重導 URI**：
   - `https://your-domain.com/accounts/google/login/callback/`

3. **建立新的 OAuth 憑證**：建議為正式環境建立獨立的憑證

4. **OAuth 同意畫面**：需要進行驗證（如果用戶數量較多）

## 參考資料

- [django-allauth 官方文件](https://docs.allauth.org/)
- [Google OAuth 2.0 文件](https://developers.google.com/identity/protocols/oauth2)
