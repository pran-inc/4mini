from django.urls import path
from . import views

urlpatterns = [
    path("", views.event_list, name="event_list"),
    path("new/", views.event_create, name="event_create"),
    path("<int:event_id>/", views.event_detail, name="event_detail"),

    # entry: select -> confirm -> create
    path("<int:event_id>/entry/", views.event_entry_create, name="event_entry_create"),
    path("<int:event_id>/entry/confirm/<int:vehicle_id>/", views.event_entry_confirm, name="event_entry_confirm"),

    path("<int:event_id>/vote/<int:entry_id>/", views.vote_toggle, name="event_vote_toggle"),

    path("<int:event_id>/awards/", views.event_awards_manage, name="event_awards_manage"),
    path("<int:event_id>/awards/new/", views.award_create, name="award_create"),
    path("<int:event_id>/awards/<int:award_id>/edit/", views.award_edit, name="award_edit"),
    path("<int:event_id>/awards/<int:award_id>/delete/", views.award_delete, name="award_delete"),
    path("<int:event_id>/gallery/", views.event_gallery, name="event_gallery"),
    path("<int:event_id>/winners/", views.event_winners, name="event_winners"),
    path("<int:event_id>/edit/", views.event_edit, name="event_edit"),
]
