# Stage

[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Blender](https://img.shields.io/badge/blender-5.1%2B-orange.svg)](https://www.blender.org/)
[![CI](https://github.com/BlueLazyFish/Stage-Render/actions/workflows/ci.yml/badge.svg)](https://github.com/BlueLazyFish/Stage-Render/actions)
[![Latest Release](https://img.shields.io/github/v/release/BlueLazyFish/Stage-Render?include_prereleases&sort=semver)](https://github.com/BlueLazyFish/Stage-Render/releases)

A KeyShot-style scene state manager and persistent render queue for Blender 5.1+.

Set up your scene once, then save it as a *Studio*. A Studio is a snapshot of camera, lighting, world, visibility, render settings, and output path. Save as many as you like, switch between them in one click, queue them all, and let Blender chew through them overnight while you keep working in the foreground.

Status: v0.1.0 is the first public release. Open source under GPL-3.0-or-later. Issues and PRs welcome.

## Install

1. Download `stage-<version>.zip` from the [latest release](https://github.com/BlueLazyFish/Stage-Render/releases/latest).
2. Open Blender, then **Edit > Preferences > Get Extensions**.
3. Click the dropdown arrow at the top right of the panel, then **Install from Disk**.
4. Pick the zip and tick **Stage** to enable it.

The same zip works on macOS, Linux, and Windows. Stage is pure Python with no platform-specific binaries.

## Requirements

* Blender 5.1 or later
* macOS, Linux, or Windows

## Quick start

1. Open the **Stage** tab in the N-panel.
2. Click **+** to add a Studio. It captures the current scene state.
3. Tweak the scene (move the camera, swap the world, hide a collection).
4. Click **+** again. The second Studio captures the new state.
5. Click between them in the list. The scene snaps back instantly.
6. Set an **Output Path**. A folder is fine, Stage names files per Studio.
7. Save the `.blend`, then **Queue All Enabled** in the Render Queue subpanel.
8. Toggle **Auto-Render: ON** in the queue panel and the worker starts processing.

Files land in the output folder you set. The foreground Blender stays responsive the whole time.

## Features

**Studios** are atomic snapshots. Each one can capture any combination of:

* Camera (transform, lens, depth of field)
* World and HDRI (image, strength, rotation)
* Visibility (collection toggles, object hide_render, view-layer exclude)
* Render settings (engine, resolution, per-engine bag for Cycles, EEVEE, Workbench)
* Output path (per-Studio override with template variables)
* Custom RNA paths via right-click then *Store in Stage*

**Render queue** is persistent and runs in a background subprocess:

* SQLite database at `~/Library/Application Support/Stage/queue.db` (platform-correct path on Linux and Windows)
* A separate Blender process renders one job at a time so the foreground UI stays free
* Survives Blender restarts and crashes; orphaned RUNNING jobs are reset to FAILED on next launch

**Production helpers:**

* Dirty-state badge that flags uncommitted changes after you mutate the scene
* Inheritance, where a child Studio stores deltas only and the parent supplies the rest
* Locked Studios that refuse Update unless explicitly unlocked, useful for client deliverables
* Click-to-preview, so selecting a Studio in the list previews it instantly
* Multi-select and bulk edit, with one popup that sets group, parent, output, facet, or lock state on every ticked Studio
* Studio Groups for variant axes (Cameras, Lighting Moods, Color Variants, etc.)
* Tags and free-text notes per Studio
* Render-settings templates: five built-ins (Default, Instagram Square, Portrait, Story, YouTube) plus your own saved from the current scene; templates persist across `.blend` files
* Post-render actions: copy, move, delete folder, play sound, Slack webhook; runs as an ordered chain
* Path templates with `{studio}`, `{studio_uuid}`, `{frame:04d}`, `{ext}`, `{date_time}`, `{user}`, and more
* Stored Properties Lister, a global searchable view of every right-click-stored property across every Studio
* Auto-disambiguation, so `Studio`, `Studio.001`, `Studio.002` works the way Blender's own datablocks do

## Panel layout

| # | Panel | Default state |
|---|---|---|
| 0 | Stage | Studio list, add/duplicate/move buttons, Apply/Update/Render row, Default Output Path |
| 1 | Active Studio | Lock toggle, Parent, Group, Output Path with resolved-path hint, Capture toggles, Notes, Tags, Stored Properties, Post-Render Actions |
| 2 | Render Queue | Pending/running/done/failed counts, add to queue, pause toggle, job list |
| 3 | Bulk Edit | Multi-select and bulk operators (closed by default) |
| 4 | Groups | Variant-axis management (closed by default) |
| 5 | Stored Properties | Global searchable list (closed by default) |

## Why Stage instead of...

| Tool | Stage's edge |
|---|---|
| Renderset | Auto-thumbnails (vs text list); inline shader-node-group inputs (no driver hacks); non-modal multi-edit; dirty-state badge; Studio inheritance; locked Studios; SQLite queue (vs JSON); cross-file user templates |
| Blender Queue | Full scene-state model, not just file-level queueing |
| B-Renderon | Blender-native UX, live scene authoring, no second app to manage |

Out of scope on purpose: render-farm orchestration, mobile dashboards, distributed rendering. Use [Flamenco](https://flamenco.blender.org/) or similar for those.

## Roadmap

What's shipped is the v1.0 core. Tracked next:

* Animation queue support (multi-frame jobs; currently single-frame stills only)
* Material variants per object slot, KeyShot Multi-Material style
* Studio diff viewer: pick two Studios, see what differs
* Studio from Viewport, plus Studio per Selected Camera
* Render-stamp Studio name burn-in
* Open Output Folder button per Studio row
* Skip-if-output-exists, plus an overwrite preflight
* Import/export Studios as JSON, plus cross-file Studio Presets

Bigger v2 ideas, deferred for now: a combinatorial Configurator (cartesian product of variant axes), Image Styles, pipeline-tier post-render actions, Studio-level Python hooks.

If any of those land high on your list, open an [issue](https://github.com/BlueLazyFish/Stage-Render/issues). It helps me prioritise.

## Repository layout

```
stage/
  core/           pure logic: facets, paths, render helper, templates
  ops/            bpy.types.Operator subclasses
  ui/             N-panel, queue panel, Studio UIList
  props/          PropertyGroup definitions (Studio, StudioCollection, etc.)
  queue/          SQLite layer, worker subprocess, monitor timer
  utils/          small helpers (logger, naming, propgroup copy, preview cache)
tests/
  unit/           pure-Python tests
  blender/        in-Blender tests (run via blender -b -P tests/blender/run.py)
scripts/
  package.py      build the extension zip
  stress.py       1000-Studio benchmark
```

## Building from source

```bash
git clone https://github.com/BlueLazyFish/Stage-Render.git
cd Stage-Render
python scripts/package.py        # writes build/stage-<version>.zip
```

The `package.py` script just zips the `stage/` folder with the right shape for Blender's extension manager. No native build step.

To iterate on a checkout without rebuilding the zip every time, symlink or copy `stage/` into your Blender extensions directory and reload from there.

## Development

```bash
# Pure-Python tests (no Blender required)
python -m pytest tests/unit

# Blender-side suite
blender -b -P tests/blender/run.py

# 1000-Studio stress benchmark
blender -b -P scripts/stress.py

# Build the extension zip
python scripts/package.py
```

CI runs both suites on Linux, macOS, and Windows for every push.

## Contributing

Issues and pull requests welcome. Before opening a PR:

1. Run `blender -b -P tests/blender/run.py` and confirm the suite still passes.
2. New behaviour gets a test alongside it. `tests/unit/` for pure-Python, `tests/blender/` if it needs `bpy`.
3. Match the existing style: small focused commits, terse comments only where the *why* isn't obvious.
4. The codebase is intentionally small and modular. If a change spans 5+ files it's probably worth a quick design discussion in the issue first.

Bugs go to the [issue tracker](https://github.com/BlueLazyFish/Stage-Render/issues). For security-relevant reports, open a private security advisory via GitHub.

## License

GPL-3.0-or-later. Required for any addon that imports `bpy`. See `LICENSE` for the full text.

## Acknowledgements

Stage's design takes ideas from earlier work in this space:

* [KeyShot](https://www.keyshot.com/) for the Studio model itself, an atomic camera, environment, and material bundle that you switch between in one click.
* [Renderset](https://blendermarket.com/products/renderset) (polygoniq) for the right-click "store any RNA path" UX and output path templating.
* [Blender Queue](https://github.com/Tilapiatsu/blender-queue) for the persistent job queue concept.
* [B-Renderon](https://github.com/lluisgarcia/B-Renderon) for the background-subprocess rendering pattern.

Stage is an independent codebase, not a fork or derivative of any of the above. The prior art shaped the choices.

---

Built by Louis Rist. [www.mrrist.com](https://www.mrrist.com)
