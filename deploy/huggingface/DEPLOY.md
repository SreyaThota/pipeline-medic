# Deploying the demo

The demo (`demo/app.py`) runs on a free Hugging Face **Docker Space** (CPU
basic: 2 vCPU, 16 GB RAM). The image holds the CPU-only torch wheel, the
embedding model and the bundled reviewed logs; the retrieval index is built
from those logs on the first page load.

## Run the image locally (Windows, PowerShell or cmd)

From the repository root, with Docker Desktop running:

```
docker build -f deploy/huggingface/Dockerfile -t pipeline-medic-demo .
docker run --rm -p 7860:7860 pipeline-medic-demo
```

Then open <http://localhost:7860>.

## Option A: automatic sync from GitHub (recommended)

`.github/workflows/deploy-space.yml` mirrors the demo onto the Space on every
push to `main` that touches the demo or the code it runs. It is skipped until
the two settings below exist.

1. Create the Space: <https://huggingface.co/new-space>
   - Space name: `pipeline-medic`
   - License: MIT
   - SDK: **Docker**, template **Blank**
   - Hardware: **CPU basic (free)**
   - Visibility: Public
2. Create a token: <https://huggingface.co/settings/tokens>, then
   **Create new token** → type **Write** (or fine-grained with write access
   to that one Space only). Copy it.
3. In the GitHub repository, open **Settings → Secrets and variables →
   Actions**:
   - **Secrets** tab → **New repository secret**: name `HF_TOKEN`, value the
     token.
   - **Variables** tab → **New repository variable**: name `HF_SPACE_ID`,
     value `<your-hf-username>/pipeline-medic`.
4. Run it once by hand: **Actions → Deploy demo to Hugging Face → Run
   workflow**. The Space then builds the image (about 5–10 minutes the first
   time) and starts.

The Space URL is `https://huggingface.co/spaces/<your-hf-username>/pipeline-medic`.

## Option B: push by hand

Install the client and log in (paste the write token when asked):

```
pip install huggingface_hub
hf auth login
```

Stage the Space folder (PowerShell, from the repository root):

```
Remove-Item -Recurse -Force space -ErrorAction SilentlyContinue
New-Item -ItemType Directory space, space\data | Out-Null
Copy-Item deploy\huggingface\Dockerfile space\Dockerfile
Copy-Item deploy\huggingface\Dockerfile.dockerignore space\.dockerignore
Copy-Item deploy\huggingface\README.md space\README.md
Copy-Item LICENSE space\LICENSE
Copy-Item -Recurse app, agents, mcp_server, rag, demo space\
Copy-Item -Recurse data\sample_logs space\data\
hf upload <your-hf-username>/pipeline-medic space . --repo-type space
Remove-Item -Recurse -Force space
```

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
