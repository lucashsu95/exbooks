from django.test import TestCase

from tests.factories import UserFactory


class ChatWidgetTemplateTests(TestCase):
    def test_widget_renders_plain_text_and_ignores_tool_result(self):
        """模板契約 pin：訊息氣泡必須純文字渲染（防 XSS 回歸）；
        tool_result 幀留在 wire 上但 UI 不渲染（D1：不得出現「Tool result:」debug 氣泡）。"""
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.get("/books/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertIn('x-text="msg.content"', html)
        self.assertNotIn("x-html", html)
        self.assertNotIn("tool_result", html)

    def test_message_content_preserves_line_breaks(self):
        """契約 pin：訊息內容 div 需 whitespace-pre-line。

        LLM 回覆與「喵」彩蛋（ASCII 貓）都含換行；沒有 pre-line 時
        瀏覽器會把換行折成空白，整段擠成一行。
        """
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.get("/books/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertIn('<div x-text="msg.content" class="whitespace-pre-line">', html)

    def test_consent_buttons_bound_to_own_message(self):
        """契約 pin：consent 按鈕綁定該訊息自己的 token/state，
        不透過全域 pendingAction（舊氣泡誤執行新 token 的回歸防護）。"""
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.get("/books/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertNotIn("pendingAction", html)
        self.assertIn("sendAction(msg, 'confirm')", html)
        self.assertIn("sendAction(msg, 'cancel')", html)
        self.assertIn("msg.consentState !== 'pending'", html)

    def test_open_chat_scrolls_to_bottom(self):
        """契約 pin（D2）：打開視窗的路徑自己負責捲到底部。
        回訪使用者的 hello 已被 dedup，addMessage 裡的捲動不會觸發
        （實測 scrollTop 0 / max 1730）。"""
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.get("/books/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertIn("scrollToBottom", html)
        # 兩個呼叫點：toggleChat 打開路徑 + addMessage（共用同一實作）
        self.assertGreaterEqual(
            html.count("this.$nextTick(() => this.scrollToBottom())"), 2
        )

    def test_load_history_guarded(self):
        """契約 pin（健壯性）：損壞的 localStorage 不得在 init() 拋錯、
        永久殺掉 bindOpenChat（實測：點貓完全沒反應）。"""
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.get("/books/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertIn("Array.isArray", html)
        # guard 與 clearHistory 各有一處 removeItem
        self.assertGreaterEqual(
            html.count("localStorage.removeItem('chat_history')"), 2
        )

    def test_widget_strips_markdown_markers(self):
        """契約 pin（D3）：LLM 文字氣泡進 addMessage 前須剥掉 Markdown 記號。

        5 輪真實 LLM 量測：BIRC-LLM 每個清單型答案都帶 ** 粗體段標，
        prompt-only（規則／負例／few-shot 共 5 版）都無法壓掉。
        氣泡維持 x-text 純文字渲染（防 XSS 契約不變、零新依賴），
        所以改在 client 端 strip 記號。
        """
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.get("/books/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertIn("function stripMarkdown(text)", html)
        # 只對 assistant 文字訊息套用（使用者輸入與 consent 氣泡不碰）
        self.assertIn("content = stripMarkdown(content)", html)
        # 渲染契約保持：仍是 x-text 純文字，沒有 x-html
        self.assertIn('x-text="msg.content"', html)
        self.assertNotIn("x-html", html)
