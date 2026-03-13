import hashlib


def short_md5(value: str, length: int = 12) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()[:length]
