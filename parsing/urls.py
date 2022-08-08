from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name="index"),
    path('query/', views.queries, name='queries'),
    path('query/tags/<int:pk>', views.tag_queries, name="tag_queries"),
    path('states', views.states_list, name='states_list'),
    path('states/<int:pk>', views.state_detail, name='state_detail'),
    path('states/<int:pk>/preview', views.state_preview, name='state_preview'),
    # path('query/add', views.query_add, name="query_add"),
    path('query/my', views.query_list, name="query_list"),
    path('query/all', views.query_all, name="query_all"),
    path('city/service/all', views.city_service_list, name="city_service_list"),

    path('query/file/<int:pk>', views.query_file_generate, name="query_file"),
    path('query/delete/<int:pk>', views.query_delete, name="query_delete"),
    path('query/<slug:slug>', views.query_detail, name="query_detail"),

    path('query/<slug:slug>/places', views.places, name='places'),
    path('city/service/<int:pk>/places/copy', views.places_copy, name='places_copy'),
    path('city/service/<int:pk>/places/copy/code', views.places_copy_code, name='places_copy_code'),
    # path('query/<slug:slug>/edit/access', views.query_edit_access, name='query_edit_access'),

    path('place/<int:pk>/reviews/uniqueize', views.place_reviews_uniqueize,
         name="place_reviews_uniqueize"),
    path('place/<slug:place_slug>/generate/description', views.place_generate_description,
         name="place_generate_description"),
    path('place/<int:pk>/edit', views.place_edit, name="place_edit"),
    path('place/<int:pk>/edit/archive', views.place_edit_archive, name="place_edit_archive"),
    path('place/<int:pk>/edit/faq', views.place_edit_faq, name="place_edit_faq"),
    # path('query/<slug:query_slug>/places/<slug:place_slug>', views.query_place_detail, name="query_place_detail"),

    path('reviews/<slug:place_slug>', views.city_service_place_detail,
         name='city_service_place_detail'),

    path('place/<slug:slug>', views.place_detail, name="place_detail"),
    path('place/<slug:place_slug>/review/create', views.review_create, name="review_create"),
    path('place/update/<int:pk>', views.place_update, name="place_update"),

    path('cabinet/<str:username>', views.public_cabinet, name="public_cabinet"),
    path('cabinet/<str:username>/reviews/', views.user_reviews, name="user_reviews"),
    path('profile/', views.profile, name="profile"),
    path('api/review/<int:pk>', views.review_api_detail, name="review_api_detail"),
    path('api/review/<int:pk>/update', views.review_api_update, name="review_api_update"),
    path('review/progress', views.unique_reviews_list, name="unique_reviews_list"),
    path('review/all', views.all_reviews, name="all_reviews"),
    path('review/my', views.my_reviews, name="my_reviews"),
    path('review/<int:pk>/edit', views.review_edit, name="review_edit"),
    path('review/<int:pk>/uniqueize', views.review_uniqueize, name="review_uniqueize"),
    path('registration/', views.registration, name="registration"),

    path('service/', views.service_list, name='service_list'),
    path('service/autocreate', views.service_autocreate, name='service_autocreate'),
    path('service/<slug:slug>', views.service_detail, name='service_detail'),
    path('service/<slug:slug>/edit', views.service_edit, name='service_edit'),
    path('service/<slug:slug>/edit/faq', views.service_edit_faq, name='service_edit_faq'),

    path('city/', views.city_list, name='city_list'),
    path('city/autocreate', views.city_autocreate, name='city_autocreate'),
    path('city/autocreate/img', views.city_img_autocreate, name='city_img_autocreate'),

    path('<slug:slug>', views.city_detail, name='city_detail'),
    path('<slug:slug>/edit', views.city_edit, name='city_edit'),
    path('<slug:city_slug>/<slug:service_slug>', views.city_service_detail, name='city_service_detail'),
    path('<slug:city_slug>/<slug:service_slug>/custom_parser', views.start_custom_parser, name='start_custom_parser'),

    path('city/service/<int:pk>', views.city_service_access, name='city_service_access'),
    path('city/service/<int:pk>/file', views.city_service_file, name='city_service_file'),
    path('city/service/<int:pk>/file/apply', views.city_service_file_apply, name='city_service_file_apply'),
    path('city/service/<int:pk>/edit', views.city_service_edit, name='city_service_edit'),
    path('city/service/<int:pk>/edit/faq', views.city_service_edit_faq, name='city_service_edit_faq'),
    path('city/service/<int:pk>/rating', views.city_service_rating_edit, name='city_service_rating_edit'),
    path('city/service/<int:pk>/reviews/uniqueize', views.city_service_reviews_uniqueize,
         name='city_service_reviews_uniqueize'),
    path('city/service/<int:pk>/reviews/preview/uniqueize', views.city_service_preview_reviews_uniqueize,
         name='city_service_preview_reviews_uniqueize'),
    path('city/service/<int:pk>/generate/description', views.city_service_places_generate_description,
         name='city_service_places_generate_description'),

    path('admin_dashboard/', views.admin_dashboard, name="admin_dashboard"),

    path('admin_dashboard/tags', views.tags, name='tags'),
    path('admin_dashboard/tags/<int:pk>/edit', views.tag_edit, name='tag_edit'),
    path('admin_dashboard/tags/<path:path>/delete', views.tag_delete, name='tag_delete'),

    path('admin_dashboard/groups/', views.group_list, name="group_list"),
    path('admin_dashboard/groups/not', views.group_not, name="group_not"),
    path('admin_dashboard/groups/<int:pk>', views.group_detail, name="group_detail"),

    path('admin_dashboard/review/types', views.review_types, name="review_types"),
    path('admin_dashboard/review/types/<int:pk>/edit', views.review_type_edit, name="review_type_edit"),

    path('admin_dashboard/users/', views.user_list, name="user_list"),
    path('admin_dashboard/users/<int:pk>', views.user_detail, name="user_detail"),
]

app_name = 'parsing'

urlpatterns += [
    # path('api/v1/tags', views.TagList.as_view(), name='tag_list_api'),
    # path('api/v1/query/add', views.QueryAdd.as_view(), name='query_add_api'),
    # path('api/v1/query/<slug:slug>/edit', views.QueryEdit.as_view(), name='query_edit_api'),
    # path('api/v1/user/<str:username>/queries', views.QueryUser.as_view(), name='query_user_api'),
    # path('api/v1/query/<slug:slug>/places', views.QueryPlaces.as_view(), name='query_places_api'),
    # path('api/v1/query/<slug:slug>/detail', views.QueryDetail.as_view(), name='query_detail_api'),
    # path('api/v1/place/<str:cid>/html', views.PlaceHTML.as_view(), name='place_html_api'),
    # path('api/v1/place/<slug:slug>', views.PlaceDetail.as_view(), name='place_detail_api'),
    # path('api/v1/review/types', views.ReviewTypeList.as_view(), name='review_type_list_api'),
    # path('api/v1/review/create', views.ReviewCreate.as_view(), name='review_create_api'),
    # path('api/v1/review/<int:pk>/types', views.ReviewTypeList.as_view(), name='review_type_list_for_review_api'),
    # path('api/v1/review/<int:pk>/edit', views.ReviewUpdateAPIView.as_view(), name='review_update_api'),
    # path('api/v1/review/<int:pk>', views.ReviewDetail.as_view(), name='review_detail_api'),
]
