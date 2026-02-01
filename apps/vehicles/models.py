from django.conf import settings
from django.db import models

class VehicleModel(models.Model):
    maker = models.CharField(max_length=100)     # Honda
    name = models.CharField(max_length=100)      # Super Cub
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return f"{self.maker} {self.name}"

class UserVehicle(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vehicles")
    model = models.ForeignKey(VehicleModel, on_delete=models.PROTECT, related_name="user_vehicles")

    title = models.CharField(max_length=120)  # 例: "C125 赤カブ"
    year = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    custom_summary = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class VehicleImage(models.Model):
    vehicle = models.ForeignKey(UserVehicle, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="vehicles/%Y/%m/")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["sort_order", "id"]
