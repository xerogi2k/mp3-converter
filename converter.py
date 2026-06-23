#!/usr/bin/env python3
"""Download YouTube audio and convert it to high-quality MP3."""

from __future__ import annotations

import argparse
from collections import Counter
import re
import shutil
import sys
import time
from pathlib import Path


QUALITY_PRESETS = {
    "best": "320",
    "high": "256",
    "medium": "192",
}

DEFAULT_OUTPUT_DIR = "/Users/xerogi/Documents/Music/Beats"
DEFAULT_BPM_MIN = 120
DEFAULT_BPM_MAX = 180

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
KEY_NAMES = ("C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B")
MAJOR_PROFILE = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
MINOR_PROFILE = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
CAMELot_MAJOR = {
    "C": "8B",
    "C#": "3B",
    "D": "10B",
    "Eb": "5B",
    "E": "12B",
    "F": "7B",
    "F#": "2B",
    "G": "9B",
    "Ab": "4B",
    "A": "11B",
    "Bb": "6B",
    "B": "1B",
}
CAMELot_MINOR = {
    "C": "5A",
    "C#": "12A",
    "D": "7A",
    "Eb": "2A",
    "E": "9A",
    "F": "4A",
    "F#": "11A",
    "G": "6A",
    "Ab": "1A",
    "A": "8A",
    "Bb": "3A",
    "B": "10A",
}

EXTRA_OUTPUT_SUFFIXES = (".analysis.txt", ".jpg", ".jpeg", ".png", ".webp")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert YouTube links to high-quality MP3 files.",
    )
    parser.add_argument("url", nargs="?", help="YouTube video URL")
    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output folder. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "-q",
        "--quality",
        choices=QUALITY_PRESETS,
        default="best",
        help="MP3 bitrate preset. Default: best (320 kbps)",
    )
    parser.add_argument(
        "--playlist",
        action="store_true",
        help="Download the whole playlist if the URL is a playlist.",
    )
    parser.add_argument(
        "--cookies",
        help="Path to a cookies.txt file for age-restricted/private videos.",
    )
    parser.add_argument(
        "--no-thumbnail",
        action="store_true",
        help="Do not embed the video thumbnail into the MP3.",
    )
    parser.add_argument(
        "--bpm-min",
        type=int,
        default=DEFAULT_BPM_MIN,
        help=f"Lowest preferred BPM for beat analysis. Default: {DEFAULT_BPM_MIN}",
    )
    parser.add_argument(
        "--bpm-max",
        type=int,
        default=DEFAULT_BPM_MAX,
        help=f"Highest preferred BPM for beat analysis. Default: {DEFAULT_BPM_MAX}",
    )
    return parser.parse_args()


def ensure_dependencies() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit(
            "ffmpeg is not installed or not in PATH.\n"
            "Install it first:\n"
            "  macOS: brew install ffmpeg\n"
            "  Ubuntu/Debian: sudo apt install ffmpeg\n"
            "  Windows: winget install Gyan.FFmpeg"
        )

    try:
        import yt_dlp  # noqa: F401
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "yt-dlp is not installed for this Python environment.\n"
            "Install project dependencies:\n"
            "  python3 -m pip install -r requirements.txt"
        ) from exc

    try:
        import librosa  # noqa: F401
        import mutagen  # noqa: F401
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Audio analysis dependencies are not installed.\n"
            "Install project dependencies:\n"
            "  .venv/bin/python -m pip install -r requirements.txt"
        ) from exc


def build_options(args: argparse.Namespace) -> dict:
    output_dir = Path(args.output).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    postprocessors = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": QUALITY_PRESETS[args.quality],
        },
        {
            "key": "FFmpegMetadata",
            "add_metadata": True,
        },
    ]

    if not args.no_thumbnail:
        postprocessors.append({"key": "EmbedThumbnail"})

    options = {
        "format": "bestaudio/best",
        "outtmpl": str(output_dir / "%(title).200B [%(id)s].%(ext)s"),
        "noplaylist": not args.playlist,
        "postprocessors": postprocessors,
        "writethumbnail": not args.no_thumbnail,
        "quiet": False,
        "no_warnings": False,
    }

    if args.cookies:
        options["cookiefile"] = str(Path(args.cookies).expanduser().resolve())

    return options


def find_new_mp3_files(output_dir: Path, started_at: float) -> list[Path]:
    return sorted(
        (path for path in output_dir.glob("*.mp3") if path.stat().st_mtime >= started_at),
        key=lambda path: path.stat().st_mtime,
    )


def sanitize_folder_name(name: str) -> str:
    clean = re.sub(r'[<>:"/\\|?*\0-\31]', "_", name).strip(" .")
    clean = re.sub(r"\s+", " ", clean)
    return clean[:120] or "Untitled Beat"


def strip_youtube_id_suffix(stem: str) -> str:
    match = re.match(r"^(?P<title>.+?)\s+\[[A-Za-z0-9_-]{6,}\]$", stem)
    return match.group("title") if match else stem


def unique_destination(path: Path) -> Path:
    if not path.exists():
        return path

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    return path.with_name(f"{path.stem} ({timestamp}){path.suffix}")


def move_related_files_to_track_folder(mp3_path: Path) -> Path:
    output_dir = mp3_path.parent
    clean_stem = sanitize_folder_name(strip_youtube_id_suffix(mp3_path.stem))
    track_folder = output_dir / clean_stem
    track_folder.mkdir(parents=True, exist_ok=True)

    destination = unique_destination(track_folder / f"{clean_stem}{mp3_path.suffix}")

    shutil.move(str(mp3_path), str(destination))

    for suffix in EXTRA_OUTPUT_SUFFIXES:
        related = output_dir / f"{mp3_path.stem}{suffix}"
        if related.exists():
            if suffix == ".analysis.txt":
                related_destination = track_folder / f"{clean_stem}.analysis.txt"
            else:
                related_destination = track_folder / f"{clean_stem}{related.suffix}"
            related_destination = unique_destination(related_destination)
            shutil.move(str(related), str(related_destination))

    return destination


def estimate_key(chroma_vector) -> tuple[str, str]:
    import numpy as np

    chroma = np.asarray(chroma_vector, dtype=float)
    chroma = chroma / (np.linalg.norm(chroma) or 1.0)

    best_score = float("-inf")
    best_root = 0
    best_mode = "Major"

    for root in range(12):
        major = np.roll(np.asarray(MAJOR_PROFILE, dtype=float), root)
        minor = np.roll(np.asarray(MINOR_PROFILE, dtype=float), root)

        major = major / np.linalg.norm(major)
        minor = minor / np.linalg.norm(minor)

        major_score = float(np.dot(chroma, major))
        minor_score = float(np.dot(chroma, minor))

        if major_score > best_score:
            best_score = major_score
            best_root = root
            best_mode = "Major"

        if minor_score > best_score:
            best_score = minor_score
            best_root = root
            best_mode = "Minor"

    key_root = KEY_NAMES[best_root]
    camelot = CAMELot_MAJOR[key_root] if best_mode == "Major" else CAMELot_MINOR[key_root]
    return f"{key_root} {best_mode}", camelot


def normalize_tempo_candidates(bpm: float, bpm_min: int, bpm_max: int) -> list[tuple[int, float]]:
    variants = [
        (bpm, 2.0),
        (bpm * 2, 0.88),
        (bpm / 2, 0.80),
        # Some beat detectors lock to a 3-against-2 pulse. Keeping this with a
        # lower weight helps cases like 96 -> 144 without overpowering normal tempos.
        (bpm * 1.5, 0.22),
        (bpm / 1.5, 0.18),
    ]

    candidates = []
    for value, weight in variants:
        rounded = int(round(float(value)))
        if bpm_min - 5 <= rounded < bpm_min:
            rounded = bpm_min
        elif bpm_max < rounded <= bpm_max + 5:
            rounded = bpm_max
        if bpm_min <= rounded <= bpm_max:
            candidates.append((rounded, weight))
    return candidates


def estimate_bpm(y, sr: int, bpm_min: int, bpm_max: int) -> tuple[int, list[int]]:
    import librosa
    import numpy as np

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    raw_tempos: list[float] = []

    for start_bpm in (90, 120, 140, 160):
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env, start_bpm=start_bpm)
        raw_tempos.append(float(np.atleast_1d(tempo)[0]))

    frame_tempos = librosa.feature.tempo(
        onset_envelope=onset_env,
        sr=sr,
        start_bpm=140,
        max_tempo=240,
        aggregate=None,
    )
    if len(frame_tempos):
        raw_tempos.extend(
            [
                float(np.median(frame_tempos)),
                float(np.percentile(frame_tempos, 25)),
                float(np.percentile(frame_tempos, 75)),
            ]
        )

    scores: Counter[int] = Counter()
    for raw_tempo in raw_tempos:
        if raw_tempo <= 0:
            continue
        for candidate, weight in normalize_tempo_candidates(raw_tempo, bpm_min, bpm_max):
            # Prefer the middle of the requested producer BPM range when two
            # mathematically related pulses have similar evidence.
            target_midpoint = (bpm_min + bpm_max) / 2
            midpoint_bonus = 1 - min(abs(candidate - target_midpoint) / max(target_midpoint, 1), 0.25)
            scores[candidate] += weight * midpoint_bonus

    if not scores:
        return 0, []

    ranked = [bpm for bpm, _ in scores.most_common()]
    return ranked[0], ranked[:5]


def analyze_mp3(path: Path, bpm_min: int, bpm_max: int) -> dict[str, str | int]:
    import librosa
    import numpy as np

    y, sr = librosa.load(path, mono=True, sr=22050)
    bpm, bpm_candidates = estimate_bpm(y, sr, bpm_min, bpm_max)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    key, alt_key = estimate_key(np.mean(chroma, axis=1))

    return {
        "bpm": bpm,
        "bpm_candidates": ", ".join(str(candidate) for candidate in bpm_candidates),
        "key": key,
        "alt_key": alt_key,
    }


def write_analysis_files(path: Path, analysis: dict[str, str | int], source_url: str) -> None:
    from mutagen.id3 import ID3, ID3NoHeaderError, TBPM, TKEY, TXXX

    try:
        try:
            id3 = ID3(path)
        except ID3NoHeaderError:
            id3 = ID3()
        id3.delall("TBPM")
        id3.delall("TKEY")
        id3.delall("TXXX:Alt Key")
        id3.add(TBPM(encoding=3, text=str(analysis["bpm"])))
        id3.add(TKEY(encoding=3, text=str(analysis["key"])))
        id3.add(TXXX(encoding=3, desc="Alt Key", text=str(analysis["alt_key"])))
        id3.save(path)
    except Exception as exc:
        print(f"Could not write ID3 tags for {path.name}: {exc}", file=sys.stderr)

    sidecar = path.with_suffix(".analysis.txt")
    sidecar.write_text(
        "\n".join(
            [
                f"Source URL: {source_url}",
                f"File: {path.name}",
                f"BPM: {analysis['bpm']}",
                f"BPM Candidates: {analysis['bpm_candidates']}",
                f"Key: {analysis['key']}",
                f"Alt Key: {analysis['alt_key']}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def print_analysis(path: Path, analysis: dict[str, str | int]) -> None:
    print("\nAnalysis")
    print(f"  File: {path.name}")
    print(f"  BPM: {analysis['bpm']}")
    print(f"  BPM Candidates: {analysis['bpm_candidates']}")
    print(f"  Key: {analysis['key']}")
    print(f"  Alt Key: {analysis['alt_key']}")


def convert(url: str, options: dict, output_dir: Path) -> list[Path]:
    from yt_dlp import YoutubeDL

    started_at = time.time()
    with YoutubeDL(options) as ydl:
        ydl.download([url])

    return find_new_mp3_files(output_dir, started_at)


def main() -> int:
    args = parse_args()

    if not args.url:
        args.url = input("Paste YouTube link: ").strip()
        if not args.url:
            print("No link provided.", file=sys.stderr)
            return 2

    ensure_dependencies()

    try:
        output_dir = Path(args.output).expanduser().resolve()
        mp3_files = convert(args.url, build_options(args), output_dir)

        if not mp3_files:
            print("\nMP3 saved, but the final filename could not be detected for analysis.")
        else:
            for mp3_file in mp3_files:
                print(f"\nAnalyzing: {mp3_file.name}")
                analysis = analyze_mp3(mp3_file, args.bpm_min, args.bpm_max)
                write_analysis_files(mp3_file, analysis, args.url)
                final_mp3_file = move_related_files_to_track_folder(mp3_file)
                print_analysis(final_mp3_file, analysis)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"\nConversion failed: {exc}", file=sys.stderr)
        return 1

    print("\nDone. MP3 file saved successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
