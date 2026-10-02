import importlib
import os
import threading
from pathlib import Path

import pytest
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


def test_background_and_template_metadata_ops(tmp_path, monkeypatch):
    monkeypatch.setenv("PVS_APPDATA", str(tmp_path))
    import pvs_storage

    importlib.reload(pvs_storage)
    src = tmp_path / "custom.jpg"
    Image.new("RGB", (120, 80), (20, 80, 130)).save(src)
    bg = pvs_storage.import_background(src)
    pvs_storage.favorite_background(bg, True)
    rows = pvs_storage.list_backgrounds(with_meta=True)
    assert rows[0]["favorite"] is True

    renamed = pvs_storage.rename_background(bg, "Family Blue")
    assert renamed.exists()
    assert not bg.exists()
    assert pvs_storage.list_backgrounds(with_meta=True)[0]["path"] == renamed

    preview = pvs_storage.templates_dir() / "preview.jpg"
    Image.new("RGB", (80, 45), (200, 180, 140)).save(preview)
    tpl = pvs_storage.save_template("My Template", {"photo_layout": "center"}, preview_path=preview)
    meta = pvs_storage.list_templates(with_meta=True)[0]
    assert meta["preview_path"] == str(preview)
    renamed_tpl = pvs_storage.rename_template(tpl, "Renamed Template")
    assert pvs_storage.load_template(renamed_tpl)["name"] == "Renamed Template"

    pvs_storage.delete_template(renamed_tpl)
    assert not renamed_tpl.exists()
    pvs_storage.delete_background(renamed)
    assert not renamed.exists()


def test_starter_pack_installs_once(tmp_path, monkeypatch):
    monkeypatch.setenv("PVS_APPDATA", str(tmp_path))
    import pvs_storage
    import starter_pack

    importlib.reload(pvs_storage)
    importlib.reload(starter_pack)
    assert starter_pack.install_if_needed() is True
    assert len(pvs_storage.list_backgrounds()) == 8
    assert len(pvs_storage.list_templates()) == 8
    names = {pvs_storage.load_template(path)["name"] for path in pvs_storage.list_templates()}
    assert "Oilaviy ko'k" in names
    assert starter_pack.install_if_needed() is False
    assert len(pvs_storage.list_backgrounds()) == 8
    assert len(pvs_storage.list_templates()) == 8


def test_build_video_cancel_event_stops_before_render():
    import studio_engine as se

    cancel_event = threading.Event()
    cancel_event.set()
    with pytest.raises(se.CancelledError):
        se.build_video(
            {"style": list(se.STYLES.keys())[0], "photos": [], "output": "unused.mp4"},
            cancel_event=cancel_event,
        )


def test_updater_version_compare():
    import updater

    assert updater.is_newer("0.3.1", "0.3.0") is True
    assert updater.is_newer("v1.0.0", "0.9.9") is True
    assert updater.is_newer("0.3.0", "0.3.0") is False
    assert updater.is_newer("0.2.9", "0.3.0") is False


def test_studio_engine_prefers_bundled_ffmpeg(monkeypatch, tmp_path):
    import studio_engine as se

    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_text("fake", encoding="utf-8")
    monkeypatch.setattr(se.runtime_paths, "find_bundled_ffmpeg", lambda: str(ffmpeg))
    monkeypatch.setattr(se.shutil, "which", lambda _name: None)
    se.FFMPEG = None
    assert se.find_ffmpeg() == str(ffmpeg)
    se.FFMPEG = None
