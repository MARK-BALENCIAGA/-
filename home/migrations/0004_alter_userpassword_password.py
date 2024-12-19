from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_alter_userpassword_application_name_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userpassword',
            name='password',
            field=models.CharField(max_length=500),
        ),
    ]
