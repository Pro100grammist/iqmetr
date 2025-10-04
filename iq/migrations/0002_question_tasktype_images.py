from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("iq", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="task_type",
            field=models.CharField(default="verbal", max_length=10),
        ),
        migrations.AddField(
            model_name="question",
            name="image_url",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AlterField(
            model_name="answer",
            name="text",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="answer",
            name="image_url",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
    ]

