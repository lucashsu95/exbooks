from django.core.cache import cache
from ai.services.conversation_cache import ConversationCache


class TestConversationCache:
    def setup_method(self):
        cache.clear()

    def test_get_history_empty(self):
        """Should return empty list if no history exists."""
        history = ConversationCache.get_history(user_id=1)
        assert history == []

    def test_add_message_and_get_history(self):
        """Should store and retrieve messages."""
        ConversationCache.add_message(user_id=1, role="user", content="Hello")
        ConversationCache.add_message(user_id=1, role="assistant", content="Hi there!")

        history = ConversationCache.get_history(user_id=1)
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there!"}

    def test_max_messages_limit(self):
        """Should only keep the last MAX_MESSAGES."""
        # Use a smaller limit for testing if it was configurable,
        # but since it's hardcoded to 20, we push 25.
        for i in range(25):
            ConversationCache.add_message(user_id=1, role="user", content=f"Msg {i}")

        history = ConversationCache.get_history(user_id=1)
        assert len(history) == 20
        assert history[0]["content"] == "Msg 5"
        assert history[-1]["content"] == "Msg 24"

    def test_clear_history(self):
        """Should remove history for the user."""
        ConversationCache.add_message(user_id=1, role="user", content="Hello")
        ConversationCache.clear_history(user_id=1)

        history = ConversationCache.get_history(user_id=1)
        assert history == []

    def test_separate_users(self):
        """Messages from different users should not leak."""
        ConversationCache.add_message(user_id=1, role="user", content="User 1 Msg")
        ConversationCache.add_message(user_id=2, role="user", content="User 2 Msg")

        h1 = ConversationCache.get_history(user_id=1)
        h2 = ConversationCache.get_history(user_id=2)

        assert len(h1) == 1
        assert h1[0]["content"] == "User 1 Msg"
        assert len(h2) == 1
        assert h2[0]["content"] == "User 2 Msg"
