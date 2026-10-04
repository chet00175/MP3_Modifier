import os
import re
import subprocess
import sys


def parse_time(value):
    if not re.fullmatch(r"[0-9]+:[0-5][0-9]", value):
        raise ValueError(value)

    minutes, seconds = value.split(":")
    return int(minutes) * 60 + int(seconds)


def main():
    if len(sys.argv) != 4:
        print("Usage:\n  py main.py INPUT_FILE START END\n\nExample:\n  py main.py song.mp3 1:20 3:22")
        return 1

    input_file, start_value, end_value = sys.argv[1:]
    if not os.path.isfile(input_file):
        print(f"Error: input file not found: {input_file}")
        return 1

    try:
        start = parse_time(start_value)
        end = parse_time(end_value)
    except ValueError as error:
        print(f"Error: invalid timestamp: {error}")
        return 1

    if end <= start:
        print("Error: end time must be after start time.")
        return 1

    output_file = "result.mp3"
    if os.path.exists(output_file) and os.path.samefile(input_file, output_file):
        print("Error: input file cannot be result.mp3.")
        return 1

    command = [
        "ffmpeg", "-y", "-ss", str(start), "-i", input_file,
        "-t", str(end - start), "-c:a", "libmp3lame", "-q:a", "2", output_file,
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("Error: ffmpeg was not found.")
        return 1

    if result.returncode != 0:
        print("Error: ffmpeg failed to trim the input file.")
        return 1

    print("Created result.mp3")
    return 0


if __name__ == "__main__":
    sys.exit(main())
