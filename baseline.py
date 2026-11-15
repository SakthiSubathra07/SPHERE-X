"""
baseline.py - a simple mover finder with NO machine learning.

Idea: line up the frames, subtract the average image, then look for the
brightest leftover spot in each frame. If the same object moves, the spot
shifts from frame to frame.

Run (needs internet):
    python baseline.py --name "Barnard's Star"
    python baseline.py --ra 08h55m10.831s --dec -7d14m42.53s --band SPHEREx-D2

Warning: a star that gets brighter or fainter between frames (SPHEREx frames
have different wavelengths) can also leave a leftover spot. So treat the output
as a hint to look at the picture, not as proof.
"""
import argparse

import numpy as np

from fetch import fetch_cutouts, parse_coord
from processing import align_frames, marker_pixels, subtract_median


def find_peaks(frames, k=5.0):
    """For each frame, the brightest leftover pixel and how strong it is (in sigma)."""
    resid, ok = subtract_median(frames)
    if not ok:
        raise SystemExit("Need at least 3 frames.")
    rows = []
    for i, f in enumerate(resid):
        r = f["image"]
        good = r[np.isfinite(r)]
        med = np.median(good)
        mad = 1.4826 * np.median(np.abs(good - med))   # robust noise estimate
        if mad <= 0:
            mad = 1e-9
        y, x = np.unravel_index(np.argmax(np.where(np.isfinite(r), r, -np.inf)), r.shape)
        sigma = (r[y, x] - med) / mad
        rows.append({"i": i, "mjd": f["time_mjd"], "x": int(x), "y": int(y),
                     "sigma": float(sigma), "hit": bool(sigma >= k),
                     "marker": f.get("marker")})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name")
    ap.add_argument("--ra")
    ap.add_argument("--dec")
    ap.add_argument("--size", type=float, default=0.05)
    ap.add_argument("--band", default="SPHEREx-D2")
    ap.add_argument("--max", type=int, default=40)
    ap.add_argument("--k", type=float, default=5.0, help="sigma needed to count as a hit")
    a = ap.parse_args()

    if a.name:
        from astropy.coordinates import SkyCoord
        c = SkyCoord.from_name(a.name)
        ra, dec = c.ra.deg, c.dec.deg
    elif a.ra and a.dec:
        ra, dec = parse_coord(a.ra, a.dec)
    else:
        raise SystemExit("give --name, or both --ra and --dec")

    frames = fetch_cutouts(ra, dec, size_deg=a.size, bandpass=a.band, max_images=a.max)
    if len(frames) < 3:
        raise SystemExit("Too few frames to test.")
    frames, aligned = align_frames(frames)
    if not aligned:
        print("WARNING: frames are not fully lined up, results will be poor.")
    marker_pixels(frames, ra, dec)
    rows = find_peaks(frames, k=a.k)

    print(f"\n{'frame':>5} {'MJD':>10} {'x':>4} {'y':>4} {'sigma':>7}  hit  dist_to_target_px")
    for r in rows:
        d = ""
        if r["marker"]:
            d = f"{np.hypot(r['x'] - r['marker'][0], r['y'] - r['marker'][1]):.1f}"
        print(f"{r['i']:>5} {r['mjd']:>10.3f} {r['x']:>4} {r['y']:>4} {r['sigma']:>7.1f}  {'yes' if r['hit'] else ' no'}  {d}")

    hits = [r for r in rows if r["hit"]]
    print(f"\n{len(hits)} of {len(rows)} frames have a leftover spot above {a.k} sigma.")
    if len(hits) >= 3:
        t = np.array([r["mjd"] for r in hits])
        sx = np.polyfit(t, [r["x"] for r in hits], 1)[0]
        sy = np.polyfit(t, [r["y"] for r in hits], 1)[0]
        span = t.max() - t.min()
        print(f"Leftover spot drifts about {sx * span:+.1f} px in x and {sy * span:+.1f} px in y "
              f"over {span:.1f} days. A steady drift can mean a mover; random jumps mean noise.")
    else:
        print("Too few hits to say anything about motion.")


if __name__ == "__main__":
    main()
