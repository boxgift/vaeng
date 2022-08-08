from django.contrib import admin
from .models import Page, Tag, Category, Blog


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_filter = ['category', 'is_redirect']
    list_display = ['id', 'name', 'url']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'user']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['user']

