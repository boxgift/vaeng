import base64
import csv
import json
import os
import io
from io import BytesIO
import random
from celery import shared_task
from django.contrib.auth.models import User, Group
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.files.temp import NamedTemporaryFile
from django.http import StreamingHttpResponse
from mimesis import Person
from mimesis.enums import Gender
from pytils.translit import slugify

from .models import Place, Query, QueryPlace, PlacePhoto, Review, ReviewType, ReviewPart, UniqueReview, City, \
    CityService, WordAiCookie, Service, CityServiceFile
from .utils import save_image, deEmojify
from .utils import city_service_create

from fake_useragent import UserAgent


@shared_task
def add_task(x, y):
    return x + y


from pip._vendor import requests
from selenium import webdriver
import csv
import time
from bs4 import BeautifulSoup as BS
from selenium.common.exceptions import ElementClickInterceptedException, StaleElementReferenceException, \
    NoSuchElementException, NoSuchAttributeException

from constants import CHROME_PATH, IS_LINUX
from datetime import datetime
import re
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

INDEX = 0
FILE_NAME = 'hotels.csv'  # Назавние файла для сохранения
# QUERY = 'lawn care New york'  # Запрос в поиске
QUERY = 'Клининги москве'  # Запрос в поиске
URL = f'https://www.google.com/search?q={QUERY}&newwindow=1&tbm=lcl&sxsrf=AOaemvJF91rSXoO-Kt8Dcs2gkt9_JXLlCQ%3A1632305149583&ei=_f9KYayPI-KExc8PlcaGqA4&oq={QUERY}&gs_l=psy-ab.3...5515.12119.0.12483.14.14.0.0.0.0.0.0..0.0....0...1c.1.64.psy-ab..14.0.0....0.zLZdDbmH5so#rlfi=hd:;'
CUSTOM_URL = 'https://www.google.com/search?q={0}&newwindow=1&tbm=lcl&sxsrf=AOaemvJF91rSXoO-Kt8Dcs2gkt9_JXLlCQ%3A1632305149583&ei=_f9KYayPI-KExc8PlcaGqA4&oq={0}&gs_l=psy-ab.3...5515.12119.0.12483.14.14.0.0.0.0.0.0..0.0....0...1c.1.64.psy-ab..14.0.0....0.zLZdDbmH5so#rlfi=hd:;'

PAGE = 100  # Количество страниц для парсинга

# KEY = 'AIzaSyAbOkxUWUw9z54up8AiMSCMX7rO7-8hqv8'
# KEY = '0'
# CID_API_URL = 'https://maps.googleapis.com/maps/api/place/details/json?cid={0}&key='+KEY
CID_URL = 'https://maps.google.com/?cid={0}'

display = None


# gmaps = googlemaps.Client(key=KEY)

def create_query_place(place, query):
    query_place = QueryPlace.objects.filter(query=query).first()
    if query_place:
        query_place.place.add(place)
    else:
        query_place = QueryPlace.objects.create(query=query)
        query_place.save()
        query_place.place.add(place)


def strToInt(string):
    value = ''
    for i in string:
        try:
            number = int(i)
            value += i
        except:
            pass
    return int(value)


def startFireFox(url=URL):
    driver = webdriver.Firefox()
    driver.get(url)
    return driver


def startChrome(url=URL, path=None):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-software-rasterizer")
    if path:
        driver = webdriver.Chrome(executable_path=path, options=chrome_options)
    else:
        driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)
    return driver


def create_place_for_file(data: dict, city_service: CityService):
    place = get_or_create_place(
        name=data.get('base_info').get('title'),
        rating=data.get('base_info').get('rating'),
        rating_user_count=data.get('base_info').get('rating_user_count'),
        cid=data.get('cid')
    )
    place.city_service = city_service
    set_info(data.get('full_info'), place)
    set_coordinate(data.get('coordinate'), place)
    set_photo_url(data.get('base_photo'), place.id, base=True)
    set_reviews(data.get('reviews'), place)
    set_photos(data.get('photos'), place.id)

    return place


@shared_task()
def city_service_file_apply_task(pk):
    try:
        city_service_file = CityServiceFile.objects.get(pk=pk)
        if not city_service_file or not city_service_file.file:
            return None

        data = json.load(city_service_file.file)
        places = data.get('places')
        for p in places:
            place = create_place_for_file(p, city_service_file.city_service)
    except Exception as e:
        print(e)
        return None


def clicked_object(object, count):
    i = 0
    while i < count:
        try:
            object.click()
            return True
        except ElementClickInterceptedException:
            i += 1
            time.sleep(1)
    return False


def is_find_object(parent_object, class_name):
    try:
        object = parent_object.find_element_by_class_name(class_name)
    except Exception as e:
        print('Ошибка при получении объекта в DOM: ', e.__class__.__name__)
        print(class_name)
        object = ''
    return object


def get_site(url, timeout=None):
    if timeout:
        r = requests.get(url, timeout=timeout)
    else:
        r = requests.get(url)
    if r.status_code == 200:
        return r.text
    return None


def get_soup(html):
    if html:
        return BS(html)
    return html


class GetPhotos:
    def __init__(self, driver):
        self.photo_list = []
        self.driver = driver

    def click_photo_button(self):
        try:
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'ofKBgf')))
            self.driver.execute_script(
                'let photo_buttons = document.getElementsByClassName("ofKBgf"); photo_buttons[0].click()'
                # 'let photo_button = document.getElementsByClassName("xtu1r-K9a4Re-ibnC6b-haAclf");photo_button[0].children[0].click()'
            )
        except Exception as e:
            print('Ошибка при нажатии на кнопку ВСЕ ФОТО: ', e.__class__.__name__)

    def finds_photo_elements(self):
        try:
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'cYB2Ge-ti6hGc')))
            photos_block = self.driver.find_element_by_class_name('cYB2Ge-ti6hGc')
            photos = photos_block.find_elements_by_class_name('mWq4Rd-eEDwDf')
            print(len(photos))
            return photos
        except Exception as e:
            print('Ошибка при получении объектов фотографии: ', e.__class__.__name__)
            return None

    def check_photo(self, photo):
        try:
            photo = photo.get_attribute('innerHTML')
            pattern = r'(?<=image: url\(&quot;)(.+?)(?=&quot;\))'
            photo_url = re.search(pattern, photo)
            url = photo_url.group()
            if url[:2] == '//':
                url = url[2:]
            print(url)
            url = url.split('=')
            url.pop()
            url = ''.join(url)
            if not url.startswith('http'):
                url = 'http://' + url
            print(url)
            self.photo_list.append(url)
        except Exception as e:
            print('Ошибка при детальной фотографии: ', e.__class__.__name__)

    def get_photos(self):
        try:
            self.click_photo_button()
            time.sleep(3)
            photos = self.finds_photo_elements()
            print(len(photos))
            if photos:
                photos = photos[:6]
            for photo in photos:
                self.check_photo(photo)
            print(self.photo_list)
            return self.photo_list
        except Exception as e:
            print('Ошибка при получении фотографии: ', e.__class__.__name__)
            pass


def set_photos(photos_list, place_id):
    place = Place.objects.filter(id=place_id).first()
    place.photos.all().delete()
    for photo_url in photos_list:
        set_photo_url(photo_url, place_id, base=False)


def get_place_information(driver):
    try:
        place_information = is_find_object(driver, 'uxOu9-sTGRBb-UmHwN')
        print(place_information.get_attribute('innerText'))
        return place_information.get_attribute('innerText')
    except Exception as e:
        print('Ошибка при получении описания места: ', e.__class__.__name__)
        return None


def get_location_information(driver):
    try:
        location_name = is_find_object(driver, 'exOO9c-V1ur5d')
        location_rating = is_find_object(driver, 'v10Rgb-v88uof-haAclf')
        location_text = is_find_object(driver, 'XgnsRd-HSrbLb-h3fvze-text')
        print(location_name.get_attribute('innerText'))
        print(location_rating.get_attribute('innerText'))
        print(location_text.get_attribute('innerText'))
    except Exception as e:
        print('Ошибка при получении информации о местности: ', e.__class__.__name__)
        return None


def get_photo(driver):
    try:
        wait = WebDriverWait(driver, 10)
        photo_class_1 = 'F8J9Nb-LfntMc-header-HiaYvf-LfntMc'
        photo_class_2 = 'aoRNLd'
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, f'{photo_class_2}')))
        photo = is_find_object(driver, f'{photo_class_2}')
        button = photo.find_element_by_tag_name('img')
        src = button.get_attribute('src')
        if len(src.split('=')) == 2:
            link = src.split('=')[0]
            print('Ссылка на главное фото: ', link)
        else:
            link = src
            print('Ссылка на главное фото: ', link)
        return link
    except Exception as e:
        print('Ошибка при получении главного фото: ', e.__class__.__name__)
        return None


def set_photo_url(img_url, place_id, base=True):
    ua = UserAgent()
    try:
        print('img url: ', img_url)
        print(Place.objects.filter(id=place_id).count())
        place = Place.objects.filter(id=place_id).first()
        if place and img_url:
            r = requests.get(img_url, timeout=10, headers={'User-Agent': ua.random})
            if r.status_code == 200:
                content = r.content
                cloud_image = save_image(content)
                if base:
                    print('cloud image')
                    print(place.cloud_img)
                    place.cloud_img = cloud_image
                    print(place.cloud_img)
                    place.save()
                    print(place.cloud_img)
                    print('---- -----')
                else:
                    photo = PlacePhoto(place=place)
                    photo.cloud_img = cloud_image
                    photo.save()
                return 'Фото назначено для {}'.format(place_id)
        return 'Фото не назначено {}'.format(place_id)
    except Exception as e:
        print(f'Ошиька при назначении фото: {img_url}', e.__class__.__name__)


def set_photo_content(content, place_id, file_name='no_name'):
    place = Place.objects.filter(id=place_id).first()
    if not place:
        return None
    place_photo = PlacePhoto()
    place_photo.img.save(os.path.basename(file_name), ContentFile(content))
    place_photo.place = place
    place_photo.save()


class GetReviews:
    def __init__(self, driver):
        self.review_list = []
        self.driver = driver

    def get_page_review_button(self):
        try:
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'Yr7JMd-pane-hSRGPd')))
            review_button = self.driver.find_element_by_class_name('Yr7JMd-pane-hSRGPd')
            clicked_object(review_button, 10)
        except Exception as e:
            print('Ошибка при получении кнопки по отзывам', e.__class__.__name__)

    def get_reviews_objects(self):
        try:
            review_card_class_1 = 'ODSEW-ShBeI'
            review_card_class_2 = 'jftiEf'
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, f'{review_card_class_2}')))
            reviews = self.driver.find_elements_by_class_name(f'{review_card_class_2}')
            print(len(reviews))
            time.sleep(1)
            return reviews
        except Exception as e:
            print('-- Ошибка при получении первых отзывов', e.__class__.__name__)

    def scrolled_driver(self):
        try:
            print(1)
            scroll_block_class_1 = 'DxyBCb'
            scroll_block_class_2 = 'siAUzd-neVct section-scrollbox cYB2Ge-oHo7ed cYB2Ge-ti6hGc'
            time.sleep(1)
            # wait = WebDriverWait(self.driver, 10)
            # wait.until(EC.presence_of_element_located((By.CLASS_NAME, f'{scroll_block_class_1}')))

            self.driver.execute_script(
                f'let q_12 = document.getElementsByClassName("{scroll_block_class_1}")[0];'
                f'q_12.scrollTo(0, q_12.scrollHeight);')
            time.sleep(1)
            print(2)
            self.driver.execute_script(
                f'let q_12 = document.getElementsByClassName("{scroll_block_class_1}")[0];'
                f'q_12.scrollTo(0, q_12.scrollHeight);')
            time.sleep(1)
            print(3)
            reviews = self.get_reviews_objects()
            print(4)
            print('Всего загружено: ', len(reviews))
            random_number = random.randint(10, 20)
            reviews = reviews[:random_number]
            print(len(reviews))
            return reviews
        except Exception as e:
            print('--- Ошибка при скролле по отзывам', e.__class__.__name__)

    def review_more_button_click(self, review):
        review_id = review.get_attribute('data-review-id')
        self.driver.execute_script(f'''
                                let review = document.querySelector("div[data-review-id={review_id}]");
                                let more = review.getElementsByClassName('w8nwRe gXqMYb-hSRGPd')[0].click();
                                ''')
        print('Review More Button Clicked')

    def get_review_text(self, review):
        try:
            try:
                self.review_more_button_click(review)
                time.sleep(1)
                print('Нашел кнопку ЕЩЕ')
            except Exception as e:
                print('Не нашел кноаку ЕЩЕ: ', e.__class__.__name__)
                pass
            review_text_class_1 = 'ODSEW-ShBeI-text'
            review_text_class_2 = 'wiI7pd'
            text = review.find_element_by_class_name(f'{review_text_class_2}').get_attribute('innerText')
        except Exception as e:
            text = ''
            print('Ошибка в отзыве: ', e.__class__.__name__)
        return text

    def get_review_rating(self, review):
        try:
            print(1)
            rating_class_1 = 'ODSEW-ShBeI-H1e3jb'
            rating_class_2 = 'kvMYJc'
            rating = review.find_element_by_class_name(f'{rating_class_2}')
            print(rating)
            available_rating = len(rating.find_elements_by_class_name('hCCjke'))
            print('Available: ', available_rating)
            checked_rating = len(rating.find_elements_by_class_name('vzX5Ic'))
            print('Checked: ', checked_rating)

            # rating = review.find_element_by_class_name('ODSEW-ShBeI-RGxYjb-wcwwM').get_attribute('innerText').split('/')
            # available_rating = int(rating[-1])
            # checked_rating = int(rating[0])

            if available_rating > 5:
                rating_coefficent = available_rating / 5
                checked_rating /= rating_coefficent
            rating = int(checked_rating)
        except:
            try:
                rating = len(review.find_elements_by_class_name('ODSEW-ShBeI-fI6EEc-active'))
            except Exception as e:
                print('Ошибка при получении звезд: ', e.__class__.__name__)
                rating = 1
        return rating

    def check_review(self, review):
        try:
            rating = self.get_review_rating(review)
            text = self.get_review_text(review)
            if text:
                self.review_list.append({
                    'rating': rating,
                    'text': text
                })
                return True
            return False
        except Exception as e:
            print('-- Ошибка при назначении атрибутов отзыву', e.__class__.__name__)
            time.sleep(1)
            return False

    def review_detail(self, review):
        try:
            exception = 0
            while exception < 3:
                checked = self.check_review(review)
                if checked:
                    break
                else:
                    exception += 1
        except Exception as e:
            print('Ошибка при получении детального отзыва', e.__class__.__name__)

    def close_review_pages(self):
        try:
            self.driver.execute_script(
                'let close_b = document.getElementsByClassName("VfPpkd-icon-Jh9lGc"); close_b[0].click()')
        except Exception as e:
            print('Ошибка при закрытии отзывов', e.__class__.__name__)

    def get_reviews(self):
        try:
            self.get_page_review_button()
            self.get_reviews_objects()
            reviews = self.scrolled_driver()
            for review in reviews:
                self.review_detail(review)
        except Exception as e:
            print('Ошибка при получении отзывов: ', e.__class__.__name__)
        self.close_review_pages()
        return self.review_list


def set_review_parts(rating, review, review_types=[]):
    for review_type in review_types:
        review_part = ReviewPart.objects.update_or_create(review=review, review_type=review_type)[0]
        review_part.rating = rating
        review_part.save()


class GenerateUser():
    def __init__(self):
        pass

    def random_color(self):
        import random
        color = "#%06x" % random.randint(0, 0xFFFFFE)
        return color

    def generate_avatar(self, name_letters):
        from PIL import Image, ImageFont, ImageDraw
        width = 320
        height = 320
        img = Image.new('RGB', (width, height), color=(self.random_color()))
        draw_text = ImageDraw.Draw(img)
        font = ImageFont.truetype('parsing/static/parsing/fonts/Raleway-Regular.ttf', size=120)
        draw_text.text((width / 2, height / 2), name_letters, anchor='mm', font=font, fill=('#ffffff'))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        return img_byte_arr

    def generate_data(self):
        person = Person('en')
        gender_choices = [Gender.FEMALE, Gender.MALE]
        random_gender = random.choice(gender_choices)
        email = person.email()

        full_name = person.full_name(gender=random_gender)
        username = full_name.replace(' ', '_')
        full_name = full_name.split(' ')
        first_name = full_name[0]
        last_name = full_name[-1]

        password = User.objects.make_random_password()

        user_data = {
            'username': username,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'gender': random_gender.name,
            'password': password
        }
        return user_data

    def get_user(self):
        user_data = self.generate_data()
        name_letters = f'{user_data["first_name"][0]}.{user_data["last_name"][0]}'
        user_img = self.generate_avatar(name_letters)
        user_data['img'] = user_img
        return user_data

    def get_or_create_user(self):
        user_data = self.get_user()
        user = User.objects.get_or_create(username=user_data['username'])
        if not user[1]:
            return user[0]
        user = user[0]
        user.email = user_data['email']
        user.first_name = user_data['first_name']
        user.last_name = user_data['last_name']
        user.password = user_data['password']
        user.save()
        group = Group.objects.filter(name='User').first()
        if group:
            user.groups.add(group)
        user.profile.gender = user_data['gender']
        cloud_image = save_image(user_data['img'])
        user.profile.cloud_img = cloud_image
        user.save()
        return user


def set_reviews(review_list, place):
    if len(review_list) == 0:
        return None
    try:
        place.reviews.all().delete()
        for review in review_list:
            user = GenerateUser().get_or_create_user()
            translate_word_1 = '(Translated by Google)'
            translate_word_2 = '(Original)'
            if translate_word_1 in review['text'] and translate_word_2 in review['text']:
                text = review['text'][len(translate_word_1) + 1:review['text'].find(translate_word_2) - 1]
            else:
                text = review['text']
            review = Review.objects.create(user=user,
                                           rating=review['rating'],
                                           text=text,
                                           original_text=text,
                                           place=place)
            review.save()
            try:
                set_review_parts(rating=review.rating, review=review,
                                 review_types=place.city_service.review_types.all())
            except Exception as e:
                print('Ошибка при назначении кусков отзыва', e)
    except Exception as e:
        print('Ошибка при назначении отзывов: ', e.__class__.__name__, e)


def get_or_create_place(name, rating, rating_user_count, cid):
    try:
        place = Place.objects.filter(cid=cid).first()
        if place:
            place.name = name
            place.rating = rating
            place.rating_user_count = rating_user_count
            place.save()
            return place
        place = Place.objects.create(name=name,
                                     rating=rating,
                                     rating_user_count=rating_user_count,
                                     cid=cid)
        place.save()
        place.slug = slugify(f'{place.name}-{str(place.id)}')
        place.save()
        return place
    except Exception as e:
        print('Ошибка при создании или взятии palce')
        print(e.__class__.__name__)


def get_info(driver):
    data = {}
    data_names = {
        'https://www.gstatic.com/images/icons/material/system_gm/1x/place_gm_blue_24dp.png': 'address',
        'https://www.gstatic.com/images/icons/material/system_gm/2x/place_gm_blue_24dp.png': 'address',
        'https://www.gstatic.com/images/icons/material/system_gm/1x/phone_gm_blue_24dp.png': 'phone_number',
        'https://www.gstatic.com/images/icons/material/system_gm/2x/phone_gm_blue_24dp.png': 'phone_number',
        # 'https://www.gstatic.com/images/icons/material/system_gm/1x/schedule_gm_blue_24dp.png': 'timetable',
        # 'https://www.gstatic.com/images/icons/material/system_gm/2x/schedule_gm_blue_24dp.png': 'timetable',
        'https://www.google.com/images/cleardot.gif': 'location',
        'https://www.gstatic.com/images/icons/material/system_gm/1x/public_gm_blue_24dp.png': 'site',
        'https://www.gstatic.com/images/icons/material/system_gm/2x/public_gm_blue_24dp.png': 'site',
        'https://maps.gstatic.com/mapfiles/maps_lite/images/1x/ic_plus_code.png': 'plus_code',
        'https://maps.gstatic.com/mapfiles/maps_lite/images/2x/ic_plus_code.png': 'plus_code',
        'https://gstatic.com/local/placeinfo/schedule_ic_24dp_blue600.png': 'schedule',
    }
    try:
        timetable = driver.find_element_by_class_name('y0skZc-jyrRxf-Tydcue')
        timetable = timetable.get_attribute('innerHTML')
    except Exception as e:
        timetable = ''
        print('Ошибка при взятии расписания: ', e.__class__.__name__)
    data['timetable'] = timetable
    try:
        data_objects = driver.find_elements_by_class_name('AeaXub')
        for i in data_objects:
            image_src = i.find_element_by_tag_name('img').get_attribute('src')
            try:
                image_type = data_names[image_src]
                print(image_type)
                data[image_type] = i.get_attribute('innerText')
                print(i.get_attribute('innerText'))
            except KeyError:
                pass
        return data
    except Exception as e:
        print('Ошибка при получении общих данных: ', e.__class__.__name__)
        return None


@shared_task()
def get_site_description(url, place_id):
    if not url or url == ' - ':
        return None
    url = 'http://' + url
    meta_data = ''
    try:
        html = get_site(url, timeout=15)
    except:
        return f'Не взял Description {0}'.format(place_id)
    if not html:
        return html
    soup = BS(html, 'lxml')
    meta = soup.find('meta', attrs={'name': 'description'})
    if meta:
        meta_data = str(meta)
    place = Place.objects.filter(id=place_id).first()
    # print(url)
    # print(meta_data)
    if place:
        place.meta = meta_data
        place.save()
    return url


def set_info(data, place):
    if not data:
        return None
    if 'site' in data:
        place_id = place.id
        get_site_description.delay(url=data['site'], place_id=place_id)
    place.address = data['address'] if 'address' in data else None
    place.phone_number = data['phone_number'] if 'phone_number' in data else None
    place.site = data['site'] if 'site' in data else None
    place.timetable = data['timetable'] if 'timetable' in data else None
    place.archive = False if place.city_service.city.name in str(place.address) else True

    place.save()


def get_coordinate(driver):
    try:
        time.sleep(1)
        print(1)
        # Это надо удалить
        # driver.execute_script('''
        #         let share_buttons = document.getElementsByClassName('etWJQ etWJQ-text csAe4e-y1XlWb-QBLLGd vqxL8-haDnnc');
        #         let share_button = share_buttons[share_buttons.length-1];
        #         share_button.children[0].click();
        # ''')
        driver.execute_script('''
                let share_buttons = document.getElementsByClassName('etWJQ jym1ob kdfrQc');
                let share_button = share_buttons[share_buttons.length-1];
                share_button.children[0].click();
        ''')
        print(2)
        time.sleep(1)
        wait = WebDriverWait(driver, 10)
        get_coordinate_class_1 = 's4ghve-AznF2e-ZMv3u-AznF2e'
        get_coordinate_class_2 = 'zaxyGe'
        wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, f'{get_coordinate_class_2}')))
        driver.execute_script(
            f'''
                let card_button = document.getElementsByClassName('{get_coordinate_class_2}')[1];
                card_button.click();
            '''
        )
        print(3)
        wait2 = WebDriverWait(driver, 10)

        # wait2.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'GALvsc-e1YmVc-map-YPqjbf')))
        # input_coordinate = driver.find_element_by_class_name('GALvsc-e1YmVc-map-YPqjbf')

        wait2.until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'm5XrEc')))
        input_coordinate = driver.find_element_by_class_name('m5XrEc').find_element_by_tag_name('input')
        coordinate = input_coordinate.get_attribute('value')

        print(4)
        driver.execute_script('''
                let coordinate_close_button = document.getElementsByClassName('AmPKde KzWhlc')[0];
                coordinate_close_button.click();
        ''')
        return coordinate
    except Exception as e:
        print('Ошибка при взятии', e.__class__.__name__)
        return None


def set_coordinate(data, place):
    if data:
        place.coordinate_html = data
        place.save()


def place_create(driver, title, rating, rating_user_count, cid, city_service):
    place = get_or_create_place(title, rating, rating_user_count, cid)
    place.city_service = city_service
    place.save()
    data = get_info(driver)
    print(data)
    set_info(data, place)

    print(' --------- Беру координаты ')
    coordinate = get_coordinate(driver)
    set_coordinate(coordinate, place)

    print(' --------- Главное фото: ')
    base_photo = get_photo(driver)
    set_photo_url(base_photo, place.id, base=True)

    print(' --------- Отзывы: ')
    reviews = []
    # reviews = get_this_page_reviews(driver)
    if rating_user_count > 0:
        print('Отзывы со страницы отзывов')
        reviews = GetReviews(driver).get_reviews()
    print('Отзывы готовы', reviews)
    set_reviews(reviews, place)

    print(' --------- Фотографии')
    photos = GetPhotos(driver).get_photos()  # class PlacePhoto
    set_photos(photos, place.id)
    print(photos)

    print(title)
    print('Закрыто')
    print('----------------')


def place_create_driver(cid, city_service_id):
    url = CID_URL.format(cid)
    try:
        if IS_LINUX:
            driver = startChrome(url=url, path=CHROME_PATH)
        else:
            driver = startFireFox(url=url)
    except Exception as e:
        time.sleep(1)
        print('Не удалось открыть детальную страницу в боаузере: ', e.__class__.__name__)
        place_create_driver(cid, city_service_id)
        return None
    try:
        try:
            title_class_1 = 'x3AX1-LfntMc-header-title-title'
            title_class_2 = 'DUwDvf'
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, f'{title_class_2}')))
            title = is_find_object(driver, f'{title_class_2}').get_attribute('innerText')
        except:
            title = 'No Name'
        try:
            rating = is_find_object(driver, 'aMPvhf-fI6EEc-KVuj8d').get_attribute('innerText')
            rating = float(rating.replace(',', '.'))
        except:
            rating = 0
        print(rating)
        try:
            rating_user_count = is_find_object(driver, 'Yr7JMd-pane-hSRGPd').get_attribute('innerText')
            rating_user_count = strToInt(rating_user_count)
        except:
            rating_user_count = 0
        print(rating_user_count)

        city_service = CityService.objects.filter(id=city_service_id).first()
        place_create(driver, title, rating, rating_user_count, cid, city_service)
        driver.close()
    except Exception as e:
        print(e.__class__.__name__)
        print('Ошибка')
        driver.close()


def get_value_or_none(data, key, default_value=' - '):
    if key in data:
        return data[key]
    return default_value


# Функция которая парсит объекты на странице
def parse_places(driver, city_service_id):
    time.sleep(3)
    try:
        places = driver.find_elements_by_class_name('uMdZh')
    except Exception as e:
        print(e, e.__class__.__name__)
        return False
    print(len(places))
    if len(places) == 0:
        return False
    for place in places:
        cid = place.find_element_by_class_name('C8TUKc').get_attribute('data-cid') if place.find_element_by_class_name(
            'C8TUKc') else None
        print('https://www.google.com/maps?cid=' + cid)
        place_create_driver(cid, city_service_id) if cid else None
    return True


# Функция для смены страниц
def get_pagination(driver, page):
    try:
        pagination = is_find_object(driver, 'AaVjTc')
        available_pages = pagination.find_elements_by_tag_name('td')
        for i in available_pages:
            if str(page) == i.text and page != 1:
                i.click()
                # После клика нужно ждать
                # чтобы не ставить на долгое зкште(шьп), использовал цикл, который при
                # изменении текущей страницы на следующую запустить парсинг страницы
                for j in range(20):
                    try:
                        pagination = driver.find_element_by_class_name('AaVjTc')
                        current_page = pagination.find_element_by_class_name('YyVfkd')
                        if current_page.text == str(page):
                            return True
                    except Exception as e:
                        print('Ошибка в пагинации1: ', e.__class__.__name__)
                        # return False
                    time.sleep(1)
                time.sleep(1)
                break
        return False
    except Exception as e:
        print('Ошибка в пагинации2: ', e.__class__.__name__)
        return False


@shared_task
def startParsing(query_name, city_service_id, pages=None):
    display = None
    print(CUSTOM_URL.format(query_name))
    if IS_LINUX:
        from pyvirtualdisplay import Display
        display = Display(visible=False, size=(800, 600))
        display.start()
        driver = startChrome(url=CUSTOM_URL.format(query_name), path=CHROME_PATH)
        # print(driver.get_cookies())
    else:
        driver = startFireFox(url=CUSTOM_URL.format(query_name))

    city_service = CityService.objects.filter(id=city_service_id).first()
    try:
        if pages:
            for page in range(1, pages + 1):
                # Проверяю сколько доступных страниц для клика, и если следующая страница есть в пагинации то происходит клик
                if page == 1:
                    print(f'СТРАНИЦА {page} начата')
                    if not parse_places(driver, city_service_id):
                        break
                    print(f'{page} страница готова')
                    print('-----------------------------------')
                elif get_pagination(driver, page):
                    print(f'СТРАНИЦА {page} начата')
                    parse = parse_places(driver, city_service_id)
                    if not parse:
                        print('Возможно список не появился на этой странице')
                        break
                    print(f'{page} страница готова')
                    print('-----------------------------------')
            city_service.status = 'success'
            city_service.save()
            print('Парсинг завершен')
            driver.close()
        else:
            page = 1
            while True:
                if page == 1:
                    print(f'СТРАНИЦА {page} начата')
                    if not parse_places(driver, city_service_id):
                        break
                    print(f'{page} страница готова')
                    print('-----------------------------------')
                elif get_pagination(driver, page):
                    print(f'СТРАНИЦА {page} начата')
                    parse = parse_places(driver, city_service_id)
                    if not parse:
                        print('Возможно список не появился на этой странице')
                        break
                    print(f'{page} страница готова')
                    print('-----------------------------------')
                else:
                    break
                page += 1
            city_service.status = 'success'
            city_service.save()
            print('Парсинг завершен')
            driver.close()
    except Exception as e:
        city_service.status = 'error'
        print(e.__class__.__name__)
        if display:
            display.stop()

        driver.close()
        print('Критическая ошибка')


#
#                                        Все что ниже нужно для генерации CSV файла
#
def get_headers():
    return {
        'cid': 'cid',
        'name': 'name',
        'address': 'address',
        'rating': 'rating',
    }


def get_data(place):
    return {
        'cid': place.cid,
        'name': place.name,
        'address': place.address,
        'rating': place.rating,
    }


class Echo(object):
    def write(self, value):
        return value


def iter_items(items, pseudo_buffer):
    writer = csv.DictWriter(pseudo_buffer, fieldnames=get_headers())
    yield writer.writerow(get_headers())

    for item in items:
        yield writer.writerow(get_data(item))


def get_response(queryset):
    response = StreamingHttpResponse(
        streaming_content=(iter_items(queryset, Echo())),
        content_type='text/csv',
    )
    response['Content-Disposition'] = 'attachment;filename=items.csv'
    return response


def generate_file(file_name, places):
    response = StreamingHttpResponse(
        streaming_content=(iter_items(places, Echo())),
        content_type='text/csv',
    )
    response['Content-Disposition'] = f'attachment;filename={file_name}.csv'
    return response


#
#               WordAI
#


WORDAI_URL = 'https://wai.wordai.com'
REWRITE_URL = 'https://wai.wordai.com/rewrite'
EMAIL = 'gtmus505@gmail.com'
PASSWORD = 'EA5ipChxbdPwA2$'
DEFAULT_COOKIES = [
    {'domain': '.wordai.com', 'expiry': 1709497294, 'httpOnly': False, 'name': '_ga_J6KTZN2VVY', 'path': '/',
     'secure': False, 'value': 'GS1.1.1646425289.1.1.1646425294.0'},
    {'domain': '.wordai.com', 'expiry': 1804105293, 'httpOnly': False, 'name': 'km_ni', 'path': '/',
     'secure': False, 'value': 'gtmus505%40gmail.com'},
    {'domain': '.wordai.com', 'expiry': 1804105293, 'httpOnly': False, 'name': 'km_lv', 'path': '/',
     'secure': False, 'value': '1646425294'},
    {'domain': '.wordai.com', 'httpOnly': False, 'name': 'kvcd', 'path': '/', 'secure': False,
     'value': '1646425293936'},
    {'domain': 'wai.wordai.com', 'httpOnly': True, 'name': '_wordai_rails_session', 'path': '/', 'secure': False,
     'value': 'bO4n61%2FlS3fXRCsg8B7zF3HCXYxzyJbkWknSFU47V9n9qiLftHGPBVYfUwHBz2K97c%2FHW2E%2FpDenclPL1C21SbHBQfP6PJ1TzyJvppRNBlKqn4eJ5JQvYqpdPnVh7vrpbJ4MJnOyT25vOc%2Fr9lJuFrXa%2FoLB6Ft8TaoAjfaQIlKYLZmRvwe8C7cJ8F6CAJlwgcyqB2IZwafx5VqS8eLsNeC96YETwQnHgWp5hO7Y1KxkMElY56Tf2ROfhcTiGlMdTdtE2yGA1qTAAmlK3WkKk198T60iDcuxhlqPj06StHGx4beNZz0SW84J5Mu9Av6OS57FTg1iSn7egvlGE12FO44kBsui9TEl28B35Dg07FvVXoegeSNXiGHJYoJqOoNvlOZ6aTItnO3PFMV3a1LdNXxZ9P70--WIgi7vqXhl2ow94y--e4o9Q7x4Z0qo2Bosz006Vw%3D%3D'},
    {'domain': '.wordai.com', 'expiry': 1646427093, 'httpOnly': False, 'name': 'km_vs', 'path': '/',
     'secure': False, 'value': '1'},
    {'domain': '.wordai.com', 'expiry': 1804105290, 'httpOnly': False, 'name': 'km_ai', 'path': '/',
     'secure': False, 'value': 'Uk6BujRMj82wPhvS3miITW4BhCw%3D'},
    {'domain': '.wordai.com', 'expiry': 1709497294, 'httpOnly': False, 'name': '_ga', 'path': '/',
     'secure': False, 'value': 'GA1.1.774710283.1646425290'}]


def login(driver: webdriver.Chrome):
    form = driver.find_element('id', 'new_user')
    username_input = form.find_element('id', 'user_email')
    password_input = form.find_element('id', 'user_password')
    username_input.send_keys(EMAIL)
    password_input.send_keys(PASSWORD)
    password_input.submit()


def save_cookies(cookies):
    word_ai_cookie = WordAiCookie.objects.create(cookies=json.dumps(cookies))
    word_ai_cookie.save()


def set_cookies(driver) -> webdriver.Chrome:
    word_ai_cookie = WordAiCookie.objects.last()
    COOKIES = json.loads(word_ai_cookie.cookies) if word_ai_cookie else None
    if COOKIES:
        for cookie in COOKIES:
            driver.add_cookie(cookie)
        driver.get(WORDAI_URL + '/rewrite')
        driver.get(WORDAI_URL + '/rewrite')
    return driver


@shared_task()
def word_ai(reviews, unique_review=None):
    driver = startChrome(url=WORDAI_URL, path=CHROME_PATH)
    driver = set_cookies(driver)
    if driver.current_url != REWRITE_URL:
        login(driver)
        cookies = driver.get_cookies()
        save_cookies(cookies)
        driver.get(WORDAI_URL + '/rewrite')
    for review in reviews:
        try:
            rewrite_input_block = driver.find_element('id', 'input_editor_wrapper')
            input_block = rewrite_input_block.find_element('class name', 'fr-element')
            input_block.click()
            input_block.send_keys(deEmojify(review.text))

            button = driver.find_element('id', 'rephrase_submit')
            button.click()

            try:
                wait = WebDriverWait(driver, 30)
                wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'enable-highlight')))
            except Exception as e:
                print(e.__class__.__name__)

            rewrite_output_block = driver.find_element('id', 'output_editor_wrapper')
            output_block = rewrite_output_block.find_element('class name', 'fr-element')
            output_text = output_block.text

            review.text = output_text
            review.save()

            if unique_review:
                unique_review.reviews_checked += 1
                unique_review.save()
            print(output_text)
            driver.get(driver.current_url)
        except:
            continue
    driver.close()


#
#                                           Uniqueize reviews
#
def uniqueize_place_reviews_task(place):
    reviews = place.reviews.all()
    word_ai(reviews)


@shared_task()
def uniqueize_review(review_id):
    review = Review.objects.filter(id=review_id).first()
    word_ai([review])


@shared_task()
def preview_uniqueize_reviews_task(review_ids, unique_review_id):
    reviews = Review.objects.filter(id__in=review_ids)
    unique_review = UniqueReview.objects.get(id=unique_review_id)
    uniqueize_reviews_task(reviews, unique_review)


@shared_task
def uniqueize_reviews_task(reviews, unique_review):
    word_ai(reviews, unique_review)
    unique_review.date_end = datetime.now()
    unique_review.save()


@shared_task
def uniqueize_text_task(city_service_id=None, place_id=None):
    if place_id:
        place = Place.objects.filter(id=place_id).first()
        reviews = place.reviews.all().order_by('-pk')
        unique_review = UniqueReview(reviews_count=reviews.count(), place=place)
    else:
        city_service = CityService.objects.filter(id=city_service_id).first()
        reviews = Review.objects.filter(place__city_service=city_service).order_by('-pk')
        if not reviews:
            return None
        unique_review = UniqueReview(reviews_count=reviews.count(), city_service=city_service)
    unique_review.save()
    uniqueize_reviews_task(reviews, unique_review)

    #
    #                               Загрузка картинок для городов
    #


base_url = 'https://en.wikipedia.org'
cities_url = '/wiki/List_of_cities_and_counties_in_Virginia'


def get_tr_data(tr):
    city = tr.find('th').find('a')
    if city:
        city_name = city.text.replace('City County', '').replace('County', '').rstrip()
        city_link = city.get('href')
        return {
            'name': city_name,
            'link': city_link,
        }
    return None


def get_table_data(table):
    tbody = table.find('tbody')
    trs = tbody.find_all('tr')
    cities = []
    for tr in trs:
        city_data = get_tr_data(tr)
        cities.append(city_data) if city_data else ''
    return cities


def get_city_data(link):
    url = base_url + link
    soup = get_soup(get_site(url))

    # get_img
    infobox = soup.find(class_='infobox')
    img = infobox.find('img')
    img_link = img['src']

    # get_description
    body = soup.find("div", {"id": "mw-content-text"}).find(class_='mw-parser-output')
    description = body.find_all('p')[1]

    # get_coordinate
    try:
        latitude = float(soup.find(class_='latitude').text.split('′')[0].replace('°', '.'))
        longitude = float(soup.find(class_='longitude').text.split('′')[0].replace('°', '.'))
    except:
        latitude = None
        longitude = None
        print(link)
    return {
        'img_link': img_link,
        'description': description.text,
        'coordinate': {
            'latitude': latitude,
            'longitude': longitude
        }
    }


@shared_task()
def cities_img_parser():
    soup = get_soup(get_site(base_url + cities_url))
    tables = soup.find_all(class_='wikitable')
    data = []
    for table in tables:
        data += get_table_data(table)
    for city in data:
        city_object = City.objects.filter(name=city['name']).first()
        if city_object and (not city_object.cloud_img or not city_object.description or
                            (not city_object.latitude or city_object.longitude)):
            city_data = get_city_data(city['link'])
            description = city_data.get('description')
            img_link = 'https:' + city_data.get('img_link')
            latitude = city_data['coordinate']['latitude']
            longitude = city_data['coordinate']['longitude']
            if latitude and longitude:
                coordinate = {
                    'latitude': latitude,
                    'longitude': longitude
                }
            else:
                coordinate = None
            city_item = {
                'name': city['name'],
                'link': city['link'],
                'img_link': img_link,
                'description': description,
                'coordinate': coordinate
            }
            set_city_data(city_item)


def set_city_data(city_item):
    print(city_item['name'])
    city = City.objects.filter(name=city_item['name']).first()
    if city:
        if not city.cloud_img:
            time.sleep(5)
            r = requests.get(city_item['img_link'], headers={'User-Agent': 'Mozilla/5.0'})
            print("Img Status: " + str(r.status_code))
            if r.status_code == 200:
                city.cloud_img = save_image(r.content)
        if not city.description:
            city.description = city_item['description']
            print('Description')
        if (not city.longitude or not city.latitude) and city_item['coordinate']:
            city.longitude = city_item['coordinate']['longitude']
            city.latitude = city_item['coordinate']['latitude']
            print('Coordinate')
        city.save()


@shared_task()
def service_autocreate_task():
    if Service.objects.count() > 600:
        return None
    service_list = [{'name': 'Above Ground Pool Repair'}, {'name': 'Air Conditioning Installation'},
                    {'name': 'Air Conditioning Repair'}, {'name': 'Air Duct Cleaning'}, {'name': 'Alarm Companies'},
                    {'name': 'Ant Exterminators'}, {'name': 'Apartment Cleaners'},
                    {'name': 'Appliance Repair Companies'}, {'name': 'Architects'},
                    {'name': 'Asbestos Removal Contractors'}, {'name': 'Asphalt Contractors'},
                    {'name': 'Asphalt Patching'}, {'name': 'Asphalt Resurfacing Companies'},
                    {'name': 'Asphalt Sealing'}, {'name': 'Attic Fan Installation'},
                    {'name': 'Attic Insulation Companies'}, {'name': 'Awning Companies'},
                    {'name': 'Backyard Design Companies'}, {'name': 'Backyard Landscapers'}, {'name': 'Barn Repair'},
                    {'name': 'Basement Finishing'}, {'name': 'Basement Leak Repair'}, {'name': 'Basement Remodeling'},
                    {'name': 'Basement Waterproofing'}, {'name': 'Bathroom Design Companies'},
                    {'name': 'Bathtub Refinishing'}, {'name': 'Bathtub Repair Companies'},
                    {'name': 'Bathtub Replacement'}, {'name': 'Bed Bug Control'}, {'name': 'Black Mold Inspection'},
                    {'name': 'Blacktop Companies'}, {'name': 'Blind Installation'}, {'name': 'Block Wall Companies'},
                    {'name': 'Blown-In Insulation'}, {'name': 'Boiler Repair'}, {'name': 'Brick Paver Companies'},
                    {'name': 'Building Contractors'}, {'name': 'Cabinet Installers'}, {'name': 'Cabinet Makers'},
                    {'name': 'Cabinet Painting'}, {'name': 'Cabinet Repair'}, {'name': 'Carpet Cleaning Companies'},
                    {'name': 'Carport Installation'}, {'name': 'Ceiling Painters'},
                    {'name': 'Ceiling Repair Companies'}, {'name': 'Ceiling Tile Installation'},
                    {'name': 'Cement Companies'}, {'name': 'Central Vacuum Repair'}, {'name': 'Ceramic Tile Repair'},
                    {'name': 'Chimney Cleaning'}, {'name': 'Chimney Repair'}, {'name': 'Christmas Lights Installers'},
                    {'name': 'Cleaning Crews'}, {'name': 'Cockroach Control'}, {'name': 'Commercial Door Repair'},
                    {'name': 'Commercial Electricians'}, {'name': 'Commercial Floor Cleaning'},
                    {'name': 'Commercial Landscaping'}, {'name': 'Commercial Locksmiths'},
                    {'name': 'Commercial Pavers'}, {'name': 'Business Roof Repair'}, {'name': 'Commercial Roofing'},
                    {'name': 'Commercial Snow Removal'}, {'name': 'Commercial Window Companies'},
                    {'name': 'Commercial Window Tinting'}, {'name': 'Computer Network Installation'},
                    {'name': 'Computer Network Repair'}, {'name': 'Computer Repair Services'},
                    {'name': 'Concrete Cutting'}, {'name': 'Concrete Delivery Companies'},
                    {'name': 'Concrete Demolition'}, {'name': 'Concrete Removal'},
                    {'name': 'Concrete Driveway Companies'}, {'name': 'Concrete Finishing'},
                    {'name': 'Concrete Floor Staining'}, {'name': 'Concrete Foundation Companies'},
                    {'name': 'Concrete Masons'}, {'name': 'Concrete Patio Contractors'}, {'name': 'Stamped Concrete'},
                    {'name': 'Copper Gutters'}, {'name': 'Corian Countertops'}, {'name': 'Couch Cleaning'},
                    {'name': 'Couch Repair Services'}, {'name': 'Countertop Installation'},
                    {'name': 'Countertop Resurfacing Companies'}, {'name': 'Crawl Space Encapsulation'},
                    {'name': 'Curtain & Drapery Repair'}, {'name': 'Custom Builders'}, {'name': 'Custom Woodworking'},
                    {'name': 'Deck Companies'}, {'name': 'Deck Cleaning Services'}, {'name': 'Deck Painters'},
                    {'name': 'Deck Refinishing Services'}, {'name': 'Deck Repair Companies'},
                    {'name': 'Deck Staining Companies'}, {'name': 'Demolition Services'}, {'name': 'Dishwasher Repair'},
                    {'name': 'Dock Builders'}, {'name': 'Door Installation'}, {'name': 'Door Refinishing'},
                    {'name': 'Door Repair'}, {'name': 'Drain Cleaning'}, {'name': 'Drain Contractors'},
                    {'name': 'Drapery Cleaning'}, {'name': 'Driveway Paving Companies'}, {'name': 'Driveway Repair'},
                    {'name': 'Driveway Sealing'}, {'name': 'Dryer Repair'}, {'name': 'Dryer Vent Cleaning'},
                    {'name': 'Dryvit Contractors Near Me'}, {'name': 'Drywall Installers'},
                    {'name': 'Drywall & Insulation Contractors'}, {'name': 'Drywall Repair'},
                    {'name': 'Dumpster Rental'}, {'name': 'Earth Moving Companies'}, {'name': 'EIFS Contractors'},
                    {'name': 'Electric Inspectors'}, {'name': 'Electric Repair'},
                    {'name': 'Electric Water Heater Repair Companies'}, {'name': 'Electrical Construction'},
                    {'name': 'Electrical Handymen'}, {'name': 'Electricians'}, {'name': 'Electrolux Appliance Repair'},
                    {'name': 'Electrolux Washer Repair'}, {'name': '24 Hour Animal Control Services'},
                    {'name': 'Emergency Appliance Repair Companies'}, {'name': 'Emergency Carpet Cleaners'},
                    {'name': 'Emergency Cleaning Services'}, {'name': 'Emergency Electricians'},
                    {'name': 'Emergency Garage Door Repair'}, {'name': 'Emergency Handymen'},
                    {'name': 'Same Day House Cleaning'}, {'name': 'Emergency Locksmiths'},
                    {'name': '24 Hour Pest Control Services'}, {'name': 'Emergency Plumbers'},
                    {'name': 'Emergency Roofing Companies'}, {'name': 'Excavation Contractors'},
                    {'name': 'Exhaust Fan Installation'}, {'name': 'Exterior Painting'},
                    {'name': 'Pest Control Services'}, {'name': 'Farmhouse Builders'}, {'name': 'Fence Installers'},
                    {'name': 'Fence & Gate Repair'}, {'name': 'Fence Repair Companies'}, {'name': 'Feng Shui Experts'},
                    {'name': 'Fiber Cement Siding'}, {'name': 'Fiberglass Pools'},
                    {'name': 'Fire Sprinkler Contractors'}, {'name': 'Fireplace Cleaners'},
                    {'name': 'Fireplace Inspection'}, {'name': 'Fireplace Remodeling'}, {'name': 'Fireplace Repair'},
                    {'name': 'Flat Roofing Companies'}, {'name': 'Flea Control'}, {'name': 'Floor Painters'},
                    {'name': 'Flooring Repair'}, {'name': 'Floor Sanding'}, {'name': 'Floor Waxing'},
                    {'name': 'Floor Installers'}, {'name': 'Foundation Installation'},
                    {'name': 'Foundation Drain Installation'}, {'name': 'Foundation Repair'},
                    {'name': 'Fountain Repair'}, {'name': 'House Framing Companies'}, {'name': 'French Drains'},
                    {'name': 'Refrigerator Repair'}, {'name': 'Entry Door Repair'}, {'name': 'Fumigation Companies'},
                    {'name': 'Furnace Cleaning'}, {'name': 'Furnace Maintenance'}, {'name': 'Furnace Repair'},
                    {'name': 'Furnace Tune-Up'}, {'name': 'Furniture Assembly'}, {'name': 'Custom Furniture Builders'},
                    {'name': 'Furniture Cleaning'}, {'name': 'Furniture Moving'},
                    {'name': 'Furniture Painting Services'}, {'name': 'Furniture Refinishers'},
                    {'name': 'Furniture Repair'}, {'name': 'Furniture Upholstery'}, {'name': 'Garage Builders'},
                    {'name': 'Garage Cleaning Services'}, {'name': 'Garage Door Installers'},
                    {'name': 'Garage Door Repair'}, {'name': 'Garage Floor Epoxy & Coating'},
                    {'name': 'Garage Door Opener Repair'}, {'name': 'Garage Remodeling'},
                    {'name': 'Garbage Disposal Repair'}, {'name': 'Garbage Removal'}, {'name': 'Garden Design'},
                    {'name': 'Gardening Services'}, {'name': 'Gas Fireplace Repair'},
                    {'name': 'Gas Fireplace Installation'}, {'name': 'Gas Grill Installers'},
                    {'name': 'Gas Stove Repair'}, {'name': 'Gate Installers'}, {'name': 'Gate Repair Companies'},
                    {'name': 'Gazebo Builders'}, {'name': 'GE Appliance Repair'}, {'name': 'GE Dishwasher Repair'},
                    {'name': 'GE Dryer Repair'}, {'name': 'GE Refrigerator Repair'}, {'name': 'GE Microwave Repair'},
                    {'name': 'GE Washing Machine Repair'}, {'name': 'General Contractors'},
                    {'name': 'Generator Installation'}, {'name': 'Home Generator Repair'},
                    {'name': 'Geothermal Installation'}, {'name': 'Glass Block Companies'},
                    {'name': 'Glass Contractors'}, {'name': 'Glass Door Installation'}, {'name': 'Glaziers'},
                    {'name': 'Grading & Hauling Services'}, {'name': 'Granite Countertop Companies'},
                    {'name': 'Granite Restoration'}, {'name': 'Gravel Driveway Installation'},
                    {'name': 'Gravel Driveway Repair'}, {'name': 'Greenhouse Companies'}, {'name': 'Groundhog Removal'},
                    {'name': 'Tile Grout Cleaners'}, {'name': 'Gutter Cleaners'}, {'name': 'Gutter Guard Installation'},
                    {'name': 'Gutter Guys'}, {'name': 'Gutter Installers'}, {'name': 'Gutter Repair'},
                    {'name': 'Hail Damage Repair'}, {'name': 'Handymen'}, {'name': 'Heat Pump Companies'},
                    {'name': 'Heating & Cooling'}, {'name': 'Heating Repair'}, {'name': 'Hedge Trimming'},
                    {'name': 'Holiday Decorators'}, {'name': 'Home Addition Companies'},
                    {'name': 'Home Air Quality Testing'}, {'name': 'Home Audio Companies'}, {'name': 'Home Automation'},
                    {'name': 'Builders'}, {'name': 'Home Energy Auditors'}, {'name': 'Window Glass Repair'},
                    {'name': 'Home Inspection'}, {'name': 'Home Maintenance'}, {'name': 'Home Organizers'},
                    {'name': 'Home Remodeling Contractors'}, {'name': 'Home Renovations'},
                    {'name': 'Home Security Services'}, {'name': 'Home Stagers'}, {'name': 'Home Theater Repair'},
                    {'name': 'Home Warranties'}, {'name': 'Home Window Tinting'}, {'name': 'Kitchen Hood Cleaning'},
                    {'name': 'Hot Tub Repair'}, {'name': 'House Appraisers'}, {'name': 'House Cleaning Services'},
                    {'name': 'House Leveling'}, {'name': 'Housekeeper Agencies'}, {'name': 'Housekeeping Services'},
                    {'name': 'Dehumidifier & Humidifier Repair'}, {'name': 'Hurricane Shutters'},
                    {'name': 'HVAC Companies'}, {'name': 'HVAC Repairs'}, {'name': 'HVAC Technicians'},
                    {'name': 'Ice Maker Repair'}, {'name': 'Inground Pool Companies'},
                    {'name': 'Inground Pool Repair Companies'}, {'name': 'Above Ground Pool Contractors'},
                    {'name': 'Aluminum Fence Companies'}, {'name': 'Appliance Installers'},
                    {'name': 'Baseboard Installation'}, {'name': 'Bathroom Tile Contractors'},
                    {'name': 'Bathtub Installation'}, {'name': 'Boiler Installation'},
                    {'name': 'Ceiling Fan Companies'}, {'name': 'Central Vacuum Installation'},
                    {'name': 'Ceramic Tile Companies'}, {'name': 'Chain Link Fence Companies'},
                    {'name': 'Chimney Cap Replacement'}, {'name': 'Commercial Carpeting'},
                    {'name': 'Crown Molding Companies'}, {'name': 'Dog Fence Companies'},
                    {'name': 'Egress Window Installers'}, {'name': 'Fireplace Builders'},
                    {'name': 'Furnace Installation'}, {'name': 'Garage Door Opener Services'},
                    {'name': 'Garbage Disposal Companies'}, {'name': 'Home Speaker Installation'},
                    {'name': 'Home Theater Companies'}, {'name': 'Hot Tub Companies'},
                    {'name': 'Humidifier Installation'}, {'name': 'Laminate Countertop Installation'},
                    {'name': 'Laminate Floor Installation'}, {'name': 'Light Fixture Installation'},
                    {'name': 'Metal Siding Contractors'}, {'name': 'Microwave Installation'},
                    {'name': 'Mirror Installation'}, {'name': 'Privacy Fence Companies'}, {'name': 'Putting Greens'},
                    {'name': 'Quartz Countertop Installers'}, {'name': 'Screen Door Installation'},
                    {'name': 'Seamless Gutter Companies'}, {'name': 'Security Camera Installation'},
                    {'name': 'Skylight Companies'}, {'name': 'Solar Panel Installation'},
                    {'name': 'Sprinkler Services'}, {'name': 'Chair Lift Companies'}, {'name': 'Handrail Installers'},
                    {'name': 'Storm Door Companies'}, {'name': 'Swing Set Installation'},
                    {'name': 'Thermostat Installation'}, {'name': 'Tile Floor Installers'},
                    {'name': 'Vinyl Siding Companies'}, {'name': 'Water Softener Companies'},
                    {'name': 'Insulation Installers'}, {'name': 'Interior Decorating'}, {'name': 'Interior Design'},
                    {'name': 'Lighting Design'}, {'name': 'Interior Painters'}, {'name': 'Invisible Fence'},
                    {'name': 'iPhone Repair'}, {'name': 'Irrigation Pump Repair'}, {'name': 'Jacuzzi Repair'},
                    {'name': 'Junk Haulers'}, {'name': 'Cabinet Refacing'}, {'name': 'Kitchen Design'},
                    {'name': 'Kitchen Refacing'}, {'name': 'Kitchen Remodeling'}, {'name': 'Kitchen Renovations'},
                    {'name': 'Laminate Floor Cleaning Services'}, {'name': 'Laminate Flooring Repair'},
                    {'name': 'Lamp Repair'}, {'name': 'Land Surveying'}, {'name': 'Landscape Architects'},
                    {'name': 'Landscape Design'}, {'name': 'Grading Companies'}, {'name': 'Landscapers'},
                    {'name': 'Lawn Aeration'}, {'name': 'Lawn Care'}, {'name': 'Lawn Dethatching Services'},
                    {'name': 'Lawn Fertilizer Companies'}, {'name': 'Lawn Cutting Services'},
                    {'name': 'Lawn Pest Control Services'}, {'name': 'Lawn Repair Services'},
                    {'name': 'Lawn Seeding Companies'}, {'name': 'Lawn Treatment'}, {'name': 'Lead Removal'},
                    {'name': 'Lead Testing'}, {'name': 'Leaf Removal Services'}, {'name': 'LED TV Repair'},
                    {'name': 'LED Light Installation'}, {'name': 'LG Appliance Repair Services'},
                    {'name': 'LG Refrigerator Repair'}, {'name': 'Local Architects'}, {'name': 'Local Movers'},
                    {'name': 'Door Lock Repair Services'}, {'name': 'Locksmiths'}, {'name': 'Mailbox Installation'},
                    {'name': 'Main Drain Camera Companies'}, {'name': 'Marble Restoration & Repair'},
                    {'name': 'Masonry'}, {'name': 'Mattress Cleaners'}, {'name': 'Maytag Appliance Repair'},
                    {'name': 'Maytag Dishwasher Repair'}, {'name': 'Maytag Dryer Repair'},
                    {'name': 'Maytag Refrigerator Repair'}, {'name': 'Maytag Washer Repair'},
                    {'name': 'Metal Fabricators'}, {'name': 'Metal Roof Installation'}, {'name': 'Metal Roofing'},
                    {'name': 'Metal Roof Repair'}, {'name': 'Rodent Control'}, {'name': 'Microwave Repair'},
                    {'name': 'Mirror Repair'}, {'name': 'Mobile Computer Repair'}, {'name': 'Mobile Locksmiths'},
                    {'name': 'Modern Architects'}, {'name': 'Modular Homes'}, {'name': 'Mold Testing'},
                    {'name': 'Mold Removal'}, {'name': 'Molly Maid'}, {'name': 'Mosquito Control Companies'},
                    {'name': 'Move Out Cleaners'}, {'name': 'Moving Services'}, {'name': 'Moving Labor'},
                    {'name': 'Mulch Delivery Services'}, {'name': 'Mulching Companies'}, {'name': 'Gas Plumbers'},
                    {'name': 'Nest Installation'}, {'name': 'New Build Homes'}, {'name': 'Odor Removal Services'},
                    {'name': 'Opossum Control'}, {'name': 'Outdoor Kitchen Builders'}, {'name': 'Outdoor Light Repair'},
                    {'name': 'Outdoor Landscape Lighting'}, {'name': 'Oven Repair'}, {'name': 'Overhead Door Repair'},
                    {'name': 'Packing Services'}, {'name': 'Paint Stripping'}, {'name': 'House Painters'},
                    {'name': 'Paver Install Companies'}, {'name': 'Paving Contractors'}, {'name': 'Pergola Builders'},
                    {'name': 'Pest Inspection'}, {'name': 'Outdoor Plant Watering'}, {'name': 'Plaster Companies'},
                    {'name': 'Playground Installation'}, {'name': 'Playground Repair Services'}, {'name': 'Plumbers'},
                    {'name': 'Handymen Plumbers'}, {'name': 'Plumbing Repairs'}, {'name': 'Pond Companies'},
                    {'name': 'Pond Services'}, {'name': 'Pool Cleaning'}, {'name': 'Pool Closing Services'},
                    {'name': 'Pool Deck Companies'}, {'name': 'Pool Designers'}, {'name': 'Pool Heater Services'},
                    {'name': 'Pool Liner Replace & Install Companies'}, {'name': 'Pool Plaster Repair'},
                    {'name': 'Pool Pump Repair'}, {'name': 'Pool Remodeling Companies'},
                    {'name': 'Pool Removal Companies'}, {'name': 'Pool Repair'}, {'name': 'Pool Maintenance'},
                    {'name': 'Pool Table Assembly'}, {'name': 'Pool Tile Companies'},
                    {'name': 'Porcelain Bathtub Refinish & Repair'}, {'name': 'Porcelain Tile'},
                    {'name': 'Porch Contractors'}, {'name': 'Porch Repair'}, {'name': 'Powder Coating Services'},
                    {'name': 'Pre-Made Cabinets'}, {'name': 'Radon Inspectors'}, {'name': 'Range Hood Companies'},
                    {'name': 'Recessed Lighting Installers'}, {'name': 'Recliner Repair'},
                    {'name': 'Cabinet Refinishers'}, {'name': 'Remodel Designers'},
                    {'name': 'Furniture Removal Services'}, {'name': 'Asphalt Repair Companies'},
                    {'name': 'Attic Fan Repair'}, {'name': 'Awning Repair'}, {'name': 'Bathroom Tile Repair'},
                    {'name': 'Boat Dock Repair'}, {'name': 'Carport Repair'}, {'name': 'Ceiling Fan Repair'},
                    {'name': 'Chain Link Fence Repair'}, {'name': 'Countertop Repair'}, {'name': 'Faucet Repair'},
                    {'name': 'Flat Roof Repair'}, {'name': 'Freezer Repair Services'},
                    {'name': 'Garage Door Spring Repair'}, {'name': 'Gas Appliance Repair'},
                    {'name': 'Gas Water Heater Repair'}, {'name': 'Geothermal Repair'},
                    {'name': 'Granite Countertop Repair'}, {'name': 'Grout Repair Services'},
                    {'name': 'Heat Pump Repair'}, {'name': 'Home Audio Equipment Repair'},
                    {'name': 'Hurricane Shutter Repair'}, {'name': 'Leather Furniture Repair'},
                    {'name': 'Masonry Repair'}, {'name': 'Patio Repair'}, {'name': 'Patio Furniture Repair'},
                    {'name': 'Plaster Repair'}, {'name': 'Pool Cover Repair'}, {'name': 'Pool Heater Repair'},
                    {'name': 'Sewer Line Repair'}, {'name': 'Siding Repair'}, {'name': 'Skylight Repair'},
                    {'name': 'Sump Pump Repair'}, {'name': 'Tankless Water Heater Repair'},
                    {'name': 'Thermostat Repair'}, {'name': 'Tile Roof Repair'}, {'name': 'Vertical Blind Repair'},
                    {'name': 'Vinyl Siding Repair Contractors'}, {'name': 'Wicker Repair'},
                    {'name': 'Window Shade Repair'}, {'name': 'Window Glass Replacement'},
                    {'name': 'Window Screen Installation'}, {'name': 'Residential Cleaners'},
                    {'name': 'Residential Designers'}, {'name': 'Fire Damage Restoration'},
                    {'name': 'Pool Resurfacing'}, {'name': 'Retaining Wall Companies'},
                    {'name': 'Retaining Wall Repair'}, {'name': 'Roof Cleaning'}, {'name': 'Roof Inspection'},
                    {'name': 'Leaky Roof Repair'}, {'name': 'Roof Moss Removal'}, {'name': 'Roof Repair'},
                    {'name': 'Roof Sealing'}, {'name': 'Roofers'}, {'name': 'Rubber Roofers'}, {'name': 'Rug Cleaning'},
                    {'name': 'Safe Movers'}, {'name': 'Landscape Rock & Sand Delivery'}, {'name': 'Sandblasting'},
                    {'name': 'Satellite Dish Companies'}, {'name': 'Satellite Dish Repair'},
                    {'name': 'Sauna Companies'}, {'name': 'Sauna Repair'}, {'name': 'Screen Porch Builders'},
                    {'name': 'Seamless Gutter Repair'}, {'name': 'Security Door Installers'},
                    {'name': 'Safe Installation'}, {'name': 'Septic Maintenance Companies'},
                    {'name': 'Septic Tank Cleaners'}, {'name': 'Septic Tank Companies'},
                    {'name': 'Septic System Repair'}, {'name': 'Sewer Cleaning'}, {'name': 'Sewer Companies'},
                    {'name': 'Shed Builders'}, {'name': 'Shower Door Installers'}, {'name': 'Shower Enclosures'},
                    {'name': 'Shower Glass Installers'}, {'name': 'Shower Installation'}, {'name': 'Shower Repair'},
                    {'name': 'Shrub Removal & Trimming'}, {'name': 'Siding Companies'}, {'name': 'Sign Makers'},
                    {'name': 'Sink Installation'}, {'name': 'Sink Refinishing'}, {'name': 'Sink Repair'},
                    {'name': 'Skunk Control'}, {'name': 'Slate Roofers'}, {'name': 'Glass Door Repair'},
                    {'name': 'Sliding Door Installation'}, {'name': 'Small Appliance Repair Services'},
                    {'name': 'Small Movers'}, {'name': 'Smartphone Repair'}, {'name': 'Snake Control'},
                    {'name': 'Snow Removal Companies'}, {'name': 'Sod Installation'}, {'name': 'Topsoil Delivery'},
                    {'name': 'Soil Testing'}, {'name': 'Solar Panel Repair'}, {'name': 'Ultrasonic Cleaning'},
                    {'name': 'Soundproofing'}, {'name': 'Spider Control'}, {'name': 'Spray Foam Insulation Installers'},
                    {'name': 'Sprinkler Winterization'}, {'name': 'Lawn Sprinkler Repair'},
                    {'name': 'Squirrel Removal'}, {'name': 'Fence Staining'}, {'name': 'Stained Glass Repair'},
                    {'name': 'Stair Builders'}, {'name': 'Stair Installers'}, {'name': 'Stone Flooring Companies'},
                    {'name': 'Stone Veneer'}, {'name': 'Storm Damage Repair Companies'},
                    {'name': 'Storm Drain Contractors'}, {'name': 'Storm Shelter Builders'},
                    {'name': 'Structural Engineers'}, {'name': 'Stucco Repair'}, {'name': 'Stucco Contractors'},
                    {'name': 'Stump Removal'}, {'name': 'Sump Pump Installation'}, {'name': 'Sump Pump Replacement'},
                    {'name': 'Surround Sound Installation'}, {'name': 'Surveillance Camera Installation'},
                    {'name': 'Suspended Ceiling Companies'}, {'name': 'Swamp Cooler Repair'},
                    {'name': 'Swimming Pool Installation'}, {'name': 'Tablet Repair'},
                    {'name': 'Tankless Water Heater Companies'}, {'name': 'Tennis Court Contractors'},
                    {'name': 'Termite Control'}, {'name': 'Termite Tenting'}, {'name': 'Tile Contractors'},
                    {'name': 'Tile Floor Cleaning'}, {'name': 'Tile Repair Companies'},
                    {'name': 'Toilet Repair & Installation'}, {'name': 'Trampoline Assembly'},
                    {'name': 'Trash Bin Rental'}, {'name': 'Trash Haulers'}, {'name': 'Treadmill Repair'},
                    {'name': 'Tree Cutting Services'}, {'name': 'Tree Debris Removal & Disposal'},
                    {'name': 'Tree Maintenance'}, {'name': 'Tree Pruning'}, {'name': 'Tree Removal'},
                    {'name': 'Tree Trimming'}, {'name': 'Treehouse Builders'}, {'name': 'Turf Installation'},
                    {'name': 'TV Antenna Services'}, {'name': 'TV Repair'}, {'name': 'Upholstery Cleaners'},
                    {'name': 'Vinyl Fencing Installers'}, {'name': 'Vinyl Flooring Companies'},
                    {'name': 'Vinyl Floor Repair'}, {'name': 'Vinyl Siding Cleaning'}, {'name': 'Wall Painters'},
                    {'name': 'Wall Repair Services'}, {'name': 'Wallpaper Installers'}, {'name': 'Wallpaper Removal'},
                    {'name': 'Washing Machine Repair'}, {'name': 'Waste Removal Companies'}, {'name': 'Water Clean Up'},
                    {'name': 'Water Heater Installation'}, {'name': 'Water Heater Repair'},
                    {'name': 'Water Softener Repair Companies'}, {'name': 'Water Softener Specialists'},
                    {'name': 'Weed Control'}, {'name': 'Well Pump Repair'}, {'name': 'Whirlpool Repair'},
                    {'name': 'Whirlpool Dryer Repair'}, {'name': 'Whirlpool Refrigerator Repair'},
                    {'name': 'Whirlpool Oven Repair'}, {'name': 'Whirlpool Washer Repair'},
                    {'name': 'Wi-Fi Installation'}, {'name': 'Window Washers'}, {'name': 'Window Installation'},
                    {'name': 'Window & Door Installation'}, {'name': 'Home Window Repair'},
                    {'name': 'Window Shutter Repair'}, {'name': 'Window Shutter Companies'},
                    {'name': 'Wood Fence Companies'}, {'name': 'Wood Fence Repair'},
                    {'name': 'Hardwood Floor Installation'}, {'name': 'Wood Floor Refinishing'},
                    {'name': 'Hardwood Floor Repair'}, {'name': 'Wood Stove Services'},
                    {'name': 'Wood Stove Inspection'}, {'name': 'Wood Stripping Services'},
                    {'name': 'Wrought Iron Fences'}, {'name': 'Wrought Iron Fence Repair'},
                    {'name': 'Yard Care Services'}, {'name': 'Yard Clean Up Services'}]
    Service.objects.all().delete()
    for s in service_list:
        service = Service.objects.create(name=s.get('name'), slug=slugify(s.get('name')))
        service.save()
        city_service_create(service=service)
