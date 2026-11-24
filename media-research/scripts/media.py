"""Stage, inspect and import permitted media without rewriting original bytes."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from PIL import Image, ImageOps


def public_url(value, strip=False):
    parts = urlsplit(value)
    if parts.scheme not in ("http", "https") or not parts.hostname or parts.username or parts.password:
        raise ValueError("Expected an HTTP(S) URL without login information.")
    if not strip and (parts.query or parts.fragment):
        raise ValueError("Use a stable URL without query parameters or fragments.")
    return urlunsplit((parts.scheme, parts.netloc, parts.path or "/", "", ""))


def discover(url):
    from playwright.sync_api import sync_playwright

    parts = urlsplit(url)
    public_url(url, strip=True)
    if parts.query and set(key.split("=")[0] for key in parts.query.split("&")) - {"q", "tbm"}:
        raise ValueError("Use the browser interface for URLs with other query parameters.")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(accept_downloads=False)
        response = page.goto(url, wait_until="domcontentloaded", timeout=25000)
        if response and response.status >= 400:
            raise ValueError(f"Discovery returned HTTP {response.status}. Check access or switch sources.")
        items = page.locator("meta[property], a[href], img[src], video[src], source[src]").evaluate_all(
            """els => els.filter(e => e.tagName !== 'META' ||
            /^og:(image|video|url)(:secure_url)?$/.test(e.getAttribute('property') || ''))
            .map(e => [e.tagName, e.getAttribute('content') || e.getAttribute('href') ||
            e.getAttribute('src')]).slice(0, 350)"""
        )
        results = []
        seen = set()
        for kind, value in items:
            if not value:
                continue
            try:
                link = public_url(urljoin(page.url, value), strip=True)
            except ValueError:
                continue
            if link not in seen:
                results.append({"kind": kind, "url": link})
                seen.add(link)
        print(json.dumps(results, indent=2))


def download(url, destination):
    public_url(url)
    request = Request(url, headers={"User-Agent": "MediaResearch/1.0 (interactive media research)"})
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError("Choose a new staging filename.")
    with tempfile.TemporaryDirectory(dir=destination.parent) as staging:
        partial = Path(staging) / "download"
        with urlopen(request, timeout=25) as response, partial.open("wb") as output:
            if not response.headers.get_content_type().startswith(("image/", "video/", "application/octet-stream")):
                raise ValueError("The source did not return media.")
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > 250 * 1024 * 1024:
                    raise ValueError("Direct download exceeds the 250 MiB limit.")
                output.write(chunk)
        copy_new(partial, destination)
    print(f"Staged {total:,} bytes at {destination}")


def load_image(path):
    with Image.open(path) as source:
        source.load()
        return ImageOps.exif_transpose(source).convert("RGB")


def difference_hash(image):
    pixels = image.convert("L").resize((9, 8), Image.Resampling.LANCZOS).tobytes()
    bits = "".join(
        "1" if pixels[row * 9 + col] > pixels[row * 9 + col + 1] else "0"
        for row in range(8) for col in range(8)
    )
    return f"{int(bits, 2):016x}"


def run_media_tool(command):
    try:
        return subprocess.run(command, check=True, capture_output=True, timeout=45).stdout
    except FileNotFoundError as exc:
        raise ValueError(f"Install {command[0]} and make it available on PATH.") from exc
    except (subprocess.SubprocessError, OSError) as exc:
        raise ValueError(f"{command[0]} could not read the staged media.") from exc


def inspect(path):
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif", ".tif", ".tiff", ".bmp"}
    if path.suffix.lower() in extensions:
        original = load_image(path)
        width, height = original.size
        original.thumbnail((1000, 750))
        return {"kind": "image", "width": width, "height": height,
                "duration_seconds": None, "visual_hashes": [difference_hash(original)]}, original

    probe = json.loads(run_media_tool([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
        "-show_format", "-of", "json", str(path.resolve()),
    ]))
    if not probe["streams"]:
        raise ValueError("The staged file has no video stream.")
    video = probe["streams"][0]
    duration = float(video.get("duration") or probe["format"].get("duration") or 0)
    if duration <= 0:
        raise ValueError("Could not determine video duration.")
    rotation = next((side.get("rotation", 0) for side in video.get("side_data_list", [])
                     if "rotation" in side), 0)
    width, height = video["width"], video["height"]
    if rotation % 180:
        width, height = height, width
    frames = []
    with tempfile.TemporaryDirectory() as temporary:
        for index, fraction in enumerate((0.2, 0.5, 0.8)):
            frame = Path(temporary) / f"{index}.png"
            run_media_tool([
                "ffmpeg", "-v", "error", "-ss", str(duration * fraction), "-i", str(path.resolve()),
                "-map", "0:v:0", "-frames:v", "1", "-vf", "scale=480:360:force_original_aspect_ratio=decrease",
                str(frame),
            ])
            frames.append(load_image(frame))
    preview = Image.new("RGB", (sum(frame.width for frame in frames), max(frame.height for frame in frames)))
    offset = 0
    for frame in frames:
        preview.paste(frame, (offset, 0))
        offset += frame.width
    return {"kind": "video", "width": width, "height": height, "duration_seconds": duration,
            "visual_hashes": [difference_hash(frame) for frame in frames]}, preview


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def copy_new(source, target):
    with source.open("rb") as incoming:
        outgoing = target.open("xb")
        try:
            with outgoing:
                shutil.copyfileobj(incoming, outgoing)
        except OSError:
            target.unlink()
            raise


def resembles(candidate, existing):
    if candidate["kind"] != existing.get("kind") or not existing.get("visual_hashes"):
        return False
    ratio_a = candidate["width"] / candidate["height"]
    ratio_b = existing["width"] / existing["height"]
    if abs(ratio_a / ratio_b - 1) > 0.035:
        return False
    if candidate["kind"] == "video":
        duration = candidate["duration_seconds"]
        if abs(duration - existing["duration_seconds"]) > min(2.0, duration * 0.03):
            return False
    first, second = candidate["visual_hashes"], existing["visual_hashes"]
    return len(first) == len(second) and all(
        (int(a, 16) ^ int(b, 16)).bit_count() <= 5 for a, b in zip(first, second)
    )


def read_metadata(path):
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not data.get("visual_review", "").strip():
        raise ValueError("Record the actual visual inspection before importing media.")
    rights = data["rights"]
    if rights["status"] not in {"licensed", "public_domain", "permission_granted", "restricted", "unknown"}:
        raise ValueError("Unrecognized rights status.")
    return {
        "source_url": public_url(data["source_url"]),
        "media_url": public_url(data["media_url"]) if data.get("media_url") else None,
        "author": data.get("author"), "published_date": data.get("published_date"),
        "captured_date": data.get("captured_date"), "visual_review": data["visual_review"],
        "rights": {"status": rights["status"], "license": rights.get("license"),
                   "evidence_url": public_url(rights["evidence_url"]) if rights.get("evidence_url") else None,
                   "notes": rights.get("notes")},
    }


def add(path, assets, metadata, min_width, min_height):
    entry = read_metadata(metadata)
    info, _ = inspect(path)
    if info["width"] < min_width or info["height"] < min_height:
        raise ValueError(f"Dimensions {info['width']}x{info['height']} are below the requested minimum.")
    digest = sha256(path)
    assets.mkdir(parents=True, exist_ok=True)
    manifest = assets / "sources.json"
    lock = assets / ".media-research.lock"
    lock.mkdir()
    try:
        entries = json.loads(manifest.read_text(encoding="utf-8-sig")) if manifest.exists() else []
        if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
            raise ValueError("Existing sources.json has a different structure. Preserve it and reconcile manually.")
        for previous in entries:
            name = previous.get("path")
            if not isinstance(name, str) or Path(name).name != name or not (assets / name).is_file():
                continue
            if digest == previous.get("sha256") or resembles(info, previous):
                print(f"Duplicate skipped: {name}")
                return
        for existing in assets.iterdir():
            if existing.is_file() and existing.stat().st_size == path.stat().st_size and sha256(existing) == digest:
                print(f"Identical file already exists: {existing.name}. Reconcile its provenance if needed.")
                return

        filename = f"{path.stem[:75]}-{digest[:12]}{path.suffix.lower()}"
        target = assets / filename
        entry.update(info, path=filename, sha256=digest, bytes=path.stat().st_size,
                     retrieved_at=datetime.now(timezone.utc).isoformat())
        with tempfile.TemporaryDirectory(dir=assets) as staging:
            new_manifest = Path(staging) / "manifest.json"
            new_manifest.write_text(json.dumps([*entries, entry], ensure_ascii=False, indent=2) + "\n",
                                    encoding="utf-8")
            staged_asset = Path(staging) / "asset"
            shutil.copyfile(path, staged_asset)
            if sha256(staged_asset) != digest:
                raise ValueError("The staged file changed during import.")
            copy_new(staged_asset, target)
            try:
                os.replace(new_manifest, manifest)
            except OSError:
                target.unlink()  # Roll back only the file created by this invocation.
                raise
        print(f"Saved {target} | {info['width']}x{info['height']} | rights: {entry['rights']['status']}")
    finally:
        lock.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("discover").add_argument("url")
    direct = commands.add_parser("download")
    direct.add_argument("url")
    direct.add_argument("destination", type=Path)
    preview = commands.add_parser("inspect")
    preview.add_argument("file", type=Path)
    preview.add_argument("preview", type=Path)
    store = commands.add_parser("add")
    for field in ("file", "assets", "metadata"):
        store.add_argument(field, type=Path)
    store.add_argument("--min-width", type=int, default=1)
    store.add_argument("--min-height", type=int, default=1)
    args = parser.parse_args()
    try:
        if args.command == "discover":
            discover(args.url)
        elif args.command == "download":
            download(args.url, args.destination)
        elif args.command == "inspect":
            info, image = inspect(args.file)
            with args.preview.open("xb") as stream:
                image.save(stream, format="JPEG", quality=88)
            print(json.dumps(info))
        else:
            add(args.file, args.assets, args.metadata, args.min_width, args.min_height)
    except Exception as exc:
        from urllib.error import HTTPError
        if isinstance(exc, HTTPError):
            retry = exc.headers.get("Retry-After")
            parser.exit(1, f"HTTP {exc.code}. Retry-After supplied: {bool(retry)}. Honor it or switch sources.\n")
        if isinstance(exc, (ValueError, OSError, KeyError)) and args.command not in {"discover", "download"}:
            parser.exit(1, f"Media operation failed: {exc}\n")
        parser.exit(1, f"Media operation failed ({type(exc).__name__}). Check access, input and dependencies.\n")


if __name__ == "__main__":
    main()
