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


def test_enhance_image_preview_is_in_memory(tmp_path):
    import image_enhance as ai

    src = tmp_path / "photo.jpg"
    Image.new("RGB", (90, 70), (100, 90, 80)).save(src, quality=90)
    before = src.read_bytes()
    with Image.open(src) as im:
        out = ai.enhance_image(im, ai.EnhanceSettings(upscale="4K"), preview_mode=True)
    assert out.mode == "RGB"
    assert max(out.size) <= 1200
    assert src.read_bytes() == before


def test_openai_multipart_uses_image_field(tmp_path):
    import image_enhance as ai

    src = tmp_path / "photo.jpg"
    src.write_bytes(b"fake-image")
    body, _boundary = ai._multipart_body({"prompt": "x"}, [("image", src)])
    assert b'name="image"; filename="photo.jpg"' in body
    assert b'name="image[]"' not in body
    assert b"response_format" not in body


def test_openai_prompt_uses_preset_and_slider_settings():
    import image_enhance as ai

    settings = ai.EnhanceSettings(brightness=1.25, saturation=1.5, upscale="2K")
    prompt = ai.build_openai_prompt(settings, "vivid")
    assert "colors" in prompt.lower()
    assert "brightness 1.25" in prompt
    assert "saturation 1.50" in prompt
    assert "upscale 2K" in prompt


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


def test_motion_preset_unknown_falls_back_to_auto():
    import studio_engine as se

    assert se.normalize_motion_preset("left_to_center") == "left_to_center"
    assert se.normalize_motion_preset("missing") == "auto"
    assert se._motion_spec("missing", 0)["preset"] == "auto"
    tiny = se._motion_spec("tiny_to_big", 0)
    assert tiny["start_scale"] == pytest.approx(0.45)
    assert tiny["end_scale"] == pytest.approx(1.10)
    custom = se._motion_spec(
        "tiny_to_big",
        0,
        settings={"start_scale": 0.3, "end_scale": 1.4, "speed": 0.5, "start_x": -0.2},
    )
    assert custom["start_scale"] == pytest.approx(0.3)
    assert custom["end_scale"] == pytest.approx(1.4)
    assert custom["speed"] == pytest.approx(0.5)
    assert custom["start_dx"] == pytest.approx(-384.0)


def test_motion_filters_use_stable_rounding():
    import studio_engine as se

    vf, _frames = se._vf(2.0, "in", 1, 0.2, 1280, 720, 60, False, 0.15, False, "tiny_to_big", 0)
    assert "scale=3840:-2:flags=lanczos+accurate_rnd" in vf
    assert "x='floor((" in vf
    assert "y='floor((" in vf


def test_background_motion_filter_uses_even_scale_and_rounded_overlay(monkeypatch, tmp_path):
    import studio_engine as se

    bg = tmp_path / "bg.jpg"
    photo = tmp_path / "photo.png"
    out = tmp_path / "scene.mkv"
    Image.new("RGB", (1280, 720), (20, 80, 130)).save(bg)
    Image.new("RGB", (640, 480), (180, 120, 80)).save(photo)
    calls = []
    monkeypatch.setattr(se, "_run", lambda cmd, cancel_event=None: calls.append(cmd))
    se.render_background_motion_scene(
        str(photo),
        str(bg),
        None,
        2.0,
        0,
        1280,
        720,
        60,
        False,
        False,
        str(out),
        "center",
        0.65,
        {"border": True, "shadow": True},
        "tiny_to_big",
        motion_settings={"start_scale": 0.45, "end_scale": 1.1, "speed": 0.55},
    )
    fc = calls[0][calls[0].index("-filter_complex") + 1]
    assert "2*floor" in fc
    assert "flags=lanczos+accurate_rnd" in fc
    assert "overlay=x='floor((" in fc


def test_build_video_passes_per_slide_motion_settings(monkeypatch, tmp_path):
    import studio_engine as se

    src = tmp_path / "photo.jpg"
    Image.new("RGB", (80, 60), (120, 100, 90)).save(src)
    captured = {}

    def fake_render_scene(*args, **kwargs):
        captured["motion"] = kwargs.get("motion") if "motion" in kwargs else args[-2]
        captured["motion_settings"] = kwargs.get("motion_settings") if "motion_settings" in kwargs else args[-1]
        Path(args[11]).write_text("clip", encoding="utf-8")

    monkeypatch.setattr(se, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(se, "render_scene", fake_render_scene)
    monkeypatch.setattr(se, "stitch", lambda *_args, **_kwargs: None)
    se.build_video(
        {
            "style": list(se.STYLES.keys())[0],
            "photos": [str(src)],
            "output": str(tmp_path / "out.mp4"),
            "music": str(tmp_path / "music.wav"),
            "text_enabled": False,
            "photo_motions": ["tiny_to_big"],
            "photo_motion_settings": [{"start_scale": 0.5, "end_scale": 1.25, "speed": 0.7}],
        }
    )
    assert captured["motion"] == "tiny_to_big"
    assert captured["motion_settings"]["start_scale"] == pytest.approx(0.5)
    assert captured["motion_settings"]["speed"] == pytest.approx(0.7)


def test_resolve_photo_durations_uses_overrides_and_minimum():
    import studio_engine as se

    assert se.resolve_photo_durations(4, 4.5, [6, None, 0.1]) == [6.0, 4.5, 0.4, 4.5]


def test_text_flags_disable_title_outro_and_captions():
    import studio_engine as se

    flags = se.resolve_text_flags(
        {"text_enabled": False, "show_title_card": True, "show_outro_card": True, "show_captions": True}
    )
    assert flags == {
        "text_enabled": False,
        "show_title_card": False,
        "show_outro_card": False,
        "show_captions": False,
    }


def test_font_preset_unknown_falls_back_to_default():
    import studio_engine as se

    style = se.STYLES[list(se.STYLES.keys())[0]]
    assert se.apply_font_preset(style, "missing")["fonts"] == style["fonts"]
    assert se.apply_font_preset(style, "modern")["fonts"]["title"] == "demi"


def test_stitch_single_clip_skips_xfade(monkeypatch, tmp_path):
    import studio_engine as se

    calls = []
    monkeypatch.setattr(se, "_run", lambda cmd, cancel_event=None: calls.append(cmd))
    clip = tmp_path / "clip.mkv"
    music = tmp_path / "music.wav"
    se.stitch([str(clip)], [1.0], 0.7, "fade", str(music), 23, "veryfast", 24, str(tmp_path / "out.mp4"))
    cmd = calls[0]
    assert "-filter_complex" not in cmd
    assert "-stream_loop" in cmd
    assert "-map" in cmd


def test_stitch_loops_short_music_for_multi_clip(monkeypatch, tmp_path):
    import studio_engine as se

    calls = []
    monkeypatch.setattr(se, "_run", lambda cmd, cancel_event=None: calls.append(cmd))
    clips = [str(tmp_path / f"clip{i}.mkv") for i in range(3)]
    music = tmp_path / "short.wav"
    se.stitch(clips, [1.4, 1.4, 1.4], 0.5, "fade", str(music), 23, "veryfast", 24, str(tmp_path / "out.mp4"))
    cmd = calls[0]
    assert "-filter_complex" in cmd
    loop_at = cmd.index("-stream_loop")
    assert cmd[loop_at + 1] == "-1"
    assert cmd[loop_at + 2] == "-i"
    assert cmd[loop_at + 3] == str(music)


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


def test_ai_history_jsonl_and_cost_estimate_respects_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("PVS_APPDATA", str(tmp_path))
    import pvs_storage
    import image_enhance as ai

    importlib.reload(pvs_storage)
    importlib.reload(ai)
    src = tmp_path / "photo.jpg"
    Image.new("RGB", (120, 90), (20, 80, 130)).save(src)
    settings = ai.EnhanceSettings(upscale="none")
    estimate = ai.estimate_openai_batch_cost([src], settings, model="gpt-image-2.5-sunburst", quality="low", preset="auto")
    assert estimate["uncached"] == 1
    assert estimate["estimated_cost"] > 0
    out = ai.cache_path(src, settings, "openai", ai.openai_cache_model("gpt-image-2.5-sunburst", "low", "auto"))
    out.write_bytes(b"cached")
    cached = ai.estimate_openai_batch_cost([src], settings, model="gpt-image-2.5-sunburst", quality="low", preset="auto")
    assert cached["cached"] == 1
    assert cached["estimated_cost"] == 0
    pvs_storage.append_ai_history({"provider": "openai", "source_path": str(src), "source_name": "photo.jpg", "status": "ok", "estimated_cost": 0.0123})
    rows = pvs_storage.list_ai_history()
    assert rows[0]["source_name"] == "photo.jpg"
    assert rows[0]["estimated_cost"] == pytest.approx(0.0123)
    pvs_storage.clear_ai_history()
    assert pvs_storage.list_ai_history() == []


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
    first = pvs_storage.load_template(pvs_storage.list_templates()[0])["data"]
    assert first["text_enabled"] is True
    assert "font_preset" in first
    assert "show_title_card" in first
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
