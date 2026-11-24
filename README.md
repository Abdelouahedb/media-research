# media-research

A skill for **Claude Code** and **Codex** that finds, verifies, and downloads authentic real-world photos and videos, then saves them to your project with a provenance manifest.

Use it when a website, deck, documentary, marketing video, or social post needs *real* visuals (a specific street, event, product, or person's work) rather than generic stock.

> Example prompt: *"Find and download four real 1920px-wide photos of Casablanca's tramway into this project's assets folder for a documentary research deck."*

## What it does

1. **Discovers** candidates with Playwright on search engines (Google/Bing Images), social platforms, news sites, and blogs. Search previews are treated as leads only.
2. **Verifies** each candidate on its canonical page: subject, context, creator, date.
3. **Stages** the best available original in a scratch folder (`gallery-dl` for social images, `yt-dlp` for video, plain HTTP for direct public media).
4. **Inspects visually**: the agent looks at the actual image (or three frames of a video) for subject, crop, sharpness, watermarks, and authenticity.
5. **Imports** approved files into `assets/` (or your project's existing assets folder) with dimensions, SHA-256, and rights info recorded in `assets/sources.json`.

Originals are copied byte-for-byte. Nothing is re-encoded.

## Install

### Windows

Extract the ZIP (or clone the repo), open PowerShell in it, and run:

```powershell
pwsh -NoProfile -File .\Install.ps1
```

Use `powershell.exe` instead of `pwsh` if PowerShell 7 isn't installed. Add `-SkipDependencies` if the dependencies are already set up.

The installer:
- copies the skill to `%USERPROFILE%\.claude\skills\media-research` and `%USERPROFILE%\.agents\skills\media-research`
- **skips a destination that already exists**, so to update, delete the old folder first
- runs `python -m pip install --user -r requirements.txt` and `python -m playwright install chromium`
- warns if `ffmpeg` / `ffprobe` are missing from PATH

Start a fresh Claude Code or Codex session afterwards.

### macOS / Linux

Copy the `media-research` folder to `~/.claude/skills/` (Claude Code) and/or `~/.agents/skills/` (Codex), then:

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

The installer and download workflow were tested on Windows only.

### Requirements

| Need | Notes |
| --- | --- |
| Python 3.10+ | `media.py` uses features from 3.10 |
| Pillow, Playwright, gallery-dl, yt-dlp | pinned minimums in `requirements.txt` |
| Playwright Chromium | installed by the commands above |
| FFmpeg + FFprobe on PATH | needed for video inspection and import only |

## Usage

Open your project, then either describe what you need and let the agent pick the skill, or invoke it explicitly:

| App | Skill location | Explicit invocation |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/media-research` | `/media-research` |
| Codex | `~/.agents/skills/media-research` | `$media-research` where supported, or pick it from `/skills` in Codex CLI |

A good brief states the subject, place/time, count, minimum size, and intended use. The agent sets minimum dimensions from that.

## Output

```
your-project/
└── assets/
    ├── tramway-casablanca-1a2b3c4d5e6f.jpg   # <name>-<first 12 of sha256>.<ext>
    └── sources.json                           # one entry per asset
```

Each `sources.json` entry records:

| Field | Meaning |
| --- | --- |
| `path`, `sha256`, `bytes` | the saved file and its checksum |
| `kind`, `width`, `height`, `duration_seconds` | image or video properties |
| `source_url`, `media_url` | canonical page and, when stable, the direct media URL |
| `author`, `published_date`, `captured_date` | `null` when unknown |
| `rights.status` | `licensed`, `public_domain`, `permission_granted`, `restricted`, or `unknown` |
| `rights.license`, `rights.evidence_url`, `rights.notes` | attribution, scope, and conditions |
| `visual_review` | what was actually checked and why the item was chosen (required) |
| `retrieved_at`, `visual_hashes` | UTC timestamp and perceptual hashes used for de-duplication |

Duplicates are skipped by SHA-256 and by perceptual hash (same kind, similar aspect ratio, and for video similar duration). Perceptual hashes miss some crops and edits, so the workflow also asks for a visual spot-check.

## The helper CLI

The agent drives `scripts/media.py`, but you can run it yourself:

```powershell
# List media and links on a public page (URL parameters stripped; only q and tbm query keys accepted)
python media.py discover "<public page URL>"

# Download a public media URL into a NEW staging file (250 MiB cap)
python media.py download "<media URL>" "<new staging file>"

# Write a JPEG preview (1000x750 max; 3 frames at 20/50/80% for video) and print metadata
python media.py inspect "<staged file>" "<preview.jpg>"

# Import into the project, enforcing minimum size and recording provenance
python media.py add "<staged file>" "<assets dir>" "<candidate.json>" --min-width 1200 --min-height 700
```

`candidate.json` format:

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

URLs in metadata must be plain `http(s)` without credentials, query strings, or fragments.

## Rights and safety

- **Public does not mean reusable.** The skill records what it can find about rights and marks anything unverified as `unknown` or `restricted`. Review the manifest and meet attribution or permission requirements before publishing.
- It stops at paywalls, CAPTCHAs, access denials, DRM, and rate limits, honors `Retry-After`, and switches sources rather than working around them.
- Downloads are serial and bounded. Downloader config is ignored (`--config-ignore` / `--ignore-config`), and only post-level URLs are used, not whole accounts or playlists.
- Cookies, credentials, auth headers, and signed URLs are never printed or saved in the project.
- If a site needs sign-in, use a dedicated Playwright browser profile **outside the project** and sign in yourself. The skill does not touch your normal browser profile.
- Site content is treated as data, not instructions.

## Limitations

- Availability depends on each site and region. Social platforms change often, so `gallery-dl` and `yt-dlp` support varies.
- Dynamic pages that `discover` can't parse are handled through the browser instead.
- A screenshot of a post has different provenance than the embedded original; the skill prefers the original.
- Windows is the only tested platform.

## Repository layout

```
Install.ps1             Windows installer
requirements.txt        Python dependencies
media-research/
├── SKILL.md            instructions the agent follows
├── references/
│   └── workflow.md     discovery and download commands
└── scripts/
    └── media.py        discover / download / inspect / add helper
```

## References

[Claude Code skills](https://code.claude.com/docs/en/skills) · [Codex skills](https://learn.chatgpt.com/docs/build-skills)
