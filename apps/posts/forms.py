# apps/posts/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.text import slugify

from .models import Post, Tag


class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.Field):
    """
    <input type="file" multiple> を安全に受け取るためのField。

    - list/tuple で来たら list 化
    - UploadedFile 単体で来たら [file] にする
    - それ以外は Invalid upload
    """
    widget = MultipleImageInput

    def to_python(self, data):
        if not data:
            return []

        if isinstance(data, (list, tuple)):
            return list(data)

        if isinstance(data, UploadedFile):
            return [data]

        return data  # validateで弾く

    def validate(self, value):
        super().validate(value)

        if value is None:
            return
        if not isinstance(value, list):
            raise ValidationError("Invalid upload.")

        if len(value) > 10:
            raise ValidationError("画像は最大10枚までです。")

        for f in value:
            if not isinstance(f, UploadedFile):
                raise ValidationError("Invalid upload.")

            ct = getattr(f, "content_type", "") or ""
            if ct and not ct.startswith("image/"):
                raise ValidationError("画像ファイルのみアップロードできます。")

            # 任意：拡張子を制限したいなら
            # name = (getattr(f, "name", "") or "").lower()
            # if name and not name.endswith((".jpg", ".jpeg", ".png", ".webp")):
            #     raise ValidationError("png/jpg/webp のみアップロードできます。")

    def clean(self, value):
        value = self.to_python(value)
        self.validate(value)
        self.run_validators(value)
        return value


class PostForm(forms.ModelForm):
    images = MultipleImageField(required=False, help_text="最大10枚（png/jpg/webp）")

    # ★タグ入力欄をテキストにする
    tags_text = forms.CharField(
        required=False,
        help_text="例: cub, c125, custom（カンマ区切り）",
        widget=forms.TextInput(attrs={"placeholder": "cub, c125, custom"}),
    )

    class Meta:
        model = Post
        fields = ["vehicle", "title", "body", "tags_text", "images"]  # tags を外す

    def save(self, commit=True):
        post = super().save(commit=commit)

        # tags_text をTagへ反映
        raw = self.cleaned_data.get("tags_text", "")
        names = [x.strip() for x in raw.split(",") if x.strip()]

        tags = []
        for name in names:
            slug = slugify(name) or name
            tag, _ = Tag.objects.get_or_create(name=name, defaults={"slug": slug})
            tags.append(tag)

        if commit:
            post.tags.set(tags)
        else:
            self._pending_tags = tags

        return post

    def save_m2m(self):
        """
        commit=False のときに溜めた tags を DB保存後に反映するための互換メソッド
        """
        tags = getattr(self, "_pending_tags", None)
        if tags is not None:
            self.instance.tags.set(tags)
            delattr(self, "_pending_tags")
