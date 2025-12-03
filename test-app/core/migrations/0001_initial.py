from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('author', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('cover_image', models.URLField(max_length=500)),
                ('price', models.DecimalField(decimal_places=2, default=9.99, max_digits=6)),
                ('published_year', models.IntegerField(default=2020)),
                ('is_public', models.BooleanField(default=True)),
            ],
        ),
    ]
