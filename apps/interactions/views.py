import json
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST

from .models import Reaction, ReactionType

from django.shortcuts import render

from apps.interactions.models import Reaction, ReactionType
from apps.vehicles.models import UserVehicle
from apps.posts.models import Post


@login_required
@require_POST
def toggle_reaction(request):
    try:
        payload = json.loads(request.body.decode("utf-8"))
        app_label = payload["app_label"]
        model = payload["model"]
        object_id = int(payload["object_id"])
        reaction_type = payload["reaction_type"]
        if reaction_type not in ReactionType.values:
            return HttpResponseBadRequest("Invalid reaction_type")
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    ct = ContentType.objects.get(app_label=app_label, model=model)

    obj, created = Reaction.objects.get_or_create(
        user=request.user,
        reaction_type=reaction_type,
        content_type=ct,
        object_id=object_id,
    )

    if not created:
        obj.delete()
        active = False
    else:
        active = True

    count = Reaction.objects.filter(
        reaction_type=reaction_type,
        content_type=ct,
        object_id=object_id,
    ).count()

    return JsonResponse({"active": active, "count": count})

@login_required
def favorite_list(request):
    user = request.user

    # ContentType をモデルごとに取得
    ct_vehicle = ContentType.objects.get_for_model(UserVehicle)
    ct_post = ContentType.objects.get_for_model(Post)

    # お気に入り（FAVORITE）の object_id を集める
    fav_vehicle_ids = list(
        Reaction.objects.filter(
            user=user, reaction_type=ReactionType.FAVORITE, content_type=ct_vehicle
        ).values_list("object_id", flat=True)
    )

    fav_post_ids = list(
        Reaction.objects.filter(
            user=user, reaction_type=ReactionType.FAVORITE, content_type=ct_post
        ).values_list("object_id", flat=True)
    )

    # 一覧は main_image だけで軽量に
    vehicles = (
        UserVehicle.objects.filter(id__in=fav_vehicle_ids)
        .select_related("model", "owner", "main_image")
        .order_by("-created_at")
    )

    posts = (
        Post.objects.filter(id__in=fav_post_ids)
        .select_related("author", "main_image")
        .order_by("-created_at")
    )

    return render(request, "favorites/favorite_list.html", {
        "vehicles": vehicles,
        "posts": posts,
    })