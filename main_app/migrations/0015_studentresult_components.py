from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0014_leavereportstudent_attachment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='studentresult',
            name='test',
        ),
        migrations.RemoveField(
            model_name='studentresult',
            name='exam',
        ),
        migrations.AddField(
            model_name='studentresult',
            name='test1',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='studentresult',
            name='test2',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='studentresult',
            name='quiz',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='studentresult',
            name='experiential',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='studentresult',
            name='see',
            field=models.FloatField(default=0),
        ),
    ]