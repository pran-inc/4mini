from django import forms
from django.utils import timezone
from .models import Event
from .models import Event, Award  # Award を追加

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title", "description",
            "starts_at", "ends_at",
            "is_published", "winners_public",
            "sponsor_name", "sponsor_url", "sponsor_logo", "sponsor_message",
        ]
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

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