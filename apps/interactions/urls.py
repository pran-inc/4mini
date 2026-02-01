from django.urls import path
from .views import toggle_reaction

urlpatterns = [
    path("toggle/", toggle_reaction, name="toggle_reaction"),
]
