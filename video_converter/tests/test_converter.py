from pathlib import Path
import threading

import pytest

import video_converter.converter as converter
from video_converter.converter import (
    SUPPORTED_FORMATS,
    build_conversion_args,
    convert,
    _probe_duration_seconds,
    find_ffmpeg,
)


def test_supported_formats_nonempty():
    assert len(SUPPORTED_FORMATS) > 0
    assert "mp4" in SUPPORTED_FORMATS


def test_probe_duration_seconds_parses_hms():
    stderr = "Duration: 00:02:03.45, start: 0.000000, bitrate: 128 kb/s"
    assert _probe_duration_seconds(stderr) == pytest.approx(123.45)


def test_probe_duration_seconds_missing_returns_none():
    assert _probe_duration_seconds("no duration here") is None


def test_find_ffmpeg_returns_path_or_raises():
    # Environment-dependent: just check it doesn't crash unexpectedly.
    try:
        path = find_ffmpeg()
        assert Path(path).name.lower().startswith("ffmpeg")
    except Exception as exc:
        assert "ffmpeg" in str(exc).lower()


def test_build_conversion_args_mp4_default():
    args = build_conversion_args("mp4")
    assert "-vf" not in args  # no resolution/fps requested -> no filter chain
    assert "-c:v" in args and args[args.index("-c:v") + 1] == "libx264"
    assert "-crf" in args and args[args.index("-crf") + 1] == "23"  # Balanced default
    assert "-movflags" in args


def test_build_conversion_args_resolution_and_fps():
    args = build_conversion_args("mp4", resolution=2160, fps=60)
    vf = args[args.index("-vf") + 1]
    assert "scale=-2:2160" in vf
    assert "fps=60" in vf


def test_build_conversion_args_quality_presets_map_to_different_crf():
    high = build_conversion_args("mp4", quality="High quality")
    small = build_conversion_args("mp4", quality="Smaller file")
    high_crf = int(high[high.index("-crf") + 1])
    small_crf = int(small[small.index("-crf") + 1])
    assert high_crf < small_crf  # lower crf = higher quality


def test_build_conversion_args_webm_uses_vp9_and_opus():
    args = build_conversion_args("webm", quality="High quality")
    assert "-c:v" in args and args[args.index("-c:v") + 1] == "libvpx-vp9"
    assert "-c:a" in args and args[args.index("-c:a") + 1] == "libopus"


def test_build_conversion_args_gif_uses_palette_filter_complex():
    args = build_conversion_args("gif", resolution=480, quality="High quality")
    assert "-filter_complex" in args
    filt = args[args.index("-filter_complex") + 1]
    assert "palettegen" in filt and "paletteuse" in filt
    assert "scale=-2:480" in filt
    assert "max_colors=256" in filt
    assert "-an" in args


def test_build_conversion_args_gif_quality_changes_max_colors():
    high = build_conversion_args("gif", quality="High quality")
    small = build_conversion_args("gif", quality="Smaller file")
    high_filt = high[high.index("-filter_complex") + 1]
    small_filt = small[small.index("-filter_complex") + 1]
    assert "max_colors=256" in high_filt
    assert "max_colors=128" in small_filt


def test_build_conversion_args_avi_uses_mp3_audio_not_aac():
    args = build_conversion_args("avi")
    assert args[args.index("-c:a") + 1] == "libmp3lame"


def test_build_conversion_args_mov_gets_faststart_like_mp4():
    args = build_conversion_args("mov")
    assert "-movflags" in args
    assert args[args.index("-c:a") + 1] == "aac"


def test_build_conversion_args_mp3_is_audio_only():
    args = build_conversion_args("mp3")
    assert args[0] == "-vn"
    assert "-c:a" in args and args[args.index("-c:a") + 1] == "libmp3lame"


def test_build_conversion_args_wav_is_audio_only():
    args = build_conversion_args("wav")
    assert args == ["-vn", "-c:a", "pcm_s16le"]


def test_build_conversion_args_unknown_quality_falls_back_to_balanced():
    args = build_conversion_args("mp4", quality="not a real preset")
    assert args[args.index("-crf") + 1] == "23"


def test_convert_cancel_event_returns_cancelled(monkeypatch, tmp_path):
    class FakeProcess:
        def __init__(self):
            self.stdout = iter(["out_time_ms=1000000\n"])
            self.stderr = iter(["Duration: 00:00:02.00, start: 0.000000\n"])
            self.returncode = None
            self.terminated = False

        def terminate(self):
            self.terminated = True
            self.returncode = -15

        def kill(self):
            self.returncode = -9

        def wait(self, timeout=None):
            if self.returncode is None:
                self.returncode = 0
            return self.returncode

    monkeypatch.setattr(converter, "find_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(converter.subprocess, "Popen", lambda *args, **kwargs: FakeProcess())
    cancel_event = threading.Event()
    cancel_event.set()
    result = convert(tmp_path / "in.mov", tmp_path / "out.mp4", cancel_event=cancel_event)
    assert result.success is False
    assert result.returncode == -1
    assert "Bekor qilindi" in result.stderr_tail
