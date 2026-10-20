"""上传图片的统一校验：用 Pillow 真实解码，不信任客户端自报的类型/扩展名。"""

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}


def sniff_image_ext(fileobj, *, max_bytes: int = MAX_IMAGE_BYTES) -> str:
    """校验是真实图片且大小合规，返回规范扩展名；不合规抛 ValueError（文案可直接给用户看）。"""
    size = getattr(fileobj, "size", None)
    if size is not None and size > max_bytes:
        raise ValueError(f"图片不能超过 {max_bytes // 1024 // 1024}MB")
    try:
        fileobj.seek(0)
        with Image.open(fileobj) as im:
            fmt = im.format
            im.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValueError("仅支持 JPG/PNG/WEBP/GIF 图片文件")
    finally:
        fileobj.seek(0)
    if fmt not in ALLOWED_FORMATS:
        raise ValueError("仅支持 JPG/PNG/WEBP/GIF 图片文件")
    return ALLOWED_FORMATS[fmt]
