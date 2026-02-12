from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.contenttypes.models import ContentType
from apps.interactions.models import Reaction, ReactionType
from .forms import PostForm
from .models import Post, PostImage
from django.db import transaction
import json
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.db.models import Prefetch
from apps.common.utils import delete_queryset_with_files

from django.views.decorators.http import require_POST


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


def _sync_post_main_image(post):
    # 一番左（sort_order最小）がメイン
    first = PostImage.objects.filter(post=post).order_by("sort_order", "id").first()

    # is_main があるプロジェクトなら整合させる（無ければ無視）
    try:
        PostImage.objects.filter(post=post).update(is_main=False)
        if first:
            PostImage.objects.filter(post=post, id=first.id).update(is_main=True)
    except Exception:
        pass

    post.main_image = first
    post.save(update_fields=["main_image"])


@login_required
def post_create(request):
    if request.method == "POST":
        form = PostForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=False)
                post.author = request.user
                post.save()
                form.save_m2m()

                # ✅ 画像保存（最大10枚）
                files = form.cleaned_data.get("images", []) or []
                for i, f in enumerate(files[:10]):
                    PostImage.objects.create(
                        post=post,
                        image=f,
                        sort_order=i,
                    )

                # ✅ 左端＝メインに同期（ここで1回だけ）
                _sync_post_main_image(post)

            return redirect("post_confirm", pk=post.pk)
    else:
        form = PostForm(user=request.user)

    return render(request, "posts/post_form.html", {"form": form})


from django.contrib.contenttypes.models import ContentType
from django.db.models import Count

def post_list(request):
    posts = list(
        Post.objects
        .select_related("author", "main_image")
        .order_by("-created_at")
    )

    # ✅ Like数をまとめて集計（N+1回避）
    ct = ContentType.objects.get_for_model(Post)

    like_map = dict(
        Reaction.objects.filter(
            reaction_type=ReactionType.LIKE,
            content_type=ct,
            object_id__in=[p.id for p in posts],
        )
        .values("object_id")
        .annotate(c=Count("id"))
        .values_list("object_id", "c")
    )

    for p in posts:
        p.like_count = like_map.get(p.id, 0)

    return render(request, "posts/post_list.html", {"posts": posts})


def post_detail(request, pk: int):
    post = get_object_or_404(
        Post.objects.select_related("author", "vehicle", "vehicle__model").prefetch_related("images", "tags"),
        pk=pk
    )

    ct = ContentType.objects.get_for_model(Post)

    like_count = Reaction.objects.filter(
        reaction_type=ReactionType.LIKE, content_type=ct, object_id=post.id
    ).count()
    fav_count = Reaction.objects.filter(
        reaction_type=ReactionType.FAVORITE, content_type=ct, object_id=post.id
    ).count()

    user_like = False
    user_fav = False
    if request.user.is_authenticated:
        user_like = Reaction.objects.filter(
            user=request.user, reaction_type=ReactionType.LIKE, content_type=ct, object_id=post.id
        ).exists()
        user_fav = Reaction.objects.filter(
            user=request.user, reaction_type=ReactionType.FAVORITE, content_type=ct, object_id=post.id
        ).exists()

    ctx = {
        "post": post,
        "like_count": like_count,
        "fav_count": fav_count,
        "user_like": user_like,
        "user_fav": user_fav,
        "target": {"app_label": ct.app_label, "model": ct.model, "object_id": post.id},
    }
    return render(request, "posts/post_detail.html", ctx)

@login_required
def post_edit(request, pk: int):
    post = get_object_or_404(
        Post.objects.select_related("author", "main_image").prefetch_related("images", "tags"),
        pk=pk
    )
    if post.author_id != request.user.id:
        return HttpResponseForbidden("Not allowed")

    if request.method == "POST":
        if request.method == "POST":
            form = PostForm(request.POST, request.FILES, instance=post, user=request.user)
            if form.is_valid():
                ...
        else:
            form = PostForm(instance=post, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                post = form.save(commit=False)
                post.save()
                form.save_m2m()

                # 1) 既存画像の削除
                delete_ids = request.POST.getlist("delete_image_ids")
                if delete_ids:
                    PostImage.objects.filter(post=post, id__in=delete_ids).delete()

                # 2) 追加画像（最大10枚：既存枚数を見て残りだけ追加）
                current_count = PostImage.objects.filter(post=post).count()
                files = form.cleaned_data["images"]  # list[UploadedFile]
                remaining = max(0, 10 - current_count)

                for i, f in enumerate(files[:remaining]):
                    PostImage.objects.create(
                        post=post,
                        image=f,
                        sort_order=current_count + i,
                    )

                # 3) 並び順を反映（hiddenの image_order_json を読む）
                order_json = request.POST.get("image_order_json", "")
                if order_json:
                    try:
                        ordered_ids = json.loads(order_json)
                        if isinstance(ordered_ids, list):
                            valid_ids = list(
                                PostImage.objects.filter(post=post, id__in=ordered_ids)
                                .values_list("id", flat=True)
                            )
                            valid_set = set(valid_ids)

                            sort = 0
                            for img_id in ordered_ids:
                                if img_id in valid_set:
                                    PostImage.objects.filter(post=post, id=img_id).update(sort_order=sort)
                                    sort += 1

                            leftovers = (
                                PostImage.objects.filter(post=post)
                                .exclude(id__in=valid_set)
                                .order_by("sort_order", "id")
                                .values_list("id", flat=True)
                            )
                            for img_id in leftovers:
                                PostImage.objects.filter(post=post, id=img_id).update(sort_order=sort)
                                sort += 1
                    except Exception:
                        pass

                # 4) 左端＝メインに同期（ここで1回だけ）
                _sync_post_main_image(post)

            messages.success(request, "投稿を更新しました。")
            return redirect("post_detail", pk=post.pk)
    else:
        if request.method == "POST":
            form = PostForm(request.POST, request.FILES, instance=post, user=request.user)
            if form.is_valid():
                ...
        else:
            form = PostForm(instance=post, user=request.user)

    post = (
        Post.objects
        .select_related("author", "main_image")
        .prefetch_related("images", "tags")
        .get(pk=post.pk)
    )

    return render(request, "posts/post_edit.html", {
        "form": form,
        "post": post,
    })



@login_required
def post_confirm(request, pk: int):
    post = get_object_or_404(
        Post.objects.select_related("author", "main_image"),
        pk=pk,
        author=request.user
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "confirm":
            messages.success(request, "投稿しました。")
            return redirect("post_detail", pk=post.pk)

        if action == "edit":
            return redirect("post_edit", pk=post.pk)

        if action == "discard":
            with transaction.atomic():
                delete_queryset_with_files(
                    PostImage.objects.filter(post=post),
                    field_names=("thumb", "image")
                )
                post.delete()

            messages.info(request, "投稿を破棄しました。")
            return redirect("post_list")

    return render(request, "posts/post_confirm.html", {"post": post})


@login_required
def post_delete_confirm(request, pk: int):
    post = get_object_or_404(
        Post.objects.select_related("author", "main_image"),
        pk=pk,
        author=request.user
    )
    return render(request, "posts/post_delete_confirm.html", {"post": post})


@login_required
@require_POST
def post_delete(request, pk: int):
    post = get_object_or_404(Post, pk=pk, author=request.user)

    with transaction.atomic():
        delete_queryset_with_files(
            PostImage.objects.filter(post=post),
            field_names=("thumb", "image"),
        )
        post.delete()

    messages.success(request, "投稿を削除しました。")
    return redirect("post_list")