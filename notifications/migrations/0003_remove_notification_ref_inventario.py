from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("notifications", "0002_notification_persistente"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="notification",
            name="ref_inventario",
        ),
    ]
