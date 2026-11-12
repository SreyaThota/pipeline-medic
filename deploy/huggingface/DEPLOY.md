# Deploying the demo

## Hugging Face Space (static replay, the default)

The Space is a **static** Space: a copy of the GitHub Pages demo
(`demo/public`) with a banner, staged by `deploy/huggingface/build_space.py`.
It replays recorded real runs, so there is no backend, no dependency, no
model and no LLM, and it loads in about a second.

1. Create a Hugging Face **Write** token: <https://huggingface.co/settings/tokens>.
2. GitHub repository → **Settings → Secrets and variables → Actions**:
   secret `HF_TOKEN` (the token) and variable `HF_SPACE_ID`
   (`<your-hf-username>/pipeline-medic`).
3. **Actions → Deploy demo to Hugging Face → Run workflow.** The workflow
   creates the Space (public, static) if needed and uploads the files.

Preview it locally exactly as the Space serves it:

```
python deploy/huggingface/build_space.py
python -m http.server 7860 --directory space
```

## Live Streamlit demo in Docker (optional, not deployed)

The Dockerfile in this folder packages the live Streamlit demo
(`demo/app.py`), which runs the real graph and builds its retrieval index on
first load. It is kept for local use and is not what the Space runs.

## Run the image locally (Windows, PowerShell or cmd)

From the repository root, with Docker Desktop running:

```
docker build -f deploy/huggingface/Dockerfile -t pipeline-medic-demo .
docker run --rm -p 7860:7860 pipeline-medic-demo
```

Then open <http://localhost:7860>.

## Fallback: Streamlit Community Cloud

If the Space does not work out, Streamlit Community Cloud runs the app
straight from GitHub, for free.

1. Sign in at <https://share.streamlit.io> with GitHub.
2. **Create app → Deploy a public app from GitHub**.
3. Repository `SreyaThota/pipeline-medic`, branch `main`, main file
   `demo/app.py`.
4. **Advanced settings**: choose Python 3.14. The code needs 3.14 (it relies
   on deferred evaluation of annotations); if 3.14 is not offered, use the
   Space instead. Community Cloud uses the `requirements.txt` next to the app,
   so `demo/requirements.txt` is installed, with the default (larger) torch
   wheel instead of the CPU-only one.
5. **Deploy**. The URL looks like `https://<name>.streamlit.app`.
