# Generated by Django 4.2.19 on 2025-02-19 14:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="healthmetric",
            name="summary_text",
            field=models.CharField(max_length=2500, null=True),
        ),
        migrations.AlterField(
            model_name="healthmetric",
            name="metric_type",
            field=models.CharField(max_length=250, null=True),
        ),
    ]
