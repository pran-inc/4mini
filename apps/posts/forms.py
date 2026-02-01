from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import Post, Tag

class MultipleImageInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleImageField(forms.Field):
    widget = MultipleImageInput

    def to_python(self, data):
        if not data:
            return []
        return data

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

class PostForm(forms.ModelForm):
    images = MultipleImageField(required=False, help_text="最大10枚（png/jpg/webp）")

    # ★タグ入力欄をテキストにする
    tags_text = forms.CharField(
        required=False,
        help_text="例: cub, c125, custom（カンマ区切り）",
        widget=forms.TextInput(attrs={"placeholder": "cub, c125, custom"})
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
            # slugは適当でOK（日本語タグも入れるならslugifyを工夫する）
            slug = slugify(name) or name
            tag, _ = Tag.objects.get_or_create(name=name, defaults={"slug": slug})
            tags.append(tag)

        if commit:
            post.tags.set(tags)
        else:
            # commit=False の場合は呼び出し側で post.save() 後に set する必要あり
            self._pending_tags = tags

        return post
