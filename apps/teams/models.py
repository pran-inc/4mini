# apps/teams/models.py

from django.conf import settings
from django.db import models

from apps.accounts.models import PREF_CHOICES


class Team(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="owned_teams",
    )

    name = models.CharField(max_length=60, unique=True)
    logo = models.ImageField(upload_to="team_logos/", blank=True, null=True)
    main_image = models.ImageField(upload_to="team_images/", blank=True, null=True)

    description = models.TextField(blank=True)
    member_limit = models.PositiveSmallIntegerField(blank=True, null=True)

    prefecture = models.CharField(max_length=20, choices=PREF_CHOICES, blank=True, default="")

    x_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)

    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)  # 論理削除

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class TeamTag(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=30)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "name"], name="uniq_team_tag")
        ]

    def __str__(self) -> str:
        return f"{self.team_id}:{self.name}"


class MembershipStatus(models.TextChoices):
    INVITED = "invited", "Invited"     # 招待された（本人が承認待ち）
    PENDING = "pending", "Pending"     # 参加申請（管理者承認待ち）
    APPROVED = "approved", "Approved"  # 参加中
    REJECTED = "rejected", "Rejected"
    LEFT = "left", "Left"


class MembershipRole(models.TextChoices):
    ADMIN = "admin", "Admin"
    MEMBER = "member", "Member"


class TeamMembership(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_memberships")

    role = models.CharField(max_length=10, choices=MembershipRole.choices, default=MembershipRole.MEMBER)
    status = models.CharField(max_length=12, choices=MembershipStatus.choices, default=MembershipStatus.INVITED)

    is_active = models.BooleanField(default=True)  # 論理削除

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="team_invites_sent",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "user"], name="uniq_team_user")
        ]

    def __str__(self) -> str:
        return f"{self.team_id}:{self.user_id}:{self.status}:{self.role}"

    def soft_delete(self):
        self.is_active = False
        self.status = MembershipStatus.LEFT
        self.save(update_fields=["is_active", "status", "updated_at"])


class TeamPinnedVehicle(models.Model):
    """
    チームの代表車両（トップで固定表示）
    """
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="pinned_vehicles")
    vehicle = models.ForeignKey("vehicles.UserVehicle", on_delete=models.CASCADE, related_name="pinned_in_teams")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "vehicle"], name="uniq_team_vehicle_pin")
        ]
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return f"{self.team_id}:{self.vehicle_id}:{self.sort_order}"
