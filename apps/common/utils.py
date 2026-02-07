# apps/common/utils.py

from __future__ import annotations
from typing import Iterable, Sequence


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
