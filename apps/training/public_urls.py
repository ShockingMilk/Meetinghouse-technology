"""Public-only training routes for the isolated training deployment."""

from django.urls import path

from . import views

app_name = 'training'

urlpatterns = [
    path('categories/<slug:slug>/', views.category_detail, name='category_detail'),
    path('<slug:slug>/', views.guide_detail, name='guide_detail'),
    path('', views.index, name='index'),
]
