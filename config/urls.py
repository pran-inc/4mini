# project/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", include("apps.pages.urls")),  # ✅ 追加（トップ）

    path("accounts/", include("django.contrib.auth.urls")),
    path("signup/", include("apps.accounts.urls")),
    path("account/", include("apps.accounts.urls")),

    path("vehicles/", include("apps.vehicles.urls")),
    path("posts/", include("apps.posts.urls")),
    path("reactions/", include("apps.interactions.urls")),
    
    path("events/", include("apps.events.urls")),
    path("teams/", include("apps.teams.urls")),


]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)