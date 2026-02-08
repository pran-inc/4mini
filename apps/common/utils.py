# apps/common/utils.py

# from __future__ import annotations
from typing import Iterable, Sequence

import os
from dataclasses import dataclass
from typing import Optional

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from apps.common.models import TempUpload
from typing import List



def delete_filefields(obj, field_names: Sequence[str] = ("thumb", "image")) -> None:
    """
    obj.<field> が Django の FieldFile(ImageField/FileField) の場合に
    ストレージ上のファイルを削除する（DBレコードは削除しない）
    """
    for name in field_names:
        f = getattr(obj, name, None)
        if not f:
            continue

        delete = getattr(f, "delete", None)
        if callable(delete):
            try:
                f.delete(save=False)
            except Exception:
                # ストレージエラーやファイル欠損でも落とさない
                pass


def delete_queryset_with_files(qs, field_names: Sequence[str] = ("thumb", "image")) -> int:
    """
    QuerySet の各要素について物理ファイルを削除してから、DBレコードを削除する。
    戻り値: 削除されたDBレコード数
    """
    objs = list(qs)
    for obj in objs:
        delete_filefields(obj, field_names=field_names)

    deleted_count, _ = qs.delete()
    return deleted_count


def delete_objects_with_files(objs: Iterable, field_names: Sequence[str] = ("thumb", "image")) -> None:
    """
    iterable で渡されたオブジェクト群の物理ファイル削除のみ行う（DB削除なし）
    """
    for obj in objs:
        delete_filefields(obj, field_names=field_names)



@dataclass
class TempFileResult:
    temp: Optional[TempUpload]
    temp_id: Optional[int]


def save_temp_upload(user, uploaded_file, purpose: str) -> TempFileResult:
    """
    request.FILES で受け取った UploadedFile を TempUpload に保存
    """
    if not uploaded_file:
        return TempFileResult(temp=None, temp_id=None)

    temp = TempUpload.objects.create(user=user, file=uploaded_file, purpose=purpose)
    return TempFileResult(temp=temp, temp_id=temp.id)


def get_temp_upload_for_user(user, temp_id: Optional[str], purpose: str) -> Optional[TempUpload]:
    if not temp_id:
        return None
    try:
        tid = int(temp_id)
    except (TypeError, ValueError):
        return None

    return TempUpload.objects.filter(id=tid, user=user, purpose=purpose).first()


def copy_temp_to_field(temp: TempUpload, instance, field_name: str) -> None:
    """
    TempUpload.file を instance.<field_name> にコピーしてセットする
    - その後 temp を削除しても本番ファイルは残る
    """
    if not temp:
        return

    src_name = temp.file.name  # temp/...
    base = os.path.basename(src_name)

    # instance側の upload_to に従って保存させたいので save=False でセットする
    # ContentFileでコピー
    with temp.file.open("rb") as f:
        content = ContentFile(f.read())

    # Djangoが upload_to を使って保存するように save(name, content)
    getattr(instance, field_name).save(base, content, save=False)


def delete_temp(temp: Optional[TempUpload]) -> None:
    if not temp:
        return
    # delete() で ImageField の実体も削除される
    temp.delete()


def save_temp_uploads_multi(user, files, purpose: str, max_files: int = 10) -> List[TempUpload]:
    """
    複数 UploadedFile を TempUpload に保存してリストで返す
    """
    temps: List[TempUpload] = []
    if not files:
        return temps
    for f in list(files)[:max_files]:
        temps.append(TempUpload.objects.create(user=user, file=f, purpose=purpose))
    return temps


def parse_temp_ids_json(s: str) -> List[int]:
    if not s:
        return []
    try:
        arr = json.loads(s)
        if not isinstance(arr, list):
            return []
        out = []
        for x in arr:
            try:
                out.append(int(x))
            except Exception:
                pass
        return out
    except Exception:
        return []


def get_temp_uploads_for_user(user, temp_ids_json: str, purpose: str) -> List[TempUpload]:
    """
    hidden で渡された temp_id 配列(JSON)から TempUpload を取得（ユーザー＆purposeで絞る）
    """
    ids = parse_temp_ids_json(temp_ids_json)
    if not ids:
        return []
    qs = TempUpload.objects.filter(user=user, purpose=purpose, id__in=ids).order_by("id")
    # ids の順序をなるべく維持したい場合はここで並べ替え（簡易）
    temp_map = {t.id: t for t in qs}
    return [temp_map[i] for i in ids if i in temp_map]


def delete_temps(temps: List[TempUpload]) -> None:
    for t in temps or []:
        try:
            t.delete()
        except Exception:
            pass