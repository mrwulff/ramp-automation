import subprocess
import os
from svgpathtools import svg2paths, wsvg, Path, Line, CubicBezier

# ---------- CONFIG ----------
BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"

MIN_SEGMENT_LENGTH = 0.002  # tweak if needed
SIMPLIFY_TOLERANCE = 0.025  # gentle only


# ---------- SVG CLEAN ----------
def segment_length(seg):
    return abs(seg.end - seg.start)


def simplify_segment(seg):
    # Only collapse VERY straight curves
    if isinstance(seg, CubicBezier):
        if (
            abs(seg.control1 - seg.start) < SIMPLIFY_TOLERANCE
            and abs(seg.control2 - seg.end) < SIMPLIFY_TOLERANCE
        ):
            return Line(seg.start, seg.end)
    return seg


def clean_svg(input_svg, output_svg):
    paths, attrs = svg2paths(input_svg)

    cleaned = []

    for p in paths:
        new_segments = []

        for seg in p:
            # 🔥 remove micro junk only
            if segment_length(seg) < MIN_SEGMENT_LENGTH:
                continue

            new_segments.append(simplify_segment(seg))

        if len(new_segments) < 2:
            continue

        cleaned.append(Path(*new_segments))

    print(f"[SVG] paths: {len(paths)} → {len(cleaned)}")

    wsvg(cleaned, filename=output_svg)


# ---------- BLENDER RUN ----------
def run_blender(svg, stl):
    cmd = [BLENDER, "-b", "-P", "wtf/process_svg.py", "--", svg, stl]

    subprocess.run(cmd, check=True)


# ---------- MAIN ----------
def main():
    input_svg = "input.svg"
    cleaned_svg = "clean.svg"
    output_stl = "output.stl"

    clean_svg(input_svg, cleaned_svg)
    run_blender(cleaned_svg, output_stl)


if __name__ == "__main__":
    main()
