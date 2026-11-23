// Minimal static server for the demo page (demo/public), used by the
// Playwright webServer config. Tests never run against the live site.
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("../demo/public", import.meta.url)));
const PORT = Number(process.env.PORT ?? 4173);
const TYPES = { ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8",
  ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8",
  ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml" };

createServer(async (req, res) => {
  const path = decodeURIComponent(new URL(req.url ?? "/", "http://localhost").pathname);
  const file = normalize(join(ROOT, path.endsWith("/") ? path + "index.html" : path));
  if (!file.startsWith(ROOT)) { res.writeHead(403).end(); return; }
  try {
    const body = await readFile(file);
    res.writeHead(200, { "Content-Type": TYPES[extname(file)] ?? "application/octet-stream",
      "Cache-Control": "no-store" }).end(body);
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain" }).end("not found");
  }
}).listen(PORT, "127.0.0.1", () => console.log(`demo/public on http://127.0.0.1:${PORT}`));
