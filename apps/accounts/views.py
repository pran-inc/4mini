from django.contrib.auth import login
from django.shortcuts import redirect, render
from .forms import SignupForm
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType

from apps.interactions.models import Reaction, ReactionType
from apps.vehicles.models import UserVehicle
from apps.posts.models import Post


def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("vehicle_list")
    else:
        form = SignupForm()

    return render(request, "registration/signup.html", {"form": form})

@login_required
def profile(request):
    return render(request, "accounts/profile.html")


@login_required
def mypage(request):
    user = request.user

    # My Vehicles
    my_vehicles = (
        UserVehicle.objects.filter(owner=user)
        .select_related("model", "main_image")
        .order_by("-created_at")
    )

    # My Posts
    my_posts = (
        Post.objects.filter(author=user)
        .select_related("main_image")
        .order_by("-created_at")
    )

    # Favorites (vehicles + posts)
    ct_vehicle = ContentType.objects.get_for_model(UserVehicle)
    ct_post = ContentType.objects.get_for_model(Post)

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

    favorite_vehicles = (
        UserVehicle.objects.filter(id__in=fav_vehicle_ids)
        .select_related("model", "main_image")
        .order_by("-created_at")
    )
    favorite_posts = (
        Post.objects.filter(id__in=fav_post_ids)
        .select_related("main_image")
        .order_by("-created_at")
    )

    return render(request, "accounts/mypage.html", {
        "my_vehicles": my_vehicles,
        "my_posts": my_posts,
        "favorite_vehicles": favorite_vehicles,
        "favorite_posts": favorite_posts,
    })