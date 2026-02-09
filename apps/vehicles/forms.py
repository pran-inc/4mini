# apps/vehicles/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile

from .models import UserVehicle, VehiclePart, PartCategory, Part, Maker


# ----------------------------
# 複数画像アップロード（最大10）
# ----------------------------
class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.Field):
    """
    <input type="file" multiple> を安全に受け取るためのField。

    - request.FILES から複数が来たら list で入る
    - 環境/実装によって UploadedFile 単体で入ってくることもある
      => ここで必ず list に正規化して扱う
    """
    widget = MultipleImageInput

    def to_python(self, data):
        # None/空なら空リスト
        if not data:
            return []

        # すでに list/tuple ならそのまま list に
        if isinstance(data, (list, tuple)):
            return list(data)

        # UploadedFile 単体なら list 化
        if isinstance(data, UploadedFile):
            return [data]

        # それ以外は不正
        return data  # validate で弾く

    def validate(self, value):
        super().validate(value)

        # ここで必ず list であることを保証
        if value is None:
            return
        if not isinstance(value, list):
            raise ValidationError("Invalid upload.")

        if len(value) > 10:
            raise ValidationError("画像は最大10枚までです。")

        for f in value:
            # UploadedFile であること（InMemory/Temporary どちらもOK）
            if not isinstance(f, UploadedFile):
                raise ValidationError("Invalid upload.")

            # content_type が取れるなら image/* のみ許可
            ct = getattr(f, "content_type", "") or ""
            if ct and not ct.startswith("image/"):
                raise ValidationError("画像ファイルのみアップロードできます。")

            # 任意：拡張子ざっくり制限（必要なら）
            # name = (getattr(f, "name", "") or "").lower()
            # if name and not name.endswith((".jpg", ".jpeg", ".png", ".webp")):
            #     raise ValidationError("png/jpg/webp のみアップロードできます。")

    def clean(self, value):
        """
        DjangoのFieldフローに合わせて
        to_python → validate → run_validators を確実に通す
        """
        value = self.to_python(value)
        self.validate(value)
        self.run_validators(value)
        return value


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
