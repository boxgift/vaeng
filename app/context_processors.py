from datetime import datetime

from django.db.models import Count, Sum

from parsing.models import Tag
from .models import Category, Page


def app_context(request):
    categories = Category.objects.all()
    tags = Tag.objects.all()
    return {'categories': categories, 'tags': tags}