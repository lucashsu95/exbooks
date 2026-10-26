from django.test import TestCase

from tests.factories import UserFactory


class ChatWidgetTemplateTests(TestCase):
    def test_widget_renders_plain_text_and_error_frames(self):
        """模板契約 pin：訊息氣泡必須純文字渲染（防 XSS 回歸）、錯誤幀顯示 error 而非 undefined。"""
        user = UserFactory()
        self.client.force_login(user)

        response = self.client.get("/books/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()

        self.assertIn('x-text="msg.content"', html)
        self.assertNotIn("x-html", html)
        self.assertIn("data.error ?? data.result", html)

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
