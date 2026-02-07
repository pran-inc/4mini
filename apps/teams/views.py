# apps/teams/views.py

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.vehicles.models import UserVehicle
from apps.posts.models import Post

from .forms import (
    TeamForm,
    TeamInviteForm,
    TeamJoinRequestForm,
    TeamPinnedVehicleForm,
    RoleChangeForm,
)
from .models import (
    Team,
    TeamMembership,
    MembershipStatus,
    MembershipRole,
    TeamPinnedVehicle,
    TeamTag,
)

User = get_user_model()


def _team_or_404(team_id: int) -> Team:
    return get_object_or_404(Team, id=team_id, is_active=True)


def _is_team_admin(team: Team, user) -> bool:
    if not user.is_authenticated:
        return False
    if team.owner_id == user.id:
        return True
    return TeamMembership.objects.filter(
        team=team,
        user=user,
        is_active=True,
        status=MembershipStatus.APPROVED,
        role=MembershipRole.ADMIN,
    ).exists()


def _is_team_member(team: Team, user) -> bool:
    if not user.is_authenticated:
        return False
    if team.owner_id == user.id:
        return True
    return TeamMembership.objects.filter(
        team=team,
        user=user,
        is_active=True,
        status=MembershipStatus.APPROVED,
    ).exists()


def _can_view_team(team: Team, user) -> bool:
    if team.is_public:
        return True
    return _is_team_member(team, user)


def _sync_team_tags(team: Team, tags_text: str):
    raw = tags_text or ""
    names = [x.strip() for x in raw.split(",") if x.strip()]
    names = list(dict.fromkeys(names))  # 重複除去

    # 既存
    existing = set(TeamTag.objects.filter(team=team).values_list("name", flat=True))

    # 追加
    for name in names:
        if name not in existing:
            TeamTag.objects.create(team=team, name=name)

    # 削除
    TeamTag.objects.filter(team=team).exclude(name__in=names).delete()


def team_list(request):
    teams = Team.objects.filter(is_active=True, is_public=True).order_by("-created_at")
    return render(request, "teams/team_list.html", {"teams": teams})


def team_detail(request, team_id: int):
    team = _team_or_404(team_id)
    if not _can_view_team(team, request.user):
        raise Http404()

    is_admin = _is_team_admin(team, request.user)
    is_member = _is_team_member(team, request.user)

    # 自分のmembership状態（申請/招待状態表示）
    my_membership = None
    if request.user.is_authenticated:
        my_membership = TeamMembership.objects.filter(team=team, user=request.user).first()

    # メンバー（承認済み）
    approved_memberships = (
        TeamMembership.objects
        .filter(team=team, is_active=True, status=MembershipStatus.APPROVED)
        .select_related("user", "user__profile")
        .order_by("id")
    )
    members = [m.user for m in approved_memberships]

    # メンバー車両（member vehicles grid）
    vehicles_qs = (
        UserVehicle.objects
        .filter(owner__in=members)
        .select_related("model", "main_image", "owner")
        .order_by("-created_at")
    )
    vehicles_by_user = {}
    for v in vehicles_qs:
        vehicles_by_user.setdefault(v.owner_id, []).append(v)

    # ✅ 代表車両（Pinned）
    pinned = (
        TeamPinnedVehicle.objects
        .filter(team=team)
        .select_related("vehicle", "vehicle__model", "vehicle__main_image")
        .order_by("sort_order", "id")[:3]
    )

    # ✅ メンバーの最新投稿（最新12件）
    # Post に author がある前提。main_image も使う
    latest_posts = (
        Post.objects
        .filter(author__in=members)
        .select_related("author", "main_image")
        .order_by("-created_at")[:12]
    )

    # join request form（未参加なら表示）
    join_form = TeamJoinRequestForm()

    says = {
        "is_admin": is_admin,
        "is_member": is_member,
        "my_membership": my_membership,
        "join_form": join_form,
    }

    pending_requests = TeamMembership.objects.none()
    pending_invites = TeamMembership.objects.none()

    if is_admin:
        pending_requests = (
            TeamMembership.objects
            .filter(team=team, is_active=True, status=MembershipStatus.PENDING)
            .select_related("user")
            .order_by("-created_at")
        )
        pending_invites = (
            TeamMembership.objects
            .filter(team=team, is_active=True, status=MembershipStatus.INVITED)
            .select_related("user")
            .order_by("-created_at")
        )

    return render(request, "teams/team_detail.html", {
        "team": team,
        "approved_memberships": approved_memberships,
        "vehicles_by_user": vehicles_by_user,
        "pinned": pinned,
        "latest_posts": latest_posts,
        "pending_requests": pending_requests,
        "pending_invites": pending_invites,
        **says,
    })


@login_required
def team_create(request):
    if request.method == "POST":
        form = TeamForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                team = form.save(commit=False)
                team.owner = request.user
                team.save()

                _sync_team_tags(team, form.cleaned_data.get("tags_text", ""))

                # 作成者は自動参加（admin）
                TeamMembership.objects.get_or_create(
                    team=team,
                    user=request.user,
                    defaults={
                        "role": MembershipRole.ADMIN,
                        "status": MembershipStatus.APPROVED,
                        "is_active": True,
                        "invited_by": request.user,
                    }
                )

            messages.success(request, "チームを作成しました。")
            return redirect("team_detail", team_id=team.id)
    else:
        form = TeamForm()

    return render(request, "teams/team_form.html", {"form": form, "mode": "create"})


@login_required
def team_edit(request, team_id: int):
    team = _team_or_404(team_id)
    if not _is_team_admin(team, request.user):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        form = TeamForm(request.POST, request.FILES, instance=team)
        if form.is_valid():
            with transaction.atomic():
                team = form.save()
                _sync_team_tags(team, form.cleaned_data.get("tags_text", ""))
            messages.success(request, "チーム情報を更新しました。")
            return redirect("team_edit", team_id=team.id)
    else:
        # tags_text 初期値
        tags_text = ", ".join(TeamTag.objects.filter(team=team).values_list("name", flat=True))
        form = TeamForm(instance=team, initial={"tags_text": tags_text})

    invite_form = TeamInviteForm()
    role_form = RoleChangeForm()

    pending_invites = (
        TeamMembership.objects
        .filter(team=team, is_active=True, status=MembershipStatus.INVITED)
        .select_related("user")
        .order_by("-created_at")
    )

    pending_requests = (
        TeamMembership.objects
        .filter(team=team, is_active=True, status=MembershipStatus.PENDING)
        .select_related("user")
        .order_by("-created_at")
    )

    approved_memberships = (
        TeamMembership.objects
        .filter(team=team, is_active=True, status=MembershipStatus.APPROVED)
        .select_related("user")
        .order_by("id")
    )

    pinned = (
        TeamPinnedVehicle.objects
        .filter(team=team)
        .select_related("vehicle", "vehicle__model", "vehicle__main_image")
        .order_by("sort_order", "id")
    )

    pinned_form = TeamPinnedVehicleForm(team=team, user=request.user)

    return render(request, "teams/team_edit.html", {
        "team": team,
        "form": form,
        "invite_form": invite_form,
        "role_form": role_form,
        "pending_invites": pending_invites,
        "pending_requests": pending_requests,
        "approved_memberships": approved_memberships,
        "pinned": pinned,
        "pinned_form": pinned_form,
    })


@login_required
@require_POST
def team_invite(request, team_id: int):
    team = _team_or_404(team_id)
    if not _is_team_admin(team, request.user):
        return HttpResponseForbidden("Not allowed")

    form = TeamInviteForm(request.POST)
    if not form.is_valid():
        messages.error(request, "入力が不正です。")
        return redirect("team_edit", team_id=team.id)

    username = form.cleaned_data["username"].strip()
    invitee = User.objects.filter(username=username).first()
    if not invitee:
        messages.error(request, "その username のユーザーが見つかりません。")
        return redirect("team_edit", team_id=team.id)

    m, created = TeamMembership.objects.get_or_create(team=team, user=invitee)
    if not created:
        if m.is_active and m.status in (MembershipStatus.APPROVED, MembershipStatus.INVITED, MembershipStatus.PENDING):
            messages.info(request, "そのユーザーは既に招待済み/申請中/参加済みです。")
            return redirect("team_edit", team_id=team.id)
        m.is_active = True

    m.status = MembershipStatus.INVITED
    m.role = MembershipRole.MEMBER
    m.invited_by = request.user
    m.save()

    messages.success(request, f"{invitee.username} を招待しました。")
    return redirect("team_edit", team_id=team.id)


@login_required
@require_POST
def team_join_request(request, team_id: int):
    """
    ✅ 参加申請（招待なしで申請）
    """
    team = _team_or_404(team_id)

    if not team.is_public:
        messages.error(request, "このチームは非公開のため申請できません。")
        return redirect("team_detail", team_id=team.id)

    if _is_team_member(team, request.user):
        messages.info(request, "すでに参加しています。")
        return redirect("team_detail", team_id=team.id)

    # 既存の membership を再利用
    m, _ = TeamMembership.objects.get_or_create(team=team, user=request.user)
    m.is_active = True
    m.status = MembershipStatus.PENDING
    m.role = MembershipRole.MEMBER
    m.invited_by = None
    m.save()

    messages.success(request, "参加申請を送信しました。")
    return redirect("team_detail", team_id=team.id)


@login_required
def my_team_invites(request):
    invites = (
        TeamMembership.objects
        .filter(user=request.user, is_active=True, status=MembershipStatus.INVITED, team__is_active=True)
        .select_related("team", "team__owner")
        .order_by("-created_at")
    )
    return render(request, "teams/my_invites.html", {"invites": invites})


@login_required
@require_POST
def invite_accept(request, membership_id: int):
    m = get_object_or_404(TeamMembership, id=membership_id, user=request.user, is_active=True)
    if m.team.is_active is False:
        raise Http404()

    m.status = MembershipStatus.APPROVED
    m.save(update_fields=["status", "updated_at"])
    messages.success(request, "招待を承認しました。")
    return redirect("team_detail", team_id=m.team_id)

@login_required
@require_POST
def invite_cancel(request, team_id: int, user_id: int):
    team = _team_or_404(team_id)
    if not _is_team_admin(team, request.user):
        return HttpResponseForbidden("Not allowed")

    m = get_object_or_404(
        TeamMembership,
        team=team,
        user_id=user_id,
        is_active=True,
        status=MembershipStatus.INVITED,
    )
    m.is_active = False
    m.status = MembershipStatus.REJECTED
    m.save(update_fields=["is_active", "status", "updated_at"])

    messages.success(request, "招待を取り消しました。")
    return redirect("team_detail", team_id=team.id)

@login_required
@require_POST
def invite_decline(request, membership_id: int):
    m = get_object_or_404(TeamMembership, id=membership_id, user=request.user, is_active=True)
    m.status = MembershipStatus.REJECTED
    m.is_active = False
    m.save(update_fields=["status", "is_active", "updated_at"])
    messages.info(request, "招待を辞退しました。")
    return redirect("my_team_invites")


@login_required
@require_POST
def request_approve(request, team_id: int, user_id: int):
    """
    ✅ 管理者が参加申請を承認
    """
    team = _team_or_404(team_id)
    if not _is_team_admin(team, request.user):
        return HttpResponseForbidden("Not allowed")

    m = get_object_or_404(TeamMembership, team=team, user_id=user_id, is_active=True, status=MembershipStatus.PENDING)
    m.status = MembershipStatus.APPROVED
    m.save(update_fields=["status", "updated_at"])
    messages.success(request, "申請を承認しました。")
    return redirect("team_edit", team_id=team.id)


@login_required
@require_POST
def request_reject(request, team_id: int, user_id: int):
    """
    ✅ 管理者が参加申請を却下（論理削除）
    """
    team = _team_or_404(team_id)
    if not _is_team_admin(team, request.user):
        return HttpResponseForbidden("Not allowed")

    m = get_object_or_404(TeamMembership, team=team, user_id=user_id, is_active=True, status=MembershipStatus.PENDING)
    m.status = MembershipStatus.REJECTED
    m.is_active = False
    m.save(update_fields=["status", "is_active", "updated_at"])
    messages.info(request, "申請を却下しました。")
    return redirect("team_edit", team_id=team.id)


@login_required
@require_POST
def role_toggle(request, team_id: int, user_id: int):
    """
    ✅ 管理者昇格/降格（ownerは固定）
    """
    team = _team_or_404(team_id)
    if not _is_team_admin(team, request.user):
        return HttpResponseForbidden("Not allowed")

    if user_id == team.owner_id:
        messages.info(request, "Owner の権限は変更できません。")
        return redirect("team_edit", team_id=team.id)

    m = get_object_or_404(TeamMembership, team=team, user_id=user_id, is_active=True, status=MembershipStatus.APPROVED)
    m.role = MembershipRole.ADMIN if m.role != MembershipRole.ADMIN else MembershipRole.MEMBER
    m.save(update_fields=["role", "updated_at"])
    messages.success(request, "権限を更新しました。")
    return redirect("team_edit", team_id=team.id)


@login_required
@require_POST
def pinned_add(request, team_id: int):
    """
    ✅ 代表車両追加（最大3）
    """
    team = _team_or_404(team_id)
    if not _is_team_admin(team, request.user):
        return HttpResponseForbidden("Not allowed")

    if TeamPinnedVehicle.objects.filter(team=team).count() >= 3:
        messages.error(request, "代表車両は最大3台までです。")
        return redirect("team_edit", team_id=team.id)

    form = TeamPinnedVehicleForm(request.POST, team=team, user=request.user)
    if not form.is_valid():
        messages.error(request, "入力が不正です。")
        return redirect("team_edit", team_id=team.id)

    obj = form.save(commit=False)
    obj.team = team
    obj.save()
    messages.success(request, "代表車両を追加しました。")
    return redirect("team_edit", team_id=team.id)


@login_required
@require_POST
def pinned_remove(request, team_id: int, pin_id: int):
    team = _team_or_404(team_id)
    if not _is_team_admin(team, request.user):
        return HttpResponseForbidden("Not allowed")

    pin = get_object_or_404(TeamPinnedVehicle, id=pin_id, team=team)
    pin.delete()
    messages.success(request, "代表車両を削除しました。")
    return redirect("team_edit", team_id=team.id)


@login_required
@require_POST
def team_member_remove(request, team_id: int, user_id: int):
    team = _team_or_404(team_id)
    if not _is_team_admin(team, request.user):
        return HttpResponseForbidden("Not allowed")

    if user_id == team.owner_id:
        messages.error(request, "作成者は削除できません。")
        return redirect("team_edit", team_id=team.id)

    m = get_object_or_404(TeamMembership, team=team, user_id=user_id, is_active=True)
    m.soft_delete()
    messages.success(request, "メンバーを削除しました（論理削除）。")
    return redirect("team_edit", team_id=team.id)


@login_required
def team_delete_confirm(request, team_id: int):
    team = _team_or_404(team_id)
    if team.owner_id != request.user.id:
        return HttpResponseForbidden("Not allowed")
    return render(request, "teams/team_delete_confirm.html", {"team": team})


@login_required
@require_POST
def team_delete(request, team_id: int):
    team = _team_or_404(team_id)
    if team.owner_id != request.user.id:
        return HttpResponseForbidden("Not allowed")

    team.is_active = False
    team.save(update_fields=["is_active", "updated_at"])

    messages.success(request, "チームを削除しました。")
    return redirect("team_list")

@login_required
def my_teams(request):
    # 参加中（承認済み）のチーム
    memberships = (
        TeamMembership.objects
        .filter(
            user=request.user,
            is_active=True,
            status=MembershipStatus.APPROVED,
            team__is_active=True,
        )
        .select_related("team", "team__owner")
        .order_by("-team__created_at")
    )

    member_teams = [m.team for m in memberships]

    # 自分が作成したチーム（論理削除除外）
    owned_teams = (
        Team.objects
        .filter(owner=request.user, is_active=True)
        .order_by("-created_at")
    )

    # 重複除去（ownedがmemberにも入ってるケース）
    member_team_ids = {t.id for t in member_teams}
    owned_only = [t for t in owned_teams if t.id not in member_team_ids]

    return render(request, "teams/my_teams.html", {
        "member_teams": member_teams,
        "owned_only": owned_only,
    })


@login_required
@require_POST
def team_invite_create(request, team_id: int):
    team = _team_or_404(team_id)

    if not _is_team_admin(team, request.user):
        return HttpResponseForbidden("Not allowed")

    username = request.POST.get("username", "").strip()
    if not username:
        messages.error(request, "ユーザー名を入力してください。")
        return redirect("team_detail", team_id=team.id)

    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        messages.error(request, "そのユーザーは存在しません。")
        return redirect("team_detail", team_id=team.id)

    # すでにメンバー or 招待中なら弾く
    if TeamMembership.objects.filter(team=team, user=user, is_active=True).exists():
        messages.info(request, "そのユーザーはすでにチームに関連しています。")
        return redirect("team_detail", team_id=team.id)

    TeamMembership.objects.create(
        team=team,
        user=user,
        role=MembershipRole.MEMBER,
        status=MembershipStatus.INVITED,
        invited_by=request.user,
    )

    messages.success(request, f"{user.username} さんを招待しました。")
    return redirect("team_detail", team_id=team.id)
