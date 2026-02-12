# apps/pages/views.py

import random
from django.shortcuts import render

from apps.vehicles.models import UserVehicle
from apps.posts.models import Post
from apps.events.models import Event
from apps.interactions.models import Reaction, ReactionType


def home(request):
    # --- News（いったん固定リスト：あとでDB化可） ---
    news_items = [
        {
            "title": "4mini がオープンしました",
            "url": "",  # 外部/内部リンクがあれば入れる（無ければ空）
            "body": "トップページに vehicle / post / event をまとめて見れるようにしました。",
        },
        {
            "title": "イベント機能を追加しました",
            "url": "",
            "body": "イベントにエントリーして投票できます。チーム主催も対応予定です。",
        },
        {
            "title": "チーム招待が使えます",
            "url": "",
            "body": "招待は🔔から確認できます。チーム詳細の管理画面から承認もできます。",
        },
        {
            "title": "次のアップデート予定",
            "url": "",
            "body": "トップを作り込み中です。検索/絞り込みも追加していきます。",
        },
    ]

    # --- Vehicles ---
    vehicles = list(
        UserVehicle.objects
        .select_related("model", "owner", "main_image")
        .order_by("-created_at")[:24]
    )
    random.shuffle(vehicles)

    # --- Posts ---
    posts = list(
        Post.objects
        .select_related("author", "main_image", "vehicle", "vehicle__model")
        .order_by("-created_at")[:24]
    )
    random.shuffle(posts)

    # --- Events ---
    events = list(
        Event.objects
        .select_related("organizer", "organizer_team")
        .filter(is_published=True)
        .order_by("-created_at")[:24]
    )
    random.shuffle(events)

    latest_vehicles = (
        UserVehicle.objects.select_related("model", "owner", "main_image")
        .order_by("-created_at")[:12]
    )
    latest_posts = (
        Post.objects.select_related("author", "main_image")
        .order_by("-created_at")[:12]
    )

    # ✅ detailと同じ ContentType を明示して一致させる
    ct_vehicle = ContentType.objects.get_for_model(UserVehicle)
    ct_post = ContentType.objects.get_for_model(Post)

    # ✅ スライダーで使っている items=vehicles / posts にも like_count を付与
    vehicles = attach_like_counts(vehicles, ct_vehicle)
    posts = attach_like_counts(posts, ct_post)

    # （もし latest_* も別で使うなら残してOK）
    latest_vehicles = attach_like_counts(latest_vehicles, ct_vehicle)
    latest_posts = attach_like_counts(latest_posts, ct_post)

    return render(request, "pages/home.html", {
        "news_items": news_items,
        "vehicles": vehicles,
        "posts": posts,
        "events": events,
        "latest_vehicles": latest_vehicles,
        "latest_posts": latest_posts,
    })


from django.contrib.contenttypes.models import ContentType
from django.db.models import Count

def attach_like_counts(items, ct):
    """
    items: list(QuerySetでも可だが最終的にlist化する)
    ct: ContentType（detailと同じものを渡す）

    各objに obj.like_count を付与して返す
    """
    items = list(items)
    if not items:
        return items

    like_map = dict(
        Reaction.objects.filter(
            reaction_type=ReactionType.LIKE,
            content_type=ct,
            object_id__in=[o.id for o in items],
        )
        .values("object_id")
        .annotate(c=Count("id"))
        .values_list("object_id", "c")
    )

    for o in items:
        o.like_count = like_map.get(o.id, 0)

    return items
