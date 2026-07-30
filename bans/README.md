# Global Kratom Interactive Map

## Why the map may appear as only a static image
The interactive map loads the official U.S. state geometry and mapping libraries from a CDN. Many browsers block those JavaScript modules when `index.html` is opened directly as a local `file://` document.

The page now includes a local fallback image, so the state map is always visible.

## To activate clicking, hover cards, search, and filtering
Upload this entire folder to your website, or run a local web server:

```bash
python serve.py
```

Then open `http://127.0.0.1:8000/index.html`.

Do not upload only `index.html`; keep `kratom-map-fallback.png` in the same folder.
