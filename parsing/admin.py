from django.contrib import admin
from .models import Query, Place, Profile, QueryPlace, Review, Tag, ReviewType, ReviewPart, CloudImage, FAQ, \
    FAQQuestion, UniqueReview, City, Service, CityService, State, WordAiCookie, CityServiceFile


@admin.register(Query)
class QueryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'places_count']
    list_display_links = ['id', 'name']
    list_filter = ['user']


@admin.register(Place)
class PlaceAdmin(admin.ModelAdmin):
    list_display = ['id', 'cid', 'name']
    list_display_links = ['id']
    exclude = ['city_service']
    # list_filter = ['query']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ReviewType)
class ReviewTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']


@admin.register(ReviewPart)
class ReviewPartAdmin(admin.ModelAdmin):
    list_display = ['id', 'rating']


admin.site.register(Profile)
admin.site.register(QueryPlace)
admin.site.register(CloudImage)
admin.site.register(FAQ)
admin.site.register(FAQQuestion)
admin.site.register(UniqueReview)
admin.site.register(Service)
admin.site.register(State)
admin.site.register(WordAiCookie)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'get_cities']
    list_filter = ['is_county']


@admin.register(CityService)
class CityServiceAdmin(admin.ModelAdmin):
    list_display = ['id', 'search_text', 'status']
    list_filter = ['status']
    list_editable = ['status']


@admin.register(CityServiceFile)
class CityServiceFileAdmin(admin.ModelAdmin):
    exclude = ['city_service']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['id', 'date_create']
