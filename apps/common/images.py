import io
from uuid import uuid4

from PIL import Image
from django.core.files.base import ContentFile


def compress_image_field(
    image_field,
    *,
    max_side: int = 1600,
    webp_quality: int = 82,
    keep_png_if_alpha: bool = True,
):
    if not image_field or not getattr(image_field, "name", ""):
        return

    image_field.file.seek(0)
    img = Image.open(image_field.file)

    # リサイズ（最大辺を制限）
    w, h = img.size
    scale = min(max_side / max(w, h), 1.0)
    if scale < 1.0:
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    has_alpha = (
        img.mode in ("RGBA", "LA") or
        (img.mode == "P" and "transparency" in img.info)
    )

    buf = io.BytesIO()

    if has_alpha and keep_png_if_alpha:
        if img.mode not in ("RGBA", "LA"):
            img = img.convert("RGBA")
        img.save(buf, format="PNG", optimize=True)
        ext = ".png"
    else:
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(buf, format="WEBP", quality=webp_quality, method=6)
        ext = ".webp"

    buf.seek(0)
    name = f"{uuid4().hex}{ext}"
    image_field.save(name, ContentFile(buf.read(), name=name), save=False)


def generate_thumbnail(
    src_field,
    dest_field,
    *,
    size=(360, 270),
    keep_png=True,
):
    if not src_field:
        return

    src_field.file.seek(0)
    img = Image.open(src_field.file)

    has_alpha = (
        img.mode in ("RGBA", "LA") or
        (img.mode == "P" and "transparency" in img.info)
    )

    img = img.convert("RGBA" if has_alpha else "RGB")

    # 中央トリミング → リサイズ
    img_ratio = img.width / img.height
    target_ratio = size[0] / size[1]

    if img_ratio > target_ratio:
        new_width = int(img.height * target_ratio)
        left = (img.width - new_width) // 2
        img = img.crop((left, 0, left + new_width, img.height))
    else:
        new_height = int(img.width / target_ratio)
        top = (img.height - new_height) // 2
        img = img.crop((0, top, img.width, top + new_height))

    img = img.resize(size, Image.LANCZOS)

    buf = io.BytesIO()
    if has_alpha and keep_png:
        img.save(buf, format="PNG", optimize=True)
        ext = ".png"
    else:
        img.save(buf, format="WEBP", quality=80, method=6)
        ext = ".webp"

    buf.seek(0)
    name = f"{uuid4().hex}{ext}"
    dest_field.save(name, ContentFile(buf.read(), name=name), save=False)
