import logging
import os
import re
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)

MODEL_NAME = "facebook/nllb-200-distilled-600M"
LANG_FI = "fin_Latn"
LANG_EN = "eng_Latn"
LANG_RU = "rus_Cyrl"
MAX_CHUNK_CHARS = 500


@lru_cache(maxsize=1)
def _load_model() -> tuple[Any, Any]:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    logger.info("Loading NLLB model: %s", MODEL_NAME)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    model.eval()
    logger.info("NLLB model ready")
    return tokenizer, model


def _translate(
    texts: list[str],
    src_lang: str,
    tgt_lang: str,
) -> list[str]:
    tokenizer, model = _load_model()

    # Устанавливаем source язык в токенайзере
    tokenizer.src_lang = src_lang

    inputs = tokenizer(
        texts,
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=512,
    )

    target_lang_id = tokenizer.convert_tokens_to_ids(tgt_lang)
    outputs = model.generate(
        **inputs,
        forced_bos_token_id=target_lang_id,
        num_beams=4,
        max_length=512,
    )
    return [tokenizer.decode(o, skip_special_tokens=True) for o in outputs]


def translate_fi_en(text: str) -> str:
    if not text.strip():
        return ""
    chunks = _split_into_chunks(text)
    results = []
    for chunk in chunks:
        results.extend(_translate([chunk], LANG_FI, LANG_EN))
    return " ".join(results)


def translate_fi_ru(text: str) -> str:
    if not text.strip():
        return ""
    chunks = _split_into_chunks(text)
    results = []
    for chunk in chunks:
        results.extend(_translate([chunk], LANG_FI, LANG_RU))
    return " ".join(results)


def translate_batch_fi_en(texts: list[str]) -> list[str]:
    return _translate(texts, LANG_FI, LANG_EN)


def translate_batch_fi_ru(texts: list[str]) -> list[str]:
    return _translate(texts, LANG_FI, LANG_RU)


def _split_into_chunks(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]

    lines = text.split("\n")
    chunks = []
    current = ""

    for line in lines:
        if len(line) > MAX_CHUNK_CHARS:
            sentences = re.split(r"(?<=[.!?])\s+", line)
            for sentence in sentences:
                if len(sentence) > MAX_CHUNK_CHARS:
                    if current:
                        chunks.append(current)
                        current = ""
                    for i in range(0, len(sentence), MAX_CHUNK_CHARS):
                        chunks.append(sentence[i : i + MAX_CHUNK_CHARS])
                elif len(current) + len(sentence) + 1 <= MAX_CHUNK_CHARS:
                    current = f"{current} {sentence}".strip()
                else:
                    if current:
                        chunks.append(current)
                    current = sentence
        else:
            if len(current) + len(line) + 1 <= MAX_CHUNK_CHARS:
                current = f"{current} {line}".strip()
            else:
                if current:
                    chunks.append(current)
                current = line

    if current:
        chunks.append(current)

    return chunks
