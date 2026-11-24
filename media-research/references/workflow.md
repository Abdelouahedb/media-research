# Discovery and acquisition

`<skill>` is the folder containing this SKILL.md. Use an isolated staging directory per post or candidate. Launch a Chromium browser with Playwright. For public pages, use the helper below or an existing Playwright browser integration. Use headed interaction for dynamic result pages. Search Google Images with `https://www.google.com/search?tbm=isch&q=...` and Bing Images with `https://www.bing.com/images/search?q=...`. For X, Instagram, Facebook, Reddit, Pinterest, and TikTok use their public search or web search with a site filter. For articles check visible credit, captions, linked originals, srcset, and open graph metadata. Inspect gallery items and their source pages individually.

For permitted sign-in, use Playwright with a dedicated browser profile outside the project and let the user sign in directly. Keep the profile private. For supported downloads use that session through normal browser download controls or a downloader's documented browser profile option with user authorization. Browser compatibility varies. Never export cookies, pass them as literal arguments, or access an unrelated browser profile. Only use tool options that apply to the selected site and permitted action. If the tools cannot access the intended item legitimately, switch sources.

```powershell
python "<skill>/scripts/media.py" discover "<public page URL>"
python "<skill>/scripts/media.py" download "<permitted public original URL>" "<new staging file>"
python -m gallery_dl --config-ignore --sleep 2 --range 1-12 -D "<staging>" -- "<public post URL>"
python -m yt_dlp --ignore-config --no-playlist --retries 0 --fragment-retries 0 --sleep-interval 2 --max-filesize 250M -P "<staging>" -o "clip.%(ext)s" -- "<public video URL>"
python "<skill>/scripts/media.py" inspect "<staged file>" "<preview.jpg>"
python "<skill>/scripts/media.py" add "<staged file>" "<project assets directory>" "<candidate metadata.json>" --min-width 1200 --min-height 700
```

Use the native browser for dynamic posts that the public discovery helper cannot parse. The helper lists visible links without query parameters and public media metadata, strips URL parameters in its output, and provides a starting point for discovery. For originals that need a query string, follow the browser's normal permitted download flow. Use the source URL as provenance, with a stable media URL only when available. When yt-dlp supports separate streams, FFmpeg merges them or the tool can select a permitted progressive format. FFmpeg and FFprobe are required for video inspection and import. A short video preview contains frames at 20%, 50%, and 80%. Review playback as needed, including audio.

Run downloader commands with stdout and stderr captured privately when a user session or signed URL may be involved. Share only sanitized outcome summaries. Disable default downloader configuration; do not enable debugging or save raw metadata, dumps, or authentication files. Use only scoped post URLs rather than account or playlist URLs. Tool support changes by site and region.

Each candidate metadata file is UTF-8 JSON:

```json
{
  "source_url": "https://publisher.example/canonical-post",
  "media_url": null,
  "author": null,
  "published_date": null,
  "captured_date": null,
  "rights": {
    "status": "unknown",
    "license": null,
    "evidence_url": "https://publisher.example/canonical-post",
    "notes": "Reuse permission could not be verified."
  },
  "visual_review": "Describe the visual check performed and why this item was selected."
}
```

Rights status can be `licensed`, `public_domain`, `permission_granted`, `restricted`, or `unknown`. For known rights describe attribution, usage scope, and other applicable conditions. Verify creator and exact date where possible. Record partial dates distinctly or use null. A screenshot of a social post has different provenance from the embedded original. Preserve the unmodified full-resolution asset and keep any project-specific crop or transcode separate.
