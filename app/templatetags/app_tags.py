from django import template
from django.template.defaultfilters import safe

from constants import base_url, admin_username

register = template.Library()


@register.filter(name='getValue')
def getValue(dic, key):
    return dic[key]


# @register.filter(name='getRating')
# def getRating(rating):
#     stars = ''
#     rating = round(rating)
#     filled_star = '''<svg viewBox="0 0 40 40" class="full-star" fill="none" xmlns="http://www.w3.org/2000/svg"> <path d="M11.2466 35.1135C10.0601 35.7278 8.67346 34.7356 8.90005 33.4346L10.5718 23.8358L3.49016 17.038C2.53029 16.1166 3.05996 14.5113 4.38646 14.3214L14.1731 12.921L18.5498 4.18778C19.143 3.00406 20.857 3.00406 21.4502 4.18778L25.8269 12.921L35.6135 14.3214C36.94 14.5113 37.4697 16.1166 36.5098 17.038L29.4282 23.8358L31.0999 33.4346C31.3265 34.7356 29.9399 35.7278 28.7534 35.1135L20 30.5816L11.2466 35.1135Z" fill="#ffc24c"></path> </svg>'''
#     empty_star = '''<svg viewBox="0 0 40 40" class="full-star" fill="none" xmlns="http://www.w3.org/2000/svg"> <path d="M11.2466 35.1135C10.0601 35.7278 8.67346 34.7356 8.90005 33.4346L10.5718 23.8358L3.49016 17.038C2.53029 16.1166 3.05996 14.5113 4.38646 14.3214L14.1731 12.921L18.5498 4.18778C19.143 3.00406 20.857 3.00406 21.4502 4.18778L25.8269 12.921L35.6135 14.3214C36.94 14.5113 37.4697 16.1166 36.5098 17.038L29.4282 23.8358L31.0999 33.4346C31.3265 34.7356 29.9399 35.7278 28.7534 35.1135L20 30.5816L11.2466 35.1135Z" fill="#EAEAEA"></path> </svg>'''
#
#     for i in range(rating):
#         stars += filled_star
#     for i in range(5 - rating):
#         stars += empty_star
#     return '<div style="display: flex; height: 20px">' + stars + '</div>'


@register.filter(name="isValue")
def isValue(value, returned=' - '):
    if value:
        return value
    return returned


@register.filter(name="isSite")
def isSite(site):
    if not site or site == ' - ':
        return ' - '
    if site[:4] == 'http':
        return site
    else:
        return 'http://' + site


@register.filter(name="checkReview")
def checkReview(review, current_user_id):
    user_id = review['dependent_user_id']
    if str(current_user_id) == str(user_id) and admin_username == review['dependent_site']:
        return True
    return False


@register.filter(name="isReview")
def isReview(reviews, user):
    if user.is_authenticated and reviews.filter(user=user).exists:
        return False
    return True
