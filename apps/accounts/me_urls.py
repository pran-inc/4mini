from django.urls import path
from . import me_views

urlpatterns = [
    path("vehicles/", me_views.my_vehicles, name="my_vehicles"),
    path("posts/", me_views.my_posts, name="my_posts"),
    path("favorites/", me_views.my_favorites, name="my_favorites"),
]
