import hashlib


def text_hash(text: str) -> str:
    """SHA-256 текста — используем для проверки не изменился ли оригинал."""
    return hashlib.sha256(text.encode()).hexdigest()


def needs_translation(
    text_fi: str,
    text_en: str | None,
    stored_hash: str | None,
) -> bool:
    """
    Возвращает True если текст нужно (пере)переводить:
    - text_en ещё нет
    - оригинальный текст изменился с момента последнего перевода
    """
    if not text_en:
        return True
    if stored_hash and text_hash(text_fi) != stored_hash:
        return True
    return False
