from django.db import migrations

# 與 docs/acquire.md「借閱限制」一致；999 = 無限制（模板哨兵值）
DOCUMENTED_LIMITS = {
    0: (1, 30),
    1: (3, 60),
    2: (5, 90),
    3: (999, 999),
}

PREVIOUS_LIMITS = {
    0: (1, 14),
    1: (2, 21),
    2: (4, 30),
    3: (6, 60),
}


def align_limits(apps, schema_editor):
    """只更新仍是 seed 原值的列，admin 改過的設定不可被覆寫。"""
    TrustLevelConfig = apps.get_model("accounts", "TrustLevelConfig")
    for level, (max_books, max_days) in DOCUMENTED_LIMITS.items():
        prev_books, prev_days = PREVIOUS_LIMITS[level]
        TrustLevelConfig.objects.filter(
            level=level, max_books=prev_books, max_days=prev_days
        ).update(max_books=max_books, max_days=max_days)


def revert_limits(apps, schema_editor):
    TrustLevelConfig = apps.get_model("accounts", "TrustLevelConfig")
    for level, (max_books, max_days) in PREVIOUS_LIMITS.items():
        TrustLevelConfig.objects.filter(level=level).update(
            max_books=max_books, max_days=max_days
        )


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0015_add_trace_id"),
    ]

    operations = [
        migrations.RunPython(align_limits, revert_limits),
    ]
