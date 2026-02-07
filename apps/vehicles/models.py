from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.upload import upload_vehicle_image
from apps.common.images import compress_image_field, generate_thumbnail

from django.db.models.signals import post_delete
from django.dispatch import receiver



def sync_vehicle_main_image(vehicle_id: int) -> None:
    """
    左端（sort_order最小）を main に同期する
    """
    from .models import VehicleImage, UserVehicle  # 循環import防止

    first = (
        VehicleImage.objects
        .filter(vehicle_id=vehicle_id)
        .order_by("sort_order", "id")
        .first()
    )

    UserVehicle.objects.filter(id=vehicle_id).update(
        main_image_id=(first.id if first else None)
    )

    if first:
        VehicleImage.objects.filter(vehicle_id=vehicle_id).update(is_main=False)
        VehicleImage.objects.filter(
            vehicle_id=vehicle_id,
            id=first.id
        ).update(is_main=True)

class VehicleModel(models.Model):
    maker = models.CharField(max_length=100)     # Honda
    name = models.CharField(max_length=100)      # Super Cub
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return f"{self.maker} {self.name}"


class UserVehicle(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    model = models.ForeignKey(
        VehicleModel,
        on_delete=models.PROTECT,
        related_name="user_vehicles",
    )

    title = models.CharField(max_length=120)  # 例: "C125 赤カブ"
    year = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField(blank=True, default="")
    custom_summary = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    # 一覧表示などを軽くするための「メイン画像ショートカット」
    main_image = models.ForeignKey(
        "VehicleImage",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    # 将来「車両スペック」を柔軟に増やす用（現状はフォームには出してない）
    specs = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.title


class VehicleImage(models.Model):
    vehicle = models.ForeignKey(
        UserVehicle,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.ImageField(upload_to=upload_vehicle_image)
    thumb = models.ImageField(upload_to="vehicles/thumbs/%Y/%m/", blank=True, null=True)

    sort_order = models.PositiveIntegerField(default=0)
    # 互換のため残してOK（運用ルールは「左端がメイン」）
    is_main = models.BooleanField(default=False)

    class Meta:
        ordering = ["sort_order", "id"]

    def save(self, *args, **kwargs):
        is_new = self.pk is None

        # 画像圧縮（PNGは keep_png=True の生成側で維持）
        if self.image and getattr(self.image, "file", None):
            compress_image_field(self.image, max_side=1600)

        super().save(*args, **kwargs)

        # サムネ生成（スマホ向け）
        if self.image and (is_new or not self.thumb):
            generate_thumbnail(
                src_field=self.image,
                dest_field=self.thumb,
                size=(360, 270),
                keep_png=True,
            )
            super().save(update_fields=["thumb"])

        if self.vehicle_id:
            sync_vehicle_main_image(self.vehicle_id)

        # main_image 同期（is_main優先、なければ先頭）
        if self.vehicle_id:
            if self.is_main:
                UserVehicle.objects.filter(id=self.vehicle_id).update(main_image_id=self.id)
            else:
                v = UserVehicle.objects.filter(id=self.vehicle_id, main_image__isnull=True).first()
                if v:
                    first = (
                        VehicleImage.objects.filter(vehicle_id=self.vehicle_id)
                        .order_by("-is_main", "sort_order", "id")
                        .first()
                    )
                    if first:
                        UserVehicle.objects.filter(id=self.vehicle_id).update(main_image_id=first.id)


class PartCategory(models.Model):
    # エンジン / 車体 / 電装 ...
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or self.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Maker(models.Model):
    # KEIHIN / 武川 / キタコ ...
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or self.name
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Part(models.Model):
    # ハンドル / キャブ / マフラー ...
    category = models.ForeignKey(PartCategory, on_delete=models.PROTECT, related_name="parts")
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=120)

    class Meta:
        unique_together = [("category", "slug")]
        ordering = ["category__sort_order", "name"]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name) or self.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category.name} / {self.name}"


class VehiclePart(models.Model):
    vehicle = models.ForeignKey(UserVehicle, on_delete=models.CASCADE, related_name="parts")

    # 選択式（マスタ）
    part = models.ForeignKey(
        Part,
        on_delete=models.PROTECT,
        related_name="vehicle_parts",
        null=True,
        blank=True,
    )

    # 自由入力（マスタに無いとき）
    part_free_text = models.CharField(max_length=120, blank=True, default="")

    maker = models.ForeignKey(
        Maker,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="vehicle_parts",
    )

    model_number = models.CharField(max_length=120, blank=True, default="")
    spec = models.CharField(max_length=200, blank=True, default="")
    note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def display_part_name(self) -> str:
        return self.part.name if self.part_id else self.part_free_text

    def __str__(self):
        mk = self.maker.name if self.maker else "-"
        return f"{self.vehicle_id} {self.display_part_name()} {mk} {self.model_number}"


@receiver(post_delete, sender=VehicleImage)
def vehicle_image_post_delete(sender, instance, **kwargs):
    if instance.vehicle_id:
        sync_vehicle_main_image(instance.vehicle_id)