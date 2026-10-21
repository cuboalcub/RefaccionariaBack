from django.urls import path

from notifications.controllers.notification_controller import (
    NotificationDetailView,
    NotificationListView,
    NotificationMarkAllView,
)

urlpatterns = [
    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/mark-all/",
        NotificationMarkAllView.as_view(),
        name="notification-mark-all",
    ),
    path(
        "notifications/<int:pk>/",
        NotificationDetailView.as_view(),
        name="notification-detail",
    ),
]
