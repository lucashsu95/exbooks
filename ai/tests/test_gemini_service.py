from unittest.mock import MagicMock, patch

from ai.services.gemini_service import GeminiService, GeminiResponse


class TestGeminiService:
    def test_build_tools_openai_format(self):
        """Ensure ToolRegistry tools are correctly converted to OpenAI format."""
        service = GeminiService(api_key="test_key")
        tools = service._build_tools()

        # We expect at least the 3 predefined tools
        assert len(tools) >= 3

        tool_names = [t["function"]["name"] for t in tools]
        assert "get_user_books" in tool_names
        assert "get_borrowing_status" in tool_names
        assert "request_renewal" in tool_names

        # Check structure of one tool
        get_books = next(
            t["function"] for t in tools if t["function"]["name"] == "get_user_books"
        )
        assert "description" in get_books
        assert "parameters" in get_books

    def test_mock_response_when_no_api_key(self, monkeypatch):
        """Without VLLM_API_KEY the service returns a mock response."""
        monkeypatch.delenv("VLLM_API_KEY", raising=False)
        service = GeminiService()
        response = service.chat(user_id=1, message="Hello", history=[])

        assert isinstance(response, GeminiResponse)
        assert "Hello" in response.content
        assert response.tool_calls == []

    def test_chat_uses_sdk_client(self):
        """With an API key the service routes through the ai-client SDK."""
        service = GeminiService(api_key="test_key")

        mock_sdk_response = MagicMock()
        mock_sdk_response.content = "Hi there"
        mock_sdk_response.tool_calls = None
        service._client = MagicMock()
        service._client.chat.return_value = mock_sdk_response

        response = service.chat(user_id=1, message="Hi", history=[])

        assert response.content == "Hi there"
        assert response.tool_calls == []
        service._client.chat.assert_called_once()
        kwargs = service._client.chat.call_args.kwargs
        assert kwargs["temperature"] == 0.7
        assert kwargs["tools"]  # ToolRegistry tools forwarded
        assert kwargs["messages"][0].role == "system"

    def test_chat_parses_tool_calls(self):
        """Tool calls from the SDK response are parsed into name/args dicts."""
        service = GeminiService(api_key="test_key")

        mock_sdk_response = MagicMock()
        mock_sdk_response.content = ""
        mock_sdk_response.tool_calls = [
            {
                "id": "call_1",
                "type": "function",
                "function": {
                    "name": "get_user_books",
                    "arguments": '{"status": "OWNED"}',
                },
            }
        ]
        service._client = MagicMock()
        service._client.chat.return_value = mock_sdk_response

        response = service.chat(user_id=1, message="My books", history=[])

        assert response.tool_calls == [{"name": "get_user_books", "args": {"status": "OWNED"}}]

    @patch("ai.services.tool_registry.ToolRegistry.get_tool")
    def test_handle_function_call(self, mock_get_tool):
        """Test function call execution through service."""
        mock_tool = MagicMock()
        mock_tool.func.return_value = "Success"
        mock_get_tool.return_value = mock_tool

        service = GeminiService(api_key="test_key")
        result = service._handle_function_call("test_tool", {"arg1": "val1"})

        assert result == "Success"
        mock_tool.func.assert_called_once_with(arg1="val1")

    def test_handle_function_call_not_found(self):
        """Test handling of non-existent tools."""
        service = GeminiService(api_key="test_key")
        result = service._handle_function_call("non_existent", {})
        assert "Error" in result
        assert "non_existent" in result
