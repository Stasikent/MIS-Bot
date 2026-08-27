from __future__ import annotations

import os
import re
import sys
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Iterable
from services.runtime_paths import names_dir

try:
    from rapidfuzz import fuzz, process
except Exception:
    fuzz = None
    process = None


CYRILLIC_RE = re.compile(r"[^А-Яа-яЁё\s-]+")
SPACE_RE = re.compile(r"\s+")
MULTI_DASH_RE = re.compile(r"-{2,}")


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _candidate_data_dirs() -> list[Path]:
    result: list[Path] = []

    env_dir = os.environ.get("MIS_BOT_NAMES_DIR")
    if env_dir:
        result.append(Path(env_dir))

    if getattr(sys, "frozen", False):
        result.append(Path(sys.executable).resolve().parent / "data" / "names")

    result.append(_project_root() / "data" / "names")
    result.append(Path.cwd() / "data" / "names")

    unique: list[Path] = []
    seen = set()

    for p in result:
        marker = str(p.resolve()) if p.exists() else str(p)
        if marker not in seen:
            seen.add(marker)
            unique.append(p)

    return unique


def get_names_dir() -> Path:
    return names_dir()


def sanitize_cyrillic_name_text(value: str) -> str:
    value = str(value or "")
    value = CYRILLIC_RE.sub(" ", value)
    value = SPACE_RE.sub(" ", value)
    value = re.sub(r"\s*-\s*", "-", value)
    value = MULTI_DASH_RE.sub("-", value)
    return value.strip(" -")


def title_name_word(word: str) -> str:
    parts = [p for p in word.split("-") if p]
    return "-".join(p[:1].upper() + p[1:].lower() for p in parts)


def normalize_fio_basic(value: str, max_parts: int = 3) -> str:
    clean = sanitize_cyrillic_name_text(value)
    parts = clean.split()[:max_parts]
    return " ".join(title_name_word(p) for p in parts if p)


def _load_wordlist(path: Path) -> tuple[str, ...]:
    if not path.exists():
        return tuple()

    result = []
    seen = set()

    with path.open("r", encoding="utf-8-sig", errors="ignore") as fh:
        for line in fh:
            word = normalize_fio_basic(line.strip(), max_parts=1)
            if len(word) < 2:
                continue

            key = word.casefold()
            if key in seen:
                continue

            seen.add(key)
            result.append(word)

    return tuple(result)


class NameDictionary:
    def __init__(self, words: Iterable[str]):
        self.words = tuple(words)
        self.exact = {w.casefold(): w for w in self.words}
        self.index: dict[tuple[str, int], list[str]] = defaultdict(list)

        for word in self.words:
            key = word.casefold()
            if not key:
                continue

            self.index[(key[0], len(key))].append(word)

    def candidates(self, word: str, length_delta: int = 2) -> list[str]:
        key = word.casefold()
        if not key:
            return []

        first = key[0]
        length = len(key)

        result: list[str] = []

        for ln in range(max(2, length - length_delta), length + length_delta + 1):
            result.extend(self.index.get((first, ln), ()))

        return result


@lru_cache(maxsize=1)
def _dictionaries():
    directory = get_names_dir()

    return {
        "surname": NameDictionary(_load_wordlist(directory / "surnames.txt")),
        "first_name": NameDictionary(_load_wordlist(directory / "first_names.txt")),
        "patronymic": NameDictionary(_load_wordlist(directory / "patronymics.txt")),
    }


def dictionaries_ready() -> bool:
    ds = _dictionaries()
    return all(len(d.words) > 0 for d in ds.values())


def dictionary_stats() -> dict[str, int]:
    ds = _dictionaries()
    return {key: len(value.words) for key, value in ds.items()}


def _similarity(a: str, b: str) -> float:
    if fuzz is not None:
        return float(fuzz.ratio(a.casefold(), b.casefold()))

    from difflib import SequenceMatcher
    return SequenceMatcher(None, a.casefold(), b.casefold()).ratio() * 100.0


def _top_matches(word: str, dictionary: NameDictionary, limit: int = 3):
    candidates = dictionary.candidates(word)

    if not candidates:
        return []

    if process is not None and fuzz is not None:
        matches = process.extract(
            word,
            candidates,
            scorer=fuzz.ratio,
            processor=lambda x: x.casefold(),
            limit=limit,
        )
        return [(candidate, float(score)) for candidate, score, _ in matches]

    scored = [(candidate, _similarity(word, candidate)) for candidate in candidates]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:limit]


def correct_name_word(
    word: str,
    kind: str,
    *,
    auto_threshold: float,
    min_margin: float,
) -> tuple[str, dict]:
    clean = normalize_fio_basic(word, max_parts=1)

    info = {
        "raw": word,
        "clean": clean,
        "kind": kind,
        "corrected": False,
        "score": None,
        "second_score": None,
        "candidate": None,
        "ambiguous": False,
        "dictionary_ready": False,
    }

    if not clean:
        return "", info

    dictionary = _dictionaries().get(kind)

    if dictionary is None or not dictionary.words:
        return clean, info

    info["dictionary_ready"] = True

    exact = dictionary.exact.get(clean.casefold())

    if exact:
        info.update({
            "candidate": exact,
            "score": 100.0,
            "second_score": None,
            "corrected": exact != clean,
        })
        return exact, info

    matches = _top_matches(clean, dictionary, limit=3)

    if not matches:
        return clean, info

    best_word, best_score = matches[0]
    second_score = matches[1][1] if len(matches) > 1 else 0.0
    margin = best_score - second_score

    info.update({
        "candidate": best_word,
        "score": round(best_score, 2),
        "second_score": round(second_score, 2),
        "ambiguous": margin < min_margin,
    })

    if best_score >= auto_threshold and margin >= min_margin:
        info["corrected"] = best_word.casefold() != clean.casefold()
        return best_word, info

    return clean, info


def correct_fio(value: str) -> tuple[str, dict]:
    basic = normalize_fio_basic(value)
    parts = basic.split()

    metadata = {
        "raw": value,
        "basic": basic,
        "dictionary_ready": dictionaries_ready(),
        "parts": [],
        "corrected": False,
    }

    if not parts:
        return "", metadata

    configs = [
        ("surname", 94.0, 6.0),
        ("first_name", 92.0, 5.0),
        ("patronymic", 92.0, 5.0),
    ]

    corrected_parts = []

    for idx, part in enumerate(parts[:3]):
        kind, threshold, margin = configs[idx]

        corrected, info = correct_name_word(
            part,
            kind,
            auto_threshold=threshold,
            min_margin=margin,
        )

        corrected_parts.append(corrected)
        metadata["parts"].append(info)

        if info["corrected"]:
            metadata["corrected"] = True

    return " ".join(corrected_parts), metadata


def enforce_cyrillic_fio(value: str) -> str:
    fio, _ = correct_fio(value)
    return fio
