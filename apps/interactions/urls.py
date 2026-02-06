from django.urls import path
from .views import toggle_reaction
from . import views


urlpatterns = [
    path("toggle/", toggle_reaction, name="toggle_reaction"),
    path("favorites/", views.favorite_list, name="favorite_list"),

]
