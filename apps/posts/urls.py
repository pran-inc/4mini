from django.urls import path
from . import views

urlpatterns = [
    path("", views.post_list, name="post_list"),
    path("new/", views.post_create, name="post_create"),
    path("<int:pk>/confirm/", views.post_confirm, name="post_confirm"),
    path("<int:pk>/", views.post_detail, name="post_detail"),
    path("<int:pk>/edit/", views.post_edit, name="post_edit"),
    path("<int:pk>/delete/", views.post_delete_confirm, name="post_delete_confirm"),
    path("<int:pk>/delete/confirm/", views.post_delete, name="post_delete"),

]
