
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userpassword',
            name='date_last_updated',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
