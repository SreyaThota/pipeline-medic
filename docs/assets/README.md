# Demo GIF

`demo.gif` (under 5 MB) is shown at the top of the main README. To record it
on Windows with [ScreenToGif](https://www.screentogif.com/):

1. Run the demo: `streamlit run demo/app.py`, open <http://localhost:8501>,
   and wait for the retrieval index to finish building.
2. Set the browser window to about 1280 × 800 and collapse nothing.
3. ScreenToGif → **Recorder**, frame the browser content, 10–12 fps.
4. Record about 20 seconds: pick **tokio-rs/tokio: Loom** → **Run the
   pipeline** → scroll slowly through the five stages → **Approve** → show the
   audit table.
5. In the editor: delete idle frames, then **File → Save as → Gif** with the
   default encoder and *Loop forever*. If the file is over 5 MB, lower the
   size to 1024 px wide (**Image → Resize**) or remove every other frame
   (**Edit → Reduce frame count**).
6. Save as `docs/assets/demo.gif`, then in `README.md` replace the
   `<!-- DEMO_GIF: ... -->` comment with the image line it contains.
