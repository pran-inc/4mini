# apps/vehicles/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # list / detail
    path("", views.vehicle_list, name="vehicle_list"),
    path("<int:pk>/", views.vehicle_detail, name="vehicle_detail"),

    # create (Step1) + confirm (YES/NO)
    path("new/", views.vehicle_create_quick, name="vehicle_create_quick"),
    path("<int:pk>/created/", views.vehicle_create_confirm, name="vehicle_create_confirm"),

    # edit (Step2 + images + parts)
    path("<int:pk>/edit/", views.vehicle_edit, name="vehicle_edit"),

    path("<int:pk>/delete/", views.vehicle_delete_confirm, name="vehicle_delete_confirm"),
    path("<int:pk>/delete/confirm/", views.vehicle_delete, name="vehicle_delete"),

    # parts API/AJAX
    path("api/parts/", views.api_parts_by_category, name="api_parts_by_category"),
    path("<int:vehicle_id>/parts/create/", views.vehicle_part_create, name="vehicle_part_create"),
    path("<int:vehicle_id>/parts/<int:part_id>/delete/", views.vehicle_part_delete, name="vehicle_part_delete"),



]