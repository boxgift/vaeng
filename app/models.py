from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import reverse

from django.db.models.signals import post_save
from django.dispatch import receiver

from parsing.models import Tag

base_url = '5.187.7.199:8001'


class Category(models.Model):
    name = models.CharField(max_length=500)
    title = models.CharField(max_length=500, null=True, blank=True)
    slug = models.SlugField(max_length=500, null=True, blank=True, unique=True)

    content = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('app:category_detail', args=[self.slug])

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['-pk']


class Page(models.Model):
    img = models.ImageField(upload_to='page_img', null=True, blank=True)

    name = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, null=True, blank=True)
    url = models.TextField()

    is_redirect = models.BooleanField(default=False)
    redirect = models.TextField(null=True, blank=True)

    title = models.TextField(null=True, blank=True, default='')
    meta = models.TextField(null=True, blank=True, default='')

    meta_data = models.TextField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)
    html = models.TextField(null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, null=True, blank=True, related_name='pages')
    is_edit = models.BooleanField(default=False)
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    date_update = models.DateTimeField(auto_now=True, null=True, blank=True)

    tags = models.ManyToManyField(Tag, related_name='pages')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        if self.url:
            return reverse('app:page_detail', args=[self.category.slug, str(self.url)[1:]])
            # return reverse('app:page_detail', args=[str(self.url).replace(f'{base_url}/', '')])
        return reverse('app:page_detail_slug', args=[str(self.slug)])

    class Meta:
        verbose_name = 'Страница'
        verbose_name_plural = 'Страницы'
        ordering = ['-pk']


class UploadFile(models.Model):
    file = models.FileField(upload_to='upload_files', null=True, blank=True)
    url = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.url


class PageReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='page_reviews')
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name='reviews')
    rating_choices = ((i, i) for i in range(1, 6))
    rating = models.IntegerField(choices=rating_choices, default=1)
    text = models.TextField(null=True, blank=True)

    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_edit = models.BooleanField(default=False)
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    date_update = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return str(self.pk)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-pk']


class BlogReview(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='blog_reviews')
    blog = models.ForeignKey('Blog', on_delete=models.CASCADE, related_name='reviews')
    rating_choices = ((i, i) for i in range(1, 6))
    rating = models.IntegerField(choices=rating_choices, default=1)
    text = models.TextField(null=True, blank=True)

    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    is_edit = models.BooleanField(default=False)
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    date_update = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return str(self.pk)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-pk']


# class Tag(models.Model):
#     name = models.CharField(max_length=500)
#     slug = models.SlugField(max_length=500, null=True, blank=True, unique=True)
#
#     def __str__(self):
#         return self.name
#
#     def get_pages_url(self):
#         return reverse('app:tag_detail_news', args=[self.slug])
#
#     def get_blogs_url(self):
#         return reverse('app:tag_detail_blogs', args=[self.slug])
#
#     class Meta:
#         verbose_name = 'Тэг'
#         verbose_name_plural = 'Тэги'
#         ordering = ['-pk']


class Blog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blogs')
    name = models.CharField(max_length=500)
    title = models.TextField(null=True, blank=True, default='')
    meta = models.TextField(null=True, blank=True, default='')

    slug = models.SlugField(max_length=500, null=True, blank=True, unique=True)
    content = models.TextField(null=True, blank=True)
    img = models.ImageField(upload_to='blog_images', null=True, blank=True)

    tags = models.ManyToManyField(Tag, related_name='blogs')
    is_edit = models.BooleanField(default=False)
    date_create = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    date_update = models.DateTimeField(auto_now=True, null=True, blank=True)

    archive = models.BooleanField(default=True)
    faq = models.OneToOneField('parsing.FAQ', null=True, blank=True, on_delete=models.CASCADE, related_name='blog')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('app:blog_detail', args=[self.slug])

    class Meta:
        verbose_name = 'Блог'
        verbose_name_plural = 'Блоги'
        ordering = ['-pk']
