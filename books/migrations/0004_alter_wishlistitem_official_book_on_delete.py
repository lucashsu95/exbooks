import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("books", "0003_officialbook_category_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="wishlistitem",
            name="official_book",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="wished_by",
                to="books.officialbook",
                verbose_name="官方書目",
            ),
        ),
    ]
