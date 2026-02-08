from django import forms
from .models import Event, Award
from apps.teams.models import Team, TeamMembership, MembershipStatus, MembershipRole


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "image",
            "starts_at",
            "ends_at",
            "is_published",
            "winners_public",
            "sponsor_name",
            "sponsor_url",
            "sponsor_logo",
            "sponsor_message",
            "organizer_team",
        ]
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["organizer_team"].queryset = Team.objects.none()
        self.fields["organizer_team"].required = False

        if user and user.is_authenticated:
            admin_team_ids = TeamMembership.objects.filter(
                user=user,
                is_active=True,
                status=MembershipStatus.APPROVED,
                role=MembershipRole.ADMIN,
                team__is_active=True,
            ).values_list("team_id", flat=True)

            self.fields["organizer_team"].queryset = Team.objects.filter(
                id__in=admin_team_ids,
                is_active=True,
            ).order_by("-created_at")

    def clean(self):
        cleaned = super().clean()
        starts_at = cleaned.get("starts_at")
        ends_at = cleaned.get("ends_at")
        if ends_at and starts_at and ends_at <= starts_at:
            self.add_error("ends_at", "終了日時は開始日時より後にしてください。")
        return cleaned


class AwardForm(forms.ModelForm):
    class Meta:
        model = Award
        fields = ["title", "description", "winner_entry", "sort_order"]
