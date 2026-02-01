from django.conf import settings
from django.db import models
from apps.common.upload import upload_vehicle_image
from apps.common.images import compress_image_field, generate_thumbnail


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
    vehicle = models.ForeignKey("UserVehicle", on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to=upload_vehicle_image)
    thumb = models.ImageField(upload_to="vehicles/thumbs/%Y/%m/", blank=True, null=True)  # ←追加
    sort_order = models.PositiveIntegerField(default=0)
    is_main = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # ① オリジナル画像を圧縮（前回入れた処理）
        if self.image and getattr(self.image, "file", None):
            compress_image_field(self.image, max_side=1600)

        super().save(*args, **kwargs)

        # ② サムネ生成（新規 or 画像更新時）
        if self.image and (is_new or not self.thumb):
            generate_thumbnail(
                src_field=self.image,
                dest_field=self.thumb,
                size=(360, 270),  # ←ここを 360x270 に
                keep_png=True,
            )
            super().save(update_fields=["thumb"])