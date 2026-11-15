# SPHEREx Sky Viewer

A small web tool for the NASA Space Apps challenge **"Planet X and SPHEREx"**.
Type the coordinates of a patch of sky (or an object name) and watch SPHEREx
images of that patch play like a short video, so moving objects stand out.

## Features
- Search by **RA/Dec** (degrees or `08h55m10.8s` / `-7d14m42s`) or by **object name**
- Plays cutouts **in time order** with play, pause, back, next, scrub bar and speed
- Frames are **lined up on the sky**, so stars stay still and movers shift
- **Target circle** shows where your coordinates are in every frame
- **Subtract average** view: static things fade, movers stay
- **Stack frames** (every 2, 3, 5, 8) to reduce noise
- Choose **field of view** and **detector** (D1 to D6)
- **Shareable links**, for example `/?ra=08h55m10.831s&dec=-7d14m42.53s&size=0.05&band=SPHEREx-D2&mode=subtract`
- `baseline.py`: a simple mover finder without machine learning

## Run it
```
python -m venv venv
venv\Scripts\activate          (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000. The first search for a new place can take 30 to 60 seconds.

## Files
| File | What it does |
|---|---|
| `fetch.py` | Asks IRSA which SPHEREx images cover a point and downloads small cutouts |
| `processing.py` | Line up, stack, subtract, make PNGs, place the target circle |
| `app.py` | The web server |
| `index.html` | The web page |
| `baseline.py` | No-ML mover finder (command line) |
| `test_processing.py` | Offline tests with fake images: `python test_processing.py` |

## Data
SPHEREx spectral images from NASA/IPAC **IRSA** (Infrared Science Archive).
The tool reads IRSA's tables live, so newly added data shows up without changes
to this code. Method follows IRSA's tutorial "Download a collection of SPHEREx
Spectral Image cutouts".

## Known limits
- Needs internet, and IRSA can be slow.
- Stacked frames mix different wavelengths, so a source can change brightness.
- Detections from `baseline.py` are hints, not proof.
- Contamination flags, spectra and catalog overlays (Gaia, WISE) are not built yet.
