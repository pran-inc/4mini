from django.urls import path
from .views import signup, profile
from . import views


urlpatterns = [
    path("", signup, name="signup"),
    path("profile/", profile, name="profile"),
    path("mypage/", views.mypage, name="mypage"),

]
