from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import render

from apps.interactions.models import Reaction, ReactionType
from apps.posts.models import Post
from apps.vehicles.models import UserVehicle


@login_required
def my_vehicles(request):
    vehicles = (
        UserVehicle.objects.filter(owner=request.user)
        .select_related("model")
        .prefetch_related("images")
        .order_by("-created_at")
    )
    return render(request, "accounts/my_vehicles.html", {"vehicles": vehicles})


@login_required
def my_posts(request):
    posts = (
        Post.objects.filter(author=request.user)
        .select_related("vehicle", "vehicle__model")
        .prefetch_related("images", "tags")
        .order_by("-created_at")
    )
    return render(request, "accounts/my_posts.html", {"posts": posts})


@login_required
def my_favorites(request):
    ct_vehicle = ContentType.objects.get_for_model(UserVehicle)
    ct_post = ContentType.objects.get_for_model(Post)

    favs = (
        Reaction.objects.filter(user=request.user, reaction_type=ReactionType.FAVORITE)
        .filter(content_type__in=[ct_vehicle, ct_post])
        .order_by("-created_at")
        .values("content_type_id", "object_id", "created_at")
    )

    vehicle_ids = [f["object_id"] for f in favs if f["content_type_id"] == ct_vehicle.id]
    post_ids = [f["object_id"] for f in favs if f["content_type_id"] == ct_post.id]

    vehicles = (
        UserVehicle.objects.filter(id__in=vehicle_ids)
        .select_related("model", "owner")
        .prefetch_related("images")
    )
    posts = (
        Post.objects.filter(id__in=post_ids)
        .select_related("author", "vehicle", "vehicle__model")
        .prefetch_related("images", "tags")
    )

    # 並び順を「お気に入りした順」に戻す（重要）
    vehicle_map = {v.id: v for v in vehicles}
    post_map = {p.id: p for p in posts}

    ordered_items = []
    for f in favs:
        if f["content_type_id"] == ct_vehicle.id:
            obj = vehicle_map.get(f["object_id"])
            if obj:
                ordered_items.append(("vehicle", obj, f["created_at"]))
        elif f["content_type_id"] == ct_post.id:
            obj = post_map.get(f["object_id"])
            if obj:
                ordered_items.append(("post", obj, f["created_at"]))

    return render(request, "accounts/my_favorites.html", {"items": ordered_items})
