"""L-8：seed 會建立固定帳密的管理員帳號，DEBUG=False 時須拒絕執行（除非 --force）。"""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from core.management.commands.seed import Command


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_seed_refuses_when_debug_false():
    with (
        patch.object(Command, "_clear_data") as mock_clear,
        patch.object(Command, "_generate_data") as mock_generate,
        pytest.raises(CommandError, match="--force"),
    ):
        call_command("seed", stdout=StringIO(), stderr=StringIO())
    mock_clear.assert_not_called()
    mock_generate.assert_not_called()


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_seed_runs_with_force_when_debug_false():
    with (
        patch.object(Command, "_clear_data") as mock_clear,
        patch.object(Command, "_generate_data") as mock_generate,
    ):
        call_command("seed", "--force", stdout=StringIO(), stderr=StringIO())
    mock_clear.assert_called_once()
    mock_generate.assert_called_once_with("small")


@pytest.mark.django_db
@override_settings(DEBUG=True)
def test_seed_runs_when_debug_true():
    with (
        patch.object(Command, "_clear_data"),
        patch.object(Command, "_generate_data") as mock_generate,
    ):
        call_command("seed", stdout=StringIO(), stderr=StringIO())
    mock_generate.assert_called_once()
