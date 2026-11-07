import unicodedata


def normalize(s: str) -> str:
    return unicodedata.normalize("NFC", s).strip().lower()


def search_name(s: str) -> str:
    n = unicodedata.normalize("NFD", normalize(s))
    return "".join(c for c in n if unicodedata.category(c) != "Mn").replace("đ", "d")
