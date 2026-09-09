---
name: explainer-video
description: Produce a narrated explainer video (plus a Google-Slides-importable deck) about a codebase, subsystem, feature, PR, or concept the user is struggling with. Use whenever the user asks for a video in any phrasing — "make me a video", "create an explainer video on X", "I'm struggling with X, can you make me a video", "explain X as a video/deck" — or invokes /explainer-video <topic>. Builds a Marp deck with a full narration script in speaker notes, exports PPTX + PNGs, synthesizes TTS voiceover, and assembles an mp4 with ffmpeg.
---

# Explainer video pipeline

Turn a topic into: a Marp deck (`deck.md`), a PPTX for Google Slides import, a per-slide narration script, and a narrated 1080p mp4. The argument names the topic; if none was given, ask what to explain and at what depth.

## 0. Prerequisites (check, don't assume)

- `node`/`npx` (marp runs via `npx -y @marp-team/marp-cli`; needs Chrome/Chromium on PATH — it auto-detects `google-chrome`)
- `ffmpeg`
- `python3` + venv with `edge-tts` (network required — it calls Microsoft's TTS). Create per-run: `python3 -m venv venv && venv/bin/pip install edge-tts`, then test one synthesis before committing to the full build. If edge-tts fails (no network), tell the user the video needs either network TTS or a locally installed `piper`/`espeak-ng`, and still deliver deck + narration script.

Work in the session scratchpad; copy only final artifacts to the destination.

## 1. Research before authoring

Slides must be *verified*, not remembered. Read the actual code/docs for every claim and code excerpt — quote code verbatim from the repo, with the real file path on the slide. If a relevant explanation doc already exists in the Obsidian vault (`~/Canonical/Ceph/Docs/Ceph/`), build from it instead of re-deriving. For a large topic with ultracode/workflows available, fan out subsystem readers first and optionally verify the finished deck's claims with skeptic agents.

## 2. Author the deck (`deck.md`)

Copy `template.md` (beside this file) for the front matter, CSS, and slide idioms. Rules that make the rest of the pipeline work:

- **One narration block per slide**, as a single HTML comment `<!-- ... -->` at the end of the slide. This becomes the PPTX speaker notes AND the video voiceover.
- Narration is **speakable prose**, ~100–160 words per slide (≈40–65 s of audio; 40+ slides ⇒ a 30–40 min video — scale slide count to the depth the user asked for). Don't read code aloud — describe what it shows. Prefer pronunciation-friendly forms ("d-q-lite", "the CLI package") over paths and acronyms.
- Directive comments (`<!-- _class: lead -->`) are fine — the build script skips comments matching `^\s*_?\w+\s*:`.
- Keep code blocks ≤ ~16 lines and tables ≤ ~10 rows at the template's font sizes.
- Structure: title → agenda → background → the content → a "where to look" map → a closing one-sentence summary. Open every section with motivation before mechanism.

## 3. Export and visually QA

```bash
npx -y @marp-team/marp-cli deck.md -o <name>.pptx
npx -y @marp-team/marp-cli deck.md --images png --image-scale 2 -o slides/deck.png
```

Then **Read 2–3 of the rendered PNGs** (a code-heavy slide, a table slide) and check for overflow/clipping. Fix and re-export before building the video — audio is the expensive step.

## 4. Build the video

Copy `build_video.py` (beside this file) into the work dir and run it: it parses the narration comments out of `deck.md`, synthesizes one clip per slide with edge-tts (default voice `en-US-AndrewNeural`, rate `+8%`; override via `TTS_VOICE`/`TTS_RATE` env vars), renders one h264 segment per slide, and concatenates to `<workdir>/output.mp4`. Run it in the background (46 slides ≈ 30 min build). It is incremental: to change one slide, delete that slide's `video_work/segNNN.*` and re-run. Verify the result with ffprobe (one h264 1920x1080 stream + one aac stream) before delivering.

## 5. Deliver

Destination: the Obsidian vault, `repositories/<repo>/media/<topic-slug>/` (repo name from `git remote get-url origin`, else ask). Copy in: `deck.md`, the `.pptx`, the final `.mp4` (rename to `<topic-slug>.mp4`), a generated `narration.md` (per-slide script — extract with the same comment regex), `build_video.py`, and a short `README.md` covering: what this is (wikilink source docs), how to import the PPTX into Google Slides (upload to Drive → Open with Google Slides; slides are images but speaker notes survive; `--pptx-editable` + LibreOffice for editable text), the Google Vids alternative, and the regeneration commands. Finish by telling the user the folder path, video length, and how to tweak-and-rebuild one slide.

The vault is a git repository, so keep the generated artifacts out of it. Copy the `.pptx` and `.mp4` into the media directory as normal — they belong on disk — but they must never be committed. `~/Canonical/Ceph/Docs/Ceph/.gitignore` already excludes `*.mp4`, `*.pptx`, `*.mp3` and the per-video `slides/`, `video_work/`, `assets/`, `venv/` and `__pycache__/` directories, while keeping the authored sources tracked: `deck.md`, `narration.md`, `build_video.py`, `gen_frames.py`, `README.md`.

**If this build produced a new kind of generated artifact, or wrote anywhere outside the `repositories/<repo>/media/<topic-slug>/` convention, add a matching rule to that `.gitignore` as part of the same change.** Then verify before you finish:

```bash
git -C ~/Canonical/Ceph/Docs/Ceph status --porcelain --untracked-files=all | head
git -C ~/Canonical/Ceph/Docs/Ceph status --porcelain --untracked-files=all \
  | sed 's/^?? //' | while read -r f; do [ -f "$f" ] && stat -c%s "$f"; done \
  | awk '{s+=$1} END {printf "%.1f MB would be added\n", s/1048576}'
```

Anything above a megabyte or so means a rule is missing. Never use `git add -f` to force a binary in.
