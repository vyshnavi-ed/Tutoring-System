"""Photos in the Science Buddy chat.

Every photo is cleaned (resized, re-encoded so all hidden metadata such as GPS location is
dropped) and then checked by the AI *before* anything is stored. Only photos of plants and
inanimate objects are accepted. Photos showing people, animals, personal information or
anything inappropriate are refused and never saved.
"""
from __future__ import annotations

import io
import json
import re
import uuid
from pathlib import Path

ALLOWED_CATEGORIES = {"plant", "object"}   # add "small_creature" here to allow insects etc. later
MAX_SIDE = 1024
MAX_UPLOAD_BYTES = 12 * 1024 * 1024

SCREEN_PROMPT = """You check photos that children aged 10-14 upload to a science-tutoring chat.
Only photos of PLANTS or INANIMATE OBJECTS (leaves, flowers, soil, a cup of water, ice, a shadow, cloth,
kitchen things, the sky, a toy) are allowed.

Classify this photo. Rules:
- "person": any person, face, or several body parts (a hand or fingers holding the item is fine and does NOT count).
- "animal": any animal, bird, insect or other creature, alive or dead.
- "personal_info": readable personal information (names, addresses, phone numbers, ID cards, school name,
  screenshots of chats or documents).
- "inappropriate": violent, sexual, frightening, or otherwise not suitable for a child's science chat.
- "plant" or "object": allowed content, with none of the above visible.
- "unclear": too dark, blurry or you can't tell.

Reply with JSON only: {"category": "plant|object|person|animal|personal_info|inappropriate|unclear",
"reason": "a few words"}"""

REFUSALS = {
    "person": "Let's keep people out of our science photos 🙂 Can you take one of just the plant or object?",
    "animal": "For now, photos are just for plants and objects. Can you tell me about the creature in words instead?",
    "personal_info": "That photo has personal details in it, so I didn't keep it. Can you take one of just the thing you're investigating?",
    "inappropriate": "I can't use that photo. Let's stick to photos of plants and objects for our investigations.",
    "unclear": "I couldn't make that photo out. Can you try again with more light, close to the plant or object?",
    "unchecked": "I can't check photos right now, so I didn't keep it. Can you tell me what you see in words?",
}


def clean_image(data: bytes) -> bytes:
    """Resize to at most MAX_SIDE and re-encode as JPEG. Re-encoding without the original
    metadata removes EXIF data, including GPS location. Raises ValueError if not an image."""
    from PIL import Image, ImageOps, UnidentifiedImageError
    if len(data) > MAX_UPLOAD_BYTES:
        raise ValueError("photo too large")
    try:
        im = Image.open(io.BytesIO(data))
        im = ImageOps.exif_transpose(im)  # keep the photo the right way up before dropping metadata
    except (UnidentifiedImageError, OSError) as e:
        raise ValueError("not an image") from e
    im = im.convert("RGB")
    im.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=85)
    return out.getvalue()


def parse_screen(text: str) -> dict:
    try:
        data = json.loads(text[text.find("{"): text.rfind("}") + 1])
    except ValueError:
        return {"category": "unclear", "reason": "could not read the check result"}
    cat = str(data.get("category", "unclear")).strip().lower()
    return {"category": cat if cat in REFUSALS or cat in ALLOWED_CATEGORIES else "unclear",
            "reason": str(data.get("reason", ""))[:200]}


class PhotoStore:
    def __init__(self, directory: str | Path):
        self.dir = Path(directory)

    def save(self, student_id: str, jpeg: bytes) -> str:
        pid = uuid.uuid4().hex
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / f"{pid}.jpg").write_bytes(jpeg)
        return pid

    def path(self, pid: str) -> Path | None:
        if not re.fullmatch(r"[0-9a-f]{32}", pid or ""):
            return None
        p = self.dir / f"{pid}.jpg"
        return p if p.exists() else None

    def load(self, pid: str) -> bytes | None:
        p = self.path(pid)
        return p.read_bytes() if p else None
