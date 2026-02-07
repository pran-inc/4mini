# apps/vehicles/forms.py

from django import forms
from django.core.exceptions import ValidationError

from .models import UserVehicle, VehiclePart, PartCategory, Part, Maker


# ----------------------------
# 複数画像アップロード（最大10）
# ----------------------------
class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.Field):
    widget = MultipleImageInput

    def to_python(self, data):
        return data or []

    def validate(self, value):
        super().validate(value)
        if not isinstance(value, list):
            raise ValidationError("Invalid upload.")
        if len(value) > 10:
            raise ValidationError("画像は最大10枚までです。")
        for f in value:
            ct = getattr(f, "content_type", "")
            if ct and not ct.startswith("image/"):
                raise ValidationError("画像ファイルのみアップロードできます。")


# ----------------------------
# Step1: 最小登録フォーム
# ----------------------------
class VehicleQuickForm(forms.ModelForm):
    images = MultipleImageField(required=False, help_text="最大10枚（png/jpg/webp）")

    class Meta:
        model = UserVehicle
        fields = ["model", "title"]


# ----------------------------
# Step2(+edit): 詳細 + 画像追加も同フォームで受ける
# ----------------------------
class VehicleDetailForm(forms.ModelForm):
    images = MultipleImageField(required=False, help_text="追加画像（最大10枚まで）")

    class Meta:
        model = UserVehicle
        fields = [
            "year",
            "description",
            "custom_summary",
            "specs",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "custom_summary": forms.Textarea(attrs={"rows": 4}),
        }


# ----------------------------
# パーツ追加フォーム
# ----------------------------
class VehiclePartForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=PartCategory.objects.all(),
        required=False,
        empty_label="（カテゴリを選択）",
    )

    class Meta:
        model = VehiclePart
        fields = ["category", "part", "part_free_text", "maker", "model_number", "spec", "note"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["maker"].queryset = Maker.objects.all().order_by("name")
        self.fields["maker"].required = False

        self.fields["part"].queryset = Part.objects.none()
        self.fields["part"].required = False

        cat = None
        if self.data.get("category"):
            try:
                cat = PartCategory.objects.get(pk=int(self.data.get("category")))
            except Exception:
                cat = None

        if not cat and getattr(self.instance, "part_id", None):
            cat = self.instance.part.category

        if cat:
            self.fields["category"].initial = cat
            self.fields["part"].queryset = Part.objects.filter(category=cat).order_by("name")

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get("category")
        part = cleaned.get("part")
        free = (cleaned.get("part_free_text") or "").strip()

        if not part and not free:
            raise ValidationError("部品を選ぶか、自由入力してください。")
        if part and free:
            cleaned["part_free_text"] = ""
        if part and category and part.category_id != category.id:
            raise ValidationError("カテゴリと部品が一致しません。")
        if free:
            cleaned["part"] = None
        return cleaned
