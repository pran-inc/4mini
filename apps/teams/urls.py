from django.urls import path
from . import views

urlpatterns = [
    path("", views.team_list, name="team_list"),
    path("new/", views.team_create, name="team_create"),
    path("<int:team_id>/", views.team_detail, name="team_detail"),
    path("<int:team_id>/edit/", views.team_edit, name="team_edit"),

    # 招待
    path("<int:team_id>/invite/", views.team_invite, name="team_invite"),
    path("invites/", views.my_team_invites, name="my_team_invites"),
    path("invites/<int:membership_id>/accept/", views.invite_accept, name="invite_accept"),
    path("invites/<int:membership_id>/decline/", views.invite_decline, name="invite_decline"),

    path("<int:team_id>/invite/", views.team_invite_create, name="team_invite_create"),
    

    path("<int:team_id>/invites/<int:user_id>/cancel/", views.invite_cancel, name="team_invite_cancel"),



    # 参加申請
    path("<int:team_id>/join/", views.team_join_request, name="team_join_request"),
    path("<int:team_id>/requests/<int:user_id>/approve/", views.request_approve, name="team_request_approve"),
    path("<int:team_id>/requests/<int:user_id>/reject/", views.request_reject, name="team_request_reject"),

    # 権限
    path("<int:team_id>/role/<int:user_id>/toggle/", views.role_toggle, name="team_role_toggle"),

    # 代表車両
    path("<int:team_id>/pinned/add/", views.pinned_add, name="team_pinned_add"),
    path("<int:team_id>/pinned/<int:pin_id>/remove/", views.pinned_remove, name="team_pinned_remove"),

    # メンバー削除
    path("<int:team_id>/members/<int:user_id>/remove/", views.team_member_remove, name="team_member_remove"),

    # チーム削除
    path("<int:team_id>/delete/", views.team_delete_confirm, name="team_delete_confirm"),
    path("<int:team_id>/delete/confirm/", views.team_delete, name="team_delete"),

    path("my_teams/", views.my_teams, name="my_teams"),

]
