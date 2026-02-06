from django.conf import settings
from django.db import models, transaction
from apps.common.upload import upload_vehicle_image
from apps.common.images import compress_image_field, generate_thumbnail
from django.db.models import Q

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

    main_image = models.ForeignKey(
        "VehicleImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    def __str__(self):
        return self.title

class VehicleImage(models.Model):
    vehicle = models.ForeignKey("UserVehicle", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=upload_vehicle_image)
    thumb = models.ImageField(upload_to="vehicles/thumbs/%Y/%m/", blank=True, null=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_main = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        if self.image and getattr(self.image, "file", None):
            compress_image_field(self.image, max_side=1600)

        super().save(*args, **kwargs)

        if self.image and (is_new or not self.thumb):
            generate_thumbnail(src_field=self.image, dest_field=self.thumb, size=(360, 270), keep_png=True)
            super().save(update_fields=["thumb"])

        # ---- main_image 同期（ここが追加）----
        # is_main=True なら main_image を自分に
        if self.is_main and self.vehicle_id:
            UserVehicle.objects.filter(id=self.vehicle_id).update(main_image_id=self.id)
        else:
            # vehicle.main_image が空なら、最優先（is_main desc, sort_order asc）の1枚を入れる
            v = UserVehicle.objects.filter(id=self.vehicle_id, main_image__isnull=True).first()
            if v:
                first = (
                    VehicleImage.objects.filter(vehicle_id=self.vehicle_id)
                    .order_by("-is_main", "sort_order", "id")
                    .first()
                )
                if first:
                    UserVehicle.objects.filter(id=self.vehicle_id).update(main_image_id=first.id)