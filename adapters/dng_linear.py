"""DNG stage-3 -> ProPhoto-encoded uint16 TIFF for the film CLI.

usage: dng_linear.py IN.dng OUT.tif [EV] [SAT]

Reads AnalogBalance, ColorMatrix2 and Orientation from `dng_validate -v`.
Reads pixels from `dng_validate -3` (stage 3). This is the SDK stage-3 dump,
not the final `-tif` render implemented in indigo_dng.py.

Requires a user-supplied Adobe DNG SDK `dng_validate`. Set DNG_VALIDATE, or
place the binary at adapters/bin/dng_validate. This repository does not ship
that binary. See adapters/DNG.md.

EV defaults to 0 and SAT defaults to 1. The TIFF ImageDescription is
"ProPhoto RGB" so film.py can decode it. No Kodak ICC profile is embedded.
"""
import sys, re, subprocess, tempfile, os
from pathlib import Path
import numpy as np, tifffile
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from indigo_dng import encode_prophoto, DESCRIPTION
DV = os.environ.get("DNG_VALIDATE") or str(HERE / "bin" / "dng_validate")
if len(sys.argv) < 3:
    sys.exit("usage: dng_linear.py IN.dng OUT.tif [EV] [SAT]")
if not (os.path.isfile(DV) and os.access(DV, os.X_OK)):
    sys.exit(
        f"dng_validate is not an executable file: {DV}\n"
        "Download the Adobe DNG SDK yourself and set DNG_VALIDATE. See adapters/DNG.md."
    )
dng, out = sys.argv[1], sys.argv[2]
ev = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
s = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
meta = subprocess.run([DV, "-v", dng], capture_output=True, text=True)
if meta.returncode != 0:
    sys.exit(f"dng_validate -v failed ({meta.returncode}):\n{meta.stderr[-2000:]}")
txt = meta.stdout
ab = re.search(r"AnalogBalance:\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)", txt)
AB = np.diag([float(x) for x in ab.groups()]) if ab else np.eye(3)
m = re.search(r"ColorMatrix2:\s*\n" + r"\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\n" * 3, txt)
CM2 = np.array([float(x) for x in m.groups()]).reshape(3, 3)
o = re.search(r"Orientation:\s*(\d)", txt); ori = int(o.group(1)) if o else 1
td = tempfile.mkdtemp(); st = os.path.join(td, "st3")
stage = subprocess.run([DV, "-3", st, dng], capture_output=True, text=True)
stage_tif = st + ".tif"
if stage.returncode != 0 or not os.path.isfile(stage_tif):
    sys.exit(f"dng_validate -3 failed ({stage.returncode}):\n{stage.stderr[-2000:]}\n{stage.stdout[-2000:]}")
a = tifffile.imread(stage_tif).astype(np.float32) / 65535
os.remove(stage_tif); os.rmdir(td)
c2x = np.linalg.inv(AB @ CM2)
d65 = np.array([0.95047, 1, 1.08883]); c2x = np.diag(d65 / (c2x @ np.ones(3))) @ c2x
B = np.array([[0.8951, 0.2664, -0.1614], [-0.7502, 1.7135, 0.0367], [0.0389, -0.0685, 1.0296]])
d50 = np.array([0.96422, 1, 0.82521]); cat = np.linalg.inv(B) @ np.diag((B @ d50) / (B @ d65)) @ B
X2P = np.linalg.inv(np.array([[0.7977, 0.1352, 0.0313], [0.2880, 0.7119, 0.0001], [0, 0, 0.8249]]))
a = np.clip(a @ (X2P @ cat @ c2x).T.astype(np.float32), 0, None) * np.float32(2 ** ev)
a = {1: a, 3: np.rot90(a, 2), 6: np.rot90(a, -1), 8: np.rot90(a, 1)}.get(ori, a)
Y = (a * np.array([0.2880, 0.7119, 0.0001], np.float32)).sum(2, keepdims=True)
a = np.clip(Y + (a - Y) * s, 0, None)
print("orientation", ori, "L pct", [round(float(np.percentile(a.mean(2), p)), 3) for p in (10, 50, 95, 99.9)], "clip", round(float((a.max(2) > 1).mean()), 4))
tifffile.imwrite(out, encode_prophoto(np.clip(a, 0, 1)), photometric="rgb", compression="zlib", description=DESCRIPTION)
