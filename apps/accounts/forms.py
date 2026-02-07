from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import Profile


User = get_user_model()

class SignupForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")  # email不要なら ("username",) でOK

class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["email"]  # 初期登録が username+email でも、ここは email編集だけにする


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "display_name",
            "avatar",
            "prefecture",
            "blog_url",
            "youtube_url",
            "x_url",
            "instagram_url",
            "bike_count",
            "bike_years",
            "is_public",

        ]