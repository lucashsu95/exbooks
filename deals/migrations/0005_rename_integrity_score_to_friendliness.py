# Generated migration for renaming integrity_score to friendliness_score

from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ("deals", "0004_remove_loanextension_approved_by_and_more"),
    ]

    operations = [
        migrations.RenameField(
            model_name="rating",
            old_name="integrity_score",
            new_name="friendliness_score",
        ),
        migrations.AlterField(
            model_name="rating",
            name="friendliness_score",
            field=models.PositiveSmallIntegerField(
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(5),
                ],
                verbose_name="友善評分",
            ),
        ),
    ]
