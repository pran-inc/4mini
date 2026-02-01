from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from django.contrib.contenttypes.models import ContentType
from apps.interactions.models import Reaction, ReactionType
from .forms import PostForm
from .models import Post, PostImage

@login_required
def post_create(request):
    if request.method == "POST":
        print("FILES keys:", request.FILES.keys())
        print("images:", request.FILES.getlist("images"))

        form = PostForm(request.POST, request.FILES)  # ←ここが超重要

        print("form errors:", form.errors)

        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            form.save_m2m()

            files = form.cleaned_data["images"]  # list が返る
            for i, f in enumerate(files[:10]):
                PostImage.objects.create(post=post, image=f, sort_order=i)

            return redirect("post_detail", pk=post.pk)
    else:
        form = PostForm()

    return render(request, "posts/post_form.html", {"form": form})

def post_list(request):
    posts = (
        Post.objects.select_related("author", "vehicle", "vehicle__model")
        .prefetch_related("images", "tags")
        .order_by("-created_at")
    )
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
