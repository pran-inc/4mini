# project/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
import apps.accounts.me_urls as me_urls  # ←追加


urlpatterns = [
    path("admin/", admin.site.urls),

    path("accounts/", include("django.contrib.auth.urls")),
    path("signup/", include("apps.accounts.urls")),

    path("me/", include("apps.accounts.me_urls")),

    path("vehicles/", include("apps.vehicles.urls")),
    path("posts/", include("apps.posts.urls")),
    path("reactions/", include("apps.interactions.urls")),
    
    path("events/", include("apps.events.urls")),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
