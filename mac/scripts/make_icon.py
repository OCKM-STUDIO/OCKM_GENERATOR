#!/usr/bin/env python3
"""Regenerate the checked-in Mac icon from the original generated PNG."""
from pathlib import Path
import subprocess
import tempfile

mac = Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(prefix="ockm-icon-") as temp:
    icons = Path(temp) / "AppIcon.iconset"
    icons.mkdir()
    for points in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            pixels = str(points * scale)
            name = f"icon_{points}x{points}" + ("@2x" if scale == 2 else "") + ".png"
            subprocess.run(["sips", "-z", pixels, pixels, str(mac / "Assets/AppIcon.png"),
                            "--out", str(icons / name)], check=True)
    subprocess.run(["iconutil", "-c", "icns", str(icons), "-o", str(mac / "Assets/AppIcon.icns")], check=True)
