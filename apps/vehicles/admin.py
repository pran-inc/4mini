from django.contrib import admin
from .models import VehicleModel, UserVehicle, VehicleImage
from .models import (
    VehicleModel, UserVehicle, VehicleImage,
    PartCategory, Part, Maker, VehiclePart
)

admin.site.register(VehicleModel)
admin.site.register(UserVehicle)
admin.site.register(VehicleImage)


@admin.register(PartCategory)
class PartCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "sort_order")
    list_editable = ("sort_order",)
    search_fields = ("name", "slug")

@admin.register(Maker)
class MakerAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")

@admin.register(Part)
class PartAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "slug")
    list_filter = ("category",)
    search_fields = ("name", "slug", "category__name")

@admin.register(VehiclePart)
class VehiclePartAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "part", "maker", "model_number", "spec", "created_at")
    list_filter = ("part__category", "maker")
    search_fields = ("vehicle__title", "part__name", "maker__name", "model_number", "spec")
