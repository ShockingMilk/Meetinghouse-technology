"""Full management and public training URL configuration."""

from django.urls import path

from . import views

app_name = 'training'

urlpatterns = [
    path('manage/guides/', views.guide_list, name='manage_guides'),
    path('manage/guides/new/', views.guide_create, name='manage_guide_create'),
    path('manage/guides/<int:pk>/edit/', views.guide_edit, name='manage_guide_edit'),
    path('manage/guides/<int:pk>/submit-review/', views.guide_submit_review, name='manage_guide_submit_review'),
    path('manage/guides/<int:pk>/review/', views.guide_review, name='manage_guide_review'),
    path('manage/guides/<int:pk>/publish/', views.guide_publish, name='manage_guide_publish'),
    path('manage/guides/<int:pk>/archive/', views.guide_archive, name='manage_guide_archive'),
    path('manage/guides/<int:pk>/revisions/', views.guide_revisions, name='manage_guide_revisions'),
    path('manage/guides/<int:pk>/revisions/<int:revision_pk>/restore/', views.guide_restore, name='manage_guide_restore'),
    path('manage/categories/', views.category_list, name='manage_categories'),
    path('manage/categories/new/', views.category_create, name='manage_category_create'),
    path('manage/categories/<int:pk>/edit/', views.category_edit, name='manage_category_edit'),
    path('categories/<slug:slug>/', views.category_detail, name='category_detail'),
    path('<slug:slug>/', views.guide_detail, name='guide_detail'),
    path('', views.index, name='index'),
]
