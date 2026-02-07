# apps/vehicles/views.py

import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST

from .forms import VehiclePartForm, VehicleQuickForm, VehicleDetailForm
from .models import Part, UserVehicle, VehicleImage, VehiclePart
from .models import sync_vehicle_main_image
from apps.common.utils import delete_queryset_with_files

def _delete_image_files(obj) -> None:
    """
    obj.image / obj.thumb が ImageField の場合に、ストレージ上のファイルも削除する
    """
    for attr in ("thumb", "image"):
        f = getattr(obj, attr, None)
        if not f:
            continue
        delete = getattr(f, "delete", None)
        if callable(delete):
            try:
                f.delete(save=False)
            except Exception:
                pass


# ----------------------------
# helper: sort_order をDBに反映
# ----------------------------
def _apply_image_order(vehicle: UserVehicle, order_json: str) -> None:
    if not order_json:
        return
    try:
        ordered_ids = json.loads(order_json)
        if not isinstance(ordered_ids, list):
            return
    except Exception:
        return

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


# ----------------------------
# Vehicle: quick create / confirm / list / detail / edit
# ----------------------------
@login_required
def vehicle_create_quick(request):
    """
    Step1: model/title/images だけ登録
    保存できたら confirm へ
    """
    if request.method == "POST":
        form = VehicleQuickForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                vehicle = form.save(commit=False)
                vehicle.owner = request.user
                vehicle.save()

                files = form.cleaned_data.get("images", [])
                for i, f in enumerate(files[:10]):
                    VehicleImage.objects.create(vehicle=vehicle, image=f, sort_order=i)

                # 左端＝メイン（画像が無くてもOK）
                sync_vehicle_main_image(vehicle.id)

            return redirect("vehicle_create_confirm", pk=vehicle.pk)
    else:
        form = VehicleQuickForm()

    return render(request, "vehicles/vehicle_quick_form.html", {"form": form})




@login_required
def vehicle_create_confirm(request, pk: int):
    vehicle = get_object_or_404(
        UserVehicle.objects.select_related("model", "main_image"),
        pk=pk,
        owner=request.user
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "confirm":
            messages.success(request, "車両を登録しました。")
            return redirect("vehicle_detail", pk=vehicle.pk)

        if action == "edit":
            return redirect("vehicle_edit", pk=vehicle.pk)

    if action == "discard":
        with transaction.atomic():
            delete_queryset_with_files(
                VehicleImage.objects.filter(vehicle=vehicle),
                field_names=("thumb", "image")
            )
            vehicle.delete()

        messages.info(request, "登録を破棄しました。")
        return redirect("vehicle_list")

    return render(request, "vehicles/vehicle_create_confirm.html", {"vehicle": vehicle})



def vehicle_list(request):
    vehicles = (
        UserVehicle.objects
        .select_related("model", "owner", "main_image")
        .order_by("-created_at")
    )
    return render(request, "vehicles/vehicle_list.html", {"vehicles": vehicles})


def vehicle_detail(request, pk: int):
    image_qs = VehicleImage.objects.order_by("sort_order", "id")

    vehicle = get_object_or_404(
        UserVehicle.objects
        .select_related("model", "owner", "main_image")
        .prefetch_related(Prefetch("images", queryset=image_qs)),
        pk=pk
    )

    parts = (
        VehiclePart.objects.filter(vehicle=vehicle)
        .select_related("part", "part__category", "maker")
        .order_by("part__category__sort_order", "part__name", "id")
    )

    return render(request, "vehicles/vehicle_detail.html", {
        "vehicle": vehicle,
        "parts": parts,
    })


@login_required
def vehicle_edit(request, pk: int):
    """
    vehicle_edit で全部やる
    - 車両詳細（VehicleDetailForm）
    - 画像（追加/削除/並べ替え）
    - パーツ（AJAXで追加/削除）
    """
    image_qs = VehicleImage.objects.order_by("sort_order", "id")

    vehicle = get_object_or_404(
        UserVehicle.objects
        .select_related("model", "owner", "main_image")
        .prefetch_related(Prefetch("images", queryset=image_qs)),
        pk=pk
    )

    if vehicle.owner_id != request.user.id:
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        form = VehicleDetailForm(request.POST, request.FILES, instance=vehicle)
        if form.is_valid():
            with transaction.atomic():
                form.save()

                # 1) 画像削除
                delete_ids = request.POST.getlist("delete_image_ids")
                if delete_ids:
                    VehicleImage.objects.filter(vehicle=vehicle, id__in=delete_ids).delete()

                # 2) 画像追加（最大10枚）
                current_count = VehicleImage.objects.filter(vehicle=vehicle).count()
                remaining = max(0, 10 - current_count)

                files = form.cleaned_data.get("images", [])
                for i, f in enumerate(files[:remaining]):
                    VehicleImage.objects.create(
                        vehicle=vehicle,
                        image=f,
                        sort_order=current_count + i,
                    )

                # 3) 並べ替え
                _apply_image_order(vehicle, request.POST.get("image_order_json", ""))

                # 4) 左端＝メインを最終同期
                sync_vehicle_main_image(vehicle.id)

            messages.success(request, "車両情報を更新しました。")
            return redirect("vehicle_edit", pk=vehicle.pk)
    else:
        form = VehicleDetailForm(instance=vehicle)

    vehicle_parts = (
        VehiclePart.objects.filter(vehicle=vehicle)
        .select_related("part", "part__category", "maker")
        .order_by("part__category__sort_order", "part__name", "id")
    )
    part_form = VehiclePartForm()

    return render(request, "vehicles/vehicle_edit.html", {
        "form": form,
        "vehicle": vehicle,
        "vehicle_parts": vehicle_parts,
        "part_form": part_form,
    })


# ----------------------------
# Parts: API / AJAX create / delete
# ----------------------------
@require_GET
def api_parts_by_category(request):
    category_id = request.GET.get("category_id")
    if not category_id:
        return JsonResponse({"results": []})

    qs = Part.objects.filter(category_id=category_id).order_by("name")
    return JsonResponse({"results": [{"id": p.id, "name": p.name} for p in qs]})


@login_required
@require_POST
def vehicle_part_create(request, vehicle_id: int):
    vehicle = get_object_or_404(UserVehicle, id=vehicle_id, owner=request.user)

    form = VehiclePartForm(request.POST)
    if not form.is_valid():
        html = render_to_string("vehicles/_part_form.html", {"form": form, "vehicle": vehicle}, request=request)
        return JsonResponse({"ok": False, "form_html": html}, status=400)

    vp = form.save(commit=False)
    vp.vehicle = vehicle
    vp.save()

    row_html = render_to_string("vehicles/_part_row.html", {"vp": vp}, request=request)
    fresh_form_html = render_to_string(
        "vehicles/_part_form.html",
        {"form": VehiclePartForm(), "vehicle": vehicle},
        request=request
    )
    return JsonResponse({"ok": True, "row_html": row_html, "form_html": fresh_form_html})


@login_required
@require_POST
def vehicle_part_delete(request, vehicle_id: int, part_id: int):
    vehicle = get_object_or_404(UserVehicle, id=vehicle_id, owner=request.user)
    vp = get_object_or_404(VehiclePart, id=part_id, vehicle=vehicle)
    vp.delete()
    return JsonResponse({"ok": True})


@login_required
def vehicle_delete_confirm(request, pk: int):
    vehicle = get_object_or_404(
        UserVehicle.objects.select_related("model", "main_image"),
        pk=pk,
        owner=request.user
    )
    return render(request, "vehicles/vehicle_delete_confirm.html", {"vehicle": vehicle})

@login_required
@require_POST
def vehicle_delete(request, pk: int):
    vehicle = get_object_or_404(UserVehicle, pk=pk, owner=request.user)

    with transaction.atomic():
        delete_queryset_with_files(
            VehicleImage.objects.filter(vehicle=vehicle),
            field_names=("thumb", "image"),
        )
        vehicle.delete()

    messages.success(request, "車両を削除しました。")
    return redirect("vehicle_list")
