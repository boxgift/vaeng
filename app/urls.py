from django.urls import path, re_path
from . import views
from .sitemap import StaticViewSitemap, CitiesViewSitemap, ArticlesViewSiteMap, PageViewSiteMap, CityServiceViewSitemap, \
    PlaceViewSiteMap, ServiceViewSiteMap
from django.contrib.sitemaps.views import sitemap

sitemaps = {
    'static': StaticViewSitemap,
    'cities': CitiesViewSitemap,
    'articles': ArticlesViewSiteMap,
    'pages': PageViewSiteMap,
    'city_services': CityServiceViewSitemap,
    'places': PlaceViewSiteMap,
    'services': ServiceViewSiteMap
}
urlpatterns = [
    path('', views.index, name='index'),
    path("robots.txt", views.robots_txt),
    path('created_places_from_json', views.created_places_from_json, name='created_places_from_json'),
    path('privacy-policy', views.privacy_policy, name='privacy_policy'),
    path('test/page', views.test_page, name='test_page'),
    path('test/create_pages', views.create_ready_pages, name='create_ready_pages'),
    path('register/', views.register, name='register'),
    path('created_new_cities', views.created_new_cities, name='created_new_cities'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}),
    # path('create_pages', views.create_pages, name='create_pages'),

    path('review/<int:pk>/edit/', views.place_review_edit, name="place_review_edit"),
    path('place/<slug:slug>/edit/', views.place_edit, name="place_edit"),
    path('service/', views.service_list, name="service_list"),
    path('service/<slug:service_slug>/', views.service_detail, name="service_detail"),
    path('reviews/<slug:place_slug>/', views.place_detail, name="place_detail"),
    path('reviews/<slug:place_slug>/review/create/', views.place_review_create,
         name="place_review_create"),

    path('articles/', views.blog, name='blog'),
    path('articles/create/', views.blog_create, name='blog_create'),
    path('articles/my/', views.my_blogs, name='my_blogs'),
    path('articles/<slug:slug>/edit/', views.blog_edit, name='blog_edit'),
    path('articles/<slug:slug>/edit/faq/', views.blog_edit_faq, name='blog_edit_faq'),
    path('articles/<slug:slug>/delete/', views.blog_delete, name='blog_delete'),
    path('articles/<int:pk>/change/archive/', views.blog_change_archive, name='blog_change_archive'),
    path('articles/<slug:slug>/', views.blog_detail, name='blog_detail'),

    path('user/<str:username>/', views.public_cabinet, name="public_cabinet"),

    path('page/create/', views.page_create, name='page_create'),
    # path('page/change/url', views.change_urls, name='change_urls'),
    path('page/<int:pk>/edit/', views.page_edit, name='page_edit'),
    path('page/<int:pk>/delete/', views.page_delete, name='page_delete'),
    path('page/<slug:slug>/', views.page_detail_slug, name='page_detail_slug'),

    path('profile/', views.profile, name='profile'),

    path('tags/', views.tags, name='tags'),
    path('tags/<slug:slug>/edit/', views.tag_edit, name='tag_edit'),
    path('tags/<int:pk>/delete/', views.tag_delete, name='tag_delete'),
    path('tags/<slug:slug>/news/', views.tag_detail, name='tag_detail_news'),
    path('tags/<slug:slug>/blog/', views.tag_detail, name='tag_detail_blogs'),

    path('reviews/my/', views.reviews, name='reviews'),
    path('news/reviews/<int:pk>/edit/', views.page_review_edit, name='page_review_edit'),
    re_path('^(?P<slug>[\w-]+)/$', views.city_detail, name='city_detail'),
    re_path('^(?P<slug>[\w-]+)/$', views.county_seat_detail, name='county_seat_detail'),
    path('<slug:city_slug>/<slug:service_slug>/', views.city_service_detail, name='city_service_detail'),
]

urlpatterns += [
    path('places/add/', views.query_add, name="query_add"),
    path('places/', views.query_list, name="query"),
    path('places/<slug:slug>/edit/', views.query_edit, name="query_edit"),
    path('places/<slug:slug>/', views.query_places, name="query_places"),
    # path('place/reviews/<int:pk>', views.place_review, name="place_detail"),
]

urlpatterns += [
    path('<slug:slug>/edit/', views.category_edit, name='category_edit'),
    path('<slug:slug>/', views.category_detail, name='category_detail'),
    path('<slug:slug>/change/urls/', views.category_change_urls, name='category_change_urls'),
    path('<slug:slug>/<path:url>/', views.page_detail, name='page_detail'),
    path('<slug:slug>/<path:url>/', views.page_redirect_detail, name='page_redirect_detail'),

]

app_name = 'app'
