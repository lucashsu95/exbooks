from unittest.mock import MagicMock, patch
from ai.services.gemini_service import GeminiService, GeminiResponse


class TestGeminiService:
    def test_build_gemini_tools(self):
        """Ensure ToolRegistry tools are correctly converted to Gemini format."""
        service = GeminiService(api_key="test_key")
        tools = service._build_gemini_tools()

        # We expect at least the 3 predefined tools
        assert len(tools) >= 3

        tool_names = [t["function_declaration"]["name"] for t in tools]
        assert "get_user_books" in tool_names
        assert "get_borrowing_status" in tool_names
        assert "request_renewal" in tool_names

        # Check structure of one tool
        get_books = next(
            t["function_declaration"]
            for t in tools
            if t["function_declaration"]["name"] == "get_user_books"
        )
        assert "description" in get_books
        assert "parameters" in get_books

    def test_chat_placeholder_response(self):
        """Test the placeholder chat logic returns expected GeminiResponse."""
        service = GeminiService(api_key="test_key")
        response = service.chat(user_id=1, message="Hello", history=[])

        assert isinstance(response, GeminiResponse)
        assert "Hello" in response.content
        assert response.tool_calls == []

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
