# Generated by Django 3.2.7 on 2022-04-19 19:14

from django.conf import settings
import django.contrib.postgres.fields
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500)),
                ('slug', models.SlugField(max_length=500)),
                ('aliases', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=512), blank=True, null=True, size=None)),
                ('map_name', models.CharField(max_length=500)),
                ('latitude', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ('zip_codes', django.contrib.postgres.fields.ArrayField(base_field=models.CharField(max_length=10), blank=True, null=True, size=None)),
                ('description', models.TextField(blank=True, default='', null=True)),
                ('population', models.IntegerField(default=0)),
                ('is_county', models.BooleanField(default=False)),
                ('cities', models.ManyToManyField(blank=True, null=True, related_name='_parsing_city_cities_+', to='parsing.City')),
            ],
            options={
                'verbose_name': 'City',
                'verbose_name_plural': 'Cities',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CityService',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sorted', models.BooleanField(default=False)),
                ('page', models.IntegerField(blank=True, null=True)),
                ('content', models.TextField(blank=True, null=True, verbose_name='Контент')),
                ('meta', models.TextField(blank=True, default='', null=True)),
                ('date_create', models.DateTimeField(auto_now_add=True, null=True)),
                ('date_parsing', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(blank=True, choices=[('wait', 'wait'), ('success', 'success'), ('warning', 'warning'), ('error', 'error')], default='success', max_length=100, null=True)),
                ('search_text', models.TextField(blank=True, null=True)),
                ('link', models.TextField(blank=True, null=True)),
                ('access', models.BooleanField(default=False)),
                ('rating', models.IntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], default=5)),
                ('city', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='city_service', to='parsing.city')),
            ],
            options={
                'verbose_name': 'City and Service',
                'verbose_name_plural': 'Cities and Services',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='CloudImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image_id', models.TextField()),
                ('image_response', models.JSONField()),
            ],
            options={
                'verbose_name': 'CloudFlare image',
                'verbose_name_plural': 'CloudFlare images',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='FAQ',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ],
            options={
                'verbose_name': 'FAQ',
                'verbose_name_plural': 'FAQ`s',
            },
        ),
        migrations.CreateModel(
            name='FAQQuestion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.TextField(blank=True, null=True)),
                ('answer', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'FAQ question',
                'verbose_name_plural': 'FAQ questions',
                'ordering': ['pk'],
            },
        ),
        migrations.CreateModel(
            name='Place',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('place_id', models.TextField(blank=True, null=True, verbose_name='Идентификатор в гугл картах')),
                ('title', models.TextField(blank=True, default='', null=True, verbose_name='Title')),
                ('name', models.CharField(blank=True, max_length=1000, null=True)),
                ('slug', models.SlugField(blank=True, max_length=1000, null=True)),
                ('cid', models.TextField(blank=True, null=True, unique=True, verbose_name='CID в гугл картах')),
                ('address', models.CharField(blank=True, max_length=500, null=True)),
                ('phone_number', models.CharField(blank=True, max_length=500, null=True)),
                ('site', models.CharField(blank=True, max_length=1000, null=True)),
                ('description', models.TextField(blank=True, null=True)),
                ('meta', models.TextField(blank=True, default='', null=True)),
                ('coordinate_html', models.TextField(blank=True, null=True, verbose_name='Координаты')),
                ('position', models.IntegerField(blank=True, db_index=True, default=None, null=True, verbose_name='Позиция в рейтинге')),
                ('rating', models.DecimalField(blank=True, decimal_places=1, max_digits=2, null=True)),
                ('rating_user_count', models.IntegerField(blank=True, default=0, null=True)),
                ('timetable', models.TextField(blank=True, null=True)),
                ('data', models.JSONField(blank=True, null=True, verbose_name='Данные JSON')),
                ('detail_data', models.JSONField(blank=True, null=True, verbose_name='Детальные данные JSON')),
                ('date_create', models.DateTimeField(auto_now_add=True, null=True)),
                ('date_update', models.DateTimeField(auto_now=True, null=True)),
                ('isApiData', models.BooleanField(default=False)),
                ('is_redirect', models.BooleanField(default=False)),
                ('redirect', models.TextField(blank=True, default='', null=True)),
                ('city_service', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='places', to='parsing.cityservice')),
                ('cloud_img', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='parsing.cloudimage', verbose_name='Image')),
                ('faq', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='place', to='parsing.faq')),
            ],
            options={
                'verbose_name': 'Объект',
                'verbose_name_plural': 'Объекты',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='Query',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=1000, verbose_name='Название')),
                ('slug', models.SlugField(blank=True, null=True, unique=True)),
                ('sorted', models.BooleanField(default=False)),
                ('page', models.IntegerField(blank=True, null=True)),
                ('content', models.TextField(blank=True, null=True, verbose_name='Контент')),
                ('access', models.BooleanField(default=False)),
                ('date_create', models.DateTimeField(auto_now_add=True, null=True)),
                ('status', models.CharField(blank=True, choices=[('wait', 'wait'), ('success', 'success'), ('warning', 'warning'), ('error', 'error')], default='success', max_length=100, null=True)),
                ('faq', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='query', to='parsing.faq')),
            ],
            options={
                'verbose_name': 'Название запроса',
                'verbose_name_plural': 'Названии запросов',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='Review',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('base', models.BooleanField(default=False)),
                ('text', models.TextField(blank=True, null=True)),
                ('original_text', models.TextField(blank=True, null=True)),
                ('rating', models.IntegerField(blank=True, choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], default=1, null=True)),
                ('is_edit', models.BooleanField(default=False)),
                ('date_create', models.DateTimeField(auto_now_add=True, null=True)),
                ('date_update', models.DateTimeField(auto_now=True, null=True)),
                ('place', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='parsing.place')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='reviews', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Отзыв',
                'verbose_name_plural': 'Отзывы',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='ReviewType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='Название типа')),
            ],
            options={
                'verbose_name': 'Тип отзыва',
                'verbose_name_plural': 'Типы отзывов',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='State',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500)),
                ('svg', models.TextField(blank=True, null=True)),
            ],
            options={
                'verbose_name': 'State',
                'verbose_name_plural': 'States',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='Tag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, max_length=1000, null=True, unique=True)),
                ('slug', models.SlugField(blank=True, max_length=1000, null=True)),
                ('path', models.TextField(blank=True, null=True, unique=True, verbose_name='Путь')),
            ],
            options={
                'verbose_name': 'Тэг',
                'verbose_name_plural': 'Тэги',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='WordAiCookie',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cookies', models.TextField(blank=True, null=True)),
                ('date_create', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Куки WordAi',
                'verbose_name_plural': 'Куки WordAi',
            },
        ),
        migrations.CreateModel(
            name='UniqueReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('reviews_count', models.IntegerField(default=0)),
                ('reviews_checked', models.IntegerField(default=0)),
                ('date_create', models.DateTimeField(auto_now_add=True, null=True)),
                ('date_end', models.DateTimeField(blank=True, null=True)),
                ('city_service', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='parsing.cityservice')),
                ('place', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='parsing.place')),
                ('query', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='parsing.query')),
            ],
            options={
                'verbose_name': 'Unique review',
                'verbose_name_plural': 'Unique reviews',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=500)),
                ('slug', models.SlugField(max_length=500, unique=True)),
                ('meta', models.TextField(blank=True, default='', null=True)),
                ('description', models.TextField(blank=True, default='', null=True)),
                ('faq', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='service', to='parsing.faq')),
            ],
            options={
                'verbose_name': 'Service',
                'verbose_name_plural': 'Services',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='ReviewPart',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.IntegerField(choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5)], default=1)),
                ('review', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='parts', to='parsing.review')),
                ('review_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reviews', to='parsing.reviewtype')),
            ],
            options={
                'verbose_name': 'Часть отзыва',
                'verbose_name_plural': 'Части отзыва',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='QueryPlace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_create', models.DateTimeField(auto_now_add=True, null=True)),
                ('date_update', models.DateTimeField(auto_now=True, null=True)),
                ('place', models.ManyToManyField(related_name='queries', to='parsing.Place')),
                ('query', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='places', to='parsing.query')),
            ],
            options={
                'verbose_name': 'Запрос - Объект',
                'verbose_name_plural': 'Запросы - Объекты',
                'ordering': ['-pk'],
            },
        ),
        migrations.AddField(
            model_name='query',
            name='tags',
            field=models.ManyToManyField(blank=True, null=True, related_name='queries', to='parsing.Tag'),
        ),
        migrations.AddField(
            model_name='query',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='queries', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('birth_date', models.DateTimeField(blank=True, null=True)),
                ('gender', models.CharField(blank=True, choices=[('FEMALE', 'FEMALE'), ('MALE', 'MALE')], max_length=100, null=True, verbose_name='Гендер')),
                ('cloud_img', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='parsing.cloudimage', verbose_name='Image')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Профиль',
                'verbose_name_plural': 'Профили',
                'ordering': ['-pk'],
            },
        ),
        migrations.CreateModel(
            name='PlacePhoto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cloud_img', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='parsing.cloudimage', verbose_name='Image')),
                ('place', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='photos', to='parsing.place')),
            ],
            options={
                'verbose_name': 'Фотография',
                'verbose_name_plural': 'Фотографии',
            },
        ),
        migrations.AddField(
            model_name='faq',
            name='questions',
            field=models.ManyToManyField(blank=True, null=True, related_name='FAQ', to='parsing.FAQQuestion'),
        ),
        migrations.AddField(
            model_name='cityservice',
            name='faq',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='city_service', to='parsing.faq'),
        ),
        migrations.AddField(
            model_name='cityservice',
            name='review_types',
            field=models.ManyToManyField(blank=True, null=True, related_name='city_services', to='parsing.ReviewType'),
        ),
        migrations.AddField(
            model_name='cityservice',
            name='service',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='city_service', to='parsing.service'),
        ),
        migrations.AddField(
            model_name='cityservice',
            name='tags',
            field=models.ManyToManyField(blank=True, null=True, related_name='city_service', to='parsing.Tag'),
        ),
        migrations.AddField(
            model_name='city',
            name='cloud_img',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='parsing.cloudimage', verbose_name='Image'),
        ),
    ]
