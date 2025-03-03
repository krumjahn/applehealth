from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('main', '0003_alter_healthmetric_health_data_llmanalytics'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE TABLE IF NOT EXISTS file_uploads (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL,
                content TEXT NOT NULL,
                uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """,
            """
            DROP TABLE IF EXISTS file_uploads;
            """
        ),
    ]
