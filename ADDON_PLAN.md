# Blender Studio Manager — Planning Document

A KeyShot-inspired scene state manager and render queue for Blender. The goal: kill the "duplicate the scene 6 times to render variations" workflow forever.

> **Working name suggestions:** *Studio*, *Atelier*, *Stage*, *Loft*, *Vignette*, *Curtain*, *RenderDeck*. Pick one with a single-word identity — easier to brand and easier for users to refer to in conversation. The doc uses **Studio** as a placeholder.

---

## 1. Vision & Positioning

### The one-line pitch
> Set up your scene once. Save unlimited "Studios" — each a complete snapshot of camera, lighting, materials, visibility, and render settings. Switch between them in one click. Render them all overnight.

### Why this exists
Blender has *workspaces* (UI layouts) and *scenes* (full duplicates), but nothing in between. Users currently solve scene variation with:

1. **Duplicating scenes** — heavy, breaks linked data, painful to keep in sync
2. **Hiding/unhiding collections manually** — error-prone, easy to forget what was on/off
3. **Multiple .blend files** — fragments work, kills iteration speed
4. **Existing addons (Renderset, Blender Queue, B-Renderon)** — solve parts of this but each has gaps

### Competitive landscape (what we learned from the references)

| Addon | What it nails | What's missing |
|---|---|---|
| **Renderset** (polygoniq) | "Right-click any property → store in context" — extremely flexible. Output path variables. Batch context editing (Multi Edit mode). Context Lister overview. Compositor File Output integration. Save & Pack for clients/farms. | No thumbnails — pure text list. Material variants are right-click-active-slot only (no proper per-object variant system). Shader node group inputs *cannot* be stored directly (users have to drive them via custom property + driver — a real hack). Multi-edit is modal (separate "mode" you enter and exit). Lister is a popup, not dockable. Per-scene preferences cause confusion. No "dirty" indicator if you forget to update a context. No KeyShot-style configurator. No reusable cross-file presets. |
| **Blender Queue** | Persistent JSON queue across sessions. Path shortcodes. | In-Blender only — no scene-state management, just a file/scene queue. |
| **B-Renderon** | Standalone, robust, parallel GPU rendering, watch folders, scheduler, multi-Blender-version support. | Standalone means no live scene state authoring. Not Blender-native UX. |
| **BRQ / BLeQ / RenderCue** | Simpler, lighter queues. Background rendering keeping UI responsive. | Limited scope — pure queue, no state system. |
| **KeyShot (the inspiration)** | **Studios** = atomic bundle of camera + environment + model set + material variants + image style. **Configurator** = render the matrix of variations. Thumbnails everywhere. | Not Blender. |

### Our wedge
Nobody combines **KeyShot's Studio model** (rich, thumbnailed, granular variation bundles) with **Blender Queue's persistence** and **B-Renderon's robust background rendering**, *delivered as a Blender-native addon*. That's the gap.

We are deliberately **not** chasing:
- Mobile dashboards or QR-code monitoring (out of scope; not what creative users buy this for)
- LAN / distributed / farm rendering (huge surface area, separate product category — leave it to Flamenco/Sheepit, integrate later if needed)
- Standalone application (B-Renderon's territory; we want Blender-native UX)

This focus lets every feature we *do* build feel deep instead of thin.

### Where we specifically beat Renderset

Renderset is the closest existing tool. Studying their docs in detail surfaces concrete optimization opportunities — these are the bullet points that should appear in every comparison chart and marketing page:

1. **Visual-first, not text-first.** Renderset is a text list with optional color dots. Every Studio in our addon has an auto-generated thumbnail. Identification is faster, demos look better, and grid view becomes possible.
2. **Native shader node group inputs.** Renderset *cannot* store node group inputs directly — they recommend a custom-property + driver workaround. We capture them as a first-class facet using the inline shader nodes API (5.0+).
3. **Geometry Nodes inputs as a real facet.** Renderset doesn't address this; we use 5.1's reworked GN modifier API (`modifier.properties.inputs.<id>.value`) to capture and swap GN inputs cleanly.
4. **Real per-object material variants.** Renderset's "right-click the active material slot to store" only handles the active slot and is awkward for multi-slot objects. We mirror KeyShot's Multi-Material: each object has a named list of variants, swappable per Studio per slot.
5. **Non-modal multi-edit.** Renderset has a "Multi Edit Mode" you enter and exit. We do shift/ctrl-click multi-select with inline spreadsheet-style editing — no mode switch.
6. **Dirty-state indicator.** Renderset silently absorbs your scene changes into the active context. We show an obvious "Studio has uncommitted changes — Update / Discard" badge so you never lose work or render a stale Studio.
7. **Hierarchical settings model.** Renderset has confusing per-scene preferences. We define a clear inheritance: **Addon Prefs → Project (.blend) → Studio Group → Studio**, where each level overrides the level above. Document the hierarchy in tooltips.
8. **Dockable Lister, not a popup window.** The all-Studios overview lives in the N-panel as a collapsible section.
9. **Snapshot history per Studio.** Renderset has no per-context undo. Every "Update Studio" pushes a revision; users can roll back.
10. **Smarter render-slot mapping.** Renderset assigns render slots by list index, even for unchecked contexts (so 8 unchecked + 8 checked = nothing in slots). We assign by *enabled order* — what users actually expect — and don't hard-cap at 8 (Renderset relaxed this in 1.8.1; we follow).
11. **Cross-file Studio presets.** Renderset stores everything in the .blend with no library export/import. We ship a reusable preset format (versioned JSON + packed assets) so a "three-point lighting Studio" can be loaded into any project.
12. **Studio inheritance.** "Studio B = Studio A with one camera swapped" via an explicit `parent` pointer. No equivalent in Renderset.
13. **Locked Studios.** Mark a Studio "approved/final"; refuses Update unless explicitly unlocked. Critical for client deliverables.
14. **Crash-resilient queue.** SQLite-backed (transactional), not JSON. Resumes incomplete jobs after crash or restart.
15. **`hide_viewport` is a known Blender limitation** (not Renderset's fault) — we surface this honestly in the UI rather than silently ignoring it.

---

## 2. Core Concepts (the vocabulary)

Get the names right early — they propagate through UI, docs, and user mental models.

### Studio
The atomic unit. A named, thumbnailed snapshot of the scene state. Contains a configurable set of **facets** (see below), an optional **parent** Studio for inheritance, free-form **tags**, and a multi-line **notes** field. One Studio = one row in the UI list = one render output.

### Facets (what a Studio can capture)
The user toggles which facets each Studio stores. Granularity is the killer feature — *don't force "store everything"*.

- **Camera** — active camera + its transform + lens settings + DoF
- **World / Environment** — active world, HDRI, strength, rotation
- **Lighting** — visibility/transform of any light or collection of lights
- **Visibility** — collection enable/exclude, object hide_render, object hide_viewport
- **Materials** — material slot assignments per object (or material override on view layer)
- **Render settings** — engine + engine-specific bag (Cycles vs EEVEE Next have non-overlapping settings; never flat-merge them)
- **View layer** — active view layer, render passes, Light Groups, Cryptomatte, custom AOVs
- **Output** — file path, format, naming pattern
- **Compositor** — node group reference or full tree (Blender 5.0+ allows this)
- **Modifiers** — modifier viewport/render visibility per object
- **Shape keys / drivers** — values
- **Animation Action** — `Object.animation_data.action` for character / pose work
- **Custom properties** — any RNA path the user right-clicks → "Store in Studio"
- **Frame range** — for animation Studios

### Studio Group (a.k.a. "Variant Axis")
A container of Studios that represent **one axis of variation**. e.g. a "Cameras" group, a "Lighting Moods" group, a "Color Variants" group. This is what enables the **Configurator** — render the matrix `Cameras × Lighting × Color = N renders`. Flat axis, not parent/child.

### Studio Inheritance (parent pointer)
Optional `parent_uuid` on a Studio. The child stores only the fields it overrides; everything else is inherited from the parent. Massively reduces duplication when "Studio B = Studio A with one camera swapped." Orthogonal to Studio Groups.

### Tags
Free-form string tags on each Studio (e.g. `#wip`, `#client-a`, `#final`). Filterable in the Lister. Orthogonal to Groups.

### Preset (cross-file reusable)
A Studio template saved to disk (versioned JSON + optional packed assets) that can be loaded into *any* .blend file. e.g. "Studio Lighting Three-Point", "Cycles Final 4K". Renderset doesn't do this well; this is a key differentiator.

### Render Job
An entry in the queue. References `(scene_name, studio_uuid)` (multi-scene .blends are common), a frame range, and a target Blender version. Lives in the persistent queue.

### Project File (queue persistence)
External SQLite database (not JSON — see §5) listing all jobs across all .blend files. Survives Blender restarts and crashes; supports transactional state updates and resume.

---

## 3. Feature List

Organized into **MVP**, **v1.0**, **v1.x**, and **v2.0+** so you can ship something useful fast and grow it.

### MVP — "Save and switch state" (4–6 weeks of focused work)

The minimum viable Studio system. Ship this first. Resist scope creep.

- [ ] Add/rename/duplicate/delete Studios in a UIList with **drag-to-reorder** + keyboard nav (arrow keys move ±1, Shift+arrow for batch step, Ctrl+arrow for top/bottom — Renderset's power-user pattern)
- [ ] **Active Studio invariant** — exactly one Studio is active at all times. Delete is disabled when only one remains; deleting the active Studio activates the next one in the list. Never zero, never two.
- [ ] Capture facets: **Camera, World, Visibility, Render Settings, Output Path** (the 5 most impactful)
- [ ] Per-Studio facet toggles (this Studio captures camera+world only, that one captures everything)
- [ ] One-click "Switch to Studio" — applies stored state to the scene
- [ ] Auto-generated thumbnail (Workbench render at 256px on Studio creation/update)
- [ ] **Studio per Selected Camera** — one click creates one Studio per selected camera, named after the camera
- [ ] **Select Active Studio's Camera** — one-click operator to select the active Studio's camera in the viewport (no outliner hunting when editing camera-specific settings)
- [ ] **Studio from Viewport** — capture current viewport as a new camera + Studio in one click. *Clears any camera animation keyframes on capture* so the new camera isn't tied to the previous one.
- [ ] **Dirty-state indicator** — when the scene mutates after applying a Studio, show a "● uncommitted changes" badge with **Update** and **Discard** buttons. *Key UX win over Renderset.*
- [ ] "Update Studio from current scene" button (also exposed via the dirty badge)
- [ ] **Per-Studio notes field** — plain free-text, multi-line. Users will paste client feedback into it.
- [ ] Render single Studio button
- [ ] Render all enabled Studios sequentially
- [ ] **Auto-burn Studio name into render stamp** metadata — built-in, not opt-in
- [ ] **Sanitize Studio names** — slashes, control chars, reserved Windows names cannot break path generation
- [ ] **Restore `render.filepath`** to its original value after each render — never permanently mutate the user's render path
- [ ] Output path variables (full set):
  - **Studio context:** `{studio}`, `{studio_group}`, `{context_render_type}` (still/animation)
  - **File:** `{blendname}`, `{blend_parent_folder}`, `{blend_full_path}`
  - **Frame:** `{frame}`, `{frame_start}`, `{frame_end}`, `{frame_step}`
  - **Resolution:** `{resolution_x}`, `{resolution_y}`, `{resolution_x_scaled}`, `{resolution_y_scaled}`, `{resolution_percentage}`
  - **Render region:** `{render_region_width}`, `{render_region_height}` plus `_scaled` variants
  - **Scene:** `{camera}`, `{world}`
  - **Date/time:** `{date_time}` (ISO), `{year}`, `{month}`, `{day}`, `{hour}`, `{minute}`, `{second}`
  - **System:** `{user}`, `{machine}` / `{hostname}`, `{ext}`
- [ ] Storage: PointerProperty on Scene → CollectionProperty of Studios. All in the .blend.

### v1.0 — "Production-ready" (additional 6–8 weeks)

What makes people pay for it.

- [ ] **Right-click → Store in Studio** for arbitrary RNA paths (Renderset's killer move — we match it)
- [ ] **Native shader node group input storage** — capture node group input values directly as a facet (Renderset *can't* do this without driver hacks; we do it cleanly)
- [ ] **Material variants per object slot** — list of named material options per object, swap-per-Studio per slot (KeyShot's "Multi-Material", done properly)
- [ ] **Studio inheritance (parent pointer)** — child stores deltas only; parent supplies the rest. Cycle detection + max depth cap.
- [ ] **Tags on Studios** — filterable in Lister, orthogonal to Groups
- [ ] **Locked / approved Studios** — refuses Update unless explicitly unlocked. For client deliverables.
- [ ] **Hover-to-preview** — hover over a Studio in the list, the viewport temporarily previews it; click to commit. *(Promoted from v1.x — it's the demo-worthy moment.)*
- [ ] **Starter Studio templates** ship with the addon (Three-point lighting, Product turntable, Architectural day/night). First-run activation moment — first thumbnail in the panel sells the addon.
- [ ] **Studio Lister** — dockable side panel (not a popup) showing every stored property across every Studio in a searchable, filterable table. Group by facet, filter by Studio, jump-to-source on any value.
- [ ] **Batch Rename** — Find/Replace + Regex across selected Studios with checkbox multi-select (Renderset pattern; essential past ~20 Studios)
- [ ] **N-panel subpanel structure** — Toolbox / Global Settings / Studio Settings / Camera / World / Output / Overrides as collapsible sections, each exposing high-frequency Blender settings inline so users don't tab-hop between Properties-editor regions. See §5 for layout.
- [ ] **Studio Groups** (variant axes) — UI grouping with collapse/colour-coding
- [ ] **Background rendering** — render Studios without freezing Blender UI (subprocess approach, see §5)
- [ ] **Auto Lock Interface during render** — *default ON* (Renderset has this as opt-in but says "heavily recommended" — we make it default). Prefs toggle to disable. Prevents crashes, speeds rendering.
- [ ] **Free persistent data after render** — auto-free Cycles persistent data when queue completes (toggleable). Memory hygiene for overnight queues.
- [ ] **Persistent SQLite queue** — `bpy.app.cachedir/studio_queue.db`. Transactional per-job state, indexes, no extra dependencies (sqlite3 is stdlib).
- [ ] **Crash recovery / queue resume** — per-job state persisted; on Blender restart, prompt "Resume incomplete queue? N jobs interrupted at <timestamp>"
- [ ] **Render scheduler** — start at X time, stop at Y time
- [ ] **Skip-if-output-exists** toggle per Studio — don't re-render if `{output}.png` is newer than the .blend. Saves hours on iterative work.
- [ ] **Notifications** — desktop notification on completion, optional webhook
- [ ] **Auto-shutdown / suspend** after queue completes
- [ ] **Diff viewer** — pick two Studios, show table of differing properties (none of the references do this)
- [ ] **Non-modal multi-edit** — shift/ctrl-click multi-select Studios, edit values inline; preview-then-apply panel shows the change list with per-row exclude (improves on Renderset's modal Multi Edit)
- [ ] **Render Slots integration** — first N *enabled* Studios fill render slots in enabled order (no hard cap; Renderset relaxed this and we follow)
- [ ] **Latest Output button per Studio** — magnifying-glass icon in the UIList row opens the Studio's output folder in the OS file browser (extends Renderset's "latest preview" affordance to all renders)
- [ ] **Color coding with optional labels** — assign a meaning per Studio (e.g. red = WIP, green = approved). Color shows in UIList row; label in tooltip and Lister. Beats Renderset's bare dots.
- [ ] **Native render-operator routing** (opt-in) — Blender's F12 / Render Image routes through the active Studio, with a clear toggle in prefs to disable for users who want raw Blender behavior
- [ ] **Variable-picker UI** — *Add Variable* and *Peek Variables* buttons next to every path field for discoverability (Renderset pattern)
- [ ] **Per-render-type output filename templates** — separate templates for *Still Image* / *Animation Frame* / *Animation Movie*. Animation-Frame template *must* include `{frame}` (or files overwrite); surface a UI warning if it doesn't.
- [ ] **Multi-frame format warning** — when user selects AVI / MP4 / MKV for animation, show an inline hint: "Per-frame PNG/EXR is safer (resume on crash, no quality loss; stitch later)". Don't block, just inform.
- [ ] **Output path overwrite preflight** — before queue start, expand every enabled Studio's path and warn if two resolve to the same file. Prevents "all my renders went to one file" mistakes.
- [ ] **Granular visibility-restriction toggles** — per-prefs choice of *which* restrictions are stored (selectable / viewport / render / holdout / indirect-only / collection enable/exclude). Renderset stores them all and pays a perf cost in big scenes; we let users opt in.
- [ ] **Overrides subpanel** — separate UI section for custom-stored RNA paths (distinct from facet-based storage). Only appears when at least one custom property is stored. Renderset's pattern; keeps the main panel uncluttered.
- [ ] **Save Output Settings as Default** + **Apply Settings to Other Scenes in .blend** — two Renderset features that save real friction. The first persists current settings as the default for new .blends; the second propagates within the current file.
- [ ] **"Freeze time" on batch renders** — all jobs in one batch share a single `{date_time}` so outputs group as a coherent batch instead of drifting per-job
- [ ] **Empty-folder cleanup on cancel** — don't leave empty output folders behind when the user aborts
- [ ] **Animation + fixed seed warning** — flag fixed Cycles seed during animation queue (causes flicker)
- [ ] **Post-Render Actions** (production tier) — global defaults + per-Studio overrides. Primitives:
  - `copy output file` / `move output file`
  - `slack webhook`
  - `delete output folder`
  - `play sound`
  - **Action ordering matters** (move before copy breaks the chain) — UI visualises the sequence.
- [ ] **Import/export Studios as JSON** — versioned (`format_version` in payload from day one)
- [ ] **Cross-file Presets** — save Studio templates to user library, load into any .blend
- [ ] **Save & Pack** — recursively make-local + pack-external all data into a copy of the .blend. Specifically handles **IES textures** (light probe), linked libraries by absolute path. For sending to clients, archiving, or backup.

### v1.x — "Nice quality of life"

- [ ] **Snapshot history per Studio** — every "Update Studio" pushes a revision (last N kept), one-click rollback. Renderset has no equivalent and it bites users; we make it core.
- [ ] **Studio thumbnail grid view** — toggle between list and content-browser-style grid (use `bpy.app.cachedir` from 5.1 for thumbnail storage)
- [ ] **Compositor variants** per Studio — store a reference to a `CompositorNodeTree` via `Scene.compositing_node_group` (clean since 5.0; no hacks)
- [ ] **Custom file output nodes** with per-Studio routing. Output naming pattern: `{NODE_NAME}_{INPUT_NAME}_{OUTPUT_FILENAME}` so multiple file output nodes don't clash. Handle 5.0+ `directory` + `file_name` socket split.
- [ ] **Auto Render Layer Split** — optionally inject a managed compositor output node that splits passes into separate files. Self-heal links if disconnected. (Opt-in.)
- [ ] **Render preview presets** — Workbench engine, sample-multiplier (%), or resolution-multiplier (%) for fast contact-sheet renders. One-click "Preview All Studios" for a low-quality grid.
- [ ] **View layer + render passes per Studio** — including Light Groups, Cryptomatte, custom AOVs (5.0+ comp pipeline)
- [ ] **Camera Render Region** stored per Studio
- [ ] **Geometry Nodes input variants** — per-Studio overrides on `modifier.properties.inputs.<name>.value` (5.1's new GN modifier API makes this clean)
- [ ] **Working color space + view transform** captured per Studio (wide-gamut/ACEScg workflows from 5.0+)
- [ ] **HDRI library panel** with thumbnail browser (auto-generates Studios when HDRI dropped onto an existing camera)
- [ ] **Animation Studios** — separate frame range per Studio, animation queue
- [ ] **Action / pose capture** — per-Studio `Object.animation_data.action` for character work
- [ ] **Pie menu** for Studio switching — user-rebindable, off by default
- [ ] **Per-Studio hotkeys (1–9)** — workspace-style modal switching
- [ ] **Disk-space preflight** — estimate queue output size, warn if `> free`. Cheap to implement, prevents 4-hour failure modes.
- [ ] **Memory-usage estimator** — Renderset shipped a Beta in 1.8; pre-flight before queue start
- [ ] **Switch to solid viewport during render** — VRAM saver for heavy scenes (toggleable)
- [ ] **Save startup defaults / Apply settings to other scenes** — propagate output settings between scenes in a .blend, or save current settings as default for new .blends

### v2.0+ — "The differentiators"

This is where you genuinely surpass the reference addons. Scope is deliberately tight — these are **deep** features, not a long list.

- [ ] **Configurator / Combinatorial Renders** — pick N Studio Groups, render the cartesian product (`Cameras × Materials × Lighting`). Output filename auto-templated using `{matrix_axis_name}` variables. Show a preview grid of "what will be rendered" before committing. KeyShot has this; no Blender addon does it well. **Headline v2 feature.**
- [ ] **Image Styles** — post-processing presets (color management + view transform + compositor LUTs + glare/bloom/vignette) as standalone reusable bundles, swappable per Studio. KeyShot equivalent that's genuinely missing in Blender.
- [ ] **Post-Render Actions: pipeline tier** — extend v1.0 primitives with: `run script`, `encode to video`, `upload to S3/Drive`. Pipeline-ready.
- [ ] **Studio-level Python hooks** — `pre_render`, `post_render`, `on_switch` script slots per Studio (with safety: disable-by-default + signed-script warning + audit log)
- [ ] **Snap to Studio** — pin a Studio thumbnail to the N-panel header for one-click recall

### Stretch / cut

Demoable but low ROI — re-evaluate post-launch.

- ~~**Watch folders**~~ — feels like B-Renderon territory, doesn't compose well with the Studio model
- ~~**Visual diff timeline**~~ — strong demo, weak utility
- ~~**Smart shaderball overrides**~~ — genuinely a separate addon

---

## 4. Development Route — Phased Roadmap

### Phase 0 — Foundations (Week 1–2)
**Goal: project skeleton, no features yet.**

- Scaffold addon with the modern extension layout (`__init__.py` + `blender_manifest.toml`, no legacy `bl_info` dict needed)
- **Lock target: Blender 5.1+** — `blender_version_min = "5.1.0"` in the manifest. This buys us:
  - Python 3.13 (modern type hints, built-in `tomllib`, performance improvements)
  - `Scene.compositing_node_group` for clean per-Studio compositor swaps (5.0+)
  - New Geometry Nodes modifier API (`modifier.properties.inputs.X.value`) — clean GN-input facets (5.1)
  - `bpy.app.cachedir` — sanctioned location for thumbnail cache and SQLite queue (5.1)
  - `bpy.app.handler.exit_pre` — hook to gracefully cancel any spawned background renders if Blender quits mid-job (5.1)
  - Wide-gamut working color space and ACES views (5.0+) as a capturable facet
  - Mature extensions repo and updated UI conventions
- **Resolve open engineering decisions** (see §5): undo behavior, driver conflict policy, library override semantics, multi-scene model, render-engine-specific facet shape. These bake into the data model — fix them before code.
- **Pricing model decided** (one-time vs sub vs free-lite split) — affects feature priorities for Phase 1+
- **Discord/community channel** stood up — cheaper support than email, builds advocates pre-1.0
- **CI matrix** including Apple Silicon — Renderset shipped a 2.0.1 bug specifically for M1/M2/M3, so M-series Mac is non-trivial
- Submit listing scaffolds to extensions.blender.org *and* Superhive early (claim names, get the validation pipeline working)
- Property registration architecture (PropertyGroups with proper `bl_idname`, `format_version` migration stubs from day one)
- Basic UI Panel in the Properties → Output area + N-Panel tab
- Logging system (don't `print` — use a wrapped logger so users can grab logs from prefs)
- Settings: addon preferences with paths, defaults, feature toggles
- Test fixtures: a few sample .blends with multi-camera setups, multi-scene .blends, linked libraries, drivers — to dogfood against

### Phase 1 — Studio core (Week 3–6)
**Goal: ship the MVP feature set above.**

- PropertyGroup hierarchy: `StudioCollection` → `Studio` → `Facet` (one PropertyGroup per facet type, or a single Studio with optional fields)
- Capture/restore for the 5 MVP facets
- **Round-trip invariant test** (Phase 1 deliverable) — capture → mutate → restore → equal. Central correctness check; catches whole categories of bugs.
- **1000-Studio stress test as Phase 1 deliverable** — 200 Studios × 50 custom props each. Measure UI redraw, save, load, switch latency. If perf is bad, the architecture changes — better to know now than at v1.0 RC.
- Thumbnail generation as a non-blocking modal operator (Workbench render to a tempfile, load as preview)
- UIList for Studios with thumbnail column, name, enabled checkbox, render-this-only button, drag-to-reorder
- Operators: `studio.add`, `studio.remove`, `studio.duplicate`, `studio.update_from_scene`, `studio.apply`, `studio.render_one`, `studio.render_all`
- Output path variable expansion (write a single `expand_path(template, context)` function — every other feature will use it)
- **Internal alpha** — share with 2–3 trusted users, get feedback on terminology and basic flows

### Phase 2 — Production polish (Week 7–14)
**Goal: paid v1.0 release-ready.**

- Right-click "Store in Studio" — register a custom RIGHT-CLICK menu via `WM_MT_button_context.append`. Store the data path string. On apply, walk it with `path_resolve`.
- Material variants — extra PropertyGroup on Object holding a list of material options
- Studio Groups, inheritance, tags, locked Studios
- **Background rendering** — the hardest engineering piece, see §5
- **SQLite queue** with transactional per-job state at `bpy.app.cachedir/studio_queue.db`
- **Crash recovery** for queue resume
- Notifications + post-render actions (copy / move / slack / delete folder / play sound)
- Diff viewer — generic property tree compare across two Studios
- Cross-file Preset library with `format_version`
- **Onboarding walkthrough on first install** — guided "create your first Studio" flow. Critical for paid addons; first 5 minutes determine retention.
- **Beta release** to existing Blender Market / Superhive customer base of similar tools

### Phase 3 — Differentiation (Month 4–6)
**Goal: features no other addon has.**

- **Configurator** — UI for selecting axis groups (Studio Groups marked as "axes"), computing the cartesian matrix, queueing N jobs with auto-templated output filenames. Show a preview grid before committing.
- **Image Styles** as a separate bundle type — color management + view transform + simple compositor effects (glare/bloom/vignette) packaged as portable JSON, swappable per Studio
- **Snapshot history per Studio** — keep last N revisions of each Studio's stored values, allow rollback
- **Studio-level Python hooks** with safety rails (off by default in prefs, audit log)
- **Public 1.0 launch** — Superhive listing, Blender Extensions submission, 1-month launch promo

### Phase 4 — Ecosystem (Month 6+)
- Asset Browser integration — Studios appear as draggable assets in the browser
- Public API for other addons — let TurboTools, geo-nodes asset packs, etc. register custom facet types via the engine adapter interface (see §5)
- Documentation site, video tutorials
- Free "lite" version on extensions.blender.org for funnel, paid Pro on Superhive
- *(Deliberately not in scope: render farm integrations, mobile/web dashboards, distributed rendering. If demand emerges post-launch, those become candidates for a separate companion product.)*

---

## 5. Technical Architecture

### Open engineering decisions (resolve in Phase 0)

These bake into the data model — changing them later is expensive. Pick a default for each before code starts.

#### Undo / redo integration
Applying a Studio mutates the scene. Decide: does it push one undo step, many, or none? **Recommended: single `bpy.ops.ed.undo_push()` after the batch property apply, labeled `Apply Studio: <name>`.** Document so users aren't surprised by `⌘Z`.

#### Driver / F-curve conflict resolution
If a stored property is driven or animated, `setattr` silently loses to the driver next frame. Three options:
1. **Refuse to capture driven properties** at capture time, with a UI warning
2. **Disable the driver on apply** (and re-enable on revert)
3. **Capture with a `driven` flag** and skip on apply

**Recommended: option 1.** Cleanest semantics; user fixes the source of truth.

#### Library override + linked-data semantics
Production scenes lean heavily on linked collections/materials. A Studio touching library-overridden data shows a clear UI banner. If the linked source moves (re-link / library re-pathed), stored data paths break — surface broken paths in the Lister with a "fix path" affordance instead of silent failure.

#### Multi-scene .blend handling
Each scene has its own `Scene.studio_data`. Queue jobs reference `(scene_name, studio_uuid)` not just `studio_uuid`. The Lister shows the scene next to each job. Switching scenes does not change which Studio is "active" — that's per-scene.

#### Render-engine-specific facets
Cycles vs EEVEE Next have non-overlapping settings. The render facet is split: store `engine` + `engine_settings` (per-engine bag). Switching a Studio's engine clears the engine-specific bag rather than corrupting it. See engine adapter pattern below.

### Engine adapter pattern

Abstract Cycles / EEVEE Next / Workbench (and eventually Octane / LuxCore / TurboTools) behind a small interface. Renderset bolts on third-party engine support over years, version-by-version — cleaner if it's a first-class extension point.

```python
class EngineAdapter:
    engine_id: str  # e.g. 'CYCLES', 'BLENDER_EEVEE_NEXT', 'BLENDER_WORKBENCH'

    def get_capturable_props(self, scene) -> list[StoredProp]:
        """Return engine-specific RNA props worth capturing."""

    def apply_props(self, scene, props: list[StoredProp]) -> None:
        """Apply the props to the scene; never throw on missing keys (log + skip)."""

    def validate(self, props) -> list[ValidationError]:
        """Pre-flight checks (e.g. fixed Cycles seed during animation)."""
```

Public API in Phase 4 lets third-party addons register their own adapters.

### Data model (sketch)

```
AddonPreferences
└── default_output_pattern, library_path, notification_settings,
    pie_menu_enabled, hotkeys_enabled, viewport_solid_during_render, ...

Scene.studio_data : StudioCollection
├── active_index : int             # invariant: 0 ≤ active_index < len(studios); never empty
├── format_version : int          # forward-compat for in-blend storage
├── groups : CollectionProperty(StudioGroup)
│   └── name, color, expanded, studios : CollectionProperty(Studio)
└── studios : CollectionProperty(Studio)  # ungrouped
    └── Studio
        ├── name, uuid, thumbnail_path, enabled, color, locked
        ├── notes : StringProperty (multiline)
        ├── tags : CollectionProperty(StringProperty)
        ├── parent_uuid : StringProperty   # optional — Studio inheritance
        ├── frame_start, frame_end, frame_step, output_override
        ├── facet_camera : FacetCamera (optional, with `enabled` flag)
        ├── facet_world : FacetWorld
        ├── facet_visibility : FacetVisibility
        ├── facet_render : FacetRender
        │   ├── engine : enum
        │   └── engine_settings : per-engine bag (Cycles, EEVEE Next, Workbench)
        ├── facet_materials : FacetMaterials
        ├── facet_action : FacetAction      # pose / character work
        └── custom_paths : CollectionProperty(StoredProp)
            └── data_path, value_repr, value_type
```

### UI panel layout (N-panel structure)

The N-panel "Studio" tab is organized into collapsible subpanels mirroring the natural editing flow. Each subpanel exposes high-frequency Blender settings inline so users don't tab-hop between Properties-editor regions. This is the UX pattern Renderset gets right and we adopt directly.

```
N-panel → Studio tab
├── Toolbox            operators: Studio per Camera, Studio from Viewport,
│                                 Select Camera, Save & Pack, Batch Rename
├── Global Settings    scene-wide: Simplify, Tiling, Light Tree, Persistent Data
├── Studio List        UIList with thumbnails, drag-to-reorder, dirty badge,
│                      lock icon, latest-output button per row
├── Studio Settings    per-Studio quick access: render type, engine, samples,
│                      max bounces, view transform, look, exposure, gamma,
│                      resolution, clamps
├── Camera             focal length, clip start/end, shift X/Y, passepartout,
│                      Select Camera + Lock-to-View buttons
├── World              HDRI, strength, rotation, transparency
├── Output             paths, filenames, format. Locked to prefs by default;
│                      per-Studio override via lock icon (matches §5 hierarchy)
├── Overrides          custom-stored RNA paths — only appears when at least
│                      one is stored
└── [Open Lister]      button opens the dockable Lister side panel
```

Quick-access subpanels **duplicate** native Blender properties; they don't replace them. Users who prefer the Properties editor can collapse the subpanels they don't use; collapse state persists per-user.

The `Studio Settings` / `Camera` / `World` / `Output` subpanels each show a **lock icon** next to every field — locked = inherited from the level above (Studio Group → Project → Prefs), unlocked = overridden on this Studio. Click to toggle, hover for the inheritance trail.

### Settings hierarchy (explicit override chain)

Renderset's biggest UX wart is its confusing per-scene preferences ("settings configured in scene A don't transfer to scene B"). We avoid this by making the inheritance chain explicit and visible:

```
Addon Preferences   (global, user-level defaults)
        ↓ overridden by
Project Settings    (per .blend, stored in Scene)
        ↓ overridden by
Studio Group        (the variant axis)
        ↓ overridden by
Studio              (the leaf)
```

Every settings field shows a small **lock icon** indicating "inherited from N levels up" — click to override locally, click again to revert to inherited. Tooltip shows the full chain. Same UX pattern Blender uses for library overrides.

Practical consequences:
- Output path defaults defined once in prefs; per-project tweaks in Project Settings; per-Studio fine-tuning on the Studio
- Sharing a .blend includes Project Settings (so a colleague gets the same output structure)
- Cross-file Studio Presets only include Studio-level settings (so they don't fight with the recipient's project setup)
- **Post-render actions follow the same hierarchy** — global defaults + per-Studio overrides

### Studio inheritance resolution

When applying a Studio with `parent_uuid` set:

1. Recursively resolve parent chain (cap at 8 levels; cycles → log + treat as no parent)
2. Merge: child's stored facets / props override parent's
3. Apply the merged set

Editing a Studio with children: warn that N children inherit from this one; show "Update children too?" toggle.

### Storing arbitrary properties (Renderset's superpower)

For "right-click any property → store":
- Capture the **full data path** (e.g. `bpy.data.objects["Cube"].modifiers["Subdivision"].levels`)
- Store `(data_path, value, type_hint)` in the Studio
- On apply: resolve the path with `path_resolve`, coerce to type, set with `setattr`
- Wrap each apply in try/except — properties may not exist if the user deleted the object. Log + skip; surface broken paths in the Lister.

### Background rendering — the engineering challenge

Three approaches, ranked:

1. **Modal operator with batched render** *(in-Blender, simple)* — works but UI is locked during render. **Don't ship this as the only option.**
2. **Subprocess Blender instance** *(headless background render)* — spawn `blender -b file.blend --python render_studio.py -- --studio "Hero Shot"`. UI stays responsive. The right default. Used by B-Renderon and BRQ.
3. **Embedded job runner with IPC** — fancier, lets you live-update progress in the panel.

Recommended path: **Start with (2)**, add IPC progress reporting on top in v1.x.

Key implementation details for subprocess approach:
- Save current .blend to a temp copy first (don't render the user's working file directly — they may want to keep editing)
- Pass the Studio name as an argument; the spawned Blender loads addon, switches to Studio, renders, exits
- Capture stdout/stderr line-by-line for the live log
- Use `subprocess.Popen` with `bufsize=1` and a thread reader (Blender's main thread can't block on `.read()`)
- Hook `bpy.app.handler.exit_pre` (5.1) to terminate orphan render processes if Blender quits mid-queue
- **Restore `Scene.render.filepath`** to its original value after each job (don't permanently mutate the working file's render path)

### Queue persistence: SQLite, not JSON

Renderset, Blender Queue, and similar tools use JSON + file lock. That breaks down at scale (~100+ jobs) and under crash conditions. We use SQLite at `bpy.app.cachedir/studio_queue.db`:

- Transactional per-job state updates (`pending` → `running` → `done` / `failed` / `interrupted`)
- Indexes on `(blend_path, scene, studio_uuid)` for fast lookups
- One dependency, no extra Python deps (sqlite3 is stdlib)
- Schema migrations via a `format_version` table

Schema sketch:
```sql
CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    blend_path TEXT NOT NULL,
    scene_name TEXT NOT NULL,
    studio_uuid TEXT NOT NULL,
    state TEXT NOT NULL,           -- pending / running / done / failed / interrupted
    started_at REAL,
    finished_at REAL,
    output_hash TEXT,
    error_msg TEXT,
    priority INTEGER DEFAULT 0,
    created_at REAL NOT NULL
);
CREATE INDEX idx_jobs_lookup ON jobs(blend_path, scene_name, studio_uuid);
CREATE INDEX idx_jobs_state ON jobs(state);
```

### Crash recovery / queue resume

- On Blender start (or addon enable), scan for `running` jobs without `finished_at`
- Mark them `interrupted` and prompt: "Resume incomplete queue? N jobs interrupted at <timestamp>"
- `bpy.app.handler.exit_pre` (5.1) cleanly marks running jobs as `interrupted` on graceful quit
- Never silently lose work — every state transition is a transaction

### Versioned preset format

Every JSON Preset includes `format_version: int` from day one. Migration logic (forward only) lives in `presets/migrations/v1_to_v2.py` etc. The pain of not having this doesn't bite until v2 — when it bites very hard. Renderset's 1.9→2.0 migration is the cautionary tale.

### Thumbnail invalidation

Thumbnails regenerate on:
1. Explicit Update Studio
2. `frame_change_post` if the Studio is currently applied (and prefs allow)
3. Manual "Refresh Thumbnail" right-click

We do **not** hook `depsgraph_update` (too noisy — every drag in the viewport would invalidate). Stale thumbnails after rapid edits are the cost; the dirty-state indicator covers the gap.

Cache lives on disk via `bpy.app.cachedir/thumbnails/<studio_uuid>.png`, not in the .blend (keeps file size sane at scale).

### Compatibility considerations
- **Minimum target: Blender 5.1.** Specified in `blender_manifest.toml` via `blender_version_min = "5.1.0"`. No 4.x backporting — keeps the codebase clean.
- **Compositor as node groups (5.0+)** — store compositor variants by reference to a `bpy.data.node_groups` entry assigned to `Scene.compositing_node_group`. Clean, no hacks.
- **File Output node split (5.0+)** — `directory` and `file_name` are separate inputs. Routing logic must handle both.
- **Geometry Nodes modifier API (5.1)** — use `modifier.properties.inputs.<id>.value` / `.attribute_name`, *not* the old `modifier["id"]` dictionary access. The old form is removed.
- **Annotations API (5.0+)** — `bpy.types.GreasePencil` was renamed to `bpy.types.Annotation`. Unlikely to affect us, but flag if we ever store grease pencil/annotation state.
- **Working color space + ACES views (5.0+)** — capture `Scene.display_settings.display_device`, `Scene.view_settings.view_transform`, and the working color space as part of the render facet.
- **EEVEE engine identifier** is now `'BLENDER_EEVEE_NEXT'` — the legacy `'BLENDER_EEVEE'` is gone. No migration needed since we're 5.1+ only.
- **Movie format outputs** (mp4 / mkv / avi) — Blender already does this via FFmpeg. Don't add a layer; just don't fight it in output-naming code.
- **Python 3.13** — use modern type hints freely (`X | None`, `list[T]`, `match` statements). Use `tomllib` from stdlib for parsing the manifest if we need to introspect it.
- **Cross-platform**: paths, shutdown commands, notifications — abstract behind a small `platform_utils` module. Use `bpy.app.cachedir` for thumbnail cache and queue DB (5.1).

### Testing strategy
- Headless Blender unit tests (`blender -b -P tests/test_studio_capture.py`) — Blender's bundled Python (3.13) can run pytest
- **Round-trip invariant** as a Phase 1 deliverable — capture → mutate → restore → equal
- **1000-Studio stress test** as a Phase 1 deliverable — measured each milestone
- Sample .blends for regression: multi-camera, multi-scene, animated, complex visibility, material variants, GN modifier inputs, compositor variants, linked libraries, drivers
- CI matrix: Blender 5.1 + 5.2-alpha × {Linux, macOS Intel, macOS Apple Silicon, Windows} — Apple Silicon is non-trivial (Renderset 2.0.1 shipped a fix specifically for M1/M2/M3 crashes)
- Snapshot tests for facet capture/restore
- Don't skip UI tests — UIList ordering bugs are the kind of thing that makes addons feel cheap

---

## 6. Risks & Open Questions

- **Property storage scale.** Renderset's docs claim "up to a thousand contexts in one .blend file" — that's the bar to beat. A heavy scene with 200 Studios × 50 custom props each = 10k stored values. Performance on UI redraw and on save? Mitigation: lazy-load facet data, cache thumbnails on disk via `bpy.app.cachedir` not in .blend, paginate the Lister. Made a Phase 1 deliverable (see §5) so we learn fast.
- **`hide_viewport` cannot be stored.** Blender exposes `hide_render` (camera icon) and collection visibility, but the *eye icon* `hide_viewport` on individual objects is a UI-only flag with no persistence hook — Renderset hits this limit too. We surface it honestly: when a user tries to store eye-icon visibility, show a tooltip explaining the limitation and suggesting collection-based visibility instead.
- **Override semantics: additive.** When a Studio captures only "camera + world", what happens to materials when you switch? Two valid models: *Additive* (only override what's stored, leave rest) or *Replacement* (everything not stored is "default"). **Pick additive — it's what users actually want.** Document it.
- **Save-on-apply / dirty handling.** Switching Studios mutates the scene. The dirty-state indicator (an MVP feature) is the answer — it makes the user the source of truth for "should this change be persisted?". Auto-save before apply is optional and prefs-controlled.
- **Naming collisions** with Renderset / Blender Queue users. Don't shadow their property names. Namespace everything: `bpy.types.Scene.studio_data` not `bpy.types.Scene.contexts`. Side benefit: a user can run our addon *alongside* Renderset during transition.
- **Native render operator routing risk.** Re-routing F12 / Render Image is convenient but risky — we override Blender behavior the user didn't ask for. **Default off**, surface the toggle prominently in prefs, add a "first time you press F12 with this enabled" confirmation.
- **Apple Silicon (M1/M2/M3) compatibility.** Renderset shipped a 2.0.1 bug specifically for M-series Mac crashes when adding contexts. Build CI on Apple Silicon from Phase 0.
- **Licensing.** GPL is mandatory for Blender addons. Don't bundle non-GPL deps in the addon. Use the Blender Extensions wheels system for any external Python packages.
- **Pricing & distribution.** Superhive ($) for the full version, free lite version on extensions.blender.org for funnel. Keep upgrade path clear.
- **Marketing assets.** Thumbnails are the addon's best marketing — record a 30-second screen capture of the Studio grid + one-click switching. That sells the addon better than 100 words of feature list.

---

## 7. Decision points (resolve before Phase 1)

1. **Name.** Pick one and lock it. Affects UI strings, namespace, branding.
2. **Pricing model.** One-time (like Renderset, B-Renderon) or sub? **Recommend one-time + paid major upgrades** — matches expectations in the Blender market. *Resolve in Phase 0 — affects how much to invest in onboarding and free-tier feature split.*
3. **Free vs paid split.** Free lite version on extensions.blender.org as funnel + paid Pro on Superhive? Or Superhive-only? Funnel approach is more work but builds community trust.
4. **Scope of MVP.** Material variants are firmly v1.0 (already cut from MVP — they're a 2-week feature alone).
5. **Solo or partnered.** Polygoniq has a team. B-Renderon is solo. Solo is fine but plan for 1–2 days/week of support work after launch.
6. **Default UX answers** for the open engineering decisions in §5: undo behavior, driver conflict policy, library override semantics, multi-scene model, render-engine-specific facet shape.

---

## 8. Inspiration list (worth studying their UX directly)

- **KeyShot** — Studios panel, Configurator, Image Styles. The original.
- **Renderset** — property storage flexibility, output naming, batch context editing, post-render action primitives
- **Blender Queue** — persistent JSON queue, path shortcodes
- **B-Renderon** — background renderer architecture, scheduler
- **K-Tools Render Preset Manager** — load preview with diff before applying
- **Blender's own Asset Browser** — the thumbnail grid pattern you should mimic for Studio browsing
- **Blender's library overrides UX** — the lock-icon inheritance pattern we mirror in §5

---

*This is a living doc. Update it as you make decisions and discover constraints.*
