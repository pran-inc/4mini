# apps/common/models.py
from django.conf import settings
from django.db import models
from django.utils import timezone


class TempUpload(models.Model):
    """
    バリデーションエラー等で戻ったときにファイルを保持するための一時アップロード
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="temp_uploads")
    file = models.ImageField(upload_to="temp/%Y/%m/%d/")
    purpose = models.CharField(max_length=50, default="", blank=True)  # 例: "event_image"
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"TempUpload({self.id}) {self.purpose}"
