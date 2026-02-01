from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from apps.vehicles.models import UserVehicle
from .forms import EventForm
from .models import Event, EventEntry, EventVote
from django.http import HttpResponseForbidden
from .models import Award  # 追加
from .forms import AwardForm  # 追加
from django.db.models import Prefetch
from apps.vehicles.models import VehicleImage
from django.db.models import Count, Prefetch
from apps.vehicles.models import VehicleImage

def event_list(request):
    events = Event.objects.filter(is_published=True).order_by("-created_at")
    return render(request, "events/event_list.html", {"events": events})


@login_required
def event_create(request):
    if request.method == "POST":
        form = EventForm(request.POST, request.FILES)  # ← request.FILES を追加
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, "イベントを作成しました。")
            return redirect("event_detail", event_id=event.id)
    else:
        form = EventForm()
    return render(request, "events/event_form.html", {"form": form})


def event_detail(request, event_id: int):
    event = get_object_or_404(Event.objects.select_related("organizer"), id=event_id)

    # エントリー一覧（投票数でランキング表示）
    entries = (
        EventEntry.objects.filter(event=event)
        .select_related("vehicle", "vehicle__model", "vehicle__owner")
        .prefetch_related("vehicle__images")
        .annotate(vote_count=Count("votes"))
        .order_by("-vote_count", "-created_at")
    )

    # ログイン中ユーザーの投票済みを把握してボタン表示に使う
    voted_entry_ids = set()
    if request.user.is_authenticated:
        voted_entry_ids = set(
            EventVote.objects.filter(event=event, user=request.user).values_list("entry_id", flat=True)
        )

    return render(request, "events/event_detail.html", {
        "event": event,
        "entries": entries,
        "voted_entry_ids": voted_entry_ids,
    })

@login_required
def event_edit(request, event_id: int):
    event = get_object_or_404(Event, id=event_id)

    if event.organizer_id != request.user.id:
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "イベントを更新しました。")
            return redirect("event_detail", event_id=event.id)
    else:
        form = EventForm(instance=event)

    return render(request, "events/event_form.html", {"form": form})

def event_gallery(request, event_id: int):
    event = get_object_or_404(Event.objects.select_related("organizer"), id=event_id)

    image_qs = VehicleImage.objects.order_by("-is_main", "sort_order", "id")

    entries = (
        EventEntry.objects.filter(event=event)
        .select_related("vehicle", "vehicle__model", "vehicle__owner")
        .prefetch_related(Prefetch("vehicle__images", queryset=image_qs))
        .annotate(vote_count=Count("votes"))
        .order_by("-vote_count", "-created_at")
    )

    voted_entry_ids = set()
    if request.user.is_authenticated:
        voted_entry_ids = set(
            EventVote.objects.filter(event=event, user=request.user).values_list("entry_id", flat=True)
        )

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

    # 自分の愛車だけ選べる
    my_vehicles = (
        UserVehicle.objects.filter(owner=request.user)
        .select_related("model")
        .prefetch_related("images")
        .order_by("-created_at")
    )

    if request.method == "POST":
        vehicle_id = request.POST.get("vehicle_id")
        if not vehicle_id:
            messages.error(request, "エントリーする愛車を選んでください。")
            return redirect("event_entry_create", event_id=event.id)

        vehicle = get_object_or_404(UserVehicle, id=vehicle_id, owner=request.user)

        try:
            EventEntry.objects.create(event=event, vehicle=vehicle)
            messages.success(request, "イベントにエントリーしました。")
            return redirect("event_detail", event_id=event.id)
        except IntegrityError:
            messages.error(request, "その愛車はすでにこのイベントにエントリー済みです。")
            return redirect("event_detail", event_id=event.id)

    return render(request, "events/event_entry_form.html", {"event": event, "my_vehicles": my_vehicles})


@login_required
def vote_toggle(request, event_id: int, entry_id: int):
    """
    クリックで投票ON/OFF（トグル）
    ※投票を「取り消し不可」にしたい場合はOFF処理を消すだけ
    """
    event = get_object_or_404(Event, id=event_id)
    entry = get_object_or_404(EventEntry, id=entry_id, event=event)

    # イベントがアクティブじゃなければ投票不可（任意）
    if not event.is_active:
        messages.error(request, "このイベントは投票期間外です。")
        return redirect("event_detail", event_id=event.id)

    # 自分のエントリーに投票禁止（任意）
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
            # ほぼ起きないが念のため
            messages.error(request, "投票に失敗しました（重複）。")

    return redirect("event_detail", event_id=event.id)



def _organizer_only(request, event: Event):
    if not request.user.is_authenticated:
        return False
    return event.organizer_id == request.user.id


@login_required
def event_awards_manage(request, event_id: int):
    event = get_object_or_404(Event, id=event_id)

    if not _organizer_only(request, event):
        return HttpResponseForbidden("Not allowed")

    awards = Award.objects.filter(event=event).select_related("winner_entry", "winner_entry__vehicle", "winner_entry__vehicle__model")
    return render(request, "events/awards_manage.html", {"event": event, "awards": awards})


@login_required
def award_create(request, event_id: int):
    event = get_object_or_404(Event, id=event_id)

    if not _organizer_only(request, event):
        return HttpResponseForbidden("Not allowed")

    # winner_entry の選択肢をこのイベントのエントリーに限定
    form = AwardForm(request.POST or None)
    form.fields["winner_entry"].queryset = EventEntry.objects.filter(event=event).select_related("vehicle", "vehicle__model")

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
    form.fields["winner_entry"].queryset = EventEntry.objects.filter(event=event).select_related("vehicle", "vehicle__model")

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

    # 公開条件:
    # - organizer はいつでも見れる
    # - 一般ユーザーは「投票終了後」かつ「winners_public=True」のときだけ
    if not is_organizer:
        if event.is_active:
            return render(request, "events/winners_not_ready.html", {"event": event}, status=403)
        if not event.winners_public:
            return render(request, "events/winners_not_ready.html", {"event": event}, status=403)

    entries = (
        EventEntry.objects.filter(event=event)
        .select_related("vehicle", "vehicle__model", "vehicle__owner")
        .prefetch_related("vehicle__images")
        .annotate(vote_count=Count("votes"))
        .order_by("-vote_count", "-created_at")
    )
    top3 = list(entries[:3])

    awards = (
        event.awards.all()
        .select_related("winner_entry", "winner_entry__vehicle", "winner_entry__vehicle__model")
        .prefetch_related("winner_entry__vehicle__images")
    )

    return render(request, "events/event_winners.html", {
        "event": event,
        "awards": awards,
        "top3": top3,
        "entries": entries,
        "is_organizer": is_organizer,
    })


