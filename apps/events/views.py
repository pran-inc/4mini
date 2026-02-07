# apps/events/views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.db.models import Count
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.vehicles.models import UserVehicle

from .forms import EventForm, AwardForm
from .models import Event, EventEntry, EventVote, Award
from apps.teams.models import TeamMembership, MembershipStatus, MembershipRole


def event_list(request):
    events = Event.objects.filter(is_published=True).order_by("-created_at")
    return render(request, "events/event_list.html", {"events": events})


def event_create(request):
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, user=request.user)  # ✅ user渡す
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, "イベントを作成しました。")
            return redirect("event_detail", event_id=event.id)
    else:
        form = EventForm(user=request.user)  # ✅ user渡す
    return render(request, "events/event_form.html", {"form": form})


def _entries_with_votes(event: Event):
    """
    event_detail / event_gallery / winners などで共通に使える queryset
    main_image 前提なので images の prefetch は不要
    """
    return (
        EventEntry.objects.filter(event=event)
        .select_related("vehicle", "vehicle__model", "vehicle__owner", "vehicle__main_image")
        .annotate(vote_count=Count("votes"))
        .order_by("-vote_count", "-created_at")
    )


def _voted_entry_ids(event: Event, user):
    if not user.is_authenticated:
        return set()
    return set(
        EventVote.objects.filter(event=event, user=user).values_list("entry_id", flat=True)
    )


def event_detail(request, event_id: int):
    event = get_object_or_404(Event.objects.select_related("organizer"), id=event_id)

    entries = _entries_with_votes(event)
    voted_entry_ids = _voted_entry_ids(event, request.user)

    return render(request, "events/event_detail.html", {
        "event": event,
        "entries": entries,
        "voted_entry_ids": voted_entry_ids,
    })


def _can_manage_event(user, event) -> bool:
    if not user.is_authenticated:
        return False

    # 個人主催なら従来通り
    if event.organizer_id == user.id:
        return True

    # チーム主催なら、そのチームのadminならOK
    if event.organizer_team_id:
        return TeamMembership.objects.filter(
            team_id=event.organizer_team_id,
            user=user,
            is_active=True,
            status=MembershipStatus.APPROVED,
            role=MembershipRole.ADMIN,
        ).exists()

    return False

@login_required
def event_edit(request, event_id: int):
    event = get_object_or_404(Event, id=event_id)

    if not _can_manage_event(request.user, event):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event, user=request.user)  # ✅ user渡す
        if form.is_valid():
            form.save()
            messages.success(request, "イベントを更新しました。")
            return redirect("event_detail", event_id=event.id)
    else:
        form = EventForm(instance=event, user=request.user)  # ✅ user渡す

    return render(request, "events/event_form.html", {"form": form})



def event_gallery(request, event_id: int):
    event = get_object_or_404(Event.objects.select_related("organizer"), id=event_id)

    entries = _entries_with_votes(event)
    voted_entry_ids = _voted_entry_ids(event, request.user)

    return render(request, "events/event_gallery.html", {
        "event": event,
        "entries": entries,
        "voted_entry_ids": voted_entry_ids,
    })



@login_required
def event_entry_create(request, event_id: int):
    event = get_object_or_404(Event, id=event_id)

    if not event.is_active:
        messages.error(request, "このイベントは期間外のためエントリーできません。")
        return redirect("event_detail", event_id=event.id)

    my_vehicles_qs = (
        UserVehicle.objects
        .filter(owner=request.user)
        .select_related("model", "main_image")
        .order_by("-created_at")
    )

    entered_vehicle_ids = set(
        EventEntry.objects.filter(event=event, vehicle__owner=request.user)
        .values_list("vehicle_id", flat=True)
    )

    # ✅ 2つに分割（上に「エントリー済み」、下に「未エントリー」）
    entered_vehicles = [v for v in my_vehicles_qs if v.id in entered_vehicle_ids]
    available_vehicles = [v for v in my_vehicles_qs if v.id not in entered_vehicle_ids]

    if request.method == "POST":
        vehicle_id = request.POST.get("vehicle_id")
        if not vehicle_id:
            messages.error(request, "エントリーする愛車を選んでください。")
            return render(request, "events/event_entry_form.html", {
                "event": event,
                "entered_vehicles": entered_vehicles,
                "available_vehicles": available_vehicles,
                "entered_vehicle_ids": entered_vehicle_ids,
            })

        try:
            vehicle_id_int = int(vehicle_id)
        except (TypeError, ValueError):
            messages.error(request, "車両の選択が不正です。")
            return redirect("event_entry_create", event_id=event.id)

        # 改ざん対策：すでにエントリー済みなら弾く
        if vehicle_id_int in entered_vehicle_ids:
            messages.error(request, "その愛車はすでにこのイベントにエントリー済みです。")
            return redirect("event_detail", event_id=event.id)

        vehicle = get_object_or_404(UserVehicle, id=vehicle_id_int, owner=request.user)
        return redirect("event_entry_confirm", event_id=event.id, vehicle_id=vehicle.id)

    return render(request, "events/event_entry_form.html", {
        "event": event,
        "entered_vehicles": entered_vehicles,
        "available_vehicles": available_vehicles,
        "entered_vehicle_ids": entered_vehicle_ids,
    })



@require_POST
@login_required
def vote_toggle(request, event_id: int, entry_id: int):
    event = get_object_or_404(Event, id=event_id)
    entry = get_object_or_404(EventEntry, id=entry_id, event=event)

    if not event.is_active:
        messages.error(request, "このイベントは投票期間外です。")
        return redirect("event_detail", event_id=event.id)

    if entry.vehicle.owner_id == request.user.id:
        messages.error(request, "自分の車両には投票できません。")
        return redirect("event_detail", event_id=event.id)

    obj = EventVote.objects.filter(event=event, entry=entry, user=request.user).first()
    if obj:
        obj.delete()
        messages.info(request, "投票を取り消しました。")
    else:
        try:
            EventVote.objects.create(event=event, entry=entry, user=request.user)
            messages.success(request, "投票しました！")
        except IntegrityError:
            messages.error(request, "投票に失敗しました（重複）。")

    return redirect("event_detail", event_id=event.id)


def _organizer_only(request, event: Event) -> bool:
    return request.user.is_authenticated and (event.organizer_id == request.user.id)


@login_required
def event_awards_manage(request, event_id: int):
    event = get_object_or_404(Event, id=event_id)

    if not _organizer_only(request, event):
        return HttpResponseForbidden("Not allowed")

    awards = (
        Award.objects.filter(event=event)
        .select_related(
            "winner_entry",
            "winner_entry__vehicle",
            "winner_entry__vehicle__model",
            "winner_entry__vehicle__main_image",
        )
        .order_by("id")
    )

    return render(request, "events/awards_manage.html", {"event": event, "awards": awards})


@login_required
def award_create(request, event_id: int):
    event = get_object_or_404(Event, id=event_id)

    if not _organizer_only(request, event):
        return HttpResponseForbidden("Not allowed")

    form = AwardForm(request.POST or None)
    form.fields["winner_entry"].queryset = (
        EventEntry.objects.filter(event=event)
        .select_related("vehicle", "vehicle__model", "vehicle__main_image")
        .order_by("-created_at")
    )

    if request.method == "POST" and form.is_valid():
        award = form.save(commit=False)
        award.event = event
        award.save()
        messages.success(request, "Award created.")
        return redirect("event_awards_manage", event_id=event.id)

    return render(request, "events/award_form.html", {"event": event, "form": form, "mode": "create"})


@login_required
def award_edit(request, event_id: int, award_id: int):
    event = get_object_or_404(Event, id=event_id)
    award = get_object_or_404(Award, id=award_id, event=event)

    if not _organizer_only(request, event):
        return HttpResponseForbidden("Not allowed")

    form = AwardForm(request.POST or None, instance=award)
    form.fields["winner_entry"].queryset = (
        EventEntry.objects.filter(event=event)
        .select_related("vehicle", "vehicle__model", "vehicle__main_image")
        .order_by("-created_at")
    )

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Award updated.")
        return redirect("event_awards_manage", event_id=event.id)

    return render(request, "events/award_form.html", {"event": event, "form": form, "mode": "edit"})


@login_required
def award_delete(request, event_id: int, award_id: int):
    event = get_object_or_404(Event, id=event_id)
    award = get_object_or_404(Award, id=award_id, event=event)

    if not _organizer_only(request, event):
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        award.delete()
        messages.success(request, "Award deleted.")
        return redirect("event_awards_manage", event_id=event.id)

    return render(request, "events/award_delete_confirm.html", {"event": event, "award": award})


def event_winners(request, event_id: int):
    event = get_object_or_404(
        Event.objects.select_related("organizer").prefetch_related("awards"),
        id=event_id
    )

    is_organizer = request.user.is_authenticated and request.user.id == event.organizer_id

    if not is_organizer:
        if event.is_active:
            return render(request, "events/winners_not_ready.html", {"event": event}, status=403)
        if not event.winners_public:
            return render(request, "events/winners_not_ready.html", {"event": event}, status=403)

    entries = _entries_with_votes(event)
    top3 = list(entries[:3])

    awards = (
        event.awards.all()
        .select_related(
            "winner_entry",
            "winner_entry__vehicle",
            "winner_entry__vehicle__model",
            "winner_entry__vehicle__main_image",
        )
        .order_by("id")
    )

    return render(request, "events/event_winners.html", {
        "event": event,
        "awards": awards,
        "top3": top3,
        "entries": entries,
        "is_organizer": is_organizer,
    })



@login_required
def event_entry_confirm(request, event_id: int, vehicle_id: int):
    event = get_object_or_404(Event, id=event_id)

    if not event.is_active:
        messages.error(request, "このイベントは期間外のためエントリーできません。")
        return redirect("event_detail", event_id=event.id)

    vehicle = get_object_or_404(
        UserVehicle.objects.select_related("model", "main_image"),
        id=vehicle_id,
        owner=request.user
    )

    # ✅ 同一車両がすでにエントリー済みなら confirm URL 直打ちでも弾く
    if EventEntry.objects.filter(event=event, vehicle=vehicle).exists():
        messages.info(request, "その愛車はすでにこのイベントにエントリー済みです。")
        return redirect("event_detail", event_id=event.id)

    if request.method == "POST":
        if request.POST.get("action") == "confirm":
            try:
                EventEntry.objects.create(event=event, vehicle=vehicle)
                messages.success(request, "イベントにエントリーしました。")
                return redirect("event_detail", event_id=event.id)
            except IntegrityError:
                messages.error(request, "その愛車はすでにこのイベントにエントリー済みです。")
                return redirect("event_detail", event_id=event.id)

        return redirect("event_entry_create", event_id=event.id)

    return render(request, "events/event_entry_confirm.html", {"event": event, "vehicle": vehicle})
