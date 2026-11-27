"""Language helpers shared by the tools: tokenizing caption text, normalizing it for alignment, Whisper model names.

English (the default) keeps the original behaviour exactly: tokens are whitespace-separated words and normalization keeps
[a-z0-9]. Chinese / Japanese / Korean narration ("lang": "zh" in narration.json) is tokenized per character, with
punctuation attached to the character before it and Latin words or numbers (XYZ, 48.2) kept whole, so at("r1", "48.2")
and at("m1", "XYZ") work in either language.
"""
import os, re

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")  # Windows without developer mode: cache still works

CJK = "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff"
PUNCT_W = "\u3000-\u303f\uff00-\uffef"  # CJK symbols and full-width forms (，。、：！？ ...)
_DROP = re.compile(f"[^0-9a-z{CJK}]")
_TOK = re.compile(f"[{CJK}]|[{PUNCT_W}]|[^\\s{CJK}{PUNCT_W}]+")
_PUNCT_ONLY = re.compile(f"^(?:[{PUNCT_W}]|[^\\w\\s])+$")
_WIDE = re.compile(f"[{CJK}{PUNCT_W}]")
_IDEO = re.compile(f"[{CJK}]")


def norm(s):
    """lower-case and keep only letters / digits / CJK characters (used for matching words and anchors)."""
    return _DROP.sub("", s.lower())


def lang_of(spec):
    return str(spec.get("lang") or "en").lower()


def is_cjk(lang):
    return lang.split("-")[0] in ("zh", "cmn", "yue", "ja", "ko")


def tokens(text, lang="en"):
    if not is_cjk(lang):
        return text.split()
    out = []
    for m in _TOK.finditer(text):
        t = m.group(0)
        if out and _PUNCT_ONLY.match(t):
            out[-1] += t  # punctuation rides on the token before it
        else:
            out.append(t)
    return out


def wide(ch):
    return bool(_WIDE.match(ch))


def _sep(a, b):
    """space between two tokens: Latin-Latin yes; a CJK character next to a Latin word or number also gets one
    (XYZ 达到 48.2); nothing next to full-width punctuation or between two CJK characters."""
    if not a or not b: return ""
    x, y = a[-1], b[0]
    if not wide(x) and not wide(y): return " "
    if (_IDEO.match(x) and y.isascii() and y.isalnum()) or (_IDEO.match(y) and x.isascii() and x.isalnum()): return " "
    return ""


def join(words):
    """join tokens for display (English: plain spaces, so the original behaviour is unchanged)."""
    s = ""
    for w in words:
        s += _sep(s, w) + w
    return s


def width(s):
    """display width in Latin-character units (a CJK character is about two)."""
    return sum(2 if wide(c) else 1 for c in s)


def whisper_model(lang, big=False):
    base = "medium" if big else "small"
    return base + ".en" if lang.split("-")[0] == "en" else base


def whisper_lang(lang):
    code = lang.split("-")[0]
    return {"cmn": "zh", "yue": "zh"}.get(code, code)


def whisper_prompt(lang, text=""):
    """an initial prompt in the script's own writing; for Chinese it keeps Whisper in simplified characters."""
    if whisper_lang(lang) == "zh":
        return ("以下是普通话的句子。" + text)[:200]
    return None
