'''URL configuration for the public training-only deployment.'''

from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='training:index', permanent=False)),
    path('training/', include('apps.training.urls')),
]
