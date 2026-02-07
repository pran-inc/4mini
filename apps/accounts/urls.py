from django.urls import path
from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("edit/", views.account_edit, name="account_edit"),

    path("<str:username>/", views.profile_detail, name="profile_detail"),
    path("<str:username>/vehicles/", views.profile_vehicles, name="profile_vehicles"),
    path("<str:username>/posts/", views.profile_posts, name="profile_posts"),
    path("<str:username>/entries/", views.profile_entries, name="profile_entries"),
]
