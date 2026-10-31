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

    def test_trim_never_starts_mid_turn(self):
        """裁切以 turn 為界：歷史不得以孤兒 tool marker／fenced 結果／assistant 開頭。"""
        from ai.services.fencing import wrap_persisted

        def turn(i):
            return [
                {"role": "user", "content": f"Q{i}"},
                {"role": "assistant", "content": "[Called tools: get_user_books]"},
                {"role": "user", "content": wrap_persisted(f"get_user_books: r{i}")},
                {"role": "assistant", "content": f"A{i}"},
            ]

        # 6 turns × 4 + 進行中 turn 3 則 = 27 則；單純取最後 20 則會從 A1 開頭
        for i in range(6):
            ConversationCache.add_messages(1, turn(i))
        ConversationCache.add_messages(1, [{"role": "user", "content": "Q6"}])
        ConversationCache.add_messages(1, turn(6)[1:3])

        history = ConversationCache.get_history(1)
        assert len(history) <= ConversationCache.MAX_MESSAGES
        assert history[0] == {"role": "user", "content": "Q2"}
        # 進行中的 turn（Q6 + 已執行的 tool 資料）完整保留
        assert history[-3]["content"] == "Q6"

    def test_trim_skips_leading_consent_record(self):
        """consent 紀錄（system + fence）也不能成為歷史開頭。"""
        from ai.services.fencing import wrap_persisted

        msgs = [
            {"role": "user", "content": "Q0"},
            {"role": "assistant", "content": "A0"},
            {"role": "system", "content": wrap_persisted("User declined")},
        ]
        for i in range(1, 10):
            msgs += [
                {"role": "user", "content": f"Q{i}"},
                {"role": "assistant", "content": f"A{i}"},
            ]
        msgs.append({"role": "user", "content": "Q10"})
        # 22 則：最後 20 則以 consent 紀錄開頭
        ConversationCache.add_messages(1, msgs)
        history = ConversationCache.get_history(1)
        assert history[0] == {"role": "user", "content": "Q1"}
        assert history[-1] == {"role": "user", "content": "Q10"}
