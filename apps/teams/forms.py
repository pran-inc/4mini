# apps/teams/forms.py

from django import forms
from django.contrib.auth import get_user_model

from apps.vehicles.models import UserVehicle
from .models import Team, TeamPinnedVehicle, TeamTag

from .models import TeamPinnedVehicle, TeamTag, TeamMembership, MembershipStatus


User = get_user_model()


class TeamForm(forms.ModelForm):
    # タグはカンマ区切りで入力（TeamTagに保存）
    tags_text = forms.CharField(
        required=False,
        help_text="例: cub, c125, custom（カンマ区切り）",
        widget=forms.TextInput(attrs={"placeholder": "cub, c125, custom"})
    )

    class Meta:
        model = Team
        fields = [
            "name",
            "logo",
            "main_image",
            "description",
            "member_limit",
            "prefecture",
            "x_url",
            "instagram_url",
            "is_public",
            "tags_text",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }


class TeamInviteForm(forms.Form):
    username = forms.CharField(help_text="招待したいユーザーの username を入力")


class TeamJoinRequestForm(forms.Form):
    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "参加したい理由（任意）"})
    )


class TeamPinnedVehicleForm(forms.ModelForm):
    class Meta:
        model = TeamPinnedVehicle
        fields = ["vehicle", "sort_order"]

    def __init__(self, *args, **kwargs):
        team = kwargs.pop("team")
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)

        # ✅ チームの承認済みメンバー（owner含む）の user_id を集める
        member_user_ids = list(
            TeamMembership.objects.filter(
                team=team,
                is_active=True,
                status=MembershipStatus.APPROVED,
            ).values_list("user_id", flat=True)
        )
        # owner は membership が無い場合もあるので保険で追加
        if team.owner_id not in member_user_ids:
            member_user_ids.append(team.owner_id)

        # ✅ チーム全メンバーの車両から選べる
        self.fields["vehicle"].queryset = (
            UserVehicle.objects
            .filter(owner_id__in=member_user_ids)
            .select_related("model", "main_image", "owner")
            .order_by("-created_at")
        )


class RoleChangeForm(forms.Form):
    user_id = forms.IntegerField()
    make_admin = forms.BooleanField(required=False)
