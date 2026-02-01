from django import forms
from django.core.exceptions import ValidationError
from .models import UserVehicle

class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleImageField(forms.Field):
    """
    1フィールドで複数ファイルを受け取るためのカスタムField
    ImageFieldだと「1ファイル前提」なのでエラーになりやすいのを回避する。
    """
    widget = MultipleImageInput

    def to_python(self, data):
        # data は list[UploadedFile] が来る
        if not data:
            return []
        return data

    def validate(self, value):
        super().validate(value)
        # value は list
        if not isinstance(value, list):
            raise ValidationError("Invalid upload.")
        if len(value) > 10:
            raise ValidationError("画像は最大10枚までです。")
        for f in value:
            ct = getattr(f, "content_type", "")
            if ct and not ct.startswith("image/"):
                raise ValidationError("画像ファイルのみアップロードできます。")

class VehicleForm(forms.ModelForm):
    images = MultipleImageField(required=False, help_text="最大10枚（png/jpg/webp）")

    class Meta:
        model = UserVehicle
        fields = ["model", "title", "year", "custom_summary", "description", "images"]
