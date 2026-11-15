"""
app.py - small web server for the SPHEREx viewer.

Run:  python app.py      then open  http://127.0.0.1:5000
Link examples (you can share these):
  /?name=Barnard's Star
  /?ra=08h55m10.831s&dec=-7d14m42.53s&size=0.05&band=SPHEREx-D2&mode=subtract&stack=2
"""
import os

from astropy.coordinates import SkyCoord
from astropy.time import Time
from flask import Flask, jsonify, request, send_from_directory

from fetch import fetch_cutouts, parse_coord
from processing import (align_frames, marker_fraction, marker_pixels,
                        stack_frames, subtract_median, to_png_uri)

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
_raw = {}   # downloaded + aligned frames, kept while the server runs


def render(raw, mode, stack):
    """Turn the stored frames into PNGs for the chosen view."""
    frames, notes = raw["frames"], []
    if not frames:
        return {"ra": raw["ra"], "dec": raw["dec"], "aligned": False, "frames": [], "notes": []}
    if stack > 1:
        frames = stack_frames(frames, stack)
    diverging = False
    if mode == "subtract":
        frames, ok = subtract_median(frames)
        diverging = ok
        if not ok:
            notes.append("Need at least 3 frames to subtract, showing the normal view.")
    out = []
    for f in frames:
        mx = my = None
        if f.get("marker"):
            mx, my = marker_fraction(f["marker"][0], f["marker"][1], f["image"].shape)
        out.append({
            "mjd": f["time_mjd"],
            "date": Time(f["time_mjd"], format="mjd").iso[:10],
            "wl_min": round(f.get("wl_min", f["wavelength_um"]), 3),
            "wl_max": round(f.get("wl_max", f["wavelength_um"]), 3),
            "n": f.get("n", 1),
            "mx": mx, "my": my,
            "png": to_png_uri(f["image"], diverging=diverging),
        })
    return {"ra": raw["ra"], "dec": raw["dec"], "aligned": raw["aligned"],
            "frames": out, "notes": notes}


@app.route("/")
def home():
    return send_from_directory(HERE, "index.html")


@app.route("/api/frames")
def api_frames():
    try:
        name = request.args.get("name", "").strip()
        if name:
            c = SkyCoord.from_name(name)        # needs internet (CDS Sesame)
            ra, dec = c.ra.deg, c.dec.deg
        else:
            ra, dec = parse_coord(request.args["ra"], request.args["dec"])
        size = min(max(float(request.args.get("size", 0.05)), 0.01), 0.3)
        band = request.args.get("band", "SPHEREx-D2")
        if not band.startswith("SPHEREx-D") or len(band) != 10:
            return jsonify(error="band must look like SPHEREx-D2"), 400
        max_images = min(max(int(request.args.get("max", 40)), 3), 100)
        mode = request.args.get("mode", "normal")
        if mode not in ("normal", "subtract"):
            return jsonify(error="mode must be normal or subtract"), 400
        stack = min(max(int(request.args.get("stack", 1)), 1), 10)

        key = (round(ra, 5), round(dec, 5), size, band, max_images)
        if key not in _raw:
            frames = fetch_cutouts(ra, dec, size_deg=size, bandpass=band, max_images=max_images)
            aligned = False
            if frames:
                frames, aligned = align_frames(frames)
                marker_pixels(frames, ra, dec)
                for f in frames:
                    f.pop("header", None)       # not needed after this, saves memory
            _raw[key] = {"ra": ra, "dec": dec, "aligned": aligned, "frames": frames}
        return jsonify(render(_raw[key], mode, stack))
    except KeyError:
        return jsonify(error="give ra and dec (or a name)"), 400
    except Exception as e:
        return jsonify(error=f"{type(e).__name__}: {e}"), 500


if __name__ == "__main__":
    app.run(port=5000, debug=False, threaded=True)
