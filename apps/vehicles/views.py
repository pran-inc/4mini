from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render

from apps.interactions.models import Reaction, ReactionType
from .forms import VehicleForm
from .models import UserVehicle, VehicleImage

@login_required
def vehicle_create(request):
    if request.method == "POST":
        print("FILES keys:", request.FILES.keys())
        print("images:", request.FILES.getlist("images"))

        form = VehicleForm(request.POST, request.FILES)  # ←ここが超重要

        print("form errors:", form.errors)

        if form.is_valid():
            vehicle = form.save(commit=False)
            vehicle.owner = request.user
            vehicle.save()

            files = form.cleaned_data["images"]  # list が返る
            for i, f in enumerate(files[:10]):
                VehicleImage.objects.create(vehicle=vehicle, image=f, sort_order=i)

            return redirect("vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleForm()

    return render(request, "vehicles/vehicle_form.html", {"form": form})



def vehicle_list(request):
    vehicles = (
        UserVehicle.objects.select_related("model", "owner")
        .prefetch_related("images")
        .order_by("-created_at")
    )
    return render(request, "vehicles/vehicle_list.html", {"vehicles": vehicles})


def vehicle_detail(request, pk: int):
    vehicle = get_object_or_404(
        UserVehicle.objects.select_related("model", "owner").prefetch_related("images"),
        pk=pk,
    )

    # いいね / お気に入り数
    from django.contrib.contenttypes.models import ContentType
    ct = ContentType.objects.get_for_model(UserVehicle)

    like_count = Reaction.objects.filter(
        reaction_type=ReactionType.LIKE, content_type=ct, object_id=vehicle.id
    ).count()
    fav_count = Reaction.objects.filter(
        reaction_type=ReactionType.FAVORITE, content_type=ct, object_id=vehicle.id
    ).count()

    user_like = False
    user_fav = False
    if request.user.is_authenticated:
        user_like = Reaction.objects.filter(
            user=request.user, reaction_type=ReactionType.LIKE, content_type=ct, object_id=vehicle.id
        ).exists()
        user_fav = Reaction.objects.filter(
            user=request.user, reaction_type=ReactionType.FAVORITE, content_type=ct, object_id=vehicle.id
        ).exists()

    ctx = {
        "vehicle": vehicle,
        "like_count": like_count,
        "fav_count": fav_count,
        "user_like": user_like,
        "user_fav": user_fav,
        "target": {"app_label": ct.app_label, "model": ct.model, "object_id": vehicle.id},
    }
    return render(request, "vehicles/vehicle_detail.html", ctx)
