# apps/events/models.py

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.vehicles.models import UserVehicle
from apps.teams.models import Team


class Event(models.Model):
    # 主催者（個人）
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="events",
    )

    # ✅ チーム主催（任意）
    organizer_team = models.ForeignKey(
        Team,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
    )

    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default="")

    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)

    is_published = models.BooleanField(default=True)
    winners_public = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    sponsor_name = models.CharField(max_length=120, blank=True, default="")
    sponsor_url = models.URLField(blank=True, default="")
    sponsor_logo = models.ImageField(upload_to="sponsors/%Y/%m/", blank=True, null=True)
    sponsor_message = models.TextField(blank=True, default="")

    def __str__(self):
        return self.title

    @property
    def is_active(self) -> bool:
        if not self.is_published:
            return False
        now = timezone.now()
        if self.starts_at and now < self.starts_at:
            return False
        if self.ends_at and now > self.ends_at:
            return False
        return True


class EventEntry(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="entries")
    vehicle = models.ForeignKey(UserVehicle, on_delete=models.CASCADE, related_name="event_entries")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "vehicle"], name="unique_vehicle_per_event")
        ]

    def __str__(self):
        return f"{self.event.title} - {self.vehicle.title}"


class EventVote(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="votes")
    entry = models.ForeignKey(EventEntry, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_votes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "entry", "user"], name="unique_vote_per_entry_user")
        ]

    def __str__(self):
        return f"vote:{self.event_id}:{self.entry_id}:{self.user_id}"


class Award(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="awards")

    title = models.CharField(max_length=100)  # 例: Best Custom
    description = models.TextField(blank=True, default="")

    winner_entry = models.ForeignKey(
        EventEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="won_awards",
    )

    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.event.title} - {self.title}"
