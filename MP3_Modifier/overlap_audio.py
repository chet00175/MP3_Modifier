import argparse
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
import subprocess
import sys


BACKGROUND_VOLUME = 0.30
OVERLAY_VOLUME = 1.0


def parse_timestamp(value):
    parts = value.split(":")
    if len(parts) > 3 or not all(re.fullmatch(r"[0-9]+", part) for part in parts[:-1]):
        raise ValueError(value)
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", parts[-1]):
        raise ValueError(value)

    seconds = Decimal(parts[-1])
    if len(parts) > 1 and seconds >= 60:
        raise ValueError(value)
    if len(parts) == 3 and int(parts[1]) >= 60:
        raise ValueError(value)

    for position, part in enumerate(reversed(parts[:-1]), start=1):
        seconds += Decimal(part) * (60 ** position)
    return seconds


def get_audio_duration(path):
    command = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        duration = Decimal(result.stdout.strip())
    except FileNotFoundError as error:
        raise RuntimeError("ffprobe was not found") from error
    except (subprocess.CalledProcessError, InvalidOperation) as error:
        raise RuntimeError(f"ffprobe could not read the duration of {path}") from error

    if not duration.is_finite() or duration <= 0:
        raise RuntimeError(f"ffprobe reported an invalid duration for {path}")
    return duration


def validate_overlay_times(times, overlay_duration, main_duration):
    ordered = sorted(times)
    for index, start in enumerate(ordered):
        if start >= main_duration:
            raise ValueError(f"overlay start {start} is at or after the end of the main audio")
        if index and start < ordered[index - 1] + overlay_duration:
            raise ValueError("overlay occurrences overlap")
    return ordered


def build_filter_graph(times, overlay_duration):
    intervals = "+".join(
        f"gte(t,{start})*lt(t,{start + overlay_duration})" for start in times
    )
    filters = [
        f"[0:a]asetpts=PTS-STARTPTS,volume='if({intervals},{BACKGROUND_VOLUME},1)':eval=frame[main]"
    ]

    if len(times) == 1:
        filters.append("[1:a]asetpts=PTS-STARTPTS[overlay0]")
    else:
        copies = "".join(f"[overlay{index}]" for index in range(len(times)))
        filters.append(f"[1:a]asetpts=PTS-STARTPTS,asplit={len(times)}{copies}")

    for index, start in enumerate(times):
        filters.append(
            f"[overlay{index}]adelay={start}s:all=1,"
            f"volume={OVERLAY_VOLUME}[delayed{index}]"
        )

    inputs = "[main]" + "".join(f"[delayed{index}]" for index in range(len(times)))
    filters.append(f"{inputs}amix=inputs={len(times) + 1}:duration=first:normalize=0[out]")
    return ";".join(filters)


def run_ffmpeg(main_path, overlay_path, output_path, times, overlay_duration):
    command = [
        "ffmpeg", "-y", "-i", str(main_path), "-i", str(overlay_path),
        "-filter_complex", build_filter_graph(times, overlay_duration),
        "-map", "[out]", "-c:a", "libmp3lame", "-f", "mp3", str(output_path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True)
    except FileNotFoundError as error:
        raise RuntimeError("ffmpeg was not found") from error
    if result.returncode != 0:
        raise RuntimeError("ffmpeg failed to combine the audio files")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("main", help="Main MP3 file")
    parser.add_argument("overlay", help="MP3 file to play over the main audio")
    parser.add_argument(
        "--at", action="append", required=True, metavar="TIME",
        help="Time at which to start the overlay; may be specified multiple times",
    )
    parser.add_argument(
        "-o", "--output", default="result.mp3",
        help="Output MP3 file (default: result.mp3)",
    )
    args = parser.parse_args()

    main_path = Path(args.main)
    overlay_path = Path(args.overlay)
    output_path = Path(args.output)
    if not main_path.is_file():
        parser.error(f"main file not found: {main_path}")
    if not overlay_path.is_file():
        parser.error(f"overlay file not found: {overlay_path}")
    if output_path.exists() and (
        output_path.samefile(main_path) or output_path.samefile(overlay_path)
    ):
        parser.error("output path must differ from both input paths")

    times = []
    for value in args.at:
        try:
            times.append(parse_timestamp(value))
        except ValueError:
            parser.error(f"invalid timestamp: {value}")

    try:
        main_duration = get_audio_duration(main_path)
        overlay_duration = get_audio_duration(overlay_path)
        times = validate_overlay_times(times, overlay_duration, main_duration)
        run_ffmpeg(main_path, overlay_path, output_path, times, overlay_duration)
    except ValueError as error:
        parser.error(str(error))
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Created {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
