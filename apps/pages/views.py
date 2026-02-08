# apps/pages/views.py

import random
from django.shortcuts import render

from apps.vehicles.models import UserVehicle
from apps.posts.models import Post
from apps.events.models import Event


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

    return render(request, "pages/home.html", {
        "news_items": news_items,
        "vehicles": vehicles,
        "posts": posts,
        "events": events,
    })
