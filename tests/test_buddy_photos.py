"""Photos in the Science Buddy: cleaned, checked before storing, only plants/objects kept."""
import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from conftest import PACKS, FakeClock
from tutor.api import create_app
from tutor.buddy.engine import Buddy, PhotoConsentRequired
from tutor.buddy.photos import parse_screen
from tutor.store import Store


def jpeg_with_gps(size=(3000, 2000)):
    im = Image.new("RGB", size, (90, 30, 120))
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"                        # Make
    exif[0x8825] = {1: "N", 2: (12.0, 58.0, 0.0)}      # GPS IFD (Bengaluru-ish)
    out = io.BytesIO()
    im.save(out, "JPEG", exif=exif)
    return out.getvalue()


class PhotoLLM:
    demo = False

    def __init__(self, category="plant"):
        self.category = category
        self.calls, self.screened = [], []

    def screen_image(self, jpeg):
        self.screened.append(jpeg)
        return {"category": self.category, "reason": "test"}

    def respond(self, system, messages):
        self.calls.append((system, messages))
        return {"reply": "Ooh! What do you notice about the leaves?"}


@pytest.fixture
def mk(tmp_path):
    def make(category="plant", photo_consent=True):
        llm = PhotoLLM(category)
        b = Buddy(Store(str(tmp_path / "p.db")), llm=llm, clock=FakeClock(), photo_dir=tmp_path / "photos")
        b.give_consent("Asha", "Lakshmi", "Mother", 7, photos=photo_consent)
        b.start("Asha")
        return b, llm, tmp_path / "photos"
    return make


def test_plant_photo_is_cleaned_stored_and_shown_to_the_ai(mk):
    b, llm, d = mk("plant")
    v = b.message("Asha", "my plant has purple leaves", jpeg_with_gps())
    stored = list(d.glob("*.jpg"))
    assert len(stored) == 1
    im = Image.open(stored[0])
    assert max(im.size) <= 1024 and not im.getexif()                    # resized, metadata (GPS) gone
    assert v["turns"][-2]["photo"] == stored[0].stem
    content = llm.calls[-1][1][-1]["content"]
    assert content[0]["type"] == "image" and content[1]["text"] == "my plant has purple leaves"
    assert "Never describe, name or identify what is in a photo" in llm.calls[-1][0]


@pytest.mark.parametrize("cat,words", [("person", "keep people out"), ("animal", "plants and objects"),
                                       ("personal_info", "personal details"), ("unclear", "more light")])
def test_refused_photos_are_never_stored_or_sent(mk, cat, words):
    b, llm, d = mk(cat)
    n_calls = len(llm.calls)
    v = b.message("Asha", "look", jpeg_with_gps((400, 300)))
    assert not d.exists() or not list(d.glob("*.jpg"))
    assert words in v["turns"][-1]["text"] and v["turns"][-2]["photo_refused"] == cat
    assert len(llm.calls) == n_calls                                     # tutor model never saw it


def test_inappropriate_photo_alerts_a_person(mk):
    b, _, d = mk("inappropriate")
    b.message("Asha", "", jpeg_with_gps((400, 300)))
    al = [a for a in b.store.alerts() if a["kind"] == "wellbeing"]
    assert al and "inappropriate" in al[0]["message"] and not list(d.glob("*.jpg")) if d.exists() else True


def test_photo_needs_its_own_consent(mk):
    b, _, _ = mk("plant", photo_consent=False)
    with pytest.raises(PhotoConsentRequired):
        b.message("Asha", "hi", jpeg_with_gps((200, 200)))
    b.give_photo_consent("Asha", "Lakshmi")
    assert b.message("Asha", "hi", jpeg_with_gps((200, 200)))["turns"][-2]["photo"]


def test_failed_check_means_not_stored(mk):
    b, llm, d = mk("plant")
    llm.screen_image = lambda jpeg: (_ for _ in ()).throw(Exception("timeout"))
    v = b.message("Asha", "x", jpeg_with_gps((200, 200)))
    assert "can't check photos" in v["turns"][-1]["text"] and (not d.exists() or not list(d.glob("*.jpg")))


def test_only_the_latest_photos_go_to_the_ai(mk):
    b, llm, _ = mk("plant")
    for i in range(3):
        b.message("Asha", f"photo {i}", jpeg_with_gps((300, 300)))
    sent = [blk for m in llm.calls[-1][1] if isinstance(m["content"], list) for blk in m["content"]]
    assert sum(1 for blk in sent if blk["type"] == "image") == 2
    texts = [m["content"] if isinstance(m["content"], str) else " ".join(b.get("text", "") for b in m["content"])
             for m in llm.calls[-1][1]]
    assert any("[a photo sent earlier] photo 0" in t for t in texts)


def test_not_an_image_is_refused(mk):
    b, _, _ = mk("plant")
    assert b.message("Asha", "x", b"definitely not a jpeg")["turns"][-2]["photo_refused"] == "unclear"


def test_screen_parser():
    assert parse_screen('{"category": "Plant", "reason": "leaf"}')["category"] == "plant"
    assert parse_screen("no idea")["category"] == "unclear"
    assert parse_screen('{"category": "dragon"}')["category"] == "unclear"


def test_photo_api(tmp_path):
    c = TestClient(create_app(PACKS, str(tmp_path / "a.db"), buddy_llm=PhotoLLM("object")))
    c.post("/api/buddy/Asha/consent", json={"parent_name": "L", "relation": "Mother", "agree": True, "grade": 6})
    c.post("/api/buddy/Asha/start")
    img = "data:image/jpeg;base64," + base64.b64encode(jpeg_with_gps((500, 400))).decode()
    assert c.post("/api/buddy/Asha/message", json={"text": "ice", "image": img}).status_code == 403   # no photo consent yet
    assert c.post("/api/buddy/Asha/consent_photos", json={"parent_name": "L", "agree": True}).json()["ok"]
    v = c.post("/api/buddy/Asha/message", json={"text": "ice", "image": img}).json()
    pid = v["turns"][-2]["photo"]
    r = c.get(f"/api/buddy/photo/{pid}")
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    assert c.get("/api/buddy/photo/../../etc").status_code == 404
    assert c.post("/api/buddy/Asha/message", json={"text": "x", "image": "data:image/jpeg;base64,@@@"}).status_code == 400
