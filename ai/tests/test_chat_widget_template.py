from django.test import TestCase
from pathlib import Path

import json
import os
import re
import shutil
import subprocess
import tempfile

from tests.factories import UserFactory

_NODE = shutil.which("node")

# 「喵」彩蛋的完整模型回覆（與 ai/services/chat_service.py 的 easter egg 一致）：
# stripMarkdown 必須原樣通過（迴歸防護）。
_MEOW_EASTER_EGG = (
    "喵～你發現了隱藏彩蛋！\n\n"
    "    /|_╱|\n"
    "   ( •̀ㅅ •́ )\n"
    "  ＿ノ ヽ ノ＼＿\n"
    " /　`/ ⌒Ｙ⌒ Ｙ　 \\\n"
    "( 　(三ヽ人　 /　 　|\n"
    "|　ﾉ⌒＼ ￣￣ヽ　 ノ\n"
    "ヽ＿＿＿＞､＿＿／\n\n"
    "這隻貓咪是 Exbooks 的守護靈，謝謝你來分享書籍 🐾"
)


def _read_widget_template() -> str:
    return (
        Path(__file__).resolve().parent.parent / "templates" / "ai" / "_chat_widget.html"
    ).read_text(encoding="utf-8")


def _extract_script(html: str) -> str:
    m = re.search(r"<script>(.*?)</script>", html, re.S)
    assert m, "widget template 缺少 <script> 區塊"
    return m.group(1)


def _run_node_strip(script: str, cases: list[tuple[str, str]]) -> subprocess.CompletedProcess:
    """把模板裡的 stripMarkdown 與一組 (input, expected) 用 node 實跑。"""
    driver = (
        "const cases = "
        + json.dumps(cases, ensure_ascii=False)
        + ";\n"
        "for (const [input, expected] of cases) {\n"
        "    const got = stripMarkdown(input);\n"
        "    if (got !== expected) {\n"
        "        console.log(JSON.stringify({input: input, expected: expected, got: got}));\n"
        "        process.exitCode = 1;\n"
        "    }\n"
        "}\n"
    )
    fd, js_path = tempfile.mkstemp(suffix=".js", encoding="utf-8")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(script)
        f.write("\n")
        f.write(driver)
    try:
        return subprocess.run(
            [_NODE, js_path], capture_output=True, text=True, timeout=30
        )
    finally:
        os.unlink(js_path)


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

    def test_strip_markdown_behavior(self):
        """行為契約（D3 邊界）：stripMarkdown 用 node 實跑真實輸入。

        上面的模板 pin 只斷言函式存在，抓不到 regex 的誤傷/漏剝。
        這裡以 node 實跑：
        - 整行 |a| = |b|（絕對值式）不得被當表格行扁平化
        - 行首 >>>（REPL/shell 提示）不得被引用 regex 吃掉字元
        - ``` 代碼塊：fence 行移除，但內部反引號/表格樣行不被剥
        - ** 跨單行換行要剥；空行（段落界）是界線
        - 行首 > 只在「>+空白」時才剝
        """
        if not _NODE:
            self.skipTest("stripMarkdown 行為測試需要 node")
        script = _extract_script(_read_widget_template())
        cases: list[tuple[str, str]] = [
            # PR 原目標：段標粗體
            ("**書籍相關**\n- 書A\n- 書B", "書籍相關\n- 書A\n- 書B"),
            # 絕對值式：整行 | 開頭且結尾，但不是表格（無分隔線上下文）
            ("|a| = |b|", "|a| = |b|"),
            # REPL 提示行：>>> 不得被吃掉一層
            (">>> print(1)", ">>> print(1)"),
            # 正常引用仍剝
            ("> 引用文字", "引用文字"),
            # 無空格的行首 > 不是引用（只在「>+空白」才剝）
            (">無空格引用", ">無空格引用"),
            # 跨單行換行的粗體要剥
            ("**跨行粗體\n第二行**", "跨行粗體\n第二行"),
            # 跨空行（段落界）不是粗體（CommonMark 的 emphasis 也不跨段）
            ("第一段 **未閉合\n\n新段落** 文字", "第一段 **未閉合\n\n新段落** 文字"),
            # 代碼塊：fence 行移除，內部反引號原樣
            ("```js\nconst a = `x`;\n```", "const a = `x`;"),
            # 代碼塊內的表格樣行不動
            ("```\n| a | b |\n```", "| a | b |"),
            # 真表格（含分隔線）仍扁平化
            (
                "| 書名 | 狀態 |\n| --- | --- |\n| 書A | 持有中 |",
                "書名 狀態\n書A 持有中",
            ),
            # 表格 cell 內的粗體先剥再扁平化
            (
                "**粗體** 標題\n| **A** | B |\n| --- | --- |\n| 1 | 2 |",
                "粗體 標題\nA B\n1 2",
            ),
            # 「喵」彩蛋原樣通過
            (_MEOW_EASTER_EGG, _MEOW_EASTER_EGG),
        ]
        proc = _run_node_strip(script, cases)
        self.assertEqual(
            proc.returncode,
            0,
            f"stripMarkdown 邊界失守：{proc.stdout.strip() or proc.stderr.strip()}",
        )
