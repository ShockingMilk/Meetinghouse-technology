"""URL configuration for operational notifications."""

from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.notification_list, name="list"),
    path(
        "<int:pk>/",
        views.notification_detail,
        name="detail",
    ),
    path(
        "<int:pk>/acknowledge/",
        views.notification_acknowledge,
        name="acknowledge",
    ),
    path(
        "<int:pk>/assign/",
        views.notification_assign,
        name="assign",
    ),
    path(
        "<int:pk>/snooze/",
        views.notification_snooze,
        name="snooze",
    ),
    path(
        "<int:pk>/unsnooze/",
        views.notification_unsnooze,
        name="unsnooze",
    ),
    path(
        "<int:pk>/resolve/",
        views.notification_resolve,
        name="resolve",
    ),
    path(
        "<int:pk>/reopen/",
        views.notification_reopen,
        name="reopen",
    ),
]
