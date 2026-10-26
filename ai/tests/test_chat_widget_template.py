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
