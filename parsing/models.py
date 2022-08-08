import re

from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Count, Sum, F
from django.db.models.functions import Round, Length
from django.template.defaultfilters import safe
from django.templatetags.static import static
from django.urls import reverse
from bs4 import BeautifulSoup as BS
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.shortcuts import reverse, redirect

# class Role(models.Model):
#     name = models.CharField(max_length=128, verbose_name='Название')
#
#     def __str__(self):
#         return self.name
from django.utils.text import slugify

from constants import CLOUDFLARE_IMAGE_DELIVERY_URL


class Tag(models.Model):
    name = models.CharField(max_length=1000, null=True, blank=True, unique=True)
    slug = models.SlugField(max_length=1000, null=True, blank=True)
    path = models.TextField(null=True, blank=True, unique=True, verbose_name='Путь')

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'
        ordering = ['-pk']


class CloudImage(models.Model):
    image_id = models.TextField()
    image_response = models.JSONField()

    def __str__(self):
        return self.image_id

    def get_img(self, variant):
        url = CLOUDFLARE_IMAGE_DELIVERY_URL.format(image_id=self.image_id, variant=variant)
        return url

    @property
    def get_default_img(self):
        variant = 'public'
        return self.get_img(variant)

    @property
    def get_thumbnail_img(self):
        variant = 'thumbnail'
        return self.get_img(variant)

    @property
    def get_min_img(self):
        variant = 'min'
        return self.get_img(variant)

    class Meta:
        verbose_name = 'CloudFlare image'
        verbose_name_plural = 'CloudFlare images'
        ordering = ['-pk']


class Query(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='queries',
                             verbose_name='User')
    name = models.CharField(max_length=1000, verbose_name='Название')
    slug = models.SlugField(null=True, blank=True, unique=True)
    sorted = models.BooleanField(default=False)
    page = models.IntegerField(null=True, blank=True)
    content = models.TextField(null=True, blank=True, verbose_name='Контент')
    tags = models.ManyToManyField(Tag, null=True, blank=True, related_name='queries')

    faq = models.OneToOneField('FAQ', null=True, blank=True, on_delete=models.CASCADE, related_name='query')

    access = models.BooleanField(default=False)
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    status_choices = (
        ('wait', 'wait'),
        ('success', 'success'),
        ('warning', 'warning'),
        ('error', 'error'),
    )
    status = models.CharField(choices=status_choices, default='success', max_length=100, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Название запроса'
        verbose_name_plural = 'Названии запросов'
        ordering = ['-pk']

    def get_absolute_url(self):
        return reverse('parsing:query_detail', args=[self.slug])

    @property
    def places_count(self):
        return Place.objects.filter(queries__query_id=self.id).count()

    @property
    def base_img(self):
        # host = 'http://170.130.40.103'
        place = Place.objects.filter(queries__query_id=self.id).order_by('pk').first()
        if place and place.cloud_img:
            return f'{place.cloud_img.get_default_img}'
        return '/static/parsing/img/not_found_place.png'

    @property
    def duration(self):
        date_format = '%d-%m-%Y %H:%M'
        end_time = self.places.order_by('pk').last().date_create
        start_time = self.date_create
        if end_time.day == start_time.day:
            end_time = end_time.strftime('%H:%M')
        else:
            end_time = end_time.strftime(date_format)
        return f'{start_time.strftime(date_format)} - {end_time}'


class QueryPlace(models.Model):
    query = models.ForeignKey(Query, on_delete=models.CASCADE, null=True, blank=True, related_name='places')
    place = models.ManyToManyField('Place', related_name='queries')
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    date_update = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return f'{self.query.name}'

    class Meta:
        verbose_name = 'Запрос - Объект'
        verbose_name_plural = 'Запросы - Объекты'
        ordering = ['-pk']


class City(models.Model):
    name = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500)
    aliases = ArrayField(base_field=models.CharField(max_length=512), null=True, blank=True)
    map_name = models.CharField(max_length=500)

    latitude = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    longitude = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    zip_codes = ArrayField(base_field=models.CharField(max_length=10), null=True, blank=True)
    description = models.TextField(null=True, blank=True, default='')
    population = models.IntegerField(default=0)

    is_county = models.BooleanField(default=False)
    cities = models.ManyToManyField('self', null=True, blank=True, related_name='parent')

    cloud_img = models.ForeignKey(CloudImage, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Image')

    def __str__(self):
        return self.name

    @property
    def get_cities(self):
        return self.cities.all()

    def get_absolute_url(self):
        return reverse('parsing:city_detail', args=[self.slug])

    class Meta:
        verbose_name = 'City'
        verbose_name_plural = 'Cities'
        ordering = ['name']


class Service(models.Model):
    name = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, unique=True)

    meta = models.TextField(null=True, blank=True, default='')
    description = models.TextField(null=True, blank=True, default='')
    faq = models.OneToOneField('FAQ', null=True, blank=True, on_delete=models.CASCADE, related_name='service')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('parsing:service_detail', args=[self.slug])

    class Meta:
        verbose_name = 'Service'
        verbose_name_plural = 'Services'
        ordering = ['name']


class CityService(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='city_service')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='city_service')

    sorted = models.BooleanField(default=False)
    page = models.IntegerField(null=True, blank=True)
    content = models.TextField(null=True, blank=True, verbose_name='Контент')
    meta = models.TextField(null=True, blank=True, default='')
    faq = models.OneToOneField('FAQ', null=True, blank=True, on_delete=models.CASCADE, related_name='city_service')
    tags = models.ManyToManyField(Tag, null=True, blank=True, related_name='city_service')

    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    date_parsing = models.DateTimeField(null=True, blank=True)
    status_choices = (
        ('not started', 'not started'),
        ('wait', 'wait'),
        ('success', 'success'),
        ('warning', 'warning'),
        ('error', 'error'),
    )
    status = models.CharField(choices=status_choices, default='not started', max_length=100, null=True, blank=True)

    search_text = models.TextField(null=True, blank=True)
    link = models.TextField(null=True, blank=True)
    access = models.BooleanField(default=False)
    rating_choices = (
        (1, 1),
        (2, 2),
        (3, 3),
        (4, 4),
        (5, 5)
    )
    rating = models.IntegerField(choices=rating_choices, default=5)

    review_types = models.ManyToManyField('ReviewType', null=True, blank=True, related_name='city_services')

    def __str__(self):
        return f'{self.city.name} - {self.service.name}'

    def get_absolute_url(self):
        return reverse('parsing:city_service_detail', args=[self.city.slug, self.service.slug])

    @property
    def get_title(self):
        return f'{self.service.name} in {self.city.name}'

    @property
    def places_count(self):
        return Place.objects.filter(city_service__id=self.id).count()

    @property
    def exact_count(self):
        return Place.objects.filter(city_service=self.id, archive=False).count()

    class Meta:
        verbose_name = 'City and Service'
        verbose_name_plural = 'Cities and Services'
        ordering = ['-pk']


class CityServiceFile(models.Model):
    city_service = models.ForeignKey(CityService, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.city_service.get_title

    class Meta:
        verbose_name = 'Файл для хабов'
        verbose_name_plural = 'Файлы для хабов'


class Place(models.Model):
    place_id = models.TextField(verbose_name='Идентификатор в гугл картах', null=True, blank=True)
    title = models.TextField(null=True, blank=True, default='', verbose_name='Title')
    name = models.CharField(max_length=1000, null=True, blank=True)
    slug = models.SlugField(max_length=1000, null=True, blank=True)
    cid = models.TextField(verbose_name='CID в гугл картах', null=True, blank=True, unique=True)
    cloud_img = models.ForeignKey(CloudImage, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Image')
    address = models.CharField(max_length=500, null=True, blank=True)
    phone_number = models.CharField(max_length=500, null=True, blank=True)
    site = models.CharField(max_length=1000, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    meta = models.TextField(null=True, blank=True, default='')
    coordinate_html = models.TextField(null=True, blank=True, verbose_name='Координаты')

    position = models.IntegerField(default=None, null=True, blank=True, db_index=True,
                                   verbose_name='Позиция в рейтинге')

    rating = models.DecimalField(max_digits=2, decimal_places=1, null=True, blank=True)
    rating_user_count = models.IntegerField(null=True, blank=True, default=0)

    timetable = models.TextField(null=True, blank=True)

    data = models.JSONField(null=True, blank=True, verbose_name='Данные JSON')
    detail_data = models.JSONField(null=True, blank=True, verbose_name='Детальные данные JSON')

    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    date_update = models.DateTimeField(auto_now=True, null=True, blank=True)

    isApiData = models.BooleanField(default=False)

    is_redirect = models.BooleanField(default=False)
    redirect = models.TextField(null=True, blank=True, default='')

    faq = models.OneToOneField('FAQ', null=True, blank=True, on_delete=models.CASCADE, related_name='place')

    city_service = models.ForeignKey(CityService, null=True, blank=True, on_delete=models.CASCADE,
                                     related_name='places')

    archive = models.BooleanField(default=False)

    def get_absolute_url(self):
        if self.city_service:
            return reverse('parsing:city_service_place_detail', args=[self.slug])
        return '/'

    @property
    def city(self):
        return self.city_service.city if self.city_service else ''

    @property
    def service(self):
        return self.city_service.service if self.city_service else ''

    @property
    def get_cloud_img(self):
        return self.cloud_img if self.cloud_img else static('static/parsing/img/not_found_place.png')

    @property
    def get_rating(self):
        return self.data['rating'] if self.data and 'rating' in self.data else 0

    def get_meta_description(self):
        if self.meta == None:
            return ' - '
        pattern = r'(?<=content=")(.+?)(?=")'
        meta = re.search(pattern, self.meta)
        if meta and meta.group():
            return meta.group()
        return ' - '

    @property
    def get_description(self):
        if self.description:
            return self.description
        return self.get_meta_description()

    @property
    def google_url(self):
        return 'https://maps.google.com/?cid={0}'.format(str(self.cid))

    # @property
    # def get_img(self):
    #     url = '/static/parsing/img/not_found_place.png'
    #     if self.img:
    #         url = self.img.url
    #     return url

    @property
    def isSite(self):
        if not self.site or self.site == ' - ':
            return ' - '
        if self.site[:4] == 'http':
            return self.site
        else:
            return 'http://' + self.site

    @property
    def get_name(self):
        return self.data['name'] if self.data and 'name' in self.data else '-'

    @property
    def locale_rating(self):
        return 1

    @property
    def get_more_text(self):
        base_review = self.reviews.filter(base=True)
        if base_review.exists():
            return base_review.first()
        queries = self.reviews.exclude(text=None).exclude(text='').annotate(text_len=Length('text')).order_by(
            '-text_len')
        if queries:
            return queries.first()
        return None

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Объект'
        verbose_name_plural = 'Объекты'
        ordering = ['-pk']

    def get_preview_url(self):
        return reverse('parsing:place_html_api', args=[self.cid])

    # def get_absolute_url(self):
    #     return reverse('parsing:place_detail', args=[self.slug])


class PlacePhoto(models.Model):
    cloud_img = models.ForeignKey(CloudImage, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Image')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True, blank=True, related_name='photos')

    def __str__(self):
        return self.id

    class Meta:
        verbose_name = 'Фотография'
        verbose_name_plural = 'Фотографии'


class ReviewType(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название типа')

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Тип отзыва'
        verbose_name_plural = 'Типы отзывов'
        ordering = ['-pk']


class ReviewPart(models.Model):
    review_type = models.ForeignKey(ReviewType, on_delete=models.CASCADE, related_name='reviews')
    review = models.ForeignKey('Review', on_delete=models.CASCADE, related_name='parts')
    stars_choices = ((i, i) for i in range(1, 6))
    rating = models.IntegerField(default=1, choices=stars_choices)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Часть отзыва'
        verbose_name_plural = 'Части отзыва'
        ordering = ['-pk']


class Review(models.Model):
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.DO_NOTHING, related_name='reviews')
    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='reviews')
    base = models.BooleanField(default=False)
    text = models.TextField(null=True, blank=True)
    original_text = models.TextField(null=True, blank=True)
    stars_choices = ((i, i) for i in range(1, 6))
    rating = models.IntegerField(default=1, choices=stars_choices, null=True, blank=True)

    is_edit = models.BooleanField(default=False)
    date_create = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    date_update = models.DateTimeField(null=True, blank=True, auto_now=True)

    def __str__(self):
        return self.text[:30]

    @property
    def get_user_name(self):
        return f'{self.user.profile.full_name}'

    @property
    def get_rating(self):
        if self.parts.exists():
            r = self.parts.all().aggregate(rating=Sum('rating'))
            c = self.parts.all().aggregate(count=Count('rating'))
            rating = round(r['rating'] / c['count'], 1)
        else:
            rating = float(self.rating)
        return str(rating).replace(',', '.')

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-pk']


class UniqueReview(models.Model):
    reviews_count = models.IntegerField(default=0)
    reviews_checked = models.IntegerField(default=0)
    place = models.ForeignKey(Place, on_delete=models.CASCADE, null=True, blank=True)
    city_service = models.ForeignKey(CityService, on_delete=models.CASCADE, null=True, blank=True)
    query = models.ForeignKey(Query, on_delete=models.CASCADE, null=True, blank=True)
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    date_end = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return str(self.id)

    @property
    def status_color(self):
        if self.percent < 50:
            status_color = 'danger'
        elif self.percent >= 50 and self.percent < 80:
            status_color = 'warning'
        else:
            status_color = 'success'
        return status_color

    @property
    def percent(self):
        return round((self.reviews_checked / self.reviews_count) * 100)

    def get_name(self):
        if self.place:
            return f'{self.place.name}'
        else:
            return f'{self.city_service.search_text} (places)' if self.city_service else ''

    class Meta:
        verbose_name = 'Unique review'
        verbose_name_plural = 'Unique reviews'
        ordering = ['-pk']


# class Location(models.Model):
#     name = models.CharField(max_length=250)
#     text = models.TextField(null=True, blank=True)
#     rating = models.CharField(max_length=250, null=True, blank=True)
#
#     place = models.OneToOneField(Place, related_name='location', on_delete=models.CASCADE)
#
#     def __str__(self):
#         return self.name
#
#     class Meta:
#         verbose_name = 'Местоположение'
#         verbose_name_plural = 'Местоположения'


class FAQQuestion(models.Model):
    question = models.TextField(null=True, blank=True)
    answer = models.TextField(null=True, blank=True)

    def __str__(self):
        return str(self.question[:100])

    class Meta:
        verbose_name = 'FAQ question'
        verbose_name_plural = 'FAQ questions'
        ordering = ['pk']


class FAQ(models.Model):
    questions = models.ManyToManyField(FAQQuestion, null=True, blank=True, related_name='FAQ')

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQ`s'


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    cloud_img = models.ForeignKey(CloudImage, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Image')
    birth_date = models.DateTimeField(null=True, blank=True)
    gender_choices = (
        ('FEMALE', 'FEMALE'),
        ('MALE', 'MALE'),
    )
    gender = models.CharField(max_length=100, null=True, blank=True, choices=gender_choices, verbose_name='Гендер')

    @property
    def full_name(self):
        return f'{self.user.first_name} {self.user.last_name}'

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'
        ordering = ['-pk']


class State(models.Model):
    name = models.CharField(max_length=500)
    svg = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('parsing:state_detail', args=[self.id])

    class Meta:
        verbose_name = 'State'
        verbose_name_plural = 'States'
        ordering = ['name']

    def usa(self):
        states = State.objects.all()
        usa = ''
        for state in states:
            usa += state.get_svg()
        return safe(usa)

    def get_svg(self):
        soup = BS(self.svg, 'lxml')
        viewbox = soup.find('svg').get('viewbox')
        svg = ''
        for j in soup.find('svg').findChildren(recursive=False)[1].findChildren(recursive=False)[1:]:
            svg += str(j)
        return {
            'svg': safe(svg),
            'viewbox': viewbox
        }


class WordAiCookie(models.Model):
    cookies = models.TextField(null=True, blank=True)
    date_create = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = 'Куки WordAi'
        verbose_name_plural = 'Куки WordAi'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
