import json
import pickle
from email.headerregistry import Group
from datetime import datetime

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.db import IntegrityError
from django.db.models import Count, F
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic import DetailView
from pytils.translit import slugify
from rest_framework import status, generics
from rest_framework.decorators import api_view
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from constants import SERVER_NAME, STATE_NAME
from parsing.forms import UserForm, UserCreateForm, UserDetailForm, QueryForm, ReviewForm, PlaceForm, TagForm, \
    QueryContentForm, ReviewTypeForm, CityForm, ServiceForm, CityServiceContentForm, CityEditForm, ServiceEditForm, \
    CityServiceFileForm
from parsing.models import Query, Place, Review, Tag, ReviewType, ReviewPart, FAQ, FAQQuestion, UniqueReview, City, \
    Service, CityService, State, CityServiceFile
from parsing.serializers import QuerySerializer, PlaceSerializer, PlaceMinSerializer, \
    TagSerializer, \
    ReviewSerializer, ReviewTypeSerializer
from parsing.tasks import startParsing, generate_file, uniqueize_place_reviews_task, \
    uniqueize_text_task, cities_img_parser, uniqueize_reviews_task, preview_uniqueize_reviews_task, uniqueize_review, \
    service_autocreate_task, city_service_file_apply_task
from parsing.utils import show_form_errors, has_group, get_paginator, sumextract, unique_error_or_save, \
    city_service_create


def index(request):
    # CityService.objects.update(status='not started')
    with open('parsing/states.pickle', 'rb') as f:
        data = pickle.load(f)
        for i in data:
            state = State.objects.get_or_create(name=i, svg=data[i]['svg'])
            state[0].save()

    user = request.user
    if user.is_authenticated:
        services_count = Service.objects.count()
        cities_count = City.objects.count()
        city_services = CityService.objects
        all = city_services.count()
        all = all if all else 1
        wait = city_services.filter(status='wait').count()
        error = city_services.filter(status='error').count()
        opened = city_services.filter(status='success', access=True).count()
        close = city_services.filter(status='success', access=False).count()
        not_started = city_services.filter(status='not started').count()
        statistic = {
            'all': {
                'count': all,
                'percent': 100
            },
            'wait': {
                'count': wait,
                'percent': round(wait / all * 100, 5),
            },
            'error': {
                'count': error,
                'percent': round(error / all * 100, 5)
            },
            'open': {
                'count': opened,
                'percent': round(opened / all * 100, 5),
            },
            'close': {
                'count': close,
                'percent': round(close / all * 100, 5),
            },
            'not_started': {
                'count': not_started,
                'percent': round(not_started / all * 100, 5)
            }
        }
        return render(request, 'parsing/index.html', {
            'user': user,
            'services_count': services_count,
            'cities_count': cities_count,
            'statistic': statistic
        })
    return render(request, 'parsing/index.html')


def states_list(request):
    states = State.objects.all()
    return render(request, 'parsing/state/list.html', {
        'states': states
    })


def get_cities():
    return City.objects.order_by('-population')


def state_detail(request, pk):
    state = get_object_or_404(State, pk=pk)
    return render(request, 'parsing/state/detail.html', {
        'state': state
    })


def state_preview(request, pk):
    state = get_object_or_404(State, pk=pk)
    data = request.GET
    print(data)
    print(dict(data))
    max_width = data['max-width']
    viewbox = str(data.get('viewbox'))
    map_color = '#' + data['map-color']
    map_hover_color = '#' + data['map-hover-color']
    map_border_color = '#' + data['map-border-color']
    text_color = '#' + data['text-color']
    state = get_object_or_404(State, pk=pk)
    return render(request, 'parsing/state/preview.html', {
        'state': state,
        'max_width': max_width,
        'viewbox': viewbox,
        'map_color': map_color,
        'map_hover_color': map_hover_color,
        'map_border_color': map_border_color,
        'text_color': text_color,
    })


@login_required()
def start_parser(request, city_slug, service_slug):
    city_service = CityService.objects.filter(city__slug=city_slug, service__slug=service_slug).first()
    return redirect(city_service.get_absolute_url())


@login_required()
def start_custom_parser(request, city_slug, service_slug):
    city_service = get_object_or_404(CityService, city__slug=city_slug, service__slug=service_slug)
    if request.method == 'POST':
        form = QueryForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            search_text = cd['name']
            not_all = cd['not_all']
            post = dict(request.POST)
            review_types = post.get('review_types')
            review_types = ReviewType.objects.filter(id__in=review_types) if review_types else None
            # return redirect(city_service.get_absolute_url())
            if not_all:
                query_page = cd['page']
                try:
                    query_page = int(query_page)
                except:
                    query_page = 1
            else:
                query_page = None
            try:
                if CityService.objects.filter(status='wait').exists():
                    messages.warning(request, 'Please wait, there are tasks in the queue')
                else:
                    city_service.search_text = search_text
                    city_service.page = query_page
                    city_service.status = 'wait'
                    city_service.date_parsing = datetime.now()
                    city_service.review_types.all().delete()
                    city_service.review_types.add(*review_types) if review_types else None
                    city_service.save()
                    messages.success(request, 'Parsing started')
                    startParsing.delay(query_name=search_text, city_service_id=city_service.id, pages=query_page)
            except Exception as e:
                print(e.__class__.__name__)
                city_service.status = 'error'
                city_service.save()
        return redirect(city_service.get_absolute_url())
    review_types = ReviewType.objects.all()
    return render(request, 'parsing/city_service/start_parser.html', {
        'city_service': city_service,
        'review_types': review_types,
        'state': STATE_NAME
    })


#
# @login_required()
# def query_add(request):
#     if request.method == 'POST':
#         form = QueryForm(request.POST)
#         if form.is_valid():
#             cd = form.cleaned_data
#             query_name = cd['name']
#             not_all = cd['not_all']
#
#             if not_all:
#                 query_page = cd['page']
#                 try:
#                     query_page = int(query_page)
#                 except:
#                     query_page = 1
#             else:
#                 query_page = None
#
#             print(query_name, not_all, query_page)
#
#             query = Query(user=request.user, name=query_name, page=query_page, status='wait')
#             query.save()
#             query_id = query.id
#
#             slug = slugify(query_name + '-' + str(query_id))
#             query.slug = slug
#             query.save()
#
#             try:
#                 startParsing.delay(query_name=query_name, query_id=query_id, pages=query_page)
#             except Exception as e:
#                 print(e.__class__.__name__)
#                 query.status = 'error'
#                 query.save()
#             return redirect('/')
#         else:
#             show_form_errors(request, form.errors)
#             return render(request, 'parsing/query/add.html')
#     return render(request, 'parsing/query/add.html')


def get_sorted_places(city_service, archive=False):
    # places = Place.objects.filter(city_service=city_service, address__icontains=F('city_service__city__name'))
    places = Place.objects.filter(city_service=city_service, archive=archive)
    if city_service.sorted:
        places = places.order_by('position')
    else:
        places = places.order_by('-rating_user_count')
    return places


def update_place_position(place_id, position):
    place = get_object_or_404(Place, id=place_id)
    place.position = position
    place.save()


@login_required()
def city_service_rating_edit(request, pk):
    city_service = get_object_or_404(CityService, pk=pk)
    places = get_sorted_places(city_service)
    if request.method == 'POST':
        city_service.sorted = True
        city_service.save()
        places.update(position=None)
        data = json.loads(request.body.decode('utf-8'))['data']
        for i in data:
            place_id = i['place_id']
            position = i['index']
            update_place_position(place_id, position)
        messages.success(request, 'Success')
        return JsonResponse({'message': 'success'})
    return render(request, 'parsing/city_service/edit_rating.html', {'city_service': city_service, 'places': places})


@login_required()
def query_all(request):
    if not has_group(request.user, 'SuperAdmin'):
        return redirect('parsing:index')
    users = User.objects.exclude(queries=None)
    selected_user = None
    try:
        username = request.GET.get('user')
        user = get_object_or_404(User, username=username)
        queries = Query.objects.filter(user=user)
        selected_user = user
    except:
        queries = Query.objects.all()
    queries = get_paginator(request, queries, 20)
    return render(request, 'parsing/query/all.html',
                  {'queries': queries, 'users': users, 'selected_user': selected_user})


@login_required()
def query_list(request):
    user = request.user
    if not has_group(user, 'Admin'):
        return redirect('parsing:index')

    queries = Query.objects.filter(user=user)
    queries = get_paginator(request, queries, 20)
    return render(request, 'parsing/query/list.html', {'queries': queries})


@login_required()
def city_service_list(request):
    city_services = CityService.objects.exclude(status='not started').order_by('-date_parsing')
    city_services = get_paginator(request, city_services)
    return render(request, 'parsing/city_service/list.html', {
        'city_services': city_services,
    })


@login_required()
def query_detail(request, slug):
    query = Query.objects.filter(slug=slug).first()
    # places = query.places.all()
    places = Place.objects.filter(queries__query=query).all()
    # print(places)
    sort_type = None
    if request.GET:
        sort_type = request.GET.get('sorted')
        if sort_type == 'rating_gt':
            places = places.order_by('rating')
        elif sort_type == 'rating_lt':
            places = places.order_by('-rating')
    places = get_paginator(request, places, 20)
    return render(request, 'parsing/query/detail.html', {'query': query, 'places': places, 'sort_type': sort_type})


@login_required()
def city_service_edit(request, pk):
    city_service = get_object_or_404(CityService, pk=pk)
    if request.method == 'POST':
        form = CityServiceContentForm(request.POST, instance=city_service)
        if form.is_valid():
            city_service = form.save()
            messages.success(request, 'Description changed')
        else:
            show_form_errors(request, form.errors)
        return redirect(city_service.get_absolute_url())
    tags = Tag.objects.all()
    review_types = ReviewType.objects.all()
    return render(request, 'parsing/city_service/edit.html', {
        'city_service': city_service,
        'tags': tags,
        'review_types': review_types
    })


@login_required()
def query_edit_access(request, slug):
    query = get_object_or_404(Query, slug=slug)
    query.access = not (query.access)
    query.save()
    return redirect(reverse('parsing:queries'))


def get_faq_questions(obj):
    faq = obj.faq
    if not faq:
        faq = FAQ()
        faq.save()
        obj.faq = faq
        obj.save()
    questions = obj.faq.questions.all()
    return questions


def save_questions(obj, questions_and_answers):
    faq = obj.faq
    faq.questions.all().delete()
    for q in questions_and_answers:
        question = FAQQuestion(question=q, answer=questions_and_answers[q])
        question.save()
        faq.questions.add(question)
    faq.save()


def set_faq(post, obj):
    data = dict(post)
    questions_and_answers = dict(zip(data['questions'], data['answers']))
    get_faq_questions(obj)
    save_questions(obj, questions_and_answers)


@login_required()
def city_service_edit_faq(request, pk):
    city_service = get_object_or_404(CityService, pk=pk)
    if request.method == 'POST':
        set_faq(request.POST, city_service)
        messages.success(request, 'FAQ updated')
        return redirect(city_service.get_absolute_url())
    return render(request, 'parsing/city_service/edit_faq.html', {'city_service': city_service})


@login_required()
def query_delete(request, pk):
    query = Query.objects.filter(pk=pk).first()
    if query and query.user == request.user or has_group(request.user, 'SuperAdmin'):
        query.delete()
        messages.success(request, f'Query "{query.name}" deleted')
    return redirect('parsing:query_list')


@login_required()
def query_file_generate(request, pk):
    query = Query.objects.filter(pk=pk).first()
    if not query:
        return redirect(query.get_absolute_url)
    # places = query.places.all()
    places = Place.objects.filter(queries__query=query).all()
    slug = query.slug
    print(slug)
    file = generate_file(slug, places)
    return file


def queries(request):
    if has_group(request.user, 'Redactor'):
        queries = Query.objects.all()
    else:
        queries = Query.objects.filter(access=True)
    try:
        search = request.GET.get('search')
        if search != '':
            queries = queries.filter(name__icontains=search)
    except:
        search = None
    try:
        tags_checked = request.GET.getlist('tags')
        if tags_checked:
            tags_checked = [int(i) for i in tags_checked]
            queries = queries.filter(tags__id__in=tags_checked).distinct()
    except:
        tags_checked = []
    queries = get_paginator(request, queries, 16)
    tags = Tag.objects.all()
    return render(request, 'parsing/query/queries.html',
                  {'queries': queries, 'tags': tags, 'search': search, 'tags_checked': tags_checked})


@login_required()
def tag_queries(request, pk):
    tag = get_object_or_404(Tag, id=pk)
    queries = tag.queries.all().distinct()
    queries = get_paginator(request, queries, 16)
    return render(request, 'parsing/tag/queries.html', {'tag': tag, 'queries': queries})


def add_path_for_tag(request, form, tag):
    cd = form.cleaned_data
    name = cd['name']
    path = slugify(name)
    if not Tag.objects.filter(path=path).exists():
        tag.path = path
        tag.save()
        return True
    messages.error(request, 'A tag with this path already exists')
    return False


@login_required()
def tags(request):
    tags = Tag.objects.all()
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            tag = form.save(commit=False)
            if add_path_for_tag(request, form, tag):
                messages.success(request, 'Tag created')
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('parsing:tags'))
    return render(request, 'parsing/tag/list.html', {'tags': tags})


@login_required()
def tag_edit(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            tag = form.save(commit=False)
            tag.save()
            messages.success(request, 'Tag changed')
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('parsing:tags'))
    return render(request, 'parsing/tag/edit.html', {'tag': tag})


@login_required()
def tag_delete(request, path):
    tag = get_object_or_404(Tag, path=path)
    tag.delete()
    messages.success(request, 'Tag deleted')
    return redirect(reverse('parsing:tags'))


def review_types(request):
    review_types = ReviewType.objects.all()
    if request.method == 'POST':
        form = ReviewTypeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Review type created')
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('parsing:review_types'))
    return render(request, 'parsing/admin_dashboard/review_type/list.html', {'review_types': review_types})


def review_type_edit(request, pk):
    review_type = get_object_or_404(ReviewType, pk=pk)
    if request.method == 'POST':
        form = ReviewTypeForm(request.POST, instance=review_type)
        if form.is_valid():
            form.save()
            messages.success(request, 'Review type changed')
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('parsing:review_types'))
    return render(request, 'parsing/admin_dashboard/review_type/edit.html', {'review_type': review_type})


def places_to_sorted_letters(places):
    places_letter = {

    }
    for i in places:
        first_letter = i.name[0]
        if first_letter in places_letter:
            places_letter[first_letter]['places'].append(i)
        else:
            places_letter[first_letter] = {
                'letter': first_letter,
                'places': [i]
            }
    letters = list(places_letter.keys())
    letters = sorted(letters)
    return {
        'places_letter': places_letter,
        'letters': letters
    }


def places(request, slug):
    query = Query.objects.filter(slug=slug).first()
    if not query:
        return redirect('parsing:index')
    places = get_sorted_places(query)
    top_places = places[:20]
    places_and_letters = places_to_sorted_letters(places)
    return render(request, 'parsing/query/places.html', {'query': query,
                                                         'top_places': top_places,
                                                         'places': places,
                                                         'places_letter': places_and_letters['places_letter'],
                                                         'letters': places_and_letters['letters']})


@login_required()
def places_copy_code(request, pk):
    city_service = get_object_or_404(CityService, pk=pk)
    places = get_sorted_places(city_service)
    top_places = places[:20]
    places_and_letters = places_to_sorted_letters(places)
    return render(request, 'parsing/city_service/places_copy_code.html', {'city_service': city_service,
                                                                          'top_places': top_places,
                                                                          'places': places,
                                                                          'places_letter': places_and_letters[
                                                                              'places_letter'],
                                                                          'letters': places_and_letters['letters']})


@login_required()
def places_copy(request, pk):
    city_service = CityService.objects.filter(pk=pk).first()
    if not city_service:
        return redirect('parsing:index')
    places = get_sorted_places(city_service)
    top_places = places[:20]
    places_and_letters = places_to_sorted_letters(places)
    return render(request, 'parsing/city_service/places_copy.html', {'city_service': city_service,
                                                                     'top_places': top_places,
                                                                     'places': places,
                                                                     'places_letter': places_and_letters[
                                                                         'places_letter'],
                                                                     'letters': places_and_letters['letters']})


# @login_required()
# def places_copy_code(request, slug):
#     query = Query.objects.filter(slug=slug).first()
#     if not query:
#         return redirect('parsing:index')
#     places = get_sorted_places(query)
#     top_places = places[:20]
#     places_and_letters = places_to_sorted_letters(places)
#
#     return render(request, 'parsing/query/places_copy_code.html', {'query': query,
#                                                               'top_places': top_places,
#                                                               'places': places,
#                                                               'places_letter': places_and_letters['places_letter'],
#                                                               'letters': places_and_letters['letters']})

def create_or_update_review_types(post, review):
    for i in post:
        if 'review_type' in i:
            review_type_id = int(i.split('_')[-1])
            review_type = ReviewType.objects.filter(pk=review_type_id).first()
            review_part = ReviewPart.objects.update_or_create(review_type=review_type, review=review)[0]
            review_part.rating = int(post[i])
            review_part.save()


def get_place_reviews(request, place):
    my_review = False
    if request.user.is_authenticated:
        reviews = place.reviews.exclude(user=request.user)
        my_review = Review.objects.filter(place=place).filter(user=request.user).first()
    else:
        reviews = place.reviews.all()
    reviews = get_paginator(request, reviews, 10)
    return {'my_review': my_review, 'reviews': reviews}


def query_place_detail(request, query_slug, place_slug):
    query = get_object_or_404(Query, slug=query_slug)
    place = get_object_or_404(Place, slug=place_slug)
    if place.is_redirect and not has_group(request.user, 'Redactor'):
        return redirect(place.redirect)
    reviews = get_place_reviews(request, place)
    return render(request, 'parsing/place/detail.html',
                  {'query': query, 'place': place, 'reviews': reviews['reviews'], 'my_review': reviews['my_review']})


def place_detail(request, slug):
    place = get_object_or_404(Place, slug=slug)
    reviews = get_place_reviews(request, place)
    return render(request, 'parsing/place/detail.html',
                  {'place': place, 'reviews': reviews['reviews'], 'my_review': reviews['my_review']})


@login_required()
def review_create(request, place_slug):
    place = get_object_or_404(Place, slug=place_slug)
    user = request.user
    review_types = ReviewType.objects.filter(city_services=place.city_service)
    if Review.objects.filter(user=request.user).filter(place=place).first():
        messages.error(request, 'You cannot leave more than one review.')
        return redirect(place.get_absolute_url())
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
        return redirect(place.get_absolute_url())
    return render(request, 'parsing/reviews/create.html',
                  {'place': place, 'user': user, 'review_types': review_types})


@login_required()
def place_edit(request, pk):
    place = get_object_or_404(Place, pk=pk)
    if request.method == 'POST':
        form = PlaceForm(request.POST, instance=place)
        if form.is_valid():
            form.save()
            messages.success(request, 'Place changed')
        else:
            show_form_errors(request, form.errors)
        return redirect(place.get_absolute_url())
    return render(request, 'parsing/place/edit.html', {'place': place})


def place_set_description(place):
    reviews = place.reviews.all()[:20]
    text = ''
    for review in reviews:
        text += review.text
    description = sumextract(text, 5)
    description = description.replace('. ', '.').replace('.', '. ')
    description = description.replace(', ', ',').replace(',', ', ')
    place.description = place.name + ' - ' + description
    place.save()


@login_required()
def place_generate_description(request, place_slug):
    place = get_object_or_404(Place, slug=place_slug)
    place_set_description(place)
    messages.success(request, "Description generated")
    return redirect(place.get_absolute_url())


@login_required()
def city_service_places_generate_description(request, pk):
    city_service = get_object_or_404(CityService, pk=pk)
    places = Place.objects.filter(city_service=city_service)
    for place in places:
        place_set_description(place)
    return redirect(city_service.get_absolute_url())


@login_required()
def place_edit_faq(request, pk):
    place = get_object_or_404(Place, pk=pk)
    if request.method == 'POST':
        set_faq(request.POST, place)
        messages.success(request, 'FAQ updated')
        return redirect(place.get_absolute_url())
    return render(request, 'parsing/place/edit_faq.html', {'place': place})


@login_required()
def place_edit_archive(request, pk):
    place = get_object_or_404(Place, pk=pk)
    if has_group(request.user, 'SuperAdmin'):
        archive = not place.archive
        place.archive = archive
        place.save()
        type = '?type=open' if archive else '?type=archive'
        return redirect(place.city_service.get_absolute_url() + type)
    return redirect(place.get_absolute_url())


@login_required()
def place_update(request, pk):
    place = Place.objects.filter(pk=pk).first()
    # selenium_query_detail(place_id=place.place_id)
    # updateDetail(place.pk)
    return redirect(place.get_absolute_url())


def generate_slug():
    places = Place.objects.all()
    for place in places:
        place.slug = slugify(f'{place.name}-{str(place.id)}')
        place.save()


@login_required()
def profile(request):
    user = request.user
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            messages.success(request, 'Data changed')
            form.save()
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('parsing:profile'))
    return render(request, 'parsing/user/profile.html', {'user': user})


@login_required()
def public_cabinet(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'parsing/user/public_cabinet.html', {'user': user})


@login_required()
def all_reviews(request):
    if not has_group(request.user, 'Redactor'):
        return redirect('parsing:index')
    reviews = Review.objects.all()
    reviews = get_paginator(request, reviews, 10)
    return render(request, 'parsing/reviews/all.html', {'reviews': reviews})


@login_required()
def user_reviews(request, username):
    user = get_object_or_404(User, username=username)
    reviews = user.reviews.all()
    reviews = get_paginator(request, reviews, 12)
    return render(request, 'parsing/user/reviews.html', {'user': user, 'reviews': reviews})


@login_required()
def my_reviews(request):
    user = request.user
    reviews = user.reviews.all()
    reviews = get_paginator(request, reviews, 10)
    return render(request, 'parsing/reviews/reviews.html', {'reviews': reviews})


@login_required()
def review_edit(request, pk):
    review = Review.objects.filter(pk=pk).first()
    if (not review or request.user != review.user) and not has_group(request.user, 'Redactor'):
        return redirect('parsing:my_reviews')
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.is_edit = True
            review.original_text = request.POST['text']
            review.save()
            create_or_update_review_types(request.POST, review)
            messages.success(request, 'Review changed')
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('parsing:review_edit', args=[review.id]))

    review_types = ReviewType.objects.filter(reviews__review=review)
    review_parts = ReviewPart.objects.values('review_type', 'rating').filter(review=review)
    print(review_parts)
    return render(request, 'parsing/reviews/review_edit.html',
                  {'review': review, 'review_types': review_types, 'review_parts': review_parts})


@login_required()
def review_uniqueize(request, pk):
    review = get_object_or_404(Review, pk=pk)
    uniqueize_review.delay(review.id)
    return redirect(reverse('parsing:review_edit', args=[review.id]))


@api_view(['GET'])
def review_api_detail(request, pk):
    review = get_object_or_404(Review, pk=pk)
    return Response({'review': {
        'text': review.text,
        'original_text': review.original_text,
        'id': review.id
    }})


@api_view(['POST'])
def review_api_update(request, pk):
    review = get_object_or_404(Review, pk=pk)
    data = request.data
    print(data)
    try:
        # review.text = data['text']
        # review.save()
        pass
    except KeyError:
        pass
    return Response({'review': {
        'id': review.id,
        'text': review.text
    }})


@login_required()
def place_reviews_uniqueize(request, pk):
    place = get_object_or_404(Place, pk=pk)
    uniqueize_text_task.delay(place_id=place.id)
    messages.success(request, 'Reviews uniqueize started')
    return redirect(place.get_absolute_url())


@login_required()
def city_service_reviews_uniqueize(request, pk):
    city_service = get_object_or_404(CityService, pk=pk)
    uniqueize_text_task.delay(city_service_id=city_service.id)
    messages.success(request, 'Reviews uniqueize started')
    return redirect(city_service.get_absolute_url())


@login_required()
def city_service_preview_reviews_uniqueize(request, pk):
    city_service = get_object_or_404(CityService, pk=pk)
    places = get_sorted_places(city_service)[:20]
    review_ids = []
    for place in places:
        more_text_review = place.get_more_text
        if more_text_review:
            more_text_review.base = True
            more_text_review.save()
            review_ids.append(more_text_review.id)
    if review_ids:
        unique_review = UniqueReview.objects.create(reviews_count=len(review_ids), city_service=city_service)
        unique_review.save()
        preview_uniqueize_reviews_task.delay(review_ids, unique_review.id)
        messages.success(request, 'Reviews uniqueize')
    return redirect(city_service.get_absolute_url())


@login_required()
def unique_reviews_list(request):
    unique_reviews = UniqueReview.objects.all().order_by('-pk')
    unique_reviews = get_paginator(request, unique_reviews)
    return render(request, 'parsing/unique_reviews/list.html', {
        'unique_reviews': unique_reviews
    })


def registration(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            group = Group.objects.filter(name='User').first()
            if group:
                user.groups.add(group)
            login(request, user)
            return redirect(reverse('parsing:profile'))
        else:
            show_form_errors(request, form.errors)
    return render(request, 'parsing/user/add.html')


@login_required()
def group_list(request):
    groups = Group.objects.all()
    groups_not_count = User.objects.filter(groups=None).count()
    return render(request, 'parsing/admin_dashboard/group/list.html',
                  {'groups': groups, 'groups_not_count': groups_not_count})


@login_required()
def group_detail(request, pk):
    group = Group.objects.filter(pk=pk).first()
    if group:
        users = group.user_set.all()
        users = get_paginator(request, users, count=12)
        return render(request, 'parsing/admin_dashboard/group/detail.html', {'group': group, 'users': users})
    return redirect('group_list')


@login_required()
def group_not(request):
    users = User.objects.filter(groups=None)
    return render(request, 'parsing/admin_dashboard/group/not.html', {'users': users})


@login_required()
def admin_dashboard(request):
    user = request.user
    if user.is_superuser:
        return render(request, 'parsing/admin_dashboard/dashboard.html')
    return redirect('/')


@login_required()
def user_list(request):
    users = User.objects.all().order_by('-pk')
    users = get_paginator(request, users, 10)
    return render(request, 'parsing/user/list.html', {'users': users})


@login_required()
def user_detail(request, pk):
    if not has_group(request.user, 'Admin'):
        return redirect('parsing:index')
    user = User.objects.filter(pk=pk).first()
    if request.method == 'POST':
        form = UserDetailForm(request.POST, instance=user)
        if form.is_valid():
            user = form.save(commit=False)
            cd = form.cleaned_data
            group_id = cd['groups']
            group = Group.objects.filter(id__in=group_id).first()
            if group:
                user.groups.clear()
                user.groups.add(group)
            user.save()
            messages.success(request, 'Data changed')
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('parsing:user_detail', args=[user.id]))

    groups = Group.objects.all()
    if user:
        return render(request, 'parsing/user/detail.html', {'user': user, 'groups': groups})
    return redirect('/')


@login_required()
def city_autocreate(request):
    cities = [
        {'name': 'Virginia Beach', 'population': 450980,
         'zip_codes': ['23464', '23462', '23452', '23454', '23456', '23455', '23451', '23457', '23460',
                       '23459', '23461'], 'coordinate': {'latitude': '36.78', 'longitude': '-76.02'}},
        {'name': 'Norfolk', 'population': 245428,
         'zip_codes': ['23503', '23513', '23505', '23518', '23504', '23508', '23502', '23511', '23509',
                       '23510', '23523', '23507', '23517', '23551'],
         'coordinate': {'latitude': '36.92', 'longitude': '-76.25'}},
        {'name': 'Chesapeake', 'population': 233371,
         'zip_codes': ['23322', '23320', '23323', '23321', '23324', '23325'],
         'coordinate': {'latitude': '36.68', 'longitude': '-76.3'}},
        {'name': 'Richmond', 'population': 217853,
         'zip_codes': ['23223', '23234', '23225', '23224', '23231', '23228', '23229', '23220', '23235',
                       '23233', '23222', '23238', '23227', '23237', '23236', '23294', '23226', '23221',
                       '23230', '23219', '23250'],
         'coordinate': {'latitude': '37.53', 'longitude': '-77.48'}},
        {'name': 'Newport News', 'population': 182965,
         'zip_codes': ['23608', '23602', '23606', '23601', '23607', '23605', '23603'],
         'coordinate': {'latitude': '37.08', 'longitude': '-76.52'}},
        {'name': 'Alexandria', 'population': 150575,
         'zip_codes': ['22304', '22309', '22306', '22314', '22312', '22310', '22315', '22311', '22305',
                       '22302', '22303', '22308', '22301', '22307'],
         'coordinate': {'latitude': '38.82', 'longitude': '-77.09'}},
        {'name': 'Hampton', 'population': 136879,
         'zip_codes': ['23666', '23669', '23663', '23661', '23664', '23665'],
         'coordinate': {'latitude': '37.05', 'longitude': '-76.3'}},
        {'name': 'Roanoke', 'population': 99428,
         'zip_codes': ['24018', '24012', '24019', '24017', '24014', '24015', '24016', '24013', '24020',
                       '24011'], 'coordinate': {'latitude': '37.28', 'longitude': '-79.96'}},
        {'name': 'Portsmouth', 'population': 96004,
         'zip_codes': ['23703', '23701', '23704', '23707', '23702', '23709', '23708'],
         'coordinate': {'latitude': '36.86', 'longitude': '-76.36'}},
        {'name': 'Suffolk', 'population': 86806,
         'zip_codes': ['23434', '23435', '23437', '23438', '23432', '23433', '23436'],
         'coordinate': {'latitude': '36.7', 'longitude': '-76.63'}},
        {'name': 'Lynchburg', 'population': 79047, 'zip_codes': ['24502', '24501', '24503', '24504'],
         'coordinate': {'latitude': '37.4', 'longitude': '-79.19'}},
        {'name': 'Harrisonburg', 'population': 52478, 'zip_codes': ['22801', '22802', '22807'],
         'coordinate': {'latitude': '38.44', 'longitude': '-78.87'}},
        {'name': 'Leesburg', 'population': 49496, 'zip_codes': ['20176', '20175'],
         'coordinate': {'latitude': '39.11', 'longitude': '-77.55'}},
        {'name': 'Charlottesville', 'population': 45593,
         'zip_codes': ['22903', '22901', '22902', '22911', '22904'],
         'coordinate': {'latitude': '38.04', 'longitude': '-78.49'}},
        {'name': 'Blacksburg', 'population': 43985, 'zip_codes': ['24060'],
         'coordinate': {'latitude': '37.23', 'longitude': '-80.43'}},
        {'name': 'Danville', 'population': 42444, 'zip_codes': ['24540', '24541'],
         'coordinate': {'latitude': '36.58', 'longitude': '-79.41'}},
        {'name': 'Manassas', 'population': 42081, 'zip_codes': ['20110', '20109'],
         'coordinate': {'latitude': '38.75', 'longitude': '-77.48'}},
        {'name': 'Petersburg', 'population': 32701, 'zip_codes': ['23803', '23805', '23806'],
         'coordinate': {'latitude': '37.2', 'longitude': '-77.39'}},
        {'name': 'Fredericksburg', 'population': 28350,
         'zip_codes': ['22407', '22405', '22408', '22401', '22406'],
         'coordinate': {'latitude': '38.3', 'longitude': '-77.49'}},
        {'name': 'Winchester', 'population': 27543, 'zip_codes': ['22602', '22601', '22603'],
         'coordinate': {'latitude': '39.17', 'longitude': '-78.17'}},
        {'name': 'Salem', 'population': 25483, 'zip_codes': ['24153'],
         'coordinate': {'latitude': '37.29', 'longitude': '-80.06'}},
        {'name': 'Herndon', 'population': 24554, 'zip_codes': ['20171', '20170'],
         'coordinate': {'latitude': '38.97', 'longitude': '-77.39'}},
        {'name': 'Staunton', 'population': 24538, 'zip_codes': ['24401'],
         'coordinate': {'latitude': '38.16', 'longitude': '-79.06'}},
        {'name': 'Fairfax', 'population': 24483, 'zip_codes': ['22030', '22033', '22031', '22032', '22035'],
         'coordinate': {'latitude': '38.85', 'longitude': '-77.3'}},
        {'name': 'Hopewell', 'population': 22196, 'zip_codes': ['23860'],
         'coordinate': {'latitude': '37.29', 'longitude': '-77.3'}},
        {'name': 'Christiansburg', 'population': 21805, 'zip_codes': ['24073'],
         'coordinate': {'latitude': '37.14', 'longitude': '-80.4'}},
        {'name': 'Waynesboro', 'population': 21366, 'zip_codes': ['22980'],
         'coordinate': {'latitude': '38.07', 'longitude': '-78.9'}},
        {'name': 'Colonial Heights', 'population': 17731, 'zip_codes': ['23834'],
         'coordinate': {'latitude': '37.27', 'longitude': '-77.4'}},
        {'name': 'Radford', 'population': 17646, 'zip_codes': ['24141', '24142'],
         'coordinate': {'latitude': '37.12', 'longitude': '-80.56'}},
        {'name': 'Culpeper', 'population': 17411, 'zip_codes': ['22701'],
         'coordinate': {'latitude': '38.47', 'longitude': '-78'}},
        {'name': 'Bristol', 'population': 17184, 'zip_codes': ['24201', '24202'],
         'coordinate': {'latitude': '36.62', 'longitude': '-82.16'}},
        {'name': 'Vienna', 'population': 16459, 'zip_codes': ['22182', '22180', '22181', '22185'],
         'coordinate': {'latitude': '38.9', 'longitude': '-77.26'}},
        {'name': 'Manassas Park', 'population': 15174, 'zip_codes': ['20111', '20112'],
         'coordinate': {'latitude': '38.77', 'longitude': '-77.44'}},
        {'name': 'Front Royal', 'population': 15038, 'zip_codes': ['22630'],
         'coordinate': {'latitude': '38.92', 'longitude': '-78.19'}},
        {'name': 'Williamsburg', 'population': 14691, 'zip_codes': ['23185', '23188', '23187'],
         'coordinate': {'latitude': '37.27', 'longitude': '-76.71'}},
        {'name': 'Martinsville', 'population': 13711, 'zip_codes': ['24112'],
         'coordinate': {'latitude': '36.68', 'longitude': '-79.86'}},
        {'name': 'Falls Church', 'population': 13601,
         'zip_codes': ['22042', '22041', '22043', '22046', '22044'],
         'coordinate': {'latitude': '38.88', 'longitude': '-77.17'}},
        {'name': 'Poquoson', 'population': 12048, 'zip_codes': ['23662'],
         'coordinate': {'latitude': '37.15', 'longitude': '-76.27'}},
        {'name': 'Warrenton', 'population': 9907, 'zip_codes': ['20187', '20186'],
         'coordinate': {'latitude': '38.72', 'longitude': '-77.8'}},
        {'name': 'Purcellville', 'population': 8929, 'zip_codes': ['20132'],
         'coordinate': {'latitude': '39.14', 'longitude': '-77.71'}},
        {'name': 'Pulaski', 'population': 8909, 'zip_codes': ['24301'],
         'coordinate': {'latitude': '37.05', 'longitude': '-80.76'}},
        {'name': 'Franklin', 'population': 8526, 'zip_codes': ['23851'],
         'coordinate': {'latitude': '36.68', 'longitude': '-76.94'}},
        {'name': 'Smithfield', 'population': 8287, 'zip_codes': ['23430'],
         'coordinate': {'latitude': '36.98', 'longitude': '-76.62'}},
        {'name': 'Farmville', 'population': 8229, 'zip_codes': ['23901', '23909'],
         'coordinate': {'latitude': '37.3', 'longitude': '-78.4'}},
        {'name': 'Vinton', 'population': 8180, 'zip_codes': ['24179'],
         'coordinate': {'latitude': '37.27', 'longitude': '-79.89'}},
        {'name': 'Abingdon', 'population': 8146, 'zip_codes': ['24210', '24211'],
         'coordinate': {'latitude': '36.71', 'longitude': '-81.97'}},
        {'name': 'Wytheville', 'population': 8133, 'zip_codes': ['24382'],
         'coordinate': {'latitude': '36.95', 'longitude': '-81.09'}},
        {'name': 'South Boston', 'population': 7986, 'zip_codes': ['24592'],
         'coordinate': {'latitude': '36.71', 'longitude': '-78.91'}},
        {'name': 'Ashland', 'population': 7328, 'zip_codes': ['23005'],
         'coordinate': {'latitude': '37.76', 'longitude': '-77.47'}},
        {'name': 'Lexington', 'population': 7311, 'zip_codes': ['24450'],
         'coordinate': {'latitude': '37.78', 'longitude': '-79.44'}},
        {'name': 'Galax', 'population': 7014, 'zip_codes': ['24333'],
         'coordinate': {'latitude': '36.67', 'longitude': '-80.92'}},
        {'name': 'Buena Vista', 'population': 6603, 'zip_codes': ['24416'],
         'coordinate': {'latitude': '37.73', 'longitude': '-79.36'}},
        {'name': 'Strasburg', 'population': 6559, 'zip_codes': ['22657', '22641'],
         'coordinate': {'latitude': '38.99', 'longitude': '-78.35'}},
        {'name': 'Bedford', 'population': 6466, 'zip_codes': ['24523'],
         'coordinate': {'latitude': '37.34', 'longitude': '-79.52'}},
        {'name': 'Bridgewater', 'population': 5951, 'zip_codes': ['22812'],
         'coordinate': {'latitude': '38.39', 'longitude': '-78.97'}},
        {'name': 'Marion', 'population': 5875, 'zip_codes': ['24354'],
         'coordinate': {'latitude': '36.84', 'longitude': '-81.51'}},
        {'name': 'Covington', 'population': 5802, 'zip_codes': ['24426'],
         'coordinate': {'latitude': '37.78', 'longitude': '-79.99'}},
        {'name': 'Richlands', 'population': 5583, 'zip_codes': ['24641'],
         'coordinate': {'latitude': '37.09', 'longitude': '-81.81'}},
        {'name': 'Emporia', 'population': 5462, 'zip_codes': ['23847'],
         'coordinate': {'latitude': '36.7', 'longitude': '-77.54'}},
        {'name': 'Big Stone Gap', 'population': 5457, 'zip_codes': ['24219'],
         'coordinate': {'latitude': '36.86', 'longitude': '-82.78'}},
        {'name': 'Bluefield', 'population': 5302, 'zip_codes': ['24605'],
         'coordinate': {'latitude': '37.24', 'longitude': '-81.27'}},
        {'name': 'Woodstock', 'population': 5226, 'zip_codes': ['22664'],
         'coordinate': {'latitude': '38.88', 'longitude': '-78.52'}},
        {'name': 'Dumfries', 'population': 5192, 'zip_codes': ['22026'],
         'coordinate': {'latitude': '38.57', 'longitude': '-77.32'}},
        {'name': 'Orange', 'population': 4902, 'zip_codes': ['22960'],
         'coordinate': {'latitude': '38.25', 'longitude': '-78.11'}},
        {'name': 'Luray', 'population': 4850, 'zip_codes': ['22835'],
         'coordinate': {'latitude': '38.67', 'longitude': '-78.45'}},
        {'name': 'Rocky Mount', 'population': 4798, 'zip_codes': ['24151'],
         'coordinate': {'latitude': '37', 'longitude': '-79.89'}},
        {'name': 'South Hill', 'population': 4541, 'zip_codes': ['23970'],
         'coordinate': {'latitude': '36.73', 'longitude': '-78.13'}},
        {'name': 'Tazewell', 'population': 4479, 'zip_codes': ['24651'],
         'coordinate': {'latitude': '37.13', 'longitude': '-81.51'}},
        {'name': 'Berryville', 'population': 4297, 'zip_codes': ['22611'],
         'coordinate': {'latitude': '39.15', 'longitude': '-77.98'}},
        {'name': 'Norton', 'population': 4031, 'zip_codes': ['24273'],
         'coordinate': {'latitude': '36.93', 'longitude': '-82.63'}},
        {'name': 'Broadway', 'population': 3780, 'zip_codes': ['22815'],
         'coordinate': {'latitude': '38.61', 'longitude': '-78.8'}},
        {'name': 'Clifton Forge', 'population': 3775, 'zip_codes': ['24422'],
         'coordinate': {'latitude': '37.82', 'longitude': '-79.82'}},
        {'name': 'Blackstone', 'population': 3553, 'zip_codes': ['23824'],
         'coordinate': {'latitude': '37.08', 'longitude': '-78'}},
        {'name': 'Colonial Beach', 'population': 3541, 'zip_codes': ['22443'],
         'coordinate': {'latitude': '38.26', 'longitude': '-76.98'}},
        {'name': 'Altavista', 'population': 3460, 'zip_codes': ['24517'],
         'coordinate': {'latitude': '37.12', 'longitude': '-79.29'}},
        {'name': 'Lebanon', 'population': 3356, 'zip_codes': ['24266'],
         'coordinate': {'latitude': '36.9', 'longitude': '-82.08'}},
        {'name': 'West Point', 'population': 3333, 'zip_codes': ['23181'],
         'coordinate': {'latitude': '37.55', 'longitude': '-76.8'}},
        {'name': 'Wise', 'population': 3144, 'zip_codes': ['24293'],
         'coordinate': {'latitude': '36.98', 'longitude': '-82.58'}},
        {'name': 'Chincoteague', 'population': 2913, 'zip_codes': ['23336'],
         'coordinate': {'latitude': '37.95', 'longitude': '-75.35'}},
        {'name': 'Elkton', 'population': 2790, 'zip_codes': ['22827'],
         'coordinate': {'latitude': '38.41', 'longitude': '-78.61'}},
        {'name': 'Grottoes', 'population': 2738, 'zip_codes': ['24441'],
         'coordinate': {'latitude': '38.27', 'longitude': '-78.82'}},
        {'name': 'Pearisburg', 'population': 2699, 'zip_codes': ['24134'],
         'coordinate': {'latitude': '37.33', 'longitude': '-80.73'}},
        {'name': 'Dublin', 'population': 2686, 'zip_codes': ['24084'],
         'coordinate': {'latitude': '37.1', 'longitude': '-80.68'}},
        {'name': 'Hillsville', 'population': 2680, 'zip_codes': ['24343'],
         'coordinate': {'latitude': '36.76', 'longitude': '-80.73'}},
        {'name': 'Windsor', 'population': 2654, 'zip_codes': ['23487'],
         'coordinate': {'latitude': '36.81', 'longitude': '-76.74'}},
        {'name': 'Timberville', 'population': 2586, 'zip_codes': ['22853'],
         'coordinate': {'latitude': '38.63', 'longitude': '-78.77'}},
        {'name': 'Tappahannock', 'population': 2380, 'zip_codes': ['22560'],
         'coordinate': {'latitude': '37.92', 'longitude': '-76.87'}},
        {'name': 'Shenandoah', 'population': 2352, 'zip_codes': ['22849'],
         'coordinate': {'latitude': '38.49', 'longitude': '-78.62'}},
        {'name': 'Chase City', 'population': 2304, 'zip_codes': ['23924'],
         'coordinate': {'latitude': '36.8', 'longitude': '-78.46'}},
        {'name': 'Crewe', 'population': 2282, 'zip_codes': ['23930'],
         'coordinate': {'latitude': '37.18', 'longitude': '-78.13'}},
        {'name': 'Amherst', 'population': 2206, 'zip_codes': ['24521'],
         'coordinate': {'latitude': '37.58', 'longitude': '-79.05'}},
        {'name': 'New Market', 'population': 2199, 'zip_codes': ['22844'],
         'coordinate': {'latitude': '38.65', 'longitude': '-78.67'}},
        {'name': 'Waverly', 'population': 2081, 'zip_codes': ['23890', '23891'],
         'coordinate': {'latitude': '37.03', 'longitude': '-77.1'}},
        {'name': 'Saltville', 'population': 2042, 'zip_codes': ['24370'],
         'coordinate': {'latitude': '36.88', 'longitude': '-81.76'}},
        {'name': 'Mount Jackson', 'population': 2036, 'zip_codes': ['22842'],
         'coordinate': {'latitude': '38.74', 'longitude': '-78.64'}},
        {'name': 'Coeburn', 'population': 2015, 'zip_codes': ['24230'],
         'coordinate': {'latitude': '36.95', 'longitude': '-82.47'}},
        {'name': 'Gate City', 'population': 1976, 'zip_codes': ['24251'],
         'coordinate': {'latitude': '36.64', 'longitude': '-82.58'}},
        {'name': 'Haymarket', 'population': 1973, 'zip_codes': ['20169'],
         'coordinate': {'latitude': '38.81', 'longitude': '-77.64'}},
        {'name': 'Narrows', 'population': 1964, 'zip_codes': ['24124'],
         'coordinate': {'latitude': '37.33', 'longitude': '-80.81'}},
        {'name': 'Stephens City', 'population': 1921, 'zip_codes': ['22655'],
         'coordinate': {'latitude': '39.09', 'longitude': '-78.22'}},
        {'name': 'Lovettsville', 'population': 1869, 'zip_codes': ['20180'],
         'coordinate': {'latitude': '39.27', 'longitude': '-77.64'}},
        {'name': 'Pennington Gap', 'population': 1823, 'zip_codes': ['24277'],
         'coordinate': {'latitude': '36.76', 'longitude': '-83.03'}},
        {'name': 'Chilhowie', 'population': 1749, 'zip_codes': ['24319'],
         'coordinate': {'latitude': '36.8', 'longitude': '-81.68'}},
        {'name': 'Appomattox', 'population': 1744, 'zip_codes': ['24522'],
         'coordinate': {'latitude': '37.36', 'longitude': '-78.83'}},
        {'name': 'Victoria', 'population': 1696, 'zip_codes': ['23974'],
         'coordinate': {'latitude': '36.99', 'longitude': '-78.22'}},
        {'name': 'Appalachia', 'population': 1684, 'zip_codes': ['24216'],
         'coordinate': {'latitude': '36.91', 'longitude': '-82.79'}},
        {'name': 'Stanley', 'population': 1663, 'zip_codes': ['22851'],
         'coordinate': {'latitude': '38.58', 'longitude': '-78.5'}},
        {'name': 'Louisa', 'population': 1610, 'zip_codes': ['23093'],
         'coordinate': {'latitude': '38.02', 'longitude': '-78'}},
        {'name': 'Dayton', 'population': 1578, 'zip_codes': ['22821'],
         'coordinate': {'latitude': '38.42', 'longitude': '-78.94'}},
        {'name': 'Gordonsville', 'population': 1560, 'zip_codes': ['22942'],
         'coordinate': {'latitude': '38.14', 'longitude': '-78.19'}},
        {'name': 'Warsaw', 'population': 1501, 'zip_codes': ['22572'],
         'coordinate': {'latitude': '37.96', 'longitude': '-76.76'}},
        {'name': 'Rural Retreat', 'population': 1485, 'zip_codes': ['24368'],
         'coordinate': {'latitude': '36.9', 'longitude': '-81.28'}},
        {'name': 'Chatham', 'population': 1476, 'zip_codes': ['24531'],
         'coordinate': {'latitude': '36.82', 'longitude': '-79.4'}},
        {'name': 'Glade Spring', 'population': 1458, 'zip_codes': ['24340'],
         'coordinate': {'latitude': '36.79', 'longitude': '-81.77'}},
        {'name': 'Stuart', 'population': 1455, 'zip_codes': ['24171'],
         'coordinate': {'latitude': '36.64', 'longitude': '-80.27'}},
        {'name': 'Kilmarnock', 'population': 1446, 'zip_codes': ['22482'],
         'coordinate': {'latitude': '37.71', 'longitude': '-76.38'}},
        {'name': 'Exmore', 'population': 1445, 'zip_codes': ['23350'],
         'coordinate': {'latitude': '37.53', 'longitude': '-75.83'}},
        {'name': 'Honaker', 'population': 1399, 'zip_codes': ['24260'],
         'coordinate': {'latitude': '37.02', 'longitude': '-81.97'}},
        {'name': 'Clintwood', 'population': 1343, 'zip_codes': ['24228'],
         'coordinate': {'latitude': '37.15', 'longitude': '-82.46'}},
        {'name': 'Middletown', 'population': 1319, 'zip_codes': ['22645'],
         'coordinate': {'latitude': '39.03', 'longitude': '-78.28'}},
        {'name': 'Hurt', 'population': 1281, 'zip_codes': ['24563'],
         'coordinate': {'latitude': '37.1', 'longitude': '-79.3'}},
        {'name': 'Weber City', 'population': 1275, 'zip_codes': ['24290'],
         'coordinate': {'latitude': '36.62', 'longitude': '-82.56'}},
        {'name': 'Onancock', 'population': 1262, 'zip_codes': ['23417'],
         'coordinate': {'latitude': '37.71', 'longitude': '-75.74'}},
        {'name': 'Halifax', 'population': 1252, 'zip_codes': ['24558'],
         'coordinate': {'latitude': '36.76', 'longitude': '-78.93'}},
        {'name': 'Courtland', 'population': 1247, 'zip_codes': ['23837'],
         'coordinate': {'latitude': '36.71', 'longitude': '-77.06'}},
        {'name': 'Gretna', 'population': 1245, 'zip_codes': ['24557'],
         'coordinate': {'latitude': '36.95', 'longitude': '-79.36'}},
        {'name': 'Kenbridge', 'population': 1241, 'zip_codes': ['23944'],
         'coordinate': {'latitude': '36.96', 'longitude': '-78.13'}},
        {'name': 'Buchanan', 'population': 1171, 'zip_codes': ['24066'],
         'coordinate': {'latitude': '37.52', 'longitude': '-79.69'}},
        {'name': 'Bowling Green', 'population': 1152, 'zip_codes': ['22427'],
         'coordinate': {'latitude': '38.05', 'longitude': '-77.35'}},
        {'name': 'Clarksville', 'population': 1117, 'zip_codes': ['23927'],
         'coordinate': {'latitude': '36.62', 'longitude': '-78.57'}},
        {'name': 'Brookneal', 'population': 1115, 'zip_codes': ['24528'],
         'coordinate': {'latitude': '37.05', 'longitude': '-78.95'}},
        {'name': 'Glasgow', 'population': 1113, 'zip_codes': ['24555'],
         'coordinate': {'latitude': '37.63', 'longitude': '-79.45'}},
        {'name': 'Cedar Bluff', 'population': 1090, 'zip_codes': ['24609'],
         'coordinate': {'latitude': '37.09', 'longitude': '-81.76'}},
        {'name': 'Pembroke', 'population': 1087, 'zip_codes': ['24136'],
         'coordinate': {'latitude': '37.32', 'longitude': '-80.64'}},
        {'name': 'Lawrenceville', 'population': 1081, 'zip_codes': ['23868'],
         'coordinate': {'latitude': '36.76', 'longitude': '-77.85'}},
        {'name': 'Edinburg', 'population': 1065, 'zip_codes': ['22824'],
         'coordinate': {'latitude': '38.82', 'longitude': '-78.56'}},
        {'name': 'Occoquan', 'population': 1013, 'zip_codes': ['22125'],
         'coordinate': {'latitude': '38.68', 'longitude': '-77.26'}}]
    # City.objects.all().delete()
    for city in cities:
        city_object = City.objects.get_or_create(name=city.get('name'))[0]
        city_object.slug = slugify(city.get('name'))
        city_object.population = city.get('population')
        city_object.zip_codes = city.get('zip_codes')
        city_object.latitude = float(city['coordinate'].get('latitude'))
        city_object.longitude = float(city['coordinate'].get('longitude'))
        city_object.save()
        print(city)

        city_service_create(city=city_object)
    return redirect(reverse('parsing:city_list'))


@login_required()
def city_img_autocreate(request):
    cities_img_parser.delay()
    messages.success(request, 'Parsing started')
    return redirect(reverse('parsing:city_list'))


def city_list(request):
    cities = get_cities()
    if request.method == 'POST' and has_group(request.user, 'Redactor'):
        form = CityForm(request.POST)
        if form.is_valid():
            city = form.save(commit=False)
            city.map_name = slugify(request.POST['name'])
            slug = slugify(request.POST['name'])
            unique_error_or_save(request, slug, city, City)
            city_service_create(city=city)
        return redirect(reverse('parsing:city_list'))
    return render(request, 'parsing/city/list.html', {
        'cities': cities
    })


def get_nearest_cities(city, nearest=5):
    latitude = city.latitude
    longitude = city.longitude
    nearest_city = {}
    if not latitude or not longitude:
        return []
    for c in get_cities():
        if c != city and (c.latitude and c.longitude):
            distance = ((float(c.latitude) - float(latitude)) ** 2 + (
                    float(c.longitude) - float(longitude)) ** 2) ** 0.5
            nearest_city.update({distance: c})
    nearest_city_list = []
    for i in sorted(nearest_city):
        print(i, nearest_city[i])
        nearest_city_list.append(nearest_city[i])
        if len(nearest_city_list) > nearest:
            break
    return nearest_city_list


def city_detail(request, slug):
    city = get_object_or_404(City, slug=slug)
    city_services = CityService.objects.filter(city=city)
    if not has_group(request.user, 'Redactor'):
        city_services = city_services.filter(access=True)

    return render(request, 'parsing/city/detail.html', {
        'city': city,
        'city_services': city_services,
        'nearest_cities': get_nearest_cities(city)
    })


def set_aliases(aliases: str, city: City):
    aliases = aliases.split(',')
    aliases = [i.strip() for i in aliases]
    city.aliases = aliases


def city_edit(request, slug):
    city = get_object_or_404(City, slug=slug)
    if request.method == 'POST':
        form = CityEditForm(request.POST, instance=city)
        if form.is_valid():
            city = form.save(commit=False)
            slug = slugify(city.name)
            set_aliases(request.POST['aliases'], city)
            unique_error_or_save(request, slug, city, City)
        return redirect(reverse('parsing:city_detail', args=[city.slug]))
    return render(request, 'parsing/city/edit.html', {
        'city': city
    })


@login_required()
def service_list(request):
    services = Service.objects.all()
    services = get_paginator(request, services, 200)
    if request.method == 'POST':
        form = ServiceForm(request.POST)
        service = form.save(commit=False)
        service.name = service.name.title()
        slug = slugify(request.POST['name'])
        unique_error_or_save(request, slug, service, Service)
        city_service_create(service=service)
        return redirect(reverse('parsing:service_list'))
    return render(request, 'parsing/service/list.html', {
        'services': services
    })


@login_required()
def service_autocreate(request):
    service_autocreate_task.delay()
    messages.success(request, 'Autocreate started')
    return redirect(reverse('parsing:service_list'))


def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug)
    cities = City.objects.filter(city_service__service=service, city_service__access=True, is_county=False)
    return render(request, 'parsing/service/detail.html', {
        'service': service,
        'cities': cities
    })


def service_edit(request, slug):
    service = get_object_or_404(Service, slug=slug)
    if request.method == 'POST':
        form = ServiceEditForm(request.POST, instance=service)
        service = form.save(commit=False)
        slug = slugify(service.name)
        unique_error_or_save(request, slug, service, Service)
        return redirect(service.get_absolute_url())
    return render(request, 'parsing/service/edit.html', {
        'service': service
    })


def service_edit_faq(request, slug):
    service = get_object_or_404(Service, slug=slug)
    if request.method == 'POST':
        set_faq(request.POST, service)
        messages.success(request, 'FAQ updated')
        return redirect(service.get_absolute_url())
    return render(request, 'parsing/service/edit_faq.html', {
        'service': service
    })


def city_service_detail(request, city_slug, service_slug):
    if not has_group(request.user, 'SuperAdmin'):
        raise Http404('Page not found')

    type = request.GET.get('type')
    type = type if type else 'open'
    if type == 'archive':
        archive = True
    else:
        archive = False

    city_service = CityService.objects.filter(city__slug=city_slug, service__slug=service_slug).first()
    places = get_sorted_places(city_service, archive=archive)
    top_places = places[:20]
    places_and_letters = places_to_sorted_letters(places)

    return render(request, 'parsing/city_service/places.html', {
        'city_service': city_service,
        'top_places': top_places,
        'places': places,
        'places_letter': places_and_letters['places_letter'],
        'letters': places_and_letters['letters'],
        'opened_count': Place.objects.filter(city_service=city_service, archive=False).count(),
        'archived_count': Place.objects.filter(city_service=city_service, archive=True).count(),
        'archive': archive
    })


@login_required()
def city_service_access(request, pk):
    city_service = CityService.objects.filter(pk=pk).first()
    if city_service:
        city_service.access = not city_service.access
        city_service.save()
        messages.success(request, 'Status changed')
    return redirect(city_service.get_absolute_url())


@login_required()
def city_service_file(request, pk):
    city_service = get_object_or_404(CityService, pk=pk)
    if request.method == "POST":
        form = CityServiceFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.save(commit=False)
            file.city_service = city_service
            file.save()
        else:
            show_form_errors(request, form.errors)
        return redirect(reverse('parsing:city_service_file', args=[city_service.pk]))
    files = city_service.files.all()
    return render(request, 'parsing/city_service/file.html', {
        'city_service': city_service,
        'files': files
    })


@login_required()
def city_service_file_apply(request, pk):
    city_service_file = get_object_or_404(CityServiceFile, pk=pk)
    city_service = city_service_file.city_service
    city_service_file_apply_task.delay(pk)
    messages.success(request, 'Started place creation')
    return redirect(reverse('parsing:city_service_file', args=[city_service.pk]))


def city_service_place_detail(request, place_slug):
    if not has_group(request.user, 'SuperAdmin'):
        raise Http404('Page not found')
    place = get_object_or_404(Place, slug=place_slug)
    if place.is_redirect and not has_group(request.user, 'Redactor'):
        return redirect(place.redirect)
    reviews = get_place_reviews(request, place)
    return render(request, 'parsing/place/detail.html', {
        'place': place,
        'reviews': reviews['reviews'],
        'my_review': reviews['my_review']
    })

#
# class QueryAdd(APIView):
#     def get(self, request, format=None):
#         username = request.GET.get('username')
#         query_name = request.GET.get('query_name')
#         query_page = request.GET.get('query_page')
#
#         user = User.objects.filter(username=username).first()
#         if not user:
#             return Response({}, status=status.HTTP_400_BAD_REQUEST)
#         try:
#             query_page = int(query_page)
#         except:
#             query_page = 1
#         if query_page == 0:
#             query_page = None
#         query = Query(user=user, name=query_name, page=query_page, status='wait')
#         query.save()
#         query_id = query.id
#         slug = slugify(query_name + '-' + str(query_id))
#         query.slug = slug
#         query.save()
#         try:
#             print(query_name)
#             startParsing.delay(query_name=query_name, query_id=query_id, pages=query_page)
#         except Exception as e:
#             print(e.__class__.__name__)
#             query.status = 'error'
#             query.save()
#
#         return Response({"message": "Парсинг начат"}, status=status.HTTP_200_OK)
#
#
# class QueryUser(APIView):
#     def get(self, request, username, format=None):
#         user = User.objects.filter(username=username).first()
#         if not user:
#             return Response({}, status=status.HTTP_400_BAD_REQUEST)
#         queries = user.queries.all()
#         tags = Tag.objects.filter(queries__in=queries).distinct()
#         query_serializer_data = QuerySerializer(queries, many=True).data
#         tags_serializer_data = TagSerializer(tags, many=True).data
#         return Response({'queries': query_serializer_data, 'tags': tags_serializer_data}, status=status.HTTP_200_OK)
#
#
# class QueryPlaces(APIView):
#     def get(self, request, slug, format=None):
#         query = Query.objects.filter(slug=slug).first()
#         if not query:
#             return Response({}, status=status.HTTP_400_BAD_REQUEST)
#
#         places_letter = {
#
#         }
#         query = Query.objects.filter(slug=slug).first()
#         if not query:
#             return redirect('parsing:index')
#         places = get_sorted_places(query)
#         for i in places:
#             first_letter = i.name[0]
#             i = PlaceMinSerializer(i).data
#             if first_letter in places_letter:
#                 places_letter[first_letter]['places'].append(i)
#             else:
#                 places_letter[first_letter] = {
#                     'letter': first_letter,
#                     'places': [i]
#                 }
#         letters = list(places_letter.keys())
#         letters = sorted(letters)
#
#         serializer = PlaceSerializer(places, many=True)
#         places_data = serializer.data
#         query_serializer = QuerySerializer(query, many=False)
#         query_data = query_serializer.data
#         data = {
#             'places': places_data,
#             'letters': letters,
#             'places_letter': places_letter,
#             'query': query_data,
#         }
#         return Response(data, status.HTTP_200_OK)
#
#
# class QueryDetail(RetrieveAPIView):
#     model = Query
#     serializer_class = QuerySerializer
#     queryset = model.objects.all()
#     lookup_field = 'slug'
#
#
# @method_decorator(xframe_options_exempt, name='dispatch')
# class PlaceHTML(DetailView):
#     model = Place
#     queryset = model.objects.all()
#     slug_field = 'cid'
#     slug_url_kwarg = 'cid'
#     template_name = 'parsing/place/copy.html'
#
#     def get_context_data(self, **kwargs):
#         context = super().get_context_data(**kwargs)
#         context['server_name'] = SERVER_NAME
#         return context
#
#
# class PlaceDetail(APIView):
#     def get(self, request, slug, format=None):
#         place = Place.objects.filter(slug=slug).first()
#         if not place:
#             return Response({}, status=status.HTTP_400_BAD_REQUEST)
#
#         query_serializer_data = {}
#         query_place = place.queries.first()
#         if query_place:
#             query = query_place.query
#             query_serializer_data = QuerySerializer(query, many=False).data
#
#         serializer = PlaceSerializer(place)
#         serializer_data = serializer.data
#         serializer_data['query'] = query_serializer_data
#         return Response(serializer_data, status=status.HTTP_200_OK)
#
#     def post(self, request, slug, format=None):
#         place = Place.objects.filter(slug=slug).first()
#         if not place:
#             return Response({}, status=status.HTTP_400_BAD_REQUEST)
#         data = request.data
#         form = PlaceForm(data, instance=place)
#         if form.is_valid():
#             form.save()
#             return Response({'status': 'success'}, status=status.HTTP_200_OK)
#         return Response({'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)
#
#
# class QueryEdit(APIView):
#     def post(self, request, slug, format=None):
#         query = generics.get_object_or_404(Query, slug=slug)
#         print(request.POST)
#         form = QueryContentForm(request.POST, instance=query)
#         if form.is_valid():
#             form.save()
#             return Response({'status': 'success'}, status=status.HTTP_200_OK)
#         return Response({'status': 'error'}, status=status.HTTP_400_BAD_REQUEST)
#
#
# class TagList(ListAPIView):
#     model = Tag
#     serializer_class = TagSerializer
#     queryset = model.objects.all()
#
#
# class ReviewCreate(APIView):
#     def post(self, request, format=None):
#         post = request.POST
#         form = ReviewForm(post)
#         if form.is_valid():
#             review = form.save(commit=False)
#             review.dependent_user_id = post['user_id']
#             review.place = Place.objects.filter(slug=post['place_slug']).first()
#             review.dependent_site = post['site']
#             review.is_dependent = True
#             review.author_name = post['author_name']
#             review.save()
#             create_or_update_review_types(request.POST, review)
#             return Response({'message': 'success'}, status=status.HTTP_200_OK)
#
#         return Response({'message': 'error'}, status=status.HTTP_400_BAD_REQUEST)
#
#
# class ReviewDetail(RetrieveAPIView):
#     model = Review
#     serializer_class = ReviewSerializer
#     queryset = model.objects.all()
#
#
# class ReviewUpdateAPIView(APIView):
#     def post(self, request, pk, format=None):
#         review = generics.get_object_or_404(Review, pk=pk)
#         form = ReviewForm(request.data, instance=review)
#         if form.is_valid():
#             review = form.save(commit=False)
#             review.is_edit = True
#             review.save()
#             create_or_update_review_types(request.data, review)
#         else:
#             print(form.errors)
#
#
# class ReviewTypeList(ListAPIView):
#     model = ReviewType
#     serializer_class = ReviewTypeSerializer
#     queryset = model.objects.all()
#
#     def get_queryset(self):
#         if 'pk' in self.kwargs:
#             return self.queryset.filter(
#                 reviews__review_id=self.kwargs['pk']
#             ).distinct()
#         return self.queryset.all()
