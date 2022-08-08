import json
import os
import pickle
from builtins import map

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import Http404, JsonResponse, HttpResponse
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from pytils.translit import slugify
import requests
from rest_framework import serializers

from app.forms import PageReviewForm, UserForm, TagForm, BlogForm, BlogReviewForm, PageForm, CategoryForm, PageEditForm, \
    UserCreateForm
from app.models import Category, Page, Blog, PageReview, Tag
from app.tasks import create_categories, create_new_cities, created_places_from_json_task
from constants import admin_username, parser_host
from parsing.forms import ReviewForm
from parsing.models import Place, ReviewType, Query, Tag, Review, State, City, CityService, Service
from parsing.tasks import GenerateUser, set_photo_url
from parsing.utils import get_paginator, has_group, save_image
from parsing.views import places_to_sorted_letters, create_or_update_review_types, get_sorted_places, \
    get_nearest_cities, set_faq, get_cities

NOT_FOUND_PLACE = '/static/parsing/img/not_found_place.png'


def show_form_errors(request, errors):
    for error in errors:
        messages.error(request, errors[error])


def get_header_img(place):
    try:
        img = place.cloud_img.get_default_img
        return img
    except:
        return None


def create_new_city_services():
    for city in City.objects.all():
        for service in Service.objects.all():
            city_service = CityService.objects.get_or_create(city=city, service=service)
            if city_service[1]:
                city_service[0].save()


def create_cities_slug():
    for city in City.objects.all():
        if not city.slug:
            city.slug = slugify(city.name)
            city.save()


def created_new_cities(request):
    create_new_cities.delay()
    return redirect('/')


def created_places_from_json(request):
    created_places_from_json_task.delay()
    return redirect(reverse('app:index'))


def index(request):
    # create_new_city_services()

    # create_cities_slug()

    # cities = City.objects.all()
    # for city in cities:
    #     city.is_county = False
    #     city.cities.clear()
    #     city.save()
    # cities = City.objects.filter(id__gt=129)
    # for city in cities:
    #     city.delete()
    #     print(city.id)
    # state = State.objects.filter(name='Virginia').first()
    popular_pages = Page.objects.all()[:6]
    return render(request, 'app/news/index.html', {
        # 'state': state,
        'cities': get_cities(),
        'popular_pages': popular_pages
    })


def robots_txt(request):
    lines = [
        "User-Agent: *",
        # "Disallow: /private/",
        # "Disallow: /junk/",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def privacy_policy(request):
    return render(request, 'app/policies/privacy_policy.html')


class PageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = '__all__'


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


def test_page(request):
    categories = Category.objects.all().order_by('pk')
    categories = CategorySerializer(categories, many=True)
    categories = categories.data

    pages = Page.objects.all().order_by('pk')
    pages = PageSerializer(pages, many=True)
    pages = pages.data
    return JsonResponse({
        'categories': categories,
        'pages': pages
    }, safe=False)


def get_category_slug(data_items: list, category_id: int) -> str:
    for data_item in data_items:
        if data_item.get('id') == category_id:
            return data_item.get('slug')


def create_ready_pages(request):
    with open('all_pages_vaeng.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    categories = data.get('categories')
    pages = data.get('pages')
    page_list = []

    Category.objects.all().delete()
    Page.objects.all().delete()

    for c in categories:
        category = Category.objects.create(name=c.get('name'), slug=c.get('slug'))
        category.save()
    for p in pages:
        category_slug = get_category_slug(categories, p.get('category'))
        category = Category.objects.get(slug=category_slug)
        page = Page.objects.create(
            name=p.get('name'),
            slug=p.get('slug'),
            title=p.get('title'),
            meta=p.get('meta'),
            meta_data=p.get('meta_data'),
            url=p.get('url'),
            content=p.get('content'),
            html=p.get('html'),
            category=category,
            is_redirect=p.get('is_redirect'),
            redirect=p.get('redirect'),
        )
        page_list.append(page)
    Page.objects.bulk_create(page_list, ignore_conflicts=True)
    return redirect(reverse('app:index'))


def register(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        email = request.POST['email']
        if User.objects.filter(email=email).exists():
            messages.error(request, 'A user with that email already exists.')
            return redirect('app:index')
        if form.is_valid():
            user = form.save()
            group = Group.objects.filter(name='User').first()
            if group:
                user.groups.add(group)
            login(request, user)
            messages.success(request, 'Authorization was successful')
            return redirect(reverse('app:profile'))
        else:
            print(form.errors)
            show_form_errors(request, form.errors)
    return redirect('app:index')


def county_seat_detail(request, slug):
    city = City.objects.filter(slug=slug, is_county=False).first()
    city_services = CityService.objects.filter(city=city, access=True)
    # print(get_nearest_cities(city, nearest=20))
    return render(request, 'app/city/detail.html', {
        'city': city,
        'city_services': city_services,
        'nearest_cities': get_nearest_cities(city, nearest=20),
        'header_img': get_header_img(city)
    })


def city_detail(request, slug):
    city = City.objects.filter(slug=slug).first()
    # print(city)
    if not city:
        return category_detail(request, slug)
    if city.is_county and city.cities.count():
        county_seat_slug = city.cities.all().order_by('population').first().slug
        if county_seat_slug == slug:
            return county_seat_detail(request, county_seat_slug)
        return redirect(reverse('app:county_seat_detail', args=[county_seat_slug]))
    city_services = CityService.objects.filter(city=city, access=True)
    return render(request, 'app/city/detail.html', {
        'city': city,
        'city_services': city_services,
        'nearest_cities': get_nearest_cities(city, nearest=20),
        'header_img': get_header_img(city)
    })


def service_list(request):
    services = Service.objects.all()
    return render(request, 'app/service/list.html', {
        'services': services
    })


def service_detail(request, service_slug):
    service = get_object_or_404(Service, slug=service_slug)
    cities = City.objects.filter(city_service__access=True, city_service__service=service)
    return render(request, 'app/service/detail.html', {
        'service': service,
        'cities': cities
    })


def city_service_detail(request, city_slug, service_slug):
    # city_service = get_object_or_404(CityService, city__slug=city_slug, service__slug=service_slug, access=True)
    city_service = CityService.objects.filter(city__slug=city_slug, service__slug=service_slug, access=True).first()
    if not city_service:
        return page_detail(request, city_slug, service_slug)
    places = get_sorted_places(city_service)
    top_places = places[:20]
    places_and_letters = places_to_sorted_letters(places)
    try:
        header_img = places.first().cloud_img.get_default_img
    except:
        header_img = NOT_FOUND_PLACE
    return render(request, 'app/city_service/places.html', {
        'city_service': city_service,
        'top_places': top_places,
        'places': places,
        'header_img': header_img,
        'places_letter': places_and_letters['places_letter'],
        'letters': places_and_letters['letters']
    })


def get_popular_pages(category=None):
    if category:
        popular_pages = Page.objects.filter(category=category).order_by('reviews')
    else:
        popular_pages = Page.objects.all().order_by('reviews')
    popular_pages = popular_pages[:5]
    return popular_pages


def get_popular_blogs():
    popular_blogs = Blog.objects.all().order_by('-pk')[:5]
    return popular_blogs


def get_tags():
    tags = Tag.objects.all()
    return tags


def delete_double_prefix():
    categories = Category.objects.all()
    for category in categories:
        pages = category.pages.all()
        for page in pages:
            url = '/'
            url_list = page.url.split('/')
            print(page.url)
            if url_list[1] == category.slug:
                if len(url_list) == 2 or (len(url_list) > 2 and url_list[2] == ''):
                    print('continue')
                    print(page.url)
                    print()
                    continue
                else:
                    print(url_list)
                    url_list.remove(category.slug)
                    url = url.join(url_list)
                    print(url_list)
                    print(url)
                    page.url = url
                    page.save()
                print()
                print(' ------ ')
                print()


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    pages = category.pages.all()
    pages = get_paginator(request, pages)
    path = 'news'
    return render(request, 'app/category/detail.html', {
        'category': category,
        'pages': pages,
        'popular_pages': get_popular_pages(category),
        'tags': get_tags(),
        'path': path
    })


@login_required()
def category_edit(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid() and not Category.objects.filter(slug=request.POST['slug']).exists():
            form.save()
        return redirect(category.get_absolute_url())
    return render(request, 'app/category/edit.html', {'category': category})


@login_required()
def category_change_urls(request, slug):
    category = get_object_or_404(Category, slug=slug)
    pages = category.pages.all()
    if request.method == 'POST':
        post = dict(request.POST)
        old_and_new_urls = dict(zip(post['old_urls'], post['new_urls']))
        print(old_and_new_urls)
        for old_url in old_and_new_urls:
            new_url = old_and_new_urls[old_url]
            page = Page.objects.filter(url=old_url).first()

            if old_url != new_url and len(new_url) >= 2:
                if new_url[0] != '/':
                    new_url = '/' + new_url
                page.is_redirect = True
                page.redirect = new_url
                page.save()
                # page.url = new_url
                # page.save()
                # print(new_url)
            if old_url == new_url and page.is_redirect:
                page.is_redirect = False
                page.redirect = None
                page.save()

        messages.success(request, 'urls changed')
        return redirect(reverse('app:category_change_urls', args=[slug]))
    return render(request, 'app/page/change_urls.html', {'pages': pages})


# @login_required()
# def change_urls(request):
#     return render(request, 'app/page/change_urls.html')


# def create_pages(request):
#     messages.success(request, 'Парсинг начат')
#     create_categories.delay()
#     return redirect('app:index')


def get_detail_page(request, page):
    user = request.user
    if request.method == 'POST':
        if not user.is_authenticated or user.page_reviews.filter(page=page).first():
            return redirect(page.get_absolute_url())
        form = PageReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.page = page
            review.user = user
            review.save()
            messages.success(request, 'Отзыв сохранен')
        else:
            show_form_errors(request, form.errors)
        return redirect(page.get_absolute_url())
    commented = False
    if user.is_authenticated:
        commented = user.page_reviews.filter(page=page).exists()
    return render(request, 'app/page/detail.html', {'page': page, 'commented': commented})


def page_detail(request, slug, url):
    # pages = Page.objects.all()
    # for page in pages:
    #     page.url = page.url[:-1] if page.url[-1] == '/' else page.url
    #     page.save()
    category = get_object_or_404(Category, slug=slug)
    page = Page.objects.filter(category=category, url='/' + url).first()
    if page and page.is_redirect:
        return redirect(reverse('app:page_redirect_detail', args=[category.slug, page.redirect[1:]]))
    if not page:
        page = Page.objects.filter(redirect='/' + url).first()
        if page:
            return get_detail_page(request, page)
        else:
            raise Http404
    return get_detail_page(request, page)


def page_redirect_detail(request, slug, redirect_url):
    page = Page.objects.filter(redirect='/' + redirect_url).first()
    if page:
        return get_detail_page(request, page)
    else:
        page = Page.objects.filter(url='/' + redirect_url).first()
        return get_detail_page(request, page)


def page_detail_slug(request, slug):
    page = get_object_or_404(Page, slug=slug)
    return get_detail_page(request, page)


@login_required()
def profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile changed')
        return redirect(reverse('app:profile'))
    return render(request, 'app/user/profile.html', {'user': user})


@login_required()
def my_blogs(request):
    user = request.user
    blogs = user.blogs.all()
    blogs = get_paginator(request, blogs, count=10)
    return render(request, 'app/user/blogs.html', {'blogs': blogs})


@login_required()
def reviews(request):
    user = request.user
    reviews = user.page_reviews.all()
    return render(request, 'app/user/reviews.html', {'reviews': reviews})


'''
                ------------------- Tag views -------------------
'''


@login_required()
def tags(request):
    tags = Tag.objects.all()
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            name = cd['name']
            if Tag.objects.filter(name=name).exists():
                messages.error(request, 'This tag already exists')
                return redirect(reverse('app:tags'))
            slug = slugify(name)
            tag = form.save(commit=False)
            tag.slug = slug
            tag.save()
            messages.success(request, 'Tag created')
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('app:tags'))
    return render(request, 'app/user/tags.html', {'tags': tags})


@login_required()
def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    page = request.GET.get('page')
    path = request.path.split('/')[-1]
    if path == 'blog':
        pages = tag.blogs.all()
    else:
        pages = tag.pages.all()
    pages = get_paginator(request, pages)
    return render(request, 'app/tag/detail.html', {
        'tag': tag,
        'pages': pages,
        'popular_pages': get_popular_pages(),
        'tags': get_tags(),
        'path': path
    })


@login_required()
def tag_edit(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            cd = form.cleaned_data
            name = cd['name']
            if Tag.objects.filter(name=name).exists():
                messages.error(request, 'This tag already exists')
                return redirect(reverse('app:tags'))
            slug = slugify(name)
            tag = form.save(commit=False)
            tag.slug = slug
            tag.save()
            messages.success(request, 'Tag edit')
            return redirect('app:tags')
        else:
            show_form_errors(request, form.errors)
    return render(request, 'app/tag/edit.html', {'tag': tag})


@login_required()
def tag_delete(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    tag.delete()
    messages.success(request, 'Tag deleted')
    return redirect('app:tags')


@login_required()
def page_review_edit(request, pk):
    user = request.user
    review = PageReview.objects.filter(pk=pk).first()
    if not review or review.user != user:
        return redirect(reverse('app:index'))
    if request.method == 'POST':
        form = PageReviewForm(request.POST, instance=review)
        if form.is_valid():
            messages.success(request, 'Отзыв изменен')
            review = form.save(commit=False)
            review.is_edit = True
            review.save()
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('app:page_review_edit', args=[str(review.pk)]))
    return render(request, 'app/user/page_review_edit.html', {'review': review})


'''
                ------------------- Page views -------------------
'''


@login_required()
def page_edit(request, pk):
    page = Page.objects.filter(pk=pk).first()
    if request.method == 'POST':
        post = request.POST
        form = PageEditForm(post, instance=page)
        if form.is_valid():
            page = form.save()
            category_id = post['category']
            category = Category.objects.filter(pk=int(category_id)).first()
            page.category = category
            add_tags(page, post)
            messages.success(request, 'Page edit')
        else:
            show_form_errors(request, form.errors)
        return redirect(page.get_absolute_url())
    return render(request, 'app/news/edit.html', {
        'page': page,
        'tags': get_tags()
    })


@login_required()
def page_delete(request, pk):
    page = get_object_or_404(Page, pk=pk)
    if not page:
        return redirect('/')
    slug = page.category.slug
    page.delete()
    messages.success(request, 'Page deleted')
    return redirect(reverse('app:category_detail', args=[slug]))


def page_create(request):
    user = request.user
    if request.method == 'POST':
        post = request.POST
        form = PageForm(post)
        if form.is_valid():
            page = form.save(commit=False)
            page.user = user
            # category_id = post['category']
            # category = Category.objects.filter(pk=int(category_id)).first()
            # page.category = category
            # page.save()

            slug = slugify(post['name'])
            url = '/' + slugify(post['name'])
            page.slug = slug
            page.url = url
            if Page.objects.filter(url=url).exists():
                messages.error(request, 'Url not unique')
            else:
                page.save()
                add_tags(page, post)

            # messages.success(request, 'Page created')
            return redirect(reverse('app:index'))
            # return redirect(category.get_absolute_url())
        else:
            show_form_errors(request, form.errors)
            return redirect(reverse('app:index'))
    return render(request, 'app/news/create.html', {
        'tags': get_tags()
    })


'''
                ------------------- Blog views -------------------
'''


def add_tags(obj, post):
    obj.tags.clear()
    for i in post:
        if 'tag_' in i:
            tag_id = int(i.split('_')[-1])
            tag = Tag.objects.filter(pk=tag_id).first()
            obj.tags.add(tag)


@login_required()
def blog_edit(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    if request.method == 'POST':
        form = BlogForm(request.POST, instance=blog)
        if form.is_valid():
            form.save()
            add_tags(blog, request.POST)
            messages.success(request, 'Blog edit')
        else:
            show_form_errors(request, form.errors)
        return redirect(blog.get_absolute_url())
    return render(request, 'app/blog/edit.html', {
        'blog': blog,
        'tags': get_tags()
    })


@login_required()
def blog_edit_faq(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    if request.method == 'POST':
        set_faq(request.POST, blog)
        return redirect(blog.get_absolute_url())
    return render(request, 'app/blog/edit_faq.html', {
        'blog': blog,
        'tags': get_tags()
    })


@login_required()
def blog_create(request):
    user = request.user
    if request.method == 'POST':
        post = request.POST
        form = BlogForm(post)
        if form.is_valid():
            blog = form.save(commit=False)
            blog.user = user
            blog.save()

            add_tags(blog, post)
            slug = slugify(post['name'] + '-' + str(blog.id))
            blog.slug = slug
            blog.save()
            messages.success(request, 'Blog page created')
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('app:blog'))
    return render(request, 'app/blog/create.html', {
        'tags': get_tags()
    })


def blog(request):
    blogs = Blog.objects.filter(archive=False)
    blogs = get_paginator(request, blogs)
    path = 'blog'
    return render(request, 'app/blog/list.html', {
        'blogs': blogs,
        'popular_blogs': get_popular_blogs(),
        'tags': get_tags(),
        'path': path
    })


def blog_detail(request, slug):
    user = request.user
    blog = get_object_or_404(Blog, slug=slug)
    print(blog.meta)
    if blog.archive and blog.user != user:
        raise Http404("Blog not found")
    if request.method == 'POST':
        form = BlogReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = user
            review.blog = blog
            review.save()
            messages.success(request, 'Review save')
        else:
            show_form_errors(request, form.errors)
        return redirect(blog.get_absolute_url())
    commented = False
    if user.is_authenticated:
        commented = user.blog_reviews.filter(blog=blog).exists()
    return render(request, 'app/blog/detail.html', {'blog': blog, 'commented': commented})


@login_required()
def blog_change_archive(request, pk):
    blog = get_object_or_404(Blog, pk=pk)
    blog.archive = not blog.archive
    blog.save()
    return redirect(blog.get_absolute_url())


@login_required()
def blog_delete(request, slug):
    blog = get_object_or_404(Blog, slug=slug)
    blog.delete()
    messages.success(request, 'blog deleted')
    return redirect(reverse('app:blog'))


def my_queries(request, id):
    username = admin_username


def my_place(request, id):
    username = admin_username


def start_parser(username, query_name, query_page):
    url = parser_host + f'query/add?username={username}&query_name={query_name}&query_page={query_page}'
    r = requests.get(url)
    if r.status_code == 200:
        try:
            return r.json()['message']
        except:
            pass
    return "Ошибка"


def query_add(request):
    username = admin_username
    if request.method == 'POST':
        post = request.POST
        query_name = post['query_name']
        try:
            not_all = post['not_all']
        except:
            not_all = None
        if not_all:
            try:
                query_page = request.POST['query_page']
                query_page = int(query_page)
            except:
                query_page = 1
        else:
            query_page = 0

        start = start_parser(username, query_name, query_page)
        messages.success(request, start)
        print(query_name)
        print(not_all)
        print(query_page)
        return redirect('app:query_add')
    return render(request, 'app/parser/form.html')


def get_queries(url):
    queries = {}
    r = requests.get(url)
    if r.status_code == 200:
        try:
            queries = r.json()
        except:
            queries = {}
    return queries


def query_list(request):
    queries = Query.objects.filter(access=True)
    tags = Tag.objects.filter(queries__in=queries).distinct()
    return render(request, 'app/parser/queries.html', {'queries': queries, 'tags': tags, 'header_img': NOT_FOUND_PLACE})


def get_query(url):
    r = requests.get(url)
    return r.json()


def get_tags_for_api(url):
    r = requests.get(url)
    return r.json()


def update_query(slug, post):
    print(post)
    url = parser_host + f'query/{slug}/edit'
    print(url)
    r = requests.post(url, data=dict(post))
    if r.status_code == 200:
        return r.json()
    return {}


def query_edit(request, slug):
    url = parser_host + f'query/{slug}/detail'
    query = get_query(url)
    if request.method == 'POST':
        print(request.POST)
        update_query(slug, request.POST)
        messages.success(request, 'Query Edit')
        return redirect(reverse('app:query_edit', args=[slug]))
    url_tags = parser_host + 'tags'
    tags = get_tags_for_api(url_tags)
    return render(request, 'app/parser/query_edit.html', {'query': query, 'tags': tags})


def get_places(url):
    places = {}
    r = requests.get(url)
    if r.status_code == 200:
        try:
            places = r.json()['places']
            letters = r.json()['letters']
            places_letter = r.json()['places_letter']
            query = r.json()['query']
            places = {
                'places': places,
                'letters': letters,
                'places_letter': places_letter,
                'query': query,
            }
            return places
        except:
            places = {}
    return places


def query_places(request, slug):
    query = get_object_or_404(Query, slug=slug)
    places = get_sorted_places(query)
    places_and_letters = places_to_sorted_letters(places)
    header_img = query.base_img
    return render(request, 'app/parser/places.html', {'places': places,
                                                      'letters': places_and_letters['letters'],
                                                      'places_letter': places_and_letters['places_letter'],
                                                      'query': query,
                                                      'header_img': header_img
                                                      })


# def get_place(url):
#     place = {}
#     r = requests.get(url)
#     if r.status_code == 200:
#         try:
#             place = r.json()
#         except:
#             place = []
#     return place


def get_place_edit(url, post, slug):
    r = requests.post(url, post)
    if r.status_code == 200:
        return {'status': 'success', 'message': 'Saved', 'status_code': r.status_code}
    return {'status': 'error', 'message': 'Error', 'status_code': r.status_code}


def place_edit(request, query_slug, place_slug):
    query = get_object_or_404(Query, slug=query_slug)
    place = get_object_or_404(Place, slug=place_slug)
    return render(request, 'app/parser/place_edit.html', {
        'query': query,
        'place': place
    })


def get_review(pk):
    url = parser_host + f'review/{pk}'
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return {}


def get_review_types(pk=None):
    if pk:
        url = parser_host + f'review/{pk}/types'
    else:
        url = parser_host + 'review/types'
    print(url)
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return []


def update_review(pk, post):
    url = parser_host + f'review/{pk}/edit'
    r = requests.post(url, post)
    if r.status_code == 200:
        return True
    return False


def create_review(place_slug, user, post):
    post = dict(post)
    post['user_id'] = user.id
    post['site'] = admin_username
    post['place_slug'] = place_slug
    post['author_name'] = f'{user.last_name} {user.first_name}'
    print(post)
    url = parser_host + f'review/create'
    r = requests.post(url, post)
    if r.status_code == 200:
        return r.json()
    return {}


def place_detail(request, place_slug):
    place = get_object_or_404(Place, slug=place_slug, city_service__access=True)
    if request.method == 'POST':
        # create_review(slug, request.user, request.POST)
        return redirect(reverse('app:place_detail', args=[place_slug]))
    try:
        header_img = place.cloud_img.get_default_img
    except:
        header_img = NOT_FOUND_PLACE
    my_review = False
    if request.user.is_authenticated:
        reviews = place.reviews.exclude(user=request.user)
        my_review = Review.objects.filter(place=place).filter(user=request.user).first()
    else:
        reviews = place.reviews.all()
    reviews = get_paginator(request, reviews)
    random_places = Place.objects.filter(city_service=place.city_service).order_by('?')[:8]
    return render(request, 'app/parser/place.html', {
        'city_service': place.city_service,
        'place': place,
        'reviews': reviews,
        'header_img': header_img,
        'my_review': my_review,
        'random_places': random_places
    })


@login_required()
def place_review_create(request, place_slug):
    place = get_object_or_404(Place, slug=place_slug)
    user = request.user
    review_types = ReviewType.objects.filter(city_services=place.city_service)
    if Review.objects.filter(user=request.user).filter(place=place).first():
        messages.error(request, 'You cannot leave more than one review.')
        return redirect(reverse('app:place_detail', args=[place.slug]))
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.place = place
            review.original_text = request.POST['text']
            review.save()
            create_or_update_review_types(request.POST, review)
            messages.success(request, 'Your review has been saved')
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('app:place_detail', args=[place.slug]))
    return render(request, 'app/parser/review_create.html', {
        'city_service': place.city_service,
        'place': place,
        'user': user,
        'review_types': review_types,
        'header_img': get_header_img(place)
    })


@login_required()
def place_review_edit(request, pk):
    review = get_review(pk)
    if request.method == 'POST':
        update_review(pk, request.POST)
        messages.success(request, 'Review edit')
        return redirect(reverse('app:place_review_edit', args=[pk]))
    review_types = get_review_types(pk)
    return render(request, 'app/parser/review_edit.html', {'review': review, 'review_types': review_types})


@login_required()
def public_cabinet(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'app/user/cabinet.html', {
        'user': user,
        'header_img': get_header_img(user.profile)
    })
