import logging
import os
from functools import lru_cache
from typing import Any

from transformers import MarianMTModel, MarianTokenizer, PreTrainedModel

logger = logging.getLogger(__name__)

os.environ["TRANSFORMERS_OFFLINE"] = "1"
MODEL_FI_EN = "Helsinki-NLP/opus-mt-fi-en"
MODEL_FI_RU = "Helsinki-NLP/opus-mt-fi-ru"
MAX_CHUNK_CHARS = 400  # MarianMT плохо справляется с очень длинными текстами


@lru_cache(maxsize=1)
def _load_fi_en() -> tuple[Any, PreTrainedModel]:
    logger.info("Loading model: %s", MODEL_FI_EN)
    tokenizer = MarianTokenizer.from_pretrained(MODEL_FI_EN)
    model = MarianMTModel.from_pretrained(MODEL_FI_EN)
    model.eval()
    return tokenizer, model

@lru_cache(maxsize=1)
def _load_fi_ru() -> tuple[Any, PreTrainedModel]:
    logger.info("Loading model: %s", MODEL_FI_RU)
    tokenizer = MarianTokenizer.from_pretrained(MODEL_FI_RU)
    model = MarianMTModel.from_pretrained(MODEL_FI_RU)
    model.eval()
    return tokenizer, model

def _translate(
    texts: list[str],
    loader: callable,
) -> list[str]:
    tokenizer, model = loader()
    inputs = tokenizer(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512,
    )
    outputs = model.generate(**inputs, num_beams=4, max_length=512)
    return [tokenizer.decode(o, skip_special_tokens=True) for o in outputs]

def translate_fi_en(text: str) -> str:
    """
    Переводит финский текст на английский.
    Длинные тексты разбиваются на чанки по предложениям.
    """
    if not text.strip():
        return ""
    chunks = _split_into_chunks(text)
    return " ".join(_translate(chunks, _load_fi_en))

def translate_fi_ru(text: str) -> str:
    if not text.strip():
        return ""
    chunks = _split_into_chunks(text)
    return " ".join(_translate(chunks, _load_fi_ru))

def translate_batch_fi_en(texts: list[str]) -> list[str]:
    """
    Переводит список текстов батчем — эффективнее чем по одному.
    Все тексты должны быть короткими (до MAX_CHUNK_CHARS).
    """
    return _translate(texts, _load_fi_en)

def translate_batch_fi_ru(texts: list[str]) -> list[str]:
    return _translate(texts, _load_fi_ru)


def _split_into_chunks(text: str) -> list[str]:
    """
    Разбивает длинный текст на чанки по предложениям.
    MarianMT деградирует на текстах длиннее ~400 символов.
    """
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    # Разбиваем по финским разделителям предложений
    import re
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks = []
    current = ""

    for sentence in sentences:
        if len(current) + len(sentence) <= MAX_CHUNK_CHARS:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            current = sentence

    if current:
        chunks.append(current)

    return chunks