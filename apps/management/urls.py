from django.urls import path

from . import views

app_name = 'management'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('reports/', views.reports, name='reports'),
]
