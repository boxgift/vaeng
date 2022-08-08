import math
import re

from django import template
import json

from django.db.models.functions import Length
from django.template.defaultfilters import safe

register = template.Library()

GROUPS = {'User': 1,
          'Redactor': 2,
          'Admin': 3,
          'SuperAdmin': 4}


@register.filter(name="getRating")
def getRating(rating):
    stars = ''
    rating = round(rating)
    # filled_star = '''<svg viewBox="0 0 40 40" class="full-star" fill="none" xmlns="http://www.w3.org/2000/svg"> <path d="M11.2466 35.1135C10.0601 35.7278 8.67346 34.7356 8.90005 33.4346L10.5718 23.8358L3.49016 17.038C2.53029 16.1166 3.05996 14.5113 4.38646 14.3214L14.1731 12.921L18.5498 4.18778C19.143 3.00406 20.857 3.00406 21.4502 4.18778L25.8269 12.921L35.6135 14.3214C36.94 14.5113 37.4697 16.1166 36.5098 17.038L29.4282 23.8358L31.0999 33.4346C31.3265 34.7356 29.9399 35.7278 28.7534 35.1135L20 30.5816L11.2466 35.1135Z" fill="#ffc24c"></path> </svg>'''
    # empty_star = '''<svg viewBox="0 0 40 40" class="full-star" fill="none" xmlns="http://www.w3.org/2000/svg"> <path d="M11.2466 35.1135C10.0601 35.7278 8.67346 34.7356 8.90005 33.4346L10.5718 23.8358L3.49016 17.038C2.53029 16.1166 3.05996 14.5113 4.38646 14.3214L14.1731 12.921L18.5498 4.18778C19.143 3.00406 20.857 3.00406 21.4502 4.18778L25.8269 12.921L35.6135 14.3214C36.94 14.5113 37.4697 16.1166 36.5098 17.038L29.4282 23.8358L31.0999 33.4346C31.3265 34.7356 29.9399 35.7278 28.7534 35.1135L20 30.5816L11.2466 35.1135Z" fill="#EAEAEA"></path> </svg>'''
    filled_star = '<img src="/static/parsing/img/filled_star.svg">'
    empty_star = '<img src="/static/parsing/img/empty_star.svg">'
    # filled_star = '''<svg viewBox="0 0 40 40" style="display: inline !important" class="full-star" xmlns="http://www.w3.org/2000/svg"> <path d="M11.2466 35.1135C10.0601 35.7278 8.67346 34.7356 8.90005 33.4346L10.5718 23.8358L3.49016 17.038C2.53029 16.1166 3.05996 14.5113 4.38646 14.3214L14.1731 12.921L18.5498 4.18778C19.143 3.00406 20.857 3.00406 21.4502 4.18778L25.8269 12.921L35.6135 14.3214C36.94 14.5113 37.4697 16.1166 36.5098 17.038L29.4282 23.8358L31.0999 33.4346C31.3265 34.7356 29.9399 35.7278 28.7534 35.1135L20 30.5816L11.2466 35.1135Z" fill="#FAA500"></path> </svg>'''
    # empty_star = '''<svg viewBox="0 0 40 40" style="display: inline !important" class="full-star" xmlns="http://www.w3.org/2000/svg"> <path d="M11.2466 35.1135C10.0601 35.7278 8.67346 34.7356 8.90005 33.4346L10.5718 23.8358L3.49016 17.038C2.53029 16.1166 3.05996 14.5113 4.38646 14.3214L14.1731 12.921L18.5498 4.18778C19.143 3.00406 20.857 3.00406 21.4502 4.18778L25.8269 12.921L35.6135 14.3214C36.94 14.5113 37.4697 16.1166 36.5098 17.038L29.4282 23.8358L31.0999 33.4346C31.3265 34.7356 29.9399 35.7278 28.7534 35.1135L20 30.5816L11.2466 35.1135Z" fill="#EAEAEA"></path> </svg>'''

    for i in range(rating):
        stars += filled_star
    for i in range(5 - rating):
        stars += empty_star
    # stars = '<div style="display: flex; height: 21px; font-size: 40px">' + stars + '</div>'
    return safe('<div style="height: 20px; display: flex">' + stars + '</div>')


@register.filter(name="hasGroup")
def hasGroup(user, group_name):
    if not user.is_authenticated:
        return False
    group = user.groups.first()
    if not group:
        return False
    current_index = GROUPS[group.name]
    recommended_index = GROUPS[group_name]
    if current_index < recommended_index:
        return False
    return True


@register.filter(name="toJson")
def toJson(data):
    return json.dumps(data)


@register.filter(name='getValue')
def getValue(dic, key):
    return dic[key]


@register.filter(name="toString")
def toString(variable):
    return str(variable)


@register.filter(name="isValue")
def isValue(value, returned=' - '):
    if value:
        return value
    return returned


@register.filter(name="getImg")
def getImg(img):
    if img:
        return img.url
    return '/static/parsing/img/not_found_place.png'


# @register.filter(name="getBaseImg")
# def getBaseImg(query):
#     if query:
#         places = query.places
#         try:
#             first_place = places.first().place.first()
#             if first_place.img:
#                 return first_place.img.url
#         except:
#             pass
#     return '/static/img/not_found_place.png'


@register.filter(name="getMetaText")
def getMetaText(meta):
    if meta == ' - ':
        return meta
    pattern = r'(?<=content=")(.+?)(?=")'
    meta = re.search(pattern, meta)
    if meta:
        return meta.group()
    return ' - '


@register.filter(name="getMoreText")
def getMoreText(queries):
    if queries:
        queries = queries.exclude(text=None).exclude(text='').annotate(text_len=Length('text')).order_by('-text_len')
        return queries.first()
    return ''


@register.filter(name="isSite")
def isSite(site):
    if not site or site == ' - ':
        return ' - '
    if site[:4] == 'http':
        return site
    else:
        return 'http://' + site


@register.filter(name="toRange")
def toRange(number):
    return range(1, number + 1)


@register.filter(name="numberToStars")
def numberToStars(number=5.0, star_count=5):
    stars = ''
    filled_star = '''<svg viewBox="0 0 40 40" class="full-star" xmlns="http://www.w3.org/2000/svg"> <path d="M11.2466 35.1135C10.0601 35.7278 8.67346 34.7356 8.90005 33.4346L10.5718 23.8358L3.49016 17.038C2.53029 16.1166 3.05996 14.5113 4.38646 14.3214L14.1731 12.921L18.5498 4.18778C19.143 3.00406 20.857 3.00406 21.4502 4.18778L25.8269 12.921L35.6135 14.3214C36.94 14.5113 37.4697 16.1166 36.5098 17.038L29.4282 23.8358L31.0999 33.4346C31.3265 34.7356 29.9399 35.7278 28.7534 35.1135L20 30.5816L11.2466 35.1135Z" fill="#FAA500"></path> </svg>'''
    empty_star = '''<svg viewBox="0 0 40 40" class="full-star" xmlns="http://www.w3.org/2000/svg"> <path d="M11.2466 35.1135C10.0601 35.7278 8.67346 34.7356 8.90005 33.4346L10.5718 23.8358L3.49016 17.038C2.53029 16.1166 3.05996 14.5113 4.38646 14.3214L14.1731 12.921L18.5498 4.18778C19.143 3.00406 20.857 3.00406 21.4502 4.18778L25.8269 12.921L35.6135 14.3214C36.94 14.5113 37.4697 16.1166 36.5098 17.038L29.4282 23.8358L31.0999 33.4346C31.3265 34.7356 29.9399 35.7278 28.7534 35.1135L20 30.5816L11.2466 35.1135Z" fill="#EAEAEA"></path> </svg>'''
    percent_star = '''<svg viewBox="0 0 40 40" class="percentage-star" xmlns="http://www.w3.org/2000/svg"> <defs> <linearGradient id="offset-70575"> <stop offset="0%" stop-color="#FAA500"></stop> <stop offset="{percent}%" stop-color="#FAA500"></stop> <stop offset="{percent}%" stop-color="#EAEAEA"></stop> <stop offset="100%" stop-color="#EAEAEA"></stop> </linearGradient> </defs> <path fill="url(#offset-70575)" fill-rule="evenodd" clip-rule="evenodd" d="M11.2466 35.1135C10.0601 35.7278 8.67346 34.7356 8.90005 33.4346L10.5718 23.8358L3.49016 17.038C2.53029 16.1166 3.05996 14.5113 4.38646 14.3214L14.1731 12.921L18.5498 4.18778C19.143 3.00406 20.857 3.00406 21.4502 4.18778L25.8269 12.921L35.6135 14.3214C36.94 14.5113 37.4697 16.1166 36.5098 17.038L29.4282 23.8358L31.0999 33.4346C31.3265 34.7356 29.9399 35.7278 28.7534 35.1135L20 30.5816L11.2466 35.1135Z"></path> </svg>'''
    number = float(number)
    filled_count = int(float(number))
    empty = star_count - filled_count
    percent = int(str(number)[-1])
    percent *= 10

    stars += filled_count * filled_star

    if percent:
        empty -= 1
        stars += percent_star.format(percent=percent)

    stars += empty * empty_star
    stars = f'<div style="display: flex; justify-content: center;">{stars}</div>'
    return safe(stars)
