from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0012_documentchunk"),
    ]

    operations = [
        migrations.AddField(
            model_name="document",
            name="chat_history",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
