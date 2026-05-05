# Stage

[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Blender](https://img.shields.io/badge/blender-5.1%2B-orange.svg)](https://www.blender.org/)
[![CI](https://github.com/BlueLazyFish/Stage-Render/actions/workflows/ci.yml/badge.svg)](https://github.com/BlueLazyFish/Stage-Render/actions)
[![Latest Release](https://img.shields.io/github/v/release/BlueLazyFish/Stage-Render?include_prereleases&sort=semver)](https://github.com/BlueLazyFish/Stage-Render/releases)

A KeyShot-inspired scene state manager and persistent render queue for Blender 5.1+.

> Set up your scene once. Save unlimited **Studios** — each a snapshot of camera, lighting, world, visibility, render settings, output path. Switch between them in one click. Queue them all and render overnight while you keep working.

**Status:** v0.1.0 — initial public release. Open source under GPL-3.0-or-later. Issues and PRs welcome.

---

## Why this exists

Blender has *workspaces* (UI layouts) and *scenes* (full duplicates), but nothing in between for scene-state variations. Today most people end up with:

- Six duplicated scenes, broken linked data, manual sync hell
- Hand-toggling collection visibility (always something forgotten)
- Multiple `.blend` files per shot
- Renderset, Blender Queue, B-Renderon — each solves *part* of the problem

Stage combines KeyShot's **Studio** model (granular, thumbnailed variation bundles) with **persistent SQLite-backed background rendering** that keeps the UI responsive and survives Blender restarts.

## What you get

**Studios** — atomic snapshots, each capturing a configurable mix of facets:

- Camera (transform + lens + DoF)
- World / HDRI (image + strength + rotation)
- Visibility (collection + object hide_render + view-layer exclude)
- Render Settings (engine + resolution + per-engine bag for Cycles / EEVEE / Workbench)
- Output Path (per-Studio override + template variables)
- Custom RNA paths via right-click → **Store in Stage**

**Render queue (persistent + background)** — adds Studios as jobs to a SQLite queue at `~/Library/Application Support/Stage/queue.db` (platform-correct path on Linux/Windows). A separate Blender subprocess processes one job at a time so the foreground UI stays free. Survives Blender restarts and crashes.

**Production polish:**

- **Dirty-state badge** — visible "uncommitted changes" indicator after you mutate the scene
- **Inheritance** — child Studio stores deltas only; parent supplies the rest
- **Locked Studios** — refuses Update unless explicitly unlocked (client deliverables)
- **Click-to-preview** — selecting a Studio in the list previews it instantly
- **Multi-select + bulk edit** — set group / parent / output / facet / lock state on every ticked Studio in one popup
- **Studio Groups** — variant axes (Cameras, Lighting Moods, Color Variants)
- **Tags + free-text Notes** per Studio
- **Render-settings templates** — builtin defaults (Default, Instagram Square / Portrait / Story, YouTube) + save your own from the current scene; templates persist across `.blend` files
- **Post-render actions** — copy / move / delete folder / play sound / Slack webhook, ordered chain
- **Path templates** — `{studio}`, `{studio_uuid}`, `{frame:04d}`, `{ext}`, `{date_time}`, `{user}`, …
- **Stored Properties Lister** — global searchable view of every right-click-stored property across every Studio
- **Auto-disambiguation** — `Studio`, `Studio.001`, `Studio.002` like Blender's own datablocks

## Install

### From the latest release

1. Grab `stage-<version>.zip` from the [Releases page](https://github.com/BlueLazyFish/Stage-Render/releases/latest)
2. Open Blender → **Edit → Preferences → Get Extensions**
3. Click the dropdown arrow at the top-right of the panel → **Install from Disk…**
4. Pick the `.zip`, tick **Stage** to enable

The same `.zip` works on macOS, Linux and Windows — Stage is pure Python, no platform-specific binaries.

### Build it yourself

```bash
python scripts/package.py        # writes build/stage-<version>.zip
```

### From source (dev)

Symlink or copy the `stage/` folder into your Blender extensions directory, or run the test runner directly to verify a checkout works in your Blender:

```bash
blender -b -P tests/blender/run.py
```

## Quick start

1. Open the **Stage** tab in the N-panel
2. Click **+** to add a Studio — it captures the current scene state
3. Tweak the scene (move camera, swap world, hide a collection)
4. Click **+** again — second Studio captures the new state
5. Click between them in the list — scene snaps back instantly
6. Set an **Output Path** (folder is fine, Stage auto-names files per Studio)
7. **Save** the `.blend`, then **Queue All Enabled** in the Render Queue subpanel
8. Toggle **Auto-Render: ON** in the queue panel to start processing — files land in your output folder

## Panel layout

| # | Panel | State |
|---|---|---|
| 0 | **Stage** | Studio list + add/duplicate/move + Apply/Update/Render + Default Output Path |
| 1 | **Active Studio: \<name\>** | Lock toggle, Parent / Group, Output Path + resolved-path hint, Capture toggles, Notes / Tags, Stored Properties, Post-Render Actions |
| 2 | **Render Queue** | Pending / running / done / failed counts, Add to queue, Pause toggle, job list |
| 3 | **Bulk Edit** *(default closed)* | Multi-select + bulk operators |
| 4 | **Groups** *(default closed)* | Variant-axis management |
| 5 | **Stored Properties** *(default closed)* | Global searchable list |

## Why Stage instead of …

| Tool | Stage's edge |
|---|---|
| **Renderset** | Auto-thumbnails (vs text list); inline shader-node-group inputs (no driver hacks); non-modal multi-edit; dirty-state badge; Studio inheritance; locked Studios; SQLite queue (vs JSON); cross-file user templates |
| **Blender Queue** | Full scene-state model, not just file-level queueing |
| **B-Renderon** | Blender-native UX; live scene authoring; no second app to manage |

Out of scope by design: render-farm orchestration, mobile dashboards, distributed rendering. Use [Flamenco](https://flamenco.blender.org/) or similar for those.

## Roadmap

What's shipped is roughly the v1.0 *core*. Tracked next:

- **Animation queue support** — multi-frame jobs (currently single-frame stills only)
- **Material variants per object slot** (KeyShot Multi-Material)
- **Studio diff viewer** — pick two Studios, see what differs
- **Studio from Viewport** + **Studio per Selected Camera** ops
- **Render-stamp Studio name burn-in**
- **Open Output Folder** button per Studio row
- **Skip-if-output-exists** / overwrite preflight
- **Import / export Studios as JSON** + cross-file Studio Presets

Bigger v2 ideas (deferred): combinatorial **Configurator** (cartesian product of variant axes), Image Styles, pipeline-tier post-render actions, Studio-level Python hooks.

Open an [issue](https://github.com/BlueLazyFish/Stage-Render/issues) if any of those land high on your list — it helps prioritise.

## Development

```bash
# Run the unit suite (pure Python, no Blender)
python -m pytest tests/unit

# Run the Blender-side suite (requires Blender 5.1+)
blender -b -P tests/blender/run.py

# Stress test: 1000-Studio benchmark
blender -b -P scripts/stress.py

# Build the extension zip
python scripts/package.py
```

CI runs both suites on Linux / macOS / Windows for every push.

### Code structure

```
stage/
  core/           pure logic — facets, paths, render helper, templates
  ops/            bpy.types.Operator subclasses
  ui/             N-panel + queue panel + Studio UIList
  props/          PropertyGroup definitions (Studio, StudioCollection, …)
  queue/          SQLite layer + worker subprocess + monitor timer
  utils/          small helpers (logger, naming, propgroup copy, preview cache)
tests/
  unit/           pure-Python tests
  blender/        in-Blender tests (run via blender -b -P tests/blender/run.py)
scripts/
  package.py      build the extension zip
  stress.py       1000-Studio benchmark
```

## Contributing

Issues and PRs welcome. Before opening a PR:

1. Run `blender -b -P tests/blender/run.py` and confirm the suite still passes
2. New behaviour gets a test alongside it (whichever side it touches — `tests/unit/` for pure-Python, `tests/blender/` if it needs `bpy`)
3. Match the existing style — small focused commits, terse comments only where the *why* is non-obvious
4. The codebase is intentionally small and modular; if a change spans 5+ files it's probably worth a quick design discussion in the issue first

Bugs go to the [issue tracker](https://github.com/BlueLazyFish/Stage-Render/issues). For security-relevant reports, please open a private security advisory via GitHub.

## License

GPL-3.0-or-later — required for any addon that imports `bpy`. See [LICENSE](LICENSE).

## Acknowledgements

Stage's design borrows liberally from work that went before:

- **[KeyShot](https://www.keyshot.com/)** — the **Studio** model (atomic camera + environment + material bundle) is theirs; we adapted it to Blender
- **[Renderset](https://blendermarket.com/products/renderset)** (polygoniq) — the right-click "store any RNA path" UX, output path templating
- **[Blender Queue](https://github.com/Tilapiatsu/blender-queue)** — persistent job queue concept
- **[B-Renderon](https://github.com/lluisgarcia/B-Renderon)** — background-subprocess rendering pattern

Stage isn't a fork or derivative of any of the above — independent codebase — but the prior art shaped the design choices.
