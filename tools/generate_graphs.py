#!/usr/bin/env python3
"""Generate small illustrative graphs for the README.

Creates `docs/graphs/architecture.png` and `docs/graphs/regression_results.png`.
Uses Pillow which is already in `requirements.txt`.
"""
import os
from PIL import Image, ImageDraw, ImageFont


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def draw_architecture(path: str):
    w, h = 900, 400
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)

    # simple boxes representing frontend/backend/calendar
    boxes = [
        (50, 120, 280, 260, "Frontend"),
        (340, 50, 560, 320, "Orchestrator / Agents"),
        (640, 120, 870, 260, "Calendar Service")
    ]

    for x1, y1, x2, y2, label in boxes:
        d.rectangle([x1, y1, x2, y2], outline="black", width=3)
        fw = ImageFont.load_default()
        bbox = d.textbbox((0, 0), label, font=fw)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        d.text(((x1 + x2 - tw) / 2, (y1 + y2 - th) / 2), label, fill="black", font=fw)

    # arrows
    d.line((280, 190, 340, 170), fill="black", width=2)
    d.line((560, 170, 640, 190), fill="black", width=2)

    img.save(path)


def draw_regression_chart(path: str):
    # Simple bar chart showing 6/6 passing
    w, h = 800, 400
    img = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(img)
    fw = ImageFont.load_default()

    title = "Deterministic Regression"
    d.text((20, 10), title, fill="black", font=fw)

    labels = ["remove","today","all","create-title","then-9pm","no"]
    values = [1,1,1,1,1,1]

    maxv = max(values)
    margin = 60
    bar_w = 80
    gap = 20
    start_x = 40
    base_y = 320

    for i, (lab, val) in enumerate(zip(labels, values)):
        x = start_x + i * (bar_w + gap)
        hbar = int((val / maxv) * 200)
        d.rectangle([x, base_y - hbar, x + bar_w, base_y], fill=(30,144,255))
        bbox = d.textbbox((0, 0), lab, font=fw)
        tw = bbox[2] - bbox[0]
        d.text((x + (bar_w - tw) / 2, base_y + 8), lab, fill="black", font=fw)

    # annotate score
    d.text((600, 60), "Passed: 6/6", fill="green", font=fw)

    img.save(path)


def main():
    outdir = os.path.join("docs", "graphs")
    ensure_dir(outdir)
    arch = os.path.join(outdir, "architecture.png")
    reg = os.path.join(outdir, "regression_results.png")
    print("Writing:", arch)
    draw_architecture(arch)
    print("Writing:", reg)
    draw_regression_chart(reg)


if __name__ == "__main__":
    main()
