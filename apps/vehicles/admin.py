from django.contrib import admin
from .models import VehicleModel, UserVehicle, VehicleImage

admin.site.register(VehicleModel)
admin.site.register(UserVehicle)
admin.site.register(VehicleImage)
