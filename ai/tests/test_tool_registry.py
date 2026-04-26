from django.test import TestCase
from ai.services.tool_registry import ToolRegistry, ConsentRequirement, ToolDefinition

class ToolRegistryTests(TestCase):
    def test_registry_contains_predefined_tools(self):
        """Ensure the registry contains the three required tools."""
        tools = ToolRegistry.get_all_tools()
        tool_names = [t.name for t in tools]
        
        self.assertIn("get_user_books", tool_names)
        self.assertIn("get_borrowing_status", tool_names)
        self.assertIn("request_renewal", tool_names)

    def test_get_tool_by_name(self):
        """Ensure we can retrieve a specific tool by name."""
        tool = ToolRegistry.get_tool("get_user_books")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "get_user_books")
        self.assertIsInstance(tool, ToolDefinition)

    def test_tool_consent_requirements(self):
        """Ensure consent requirements are correctly set."""
        get_books = ToolRegistry.get_tool("get_user_books")
        renewal = ToolRegistry.get_tool("request_renewal")
        
        self.assertEqual(get_books.consent, ConsentRequirement.NOT_REQUIRED)
        self.assertEqual(renewal.consent, ConsentRequirement.USER_CONFIRM)

    def test_tool_execution(self):
        """Ensure the placeholder functions can be called."""
        get_books = ToolRegistry.get_tool("get_user_books")
        result = get_books.func(status="OWNED")
        self.assertIn("get_user_books", result)
        
        renewal = ToolRegistry.get_tool("request_renewal")
        result = renewal.func(deal_id=123)
        self.assertIn("request_renewal", result)
        self.assertIn("123", result)
