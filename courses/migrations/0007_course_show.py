from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0006_task_show_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='show',
            field=models.BooleanField(default=True),
        ),
    ]
