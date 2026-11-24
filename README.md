# Media Research for Claude Code and Codex

Find, visually review, and download authentic photos and videos. The skill saves selected originals in your project’s assets directory and records their sources and known usage rights in `sources.json`.

## Windows installation

Extract the ZIP. Open PowerShell in the extracted package and run `pwsh -NoProfile -File .\Install.ps1` (or use `powershell.exe` in place of `pwsh`). The installer uses Python 3.10 or newer, installs the four Python dependencies and Playwright Chromium, and skips existing skill directories. Use `-SkipDependencies` if the dependencies are already available. Video needs FFmpeg and FFprobe on PATH. Use a fresh session after installation.

| App | Personal directory | Explicit invocation |
| --- | --- | --- |
| Claude Code | `%USERPROFILE%\.claude\skills\media-research` | `/media-research` |
| Codex | `%USERPROFILE%\.agents\skills\media-research` | `$media-research` where supported, or select from `/skills` in Codex CLI |

## macOS and Linux installation

Copy the `media-research` folder into `~/.claude/skills/` for Claude Code or `~/.agents/skills/` for Codex. With Python 3.10 or newer, run `python3 -m pip install -r requirements.txt` and `python3 -m playwright install chromium` in your Python environment. Make FFmpeg and FFprobe available on your PATH for video inspection. The installer and download workflow were tested on Windows.

## Usage

Both apps can also choose the skill automatically when authentic external visuals are needed. Open the desired project before invoking it. An example request is “Find and download four real 1920-pixel-wide photos of Casablanca's tramway into this project's assets folder for a documentary research deck.”

The workflow stores selected originals and a `sources.json` manifest. Sources and download availability vary by site. For publishing, review rights and apply the attribution or permission requirements recorded in the manifest. Keep any authorized browser profile outside the project.

Official references: [Claude Code skills](https://code.claude.com/docs/en/skills) and [Codex skills](https://learn.chatgpt.com/docs/build-skills).
