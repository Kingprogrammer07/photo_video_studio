import importlib
import os
from pathlib import Path

from PIL import Image


def test_settings_and_templates_use_appdata_override(tmp_path, monkeypatch):
    monkeypatch.setenv("PVS_APPDATA", str(tmp_path))
    import pvs_storage

    importlib.reload(pvs_storage)
    settings = pvs_storage.load_settings()
    settings["ai_consent"] = True
    pvs_storage.save_settings(settings)
    assert pvs_storage.load_settings()["ai_consent"] is True

    path = pvs_storage.save_template("Oilaviy test", {"photo_layout": "center"})
    loaded = pvs_storage.load_template(path)
    assert loaded["name"] == "Oilaviy test"
    assert loaded["data"]["photo_layout"] == "center"


def test_cache_key_changes_with_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("PVS_APPDATA", str(tmp_path))
    import image_enhance as ai

    src = tmp_path / "photo.jpg"
    Image.new("RGB", (80, 60), (120, 100, 90)).save(src)
    a = ai.EnhanceSettings(brightness=1.0)
    b = ai.EnhanceSettings(brightness=1.2)
    assert ai.cache_key(src, a, "local", "pillow") != ai.cache_key(src, b, "local", "pillow")


def test_local_enhance_writes_copy_without_touching_original(tmp_path, monkeypatch):
    monkeypatch.setenv("PVS_APPDATA", str(tmp_path))
    import image_enhance as ai

    src = tmp_path / "photo.jpg"
    Image.new("RGB", (90, 70), (100, 90, 80)).save(src, quality=90)
    before = src.read_bytes()
    out = tmp_path / "out.jpg"
    ai.enhance_local(src, out, ai.EnhanceSettings(upscale="none"))
    assert out.exists()
    assert src.read_bytes() == before


def test_openai_multipart_uses_image_field(tmp_path):
    import image_enhance as ai

    src = tmp_path / "photo.jpg"
    src.write_bytes(b"fake-image")
    body, _boundary = ai._multipart_body({"prompt": "x"}, [("image", src)])
    assert b'name="image"; filename="photo.jpg"' in body
    assert b'name="image[]"' not in body


def test_background_scene_composes_expected_size(tmp_path):
    import studio_engine as se

    bg = tmp_path / "bg.jpg"
    Image.new("RGB", (400, 220), (20, 80, 130)).save(bg)
    photo = Image.new("RGB", (120, 90), (200, 180, 160))
    scene = se.compose_background_scene(
        photo,
        bg,
        640,
        360,
        layout="center",
        scale=0.55,
        frame={"border": True, "shadow": True},
    )
    assert scene.size == (640, 360)
