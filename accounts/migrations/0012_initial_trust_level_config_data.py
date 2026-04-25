from django.db import migrations


def create_initial_trust_level_configs(apps, schema_editor):
    TrustLevelConfig = apps.get_model("accounts", "TrustLevelConfig")

    configs = [
        {
            "level": 0,
            "group_name": "trust_lv0",
            "display_name": "新手",
            "min_score": 0,
            "max_books": 1,
            "max_days": 14,
            "badge_icon": "",
            "demotion_protection_weeks": 26,
        },
        {
            "level": 1,
            "group_name": "trust_lv1",
            "display_name": "一般會員",
            "min_score": 100,
            "max_books": 2,
            "max_days": 21,
            "badge_icon": "🥉",
            "demotion_protection_weeks": 26,
        },
        {
            "level": 2,
            "group_name": "trust_lv2",
            "display_name": "可信會員",
            "min_score": 400,
            "max_books": 4,
            "max_days": 30,
            "badge_icon": "🥈",
            "demotion_protection_weeks": 26,
        },
        {
            "level": 3,
            "group_name": "trust_lv3",
            "display_name": "優良會員",
            "min_score": 900,
            "max_books": 6,
            "max_days": 60,
            "badge_icon": "🥇",
            "demotion_protection_weeks": 26,
        },
    ]

    for config_data in configs:
        TrustLevelConfig.objects.get_or_create(
            level=config_data["level"], defaults=config_data
        )


def remove_trust_level_configs(apps, schema_editor):
    TrustLevelConfig = apps.get_model("accounts", "TrustLevelConfig")
    TrustLevelConfig.objects.filter(level__in=[0, 1, 2, 3]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0011_userprofile_trust_level_protected_since"),
    ]

    operations = [
        migrations.RunPython(
            create_initial_trust_level_configs, remove_trust_level_configs
        ),
    ]
