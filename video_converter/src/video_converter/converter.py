"""ffmpeg subprocess wrapper: build commands, run conversions, report progress."""

from __future__ import annotations

import re
import shutil
import subprocess
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

SUPPORTED_FORMATS = ("mp4", "mkv", "avi", "mov", "webm", "gif", "mp3", "wav")
AUDIO_ONLY_FORMATS = frozenset({"mp3", "wav"})

# Label -> target height in px. Width is derived to preserve the source
# aspect ratio (ffmpeg's scale=-2:H, which also rounds to an even width so
# H.264/VP9 encoders don't reject the frame size). None = keep source size.
RESOLUTIONS: dict[str, Optional[int]] = {
    "Original": None,
    "4K (2160p)": 2160,
    "2K / QHD (1440p)": 1440,
    "Full HD (1080p)": 1080,
    "HD (720p)": 720,
}

FRAME_RATES: dict[str, Optional[int]] = {
    "Original": None,
    "24 fps": 24,
    "30 fps": 30,
    "60 fps": 60,
    "90 fps": 90,
    "120 fps": 120,
}

QUALITY_PRESETS = ("High quality", "Balanced", "Smaller file")

# (crf, x264/x265 preset) — lower crf = higher quality/bigger file.
_X264_QUALITY = {
    "High quality": (18, "slow"),
    "Balanced": (23, "medium"),
    "Smaller file": (28, "fast"),
}

# VP9 constant-quality mode: -crf N -b:v 0. Lower crf = higher quality.
_VP9_CRF = {
    "High quality": 24,
    "Balanced": 32,
    "Smaller file": 40,
}

# libmp3lame VBR quality (-q:a): 0 = best/largest, 9 = worst/smallest.
_MP3_QUALITY = {
    "High quality": "0",
    "Balanced": "4",
    "Smaller file": "7",
}

# palettegen max_colors: gif is limited to a 256-color palette anyway, so
# "quality" here trades palette size (and thus banding) for file size.
_GIF_MAX_COLORS = {
    "High quality": 256,
    "Balanced": 192,
    "Smaller file": 128,
}

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)")
_TIME_RE = re.compile(r"out_time_ms=(\d+)")


class FfmpegNotFoundError(RuntimeError):
    """Raised when the ffmpeg binary cannot be located on PATH."""


@dataclass
class ConversionResult:
    success: bool
    returncode: int
    stderr_tail: str


def find_ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise FfmpegNotFoundError(
            "ffmpeg not found on PATH. Install it and ensure ffmpeg.exe is reachable."
        )
    return path


def _probe_duration_seconds(stderr_so_far: str) -> Optional[float]:
    match = _DURATION_RE.search(stderr_so_far)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def build_conversion_args(
    output_format: str,
    *,
    resolution: Optional[int] = None,
    fps: Optional[int] = None,
    quality: str = "Balanced",
) -> list[str]:
    """Build ffmpeg args (everything between `-i input` and the output path)
    for the requested output format, resolution (target height, aspect
    preserved), frame rate, and quality preset.
    """
    output_format = output_format.lower().lstrip(".")
    if quality not in QUALITY_PRESETS:
        quality = "Balanced"

    if output_format in AUDIO_ONLY_FORMATS:
        if output_format == "mp3":
            return ["-vn", "-c:a", "libmp3lame", "-q:a", _MP3_QUALITY[quality]]
        return ["-vn", "-c:a", "pcm_s16le"]  # wav

    vf_parts = []
    if resolution:
        vf_parts.append(f"scale=-2:{resolution}:flags=lanczos")
    if fps:
        vf_parts.append(f"fps={fps}")
    vf_chain = ",".join(vf_parts)

    if output_format == "gif":
        prefix = f"{vf_chain}," if vf_chain else ""
        max_colors = _GIF_MAX_COLORS[quality]
        return [
            "-filter_complex",
            f"[0:v]{prefix}split[a][b];"
            f"[a]palettegen=max_colors={max_colors}:stats_mode=diff[p];"
            "[b][p]paletteuse=dither=bayer",
            "-loop",
            "0",
            "-an",
        ]

    args: list[str] = []
    if vf_chain:
        args += ["-vf", vf_chain]

    if output_format == "webm":
        args += [
            "-c:v",
            "libvpx-vp9",
            "-crf",
            str(_VP9_CRF[quality]),
            "-b:v",
            "0",
            "-row-mt",
            "1",
            "-c:a",
            "libopus",
            "-b:a",
            "128k",
        ]
    else:
        crf, preset = _X264_QUALITY[quality]
        args += [
            "-c:v",
            "libx264",
            "-crf",
            str(crf),
            "-preset",
            preset,
            "-pix_fmt",
            "yuv420p",
        ]
        if output_format == "avi":
            # AVI is a legacy container; many players only recognize
            # MP3/PCM/AC3 audio in it and won't play (or will mis-sync)
            # an AAC track, even though ffmpeg itself muxes it fine.
            args += ["-c:a", "libmp3lame", "-b:a", "192k"]
        else:
            args += ["-c:a", "aac", "-b:a", "192k"]
        if output_format in ("mp4", "mov"):
            args += ["-movflags", "+faststart"]

    return args


def convert(
    input_path: Path,
    output_path: Path,
    *,
    on_progress: Optional[Callable[[float], None]] = None,
    extra_args: Optional[list[str]] = None,
    cancel_event: Optional[threading.Event] = None,
) -> ConversionResult:
    """Convert input_path to output_path via ffmpeg.

    on_progress receives a 0.0-1.0 fraction estimate when the source
    duration can be parsed from ffmpeg's stderr banner; otherwise it is
    called with 0.0 once at start and 1.0 on completion.
    """
    ffmpeg = find_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        *(extra_args or []),
        "-progress",
        "pipe:1",
        "-nostats",
        str(output_path),
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None and process.stderr is not None

    stderr_lines: list[str] = []
    duration_seconds: Optional[float] = None

    def _drain_stderr() -> None:
        nonlocal duration_seconds
        for line in process.stderr:
            stderr_lines.append(line.rstrip())
            if duration_seconds is None:
                duration_seconds = _probe_duration_seconds(line)

    stderr_thread = threading.Thread(target=_drain_stderr, daemon=True)
    stderr_thread.start()

    if on_progress:
        on_progress(0.0)

    for line in process.stdout:
        if cancel_event is not None and cancel_event.is_set():
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            stderr_thread.join(timeout=1)
            return ConversionResult(False, -1, "Bekor qilindi")
        time_match = _TIME_RE.search(line)
        if time_match and on_progress and duration_seconds:
            elapsed = int(time_match.group(1)) / 1_000_000
            on_progress(min(elapsed / duration_seconds, 1.0))

    if cancel_event is not None and cancel_event.is_set():
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        stderr_thread.join(timeout=1)
        return ConversionResult(False, -1, "Bekor qilindi")

    process.wait()
    stderr_thread.join()

    if on_progress and process.returncode == 0:
        on_progress(1.0)

    tail = "\n".join(stderr_lines[-15:])
    return ConversionResult(
        success=process.returncode == 0, returncode=process.returncode, stderr_tail=tail
    )
