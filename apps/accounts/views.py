# apps/accounts/views.py

from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

from apps.interactions.models import Reaction, ReactionType
from apps.vehicles.models import UserVehicle
from apps.posts.models import Post
from apps.events.models import EventEntry  # ✅ 参加履歴用

from .forms import SignupForm, ProfileUpdateForm, UserUpdateForm
from .models import Profile
from django.core.paginator import Paginator


User = get_user_model()


# ----------------------------
# Auth
# ----------------------------
def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("vehicle_list")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})


# ----------------------------
# Simple pages
# ----------------------------
@login_required
def profile(request):
    return render(request, "accounts/profile.html")

# ----------------------------
# Account edit
# ----------------------------
@login_required
def account_edit(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)

        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
            messages.success(request, "アカウント情報を更新しました。")
            return redirect("account_edit")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, "accounts/account_edit.html", {
        "user_form": user_form,
        "profile_form": profile_form,
    })


# ----------------------------
# Public profile page
# ----------------------------
def profile_detail(request, username: str):
    """
    公開プロフィール:
    - 表示名/アイコン/地域/SNSリンク/バイク情報
    - Vehicles/Posts（最新12件）
    - Event entries（参加イベント・参加車両の履歴）
    """
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)

    # 非公開プロフィール（自分以外は見せない）
    if hasattr(profile, "is_public") and (not profile.is_public):
        if not (request.user.is_authenticated and request.user.id == user.id):
            raise Http404()

    # 表示名のフォールバック
    display_name = profile.display_name.strip() if profile.display_name else user.username

    # 車両：main_imageだけで軽く
    vehicles = (
        UserVehicle.objects
        .filter(owner=user)
        .select_related("model", "main_image")
        .order_by("-created_at")[:12]
    )

    # 投稿：main_imageだけで軽く
    posts = (
        Post.objects
        .filter(author=user)
        .select_related("main_image")
        .order_by("-created_at")[:12]
    )

    # ✅ イベント参加履歴（Entry）
    # EventEntry: event + vehicle をまとめて取得（vehicle.main_image を使う）
    entries = (
        EventEntry.objects
        .filter(vehicle__owner=user)
        .select_related(
            "event",
            "vehicle",
            "vehicle__model",
            "vehicle__main_image",
        )
        .order_by("-created_at")[:30]
    )

    # 参加イベント数 / エントリー数の簡易集計（任意で表示に使える）
    entry_count = EventEntry.objects.filter(vehicle__owner=user).count()
    event_count = (
        EventEntry.objects.filter(vehicle__owner=user)
        .values("event_id").distinct().count()
    )

    return render(request, "accounts/profile_detail.html", {
        "profile_user": user,
        "profile": profile,
        "display_name": display_name,
        "vehicles": vehicles,
        "posts": posts,
        "entries": entries,
        "entry_count": entry_count,
        "event_count": event_count,
        "is_me": request.user.is_authenticated and request.user.id == user.id,
    })


def _get_public_profile_or_404(request, username: str):
    user = get_object_or_404(User, username=username)
    profile, _ = Profile.objects.get_or_create(user=user)

    if hasattr(profile, "is_public") and (not profile.is_public):
        if not (request.user.is_authenticated and request.user.id == user.id):
            raise Http404()

    display_name = profile.display_name.strip() if profile.display_name else user.username
    is_me = request.user.is_authenticated and request.user.id == user.id
    return user, profile, display_name, is_me


def profile_vehicles(request, username: str):
    user, profile, display_name, is_me = _get_public_profile_or_404(request, username)

    qs = (
        UserVehicle.objects
        .filter(owner=user)
        .select_related("model", "main_image")
        .order_by("-created_at")
    )

    paginator = Paginator(qs, 24)  # 1ページ24件
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "accounts/profile_vehicles.html", {
        "profile_user": user,
        "profile": profile,
        "display_name": display_name,
        "is_me": is_me,
        "page_obj": page_obj,
    })


def profile_posts(request, username: str):
    user, profile, display_name, is_me = _get_public_profile_or_404(request, username)

    qs = (
        Post.objects
        .filter(author=user)
        .select_related("main_image")
        .order_by("-created_at")
    )

    paginator = Paginator(qs, 24)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "accounts/profile_posts.html", {
        "profile_user": user,
        "profile": profile,
        "display_name": display_name,
        "is_me": is_me,
        "page_obj": page_obj,
    })


def profile_entries(request, username: str):
    user, profile, display_name, is_me = _get_public_profile_or_404(request, username)

    qs = (
        EventEntry.objects
        .filter(vehicle__owner=user)
        .select_related("event", "vehicle", "vehicle__model", "vehicle__main_image")
        .order_by("-created_at")
    )

    paginator = Paginator(qs, 30)  # entriesは30件/ページでも見やすい
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "accounts/profile_entries.html", {
        "profile_user": user,
        "profile": profile,
        "display_name": display_name,
        "is_me": is_me,
        "page_obj": page_obj,
    })
