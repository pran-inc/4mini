# 標準ライブラリ
import json

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Prefetch
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

# アプリ内
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
    image_qs = VehicleImage.objects.order_by("-is_main", "sort_order", "id")

    vehicles = (
        UserVehicle.objects
        .select_related("model", "owner")
        .prefetch_related(Prefetch("images", queryset=image_qs))
        .order_by("-created_at")
    )
    return render(request, "vehicles/vehicle_list.html", {"vehicles": vehicles})



# def vehicle_detail(request, pk: int):
#     vehicle = get_object_or_404(
#         UserVehicle.objects.select_related("model", "owner").prefetch_related("images"),
#         pk=pk,
#     )

#     # いいね / お気に入り数
#     from django.contrib.contenttypes.models import ContentType
#     ct = ContentType.objects.get_for_model(UserVehicle)

#     like_count = Reaction.objects.filter(
#         reaction_type=ReactionType.LIKE, content_type=ct, object_id=vehicle.id
#     ).count()
#     fav_count = Reaction.objects.filter(
#         reaction_type=ReactionType.FAVORITE, content_type=ct, object_id=vehicle.id
#     ).count()

#     user_like = False
#     user_fav = False
#     if request.user.is_authenticated:
#         user_like = Reaction.objects.filter(
#             user=request.user, reaction_type=ReactionType.LIKE, content_type=ct, object_id=vehicle.id
#         ).exists()
#         user_fav = Reaction.objects.filter(
#             user=request.user, reaction_type=ReactionType.FAVORITE, content_type=ct, object_id=vehicle.id
#         ).exists()

#     ctx = {
#         "vehicle": vehicle,
#         "like_count": like_count,
#         "fav_count": fav_count,
#         "user_like": user_like,
#         "user_fav": user_fav,
#         "target": {"app_label": ct.app_label, "model": ct.model, "object_id": vehicle.id},
#     }
#     return render(request, "vehicles/vehicle_detail.html", ctx)

def vehicle_detail(request, pk: int):
    image_qs = VehicleImage.objects.order_by("-is_main", "sort_order", "id")

    vehicle = get_object_or_404(
        UserVehicle.objects
        .select_related("model", "owner")
        .prefetch_related(Prefetch("images", queryset=image_qs)),
        pk=pk
    )
    return render(request, "vehicles/vehicle_detail.html", {"vehicle": vehicle})

@login_required
def vehicle_edit(request, pk: int):
    vehicle = get_object_or_404(
        UserVehicle.objects.select_related("model", "owner").prefetch_related("images"),
        pk=pk
    )
    if vehicle.owner_id != request.user.id:
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        form = VehicleForm(request.POST, request.FILES, instance=vehicle)
        if form.is_valid():
            with transaction.atomic():
                vehicle = form.save()

                # 1) 既存画像の削除
                delete_ids = request.POST.getlist("delete_image_ids")
                if delete_ids:
                    VehicleImage.objects.filter(vehicle=vehicle, id__in=delete_ids).delete()

                # 2) 追加画像（最大10枚：既存枚数を見て残りだけ追加）
                current_count = VehicleImage.objects.filter(vehicle=vehicle).count()
                files = form.cleaned_data["images"]  # list[UploadedFile]
                remaining = max(0, 10 - current_count)

                # 追加した画像の sort_order は末尾に
                for i, f in enumerate(files[:remaining]):
                    VehicleImage.objects.create(
                        vehicle=vehicle,
                        image=f,
                        sort_order=current_count + i,
                        is_main=False,
                    )

                # 3) 並び順を反映（hiddenの image_order_json を読む）
                order_json = request.POST.get("image_order_json", "")
                if order_json:
                    try:
                        ordered_ids = json.loads(order_json)
                        if isinstance(ordered_ids, list):
                            # vehicleに属する画像だけに限定
                            valid_ids = list(
                                VehicleImage.objects.filter(vehicle=vehicle, id__in=ordered_ids)
                                .values_list("id", flat=True)
                            )
                            valid_set = set(valid_ids)

                            # ordered_ids の順に sort_order を付け直し
                            sort = 0
                            for img_id in ordered_ids:
                                if img_id in valid_set:
                                    VehicleImage.objects.filter(vehicle=vehicle, id=img_id).update(sort_order=sort)
                                    sort += 1

                            # もし order_json に含まれていない画像があれば末尾に回す
                            leftovers = (
                                VehicleImage.objects.filter(vehicle=vehicle)
                                .exclude(id__in=valid_set)
                                .order_by("sort_order", "id")
                                .values_list("id", flat=True)
                            )
                            for img_id in leftovers:
                                VehicleImage.objects.filter(vehicle=vehicle, id=img_id).update(sort_order=sort)
                                sort += 1
                    except Exception:
                        # 壊れたJSONでも保存自体は続行（UX優先）
                        pass

                # 4) メイン画像反映（radioの main_image_id）
                main_id = request.POST.get("main_image_id", "")
                if main_id:
                    try:
                        main_id_int = int(main_id)
                        # まず全てOFF
                        VehicleImage.objects.filter(vehicle=vehicle).update(is_main=False)
                        # vehicleに属するものだけON
                        VehicleImage.objects.filter(vehicle=vehicle, id=main_id_int).update(is_main=True)
                    except ValueError:
                        pass
                else:
                    # 未指定なら、is_mainが存在しない場合だけ先頭を自動でmainにする（任意）
                    if not VehicleImage.objects.filter(vehicle=vehicle, is_main=True).exists():
                        first = VehicleImage.objects.filter(vehicle=vehicle).order_by("sort_order", "id").first()
                        if first:
                            VehicleImage.objects.filter(vehicle=vehicle).update(is_main=False)
                            first.is_main = True
                            first.save(update_fields=["is_main"])

            messages.success(request, "車両情報を更新しました。")
            return redirect("vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleForm(instance=vehicle)

    # 最新状態で渡す（削除/並び替え後が反映される）
    vehicle = UserVehicle.objects.select_related("model", "owner").prefetch_related("images").get(pk=vehicle.pk)

    return render(request, "vehicles/vehicle_edit.html", {
        "form": form,
        "vehicle": vehicle,
    })