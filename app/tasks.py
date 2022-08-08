import json
import os

from celery import shared_task
from pytils.translit import slugify
from fake_useragent import UserAgent
import requests
from bs4 import BeautifulSoup as BS
import pickle
import datetime

from app.models import Category, Page
from parsing.models import City, Service, CityService, Review, Place
from parsing.tasks import GenerateUser, set_photo_url
from parsing.utils import save_image
import time

from parsing.utils import city_service_create


class FilePickle:
    def __init__(self, file_name='app/db.pickle'):
        self.file_name = file_name

    def read_file(self):
        try:
            with open(self.file_name, 'rb') as f:
                data = pickle.load(f)
            return data
        except FileNotFoundError:
            file = open(self.file_name, 'wb')
            pickle.dump({}, file)
            file.close()
            return self.read_file()
        except EOFError:
            self.write_file(data={})

    def write_file(self, data):
        with open(self.file_name, 'wb') as f:
            pickle.dump(data, f)


class GetSoup:
    def __init__(self, url: str):
        self.url = url

    def get_site(self):
        r = requests.get(self.url, allow_redirects=False)
        if r.status_code == 200:
            return r.text
        return None

    def get_soup(self):
        try:
            soup = BS(self.get_site(), 'lxml')
            return soup
        except:
            return self.get_site()

    def get_page_content(self):
        soup = self.get_soup()
        try:
            main = soup.find('div', {"id": "main"})
            content = main.find('div', {"id": "content"})
            title = content.find('div', class_='top').text
            middle = str(content.find('div', class_='middle'))
            page_data = {
                'url': self.url,
                'title': str(title),
                'content': middle,
                'html': str(soup)
            }
            return page_data
        except:
            page_data = {
                'url': self.url,
                'title': '  ',
                'content': None,
                'html': None
            }
            return page_data

    def get_file_content(self):
        r = requests.get(self.url)
        if r.status_code == 200:
            return r.content

    def save_file(self, file: bytes):
        print(file)

    def file_upload(self):
        file = self.get_file_content()
        self.save_file(file)

    def is_file(self):
        file_types = ['pdf', 'xlsx', 'doc', 'docx']
        file_type = self.url.split('.')[-1]
        if file_type in file_types:
            self.file_upload()
            return True
        return False

    def get_links(self):
        if self.is_file():
            return []
        links = []
        page_links = self.get_soup().find_all('a')
        for link in page_links:
            try:
                link = link['href']
                if link[0] == '/':
                    links.append(link)
            except Exception as e:
                # print(e.__class__.__name__)
                pass
        return links


def parser():
    dt1 = datetime.datetime.now()
    links = {
        'unchecked': [],
        'checked': [],
    }
    url = 'http://vaeng.com'
    site = GetSoup(url=url)
    # data = site.get_page_content()
    page_links = site.get_links()

    for page_link in page_links:
        if page_link not in links['checked'] + links['unchecked']:
            links['unchecked'].append(page_link)

    for index, link in enumerate(links['unchecked']):
        page_links = GetSoup(url + link).get_links()
        for page_link in page_links:
            if page_link not in links['checked'] + links['unchecked']:
                links['unchecked'].append(page_link)
        links['checked'].append(link)
        links['unchecked'][index] = None
        try:
            file = FilePickle()
            file.write_file(data=links)
        except:
            pass
        print(link)
        print(len(links['checked']))
        print(len(links['unchecked']))
        print()

    dt2 = datetime.datetime.now()
    print(links)
    print(dt2 - dt1)


def recurse(a, a_len, data, rec):
    rec += 1
    for j in data:
        b = j.split('/')
        b = b[1:]
        if b[-1] == '':
            b = b[:-1]
        # print('        ', set(a), '  ==  ', set(b[:a_len]))
        if set(b[:a_len]) == set(a) and set(a) != set(b):
            print('-----' * rec, j)
        recurse(b, len(b), data, rec)


def recursion_list(data):
    for i in data:
        a = i.split('/')
        a = a[1:]
        if a[-1] == '':
            a = a[:-1]
        print(a)
        a_len = len(a)
        recurse(a, a_len, data, rec=1)


def get_filter_pages():
    file = FilePickle().read_file()
    pages_list = []
    for index, item in enumerate(file['checked']):
        item_split = item.split('/')
        if item_split[1]:
            pages_list.append(item_split[1]) if item_split[1] not in pages_list else None
    pages_list.remove('') if '' in pages_list else None
    return pages_list


def create_page(url, category):
    if url.split('/')[-1] == '':
        name = url.split('/')[-2]
    else:
        name = url.split('/')[-1]
    page = Page.objects.create(name=name, url=url, category=category)
    soup = GetSoup(url='https://vaeng.com' + url).get_page_content()
    if soup['content']:
        print(soup['content'][:40])
    page.content = soup['content']
    page.html = soup['html']
    page.save()


def create_pages(category):
    file = FilePickle().read_file()
    for j in file['checked']:
        if category.name == j.split('/')[1]:
            create_page(j, category=category)


def create_category(url):
    print(url.split('/'))
    name = url.split('/')[0]
    slug = slugify(name)
    category = Category.objects.create(name=name, title=name, slug=slug)
    category.save()
    create_pages(category)


@shared_task()
def create_categories():
    Page.objects.all().delete()
    Category.objects.all().delete()
    file = FilePickle().read_file()
    dic = {}
    category_list = [
        'news_home',
        'move_home',
        'feature_home',
        'guest_home',
        'engineering-consultants',
        'manufacturers-reps',
        'engineering-contractors',
        'professional-services',
        'equipment_suppliers',
        'schools',
        'societies',
        'registration',
        'jobs',
        'print_home',
        'subscribe',
        'advertise',
        'interactive',
        'print',
    ]
    files_category = [
        'files',
        'pdf',
        'file_download'
    ]

    pages = get_filter_pages()

    all_pages = 0
    for i in pages:
        page_count = 0
        for j in file['checked']:
            if i == j.split('/')[1]:
                page_count += 1

        if page_count > 1 and i not in files_category:
            create_category(i)
            all_pages += page_count
    print(all_pages)


if __name__ == '__main__':
    # soup = GetSoup(url='https://vaeng.com/print/december-2019-online-edition').get_soup()
    # print(soup)
    pass

a = ['', 'news_home', 'move_home', 'feature_home', 'guest_home', 'engineering-consultants', 'manufacturers-reps',
     'engineering-contractors', 'professional-services', 'equipment_suppliers', 'schools', 'societies',
     'registration',
     'jobs', 'print_home', 'subscribe', 'advertise', 'interactive', 'print', 'representatives', 'atom', 'rss',
     'vaengmail', 'bids-rfp-rfq', 'news', 'move', 'feature', 'rss.xml', 'atom.xml', 'guestarticle', 'consultants',
     'file_download', 'mailto:frost@iso.org', 'dbsys.php?page=socs', 'mailto:mayers@pavement.com',
     'dbsys.php?page=schools', 'files', 'pdf', 'index.php', 'contractors', 'professionals', 'equip',
     'index.php?page=rep&Company=Sterling%20Engineered%20Sales', 'engineering-news', '?page=rep',
     '?page=contractor',
     '?page=prof', '?page=schools', '?page=socs', 'eng', 'archive', '?page=consultant', 'jo', '?page=eom']


#
#               GET CITIES
#
@shared_task()
def create_new_cities():
    cities = [
        {'name': 'Virginia Beach', 'population': 450980,
         'zip_codes': ['23464', '23462', '23452', '23454', '23456', '23455', '23451', '23457', '23460',
                       '23459', '23461']}, {'name': 'Norfolk', 'population': 245428,
                                            'zip_codes': ['23503', '23513', '23505', '23518', '23504',
                                                          '23508', '23502', '23511', '23509', '23510',
                                                          '23523', '23507', '23517', '23551']},
        {'name': 'Chesapeake', 'population': 233371,
         'zip_codes': ['23322', '23320', '23323', '23321', '23324', '23325']},
        {'name': 'Richmond', 'population': 217853,
         'zip_codes': ['23223', '23234', '23225', '23224', '23231', '23228', '23229', '23220', '23235',
                       '23233', '23222', '23238', '23227', '23237', '23236', '23294', '23226', '23221',
                       '23230', '23219', '23250']}, {'name': 'Newport News', 'population': 182965,
                                                     'zip_codes': ['23608', '23602', '23606', '23601',
                                                                   '23607', '23605', '23603']},
        {'name': 'Alexandria', 'population': 150575,
         'zip_codes': ['22304', '22309', '22306', '22314', '22312', '22310', '22315', '22311', '22305',
                       '22302', '22303', '22308', '22301', '22307']},
        {'name': 'Hampton', 'population': 136879,
         'zip_codes': ['23666', '23669', '23663', '23661', '23664', '23665']},
        {'name': 'Roanoke', 'population': 99428,
         'zip_codes': ['24018', '24012', '24019', '24017', '24014', '24015', '24016', '24013', '24020',
                       '24011']}, {'name': 'Portsmouth', 'population': 96004,
                                   'zip_codes': ['23703', '23701', '23704', '23707', '23702', '23709',
                                                 '23708']}, {'name': 'Suffolk', 'population': 86806,
                                                             'zip_codes': ['23434', '23435', '23437', '23438',
                                                                           '23432', '23433', '23436']},
        {'name': 'Lynchburg', 'population': 79047, 'zip_codes': ['24502', '24501', '24503', '24504']},
        {'name': 'Harrisonburg', 'population': 52478, 'zip_codes': ['22801', '22802', '22807']},
        {'name': 'Leesburg', 'population': 49496, 'zip_codes': ['20176', '20175']},
        {'name': 'Charlottesville', 'population': 45593,
         'zip_codes': ['22903', '22901', '22902', '22911', '22904']},
        {'name': 'Blacksburg', 'population': 43985, 'zip_codes': ['24060']},
        {'name': 'Danville', 'population': 42444, 'zip_codes': ['24540', '24541']},
        {'name': 'Manassas', 'population': 42081, 'zip_codes': ['20110', '20109', '20111', '20112']},
        {'name': 'Petersburg', 'population': 32701, 'zip_codes': ['23803', '23805', '23806']},
        {'name': 'Fredericksburg', 'population': 28350,
         'zip_codes': ['22407', '22405', '22408', '22401', '22406']},
        {'name': 'Winchester', 'population': 27543, 'zip_codes': ['22602', '22601', '22603']},
        {'name': 'Salem', 'population': 25483, 'zip_codes': ['24153']},
        {'name': 'Herndon', 'population': 24554, 'zip_codes': ['20171', '20170']},
        {'name': 'Staunton', 'population': 24538, 'zip_codes': ['24401']},
        {'name': 'Fairfax', 'population': 24483, 'zip_codes': ['22030', '22033', '22031', '22032', '22035']},
        {'name': 'Hopewell', 'population': 22196, 'zip_codes': ['23860']},
        {'name': 'Christiansburg', 'population': 21805, 'zip_codes': ['24073']},
        {'name': 'Waynesboro', 'population': 21366, 'zip_codes': ['22980']},
        {'name': 'Colonial Heights', 'population': 17731, 'zip_codes': ['23834']},
        {'name': 'Radford', 'population': 17646, 'zip_codes': ['24141', '24142']},
        {'name': 'Culpeper', 'population': 17411, 'zip_codes': ['22701']},
        {'name': 'Bristol', 'population': 17184, 'zip_codes': ['24201', '24202']},
        {'name': 'Vienna', 'population': 16459, 'zip_codes': ['22182', '22180', '22181', '22185']},
        {'name': 'Manassas Park', 'population': 15174, 'zip_codes': []},
        {'name': 'Front Royal', 'population': 15038, 'zip_codes': ['22630']},
        {'name': 'Williamsburg', 'population': 14691, 'zip_codes': ['23185', '23188', '23187']},
        {'name': 'Martinsville', 'population': 13711, 'zip_codes': ['24112']},
        {'name': 'Falls Church', 'population': 13601,
         'zip_codes': ['22042', '22041', '22043', '22046', '22044']},
        {'name': 'Poquoson', 'population': 12048, 'zip_codes': ['23662']},
        {'name': 'Warrenton', 'population': 9907, 'zip_codes': ['20187', '20186']},
        {'name': 'Purcellville', 'population': 8929, 'zip_codes': ['20132']},
        {'name': 'Pulaski', 'population': 8909, 'zip_codes': ['24301']},
        {'name': 'Franklin', 'population': 8526, 'zip_codes': ['23851']},
        {'name': 'Smithfield', 'population': 8287, 'zip_codes': ['23430']},
        {'name': 'Farmville', 'population': 8229, 'zip_codes': ['23901', '23909']},
        {'name': 'Vinton', 'population': 8180, 'zip_codes': ['24179']},
        {'name': 'Abingdon', 'population': 8146, 'zip_codes': ['24210', '24211']},
        {'name': 'Wytheville', 'population': 8133, 'zip_codes': ['24382']},
        {'name': 'South Boston', 'population': 7986, 'zip_codes': ['24592']},
        {'name': 'Ashland', 'population': 7328, 'zip_codes': ['23005']},
        {'name': 'Lexington', 'population': 7311, 'zip_codes': ['24450']},
        {'name': 'Galax', 'population': 7014, 'zip_codes': ['24333']},
        {'name': 'Buena Vista', 'population': 6603, 'zip_codes': ['24416']},
        {'name': 'Strasburg', 'population': 6559, 'zip_codes': ['22657', '22641']},
        {'name': 'Bedford', 'population': 6466, 'zip_codes': ['24523']},
        {'name': 'Bridgewater', 'population': 5951, 'zip_codes': ['22812']},
        {'name': 'Marion', 'population': 5875, 'zip_codes': ['24354']},
        {'name': 'Covington', 'population': 5802, 'zip_codes': ['24426']},
        {'name': 'Richlands', 'population': 5583, 'zip_codes': ['24641']},
        {'name': 'Emporia', 'population': 5462, 'zip_codes': ['23847']},
        {'name': 'Big Stone Gap', 'population': 5457, 'zip_codes': ['24219']},
        {'name': 'Bluefield', 'population': 5302, 'zip_codes': ['24605']},
        {'name': 'Woodstock', 'population': 5226, 'zip_codes': ['22664']},
        {'name': 'Dumfries', 'population': 5192, 'zip_codes': ['22026']},
        {'name': 'Orange', 'population': 4902, 'zip_codes': ['22960']},
        {'name': 'Luray', 'population': 4850, 'zip_codes': ['22835']},
        {'name': 'Rocky Mount', 'population': 4798, 'zip_codes': ['24151']},
        {'name': 'South Hill', 'population': 4541, 'zip_codes': ['23970']},
        {'name': 'Tazewell', 'population': 4479, 'zip_codes': ['24651']},
        {'name': 'Berryville', 'population': 4297, 'zip_codes': ['22611']},
        {'name': 'Norton', 'population': 4031, 'zip_codes': ['24273']},
        {'name': 'Broadway', 'population': 3780, 'zip_codes': ['22815']},
        {'name': 'Clifton Forge', 'population': 3775, 'zip_codes': ['24422']},
        {'name': 'Blackstone', 'population': 3553, 'zip_codes': ['23824']},
        {'name': 'Colonial Beach', 'population': 3541, 'zip_codes': ['22443']},
        {'name': 'Altavista', 'population': 3460, 'zip_codes': ['24517']},
        {'name': 'Lebanon', 'population': 3356, 'zip_codes': ['24266']},
        {'name': 'West Point', 'population': 3333, 'zip_codes': ['23181']},
        {'name': 'Wise', 'population': 3144, 'zip_codes': ['24293']},
        {'name': 'Chincoteague', 'population': 2913, 'zip_codes': []},
        {'name': 'Elkton', 'population': 2790, 'zip_codes': ['22827']},
        {'name': 'Grottoes', 'population': 2738, 'zip_codes': ['24441']},
        {'name': 'Pearisburg', 'population': 2699, 'zip_codes': ['24134']},
        {'name': 'Dublin', 'population': 2686, 'zip_codes': ['24084']},
        {'name': 'Hillsville', 'population': 2680, 'zip_codes': ['24343']},
        {'name': 'Windsor', 'population': 2654, 'zip_codes': ['23487']},
        {'name': 'Timberville', 'population': 2586, 'zip_codes': ['22853']},
        {'name': 'Tappahannock', 'population': 2380, 'zip_codes': ['22560']},
        {'name': 'Shenandoah', 'population': 2352, 'zip_codes': ['22849']},
        {'name': 'Chase City', 'population': 2304, 'zip_codes': ['23924']},
        {'name': 'Crewe', 'population': 2282, 'zip_codes': ['23930']},
        {'name': 'Amherst', 'population': 2206, 'zip_codes': ['24521']},
        {'name': 'New Market', 'population': 2199, 'zip_codes': ['22844']},
        {'name': 'Waverly', 'population': 2081, 'zip_codes': ['23890', '23891']},
        {'name': 'Saltville', 'population': 2042, 'zip_codes': ['24370']},
        {'name': 'Mount Jackson', 'population': 2036, 'zip_codes': ['22842']},
        {'name': 'Coeburn', 'population': 2015, 'zip_codes': ['24230']},
        {'name': 'Gate City', 'population': 1976, 'zip_codes': ['24251']},
        {'name': 'Haymarket', 'population': 1973, 'zip_codes': ['20169']},
        {'name': 'Narrows', 'population': 1964, 'zip_codes': ['24124']},
        {'name': 'Stephens Sity', 'population': 1921, 'zip_codes': []},
        {'name': 'Lovettsville', 'population': 1869, 'zip_codes': ['20180']},
        {'name': 'Pennington Gap', 'population': 1823, 'zip_codes': ['24277']},
        {'name': 'Chilhowie', 'population': 1749, 'zip_codes': ['24319']},
        {'name': 'Appomattox', 'population': 1744, 'zip_codes': ['24522']},
        {'name': 'Victoria', 'population': 1696, 'zip_codes': ['23974']},
        {'name': 'Appalachia', 'population': 1684, 'zip_codes': ['24216']},
        {'name': 'Stanley', 'population': 1663, 'zip_codes': ['22851']},
        {'name': 'Louisa', 'population': 1610, 'zip_codes': ['23093']},
        {'name': 'Dayton', 'population': 1578, 'zip_codes': ['22821']},
        {'name': 'Gordonsville', 'population': 1560, 'zip_codes': ['22942']},
        {'name': 'Warsaw', 'population': 1501, 'zip_codes': ['22572']},
        {'name': 'Rural Retreat', 'population': 1485, 'zip_codes': ['24368']},
        {'name': 'Chatham', 'population': 1476, 'zip_codes': ['24531']},
        {'name': 'Glade Spring', 'population': 1458, 'zip_codes': ['24340']},
        {'name': 'Stuart', 'population': 1455, 'zip_codes': ['24171']},
        {'name': 'Kilmarnock', 'population': 1446, 'zip_codes': ['22482']},
        {'name': 'Exmore', 'population': 1445, 'zip_codes': ['23350']},
        {'name': 'Honaker', 'population': 1399, 'zip_codes': ['24260']},
        {'name': 'Clintwood', 'population': 1343, 'zip_codes': ['24228']},
        {'name': 'Middletown', 'population': 1319, 'zip_codes': ['22645']},
        {'name': 'Hurt', 'population': 1281, 'zip_codes': ['24563']},
        {'name': 'Weber City', 'population': 1275, 'zip_codes': ['24290']},
        {'name': 'Onancock', 'population': 1262, 'zip_codes': ['23417']},
        {'name': 'Halifax', 'population': 1252, 'zip_codes': ['24558']},
        {'name': 'Courtland', 'population': 1247, 'zip_codes': ['23837']},
        {'name': 'Gretna', 'population': 1245, 'zip_codes': ['24557']},
        {'name': 'Kenbridge', 'population': 1241, 'zip_codes': ['23944']},
        {'name': 'Buchanan', 'population': 1171, 'zip_codes': ['24066']},
        {'name': 'Bowling Green', 'population': 1152, 'zip_codes': ['22427']},
        {'name': 'Clarksville', 'population': 1117, 'zip_codes': ['23927']},
        {'name': 'Brookneal', 'population': 1115, 'zip_codes': ['24528']},
        {'name': 'Glasgow', 'population': 1113, 'zip_codes': ['24555']},
        {'name': 'Cedar Bluff', 'population': 1090, 'zip_codes': ['24609']},
        {'name': 'Pembroke', 'population': 1087, 'zip_codes': ['24136']},
        {'name': 'Lawrenceville', 'population': 1081, 'zip_codes': ['23868']},
        {'name': 'Edinburg', 'population': 1065, 'zip_codes': ['22824']},
        {'name': 'Occoquan', 'population': 1013, 'zip_codes': ['22125']}]
    City.objects.all().delete()
    for city in cities:
        city = City.objects.create(name=city.get('name'),
                                   slug=slugify(city.get('name')),
                                   zip_codes=city.get('zip_codes'),
                                   population=city.get('population'))
        city.save()
        print(city)

        city_service_create(city=city)


#
#                   Create places from json
#
@shared_task()
def created_places_from_json_task():
    path = 'app/cities'
    cities = os.listdir(path)
    for city in cities:
        print(city)
        services = os.listdir(f'{path}/{city}')
        for service in services:
            print('  -   ', service)
            files = os.listdir(f'{path}/{city}/{service}')
            _create_places(city, service, files)


def _create_places(city, service, files):
    ua = UserAgent()
    city_service = CityService.objects.get(city__name=city, service__name=service)
    for file in files:
        cid = file.split('.')[0]
        with open(f'app/cities/{city}/{service}/{file}') as f:
            place = Place.objects.get_or_create(cid=cid)[0]
            data = json.load(f)
            base_info = data.get('base_info')
            full_info = data.get('full_info')
            coordinate = data.get('coordinate')
            base_photo = data.get('base_photo')
            reviews = data.get('reviews')
            photos = data.get('photos')

            place.city_service = city_service
            place.name = base_info.get('title')
            place.slug = slugify(base_info.get('title'))
            place.title = base_info.get('title')
            place.rating = base_info.get('rating')
            place.rating_user_count = base_info.get('rating_user_count')
            place.address = full_info.get('address')
            place.site = full_info.get('site')
            place.phone_number = full_info.get('phone_number')
            place.timetable = full_info.get('timetable')
            place.coordinate_html = coordinate
            place.save()
            print(base_photo)
            place.base_img = set_photo_url(base_photo, place.id)
            for review in reviews:
                user = GenerateUser().get_or_create_user()
                review = Review.objects.create(user=user, text=review.get('text'), rating=review.get('rating'),
                                               place=place)
                review.save()
            for photo_url in photos:
                set_photo_url(photo_url, place.id, base=False)
