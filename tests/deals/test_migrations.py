"""deals/migrations 的測試（前置檢查邏輯與 operation 順序）。"""

import importlib
from unittest.mock import patch

import pytest


class TestMigrationPendingPrecheck:
    """0010 的 RunPython 前置檢查：同 deal 多筆 PENDING 時 fail-fast。"""

    def _migration_module(self):
        return importlib.import_module(
            "deals.migrations.0010_loanextension_is_pending_unique"
        )

    def _fake_cursor(self, rows):
        class _Cursor:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def execute(self, *args, **kwargs):
                pass

            def fetchall(self):
                return rows

        class _Conn:
            def cursor(self):
                return _Cursor()

        return _Conn()

    def test_duplicate_pending_raises_with_violating_rows(self):
        migration = self._migration_module()
        with patch.object(migration, "connection", self._fake_cursor([("deal-1", 3)])):
            with pytest.raises(RuntimeError, match="多筆 PENDING"):
                migration._check_no_duplicate_pending(None, None)

    def test_clean_data_passes(self):
        migration = self._migration_module()
        with patch.object(migration, "connection", self._fake_cursor([])):
            migration._check_no_duplicate_pending(None, None)  # 不拋

    def test_precheck_runs_before_any_ddl(self):
        """前置檢查必須排在 AddField 之前：MySQL DDL auto-commit，
        只有排在最前，fail 時資料庫才能零變更（半套用狀態的防線）。"""
        migration = self._migration_module()
        op_types = [type(op).__name__ for op in migration.Migration.operations]
        assert op_types == ["RunPython", "AddField", "AddConstraint"]
