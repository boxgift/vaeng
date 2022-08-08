from django.contrib.sitemaps import Sitemap
from django.shortcuts import reverse

from app.models import Blog, Page
from parsing.models import City, CityService, Place, Service


class StaticViewSitemap(Sitemap):
    def items(self):
        return ['index', 'service_list', 'blog']

    def location(self, item):
        return reverse(f'app:{item}')


class CityServiceViewSitemap(Sitemap):
    def items(self):
        return CityService.objects.filter(access=True)

    def location(self, item):
        return reverse('app:city_service_detail', args=[item.city.slug, item.service.slug])


class CitiesViewSitemap(Sitemap):
    def items(self):
        return City.objects.filter(is_county=False)

    def location(self, item):
        # return reverse('news-page', args=[item.pk])
        return reverse('app:city_detail', args=[item.slug])


class ArticlesViewSiteMap(Sitemap):
    def items(self):
        return Blog.objects.filter(archive=False)

    def location(self, item):
        return reverse('app:blog_detail', args=[item.slug])


class PageViewSiteMap(Sitemap):
    def items(self):
        return Page.objects.all()


class PlaceViewSiteMap(Sitemap):
    def items(self):
        return Place.objects.filter(city_service__access=True)

    def location(self, item):
        return reverse('app:place_detail', args=[item.slug])


class ServiceViewSiteMap(Sitemap):
    def items(self):
        return Service.objects.all()

    def location(self, item):
        return reverse('app:service_detail', args=[item.slug])
