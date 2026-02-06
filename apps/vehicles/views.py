# 標準ライブラリ
import json

# Django
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

# アプリ内
from .forms import VehicleForm
from .models import UserVehicle, VehicleImage
from django.db.models import Prefetch


def _rebuild_main_image(vehicle: UserVehicle) -> None:
    """
    vehicle.main_image を必ず整合させる。
    優先順位:
      1) is_main=True があればそれ
      2) なければ sort_order が最小の先頭
      3) 画像が無ければ None
    """
    main = (
        VehicleImage.objects.filter(vehicle=vehicle)
        .order_by("-is_main", "sort_order", "id")
        .first()
    )
    vehicle.main_image = main
    vehicle.save(update_fields=["main_image"])


@login_required
def vehicle_create(request):
    if request.method == "POST":
        form = VehicleForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                vehicle = form.save(commit=False)
                vehicle.owner = request.user
                vehicle.save()

                files = form.cleaned_data["images"]  # list が返る
                created = []
                for i, f in enumerate(files[:10]):
                    img = VehicleImage.objects.create(
                        vehicle=vehicle,
                        image=f,
                        sort_order=i,
                        is_main=False,
                    )
                    created.append(img)

                # 最初の1枚を main に（ラジオ未指定のため）
                if created:
                    created[0].is_main = True
                    created[0].save(update_fields=["is_main"])
                    vehicle.main_image = created[0]
                    vehicle.save(update_fields=["main_image"])

            messages.success(request, "車両を作成しました。")
            return redirect("vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleForm()

    return render(request, "vehicles/vehicle_form.html", {"form": form})


def vehicle_list(request):
    # 一覧は main_image だけで十分（最軽量）
    vehicles = (
        UserVehicle.objects
        .select_related("model", "owner", "main_image")
        .order_by("-created_at")
    )
    return render(request, "vehicles/vehicle_list.html", {"vehicles": vehicles})


def vehicle_detail(request, pk: int):
    image_qs = VehicleImage.objects.order_by("-is_main", "sort_order", "id")

    vehicle = get_object_or_404(
        UserVehicle.objects
        .select_related("model", "owner", "main_image")
        .prefetch_related(Prefetch("images", queryset=image_qs)),
        pk=pk
    )
    return render(request, "vehicles/vehicle_detail.html", {"vehicle": vehicle})


@login_required
def vehicle_edit(request, pk: int):
    vehicle = get_object_or_404(
        UserVehicle.objects.select_related("model", "owner", "main_image").prefetch_related("images"),
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

                for i, f in enumerate(files[:remaining]):
                    VehicleImage.objects.create(
                        vehicle=vehicle,
                        image=f,
                        sort_order=current_count + i,
                        is_main=False,  # 後で先頭だけ True にする
                    )

                # 3) 並び順を反映（hiddenの image_order_json を読む）
                order_json = request.POST.get("image_order_json", "")
                if order_json:
                    try:
                        ordered_ids = json.loads(order_json)
                        if isinstance(ordered_ids, list):
                            valid_ids = list(
                                VehicleImage.objects.filter(vehicle=vehicle, id__in=ordered_ids)
                                .values_list("id", flat=True)
                            )
                            valid_set = set(valid_ids)

                            sort = 0
                            for img_id in ordered_ids:
                                if img_id in valid_set:
                                    VehicleImage.objects.filter(vehicle=vehicle, id=img_id).update(sort_order=sort)
                                    sort += 1

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
                        pass

                # 4) 先頭（sort_order最小）を必ず main にする
                first = VehicleImage.objects.filter(vehicle=vehicle).order_by("sort_order", "id").first()

                # is_main を使っている箇所が残っていても整合するように、先頭だけ True に統一
                VehicleImage.objects.filter(vehicle=vehicle).update(is_main=False)
                if first:
                    VehicleImage.objects.filter(vehicle=vehicle, id=first.id).update(is_main=True)

                # vehicle.main_image も先頭に同期
                vehicle.refresh_from_db()
                vehicle.main_image = first
                vehicle.save(update_fields=["main_image"])

            messages.success(request, "車両情報を更新しました。")
            return redirect("vehicle_detail", pk=vehicle.pk)
    else:
        form = VehicleForm(instance=vehicle)

    vehicle = UserVehicle.objects.select_related("model", "owner", "main_image").prefetch_related("images").get(pk=vehicle.pk)

    return render(request, "vehicles/vehicle_edit.html", {
        "form": form,
        "vehicle": vehicle,
    })