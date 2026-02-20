# Veridoc — Three.js Hero Section (Next.js 14)

A mind-blowing Three.js hero section featuring a **RAG Knowledge Galaxy** —
a living visualization of document chunks as nodes in a semantic embedding space,
with singularity collapse, big bang expansion, query beams, and answer crystallization.

## What You're Getting

### The 3D Scene (6 layers)
1. **Knowledge Graph** — 560 nodes across 8 semantic clusters (Treatment, Diagnosis, Dosage, etc.)
   connected by 1,100+ embedding similarity edges. Nodes float with independent sine-wave oscillation.

2. **Singularity → Galaxy Phase** — On load, all nodes collapse to a single point (the accretion disk).
   After 2.5s, a big bang explodes them outward to their cluster positions with a full-screen flash.

3. **6 Query Pulses** — Glowing spheres with halo rings traverse the graph, lighting up nodes and edges
   as they search. Green = semantic (FAISS), Amber = keyword (BM25).

4. **Query Beam System** — A laser cylinder sweeps the graph during retrieval phases.
   On ANSWERING phase, a dodecahedron wireframe crystallizes — the "grounded answer."

5. **Wormhole Tunnel** — A tube geometry with animated ring shader fires during the explosion moment.

6. **Cosmic Dust** — 2,200 background particles at varying depths with additive blending.

### Phase Sequence (automatic + click-triggered)
```
SINGULARITY → EXPLODING → GALAXY → QUERYING → RETRIEVING → ANSWERING → GALAXY
   2.5s           1.2s      ∞         1.4s         1.6s         2.2s     ↺
```

### UI Layers
- **Custom cursor** — dot + ring with spring-follow, hover states change color
- **HUD Overlays** — 4 corners with animated counters, live system stats, phase indicator
- **Query Feed** — bottom-right panel with typewriter Q&A simulation, citation chips
- **Marquee Strip** — scrolling status bar at the bottom
- **Grain overlay** — subtle noise texture on body for depth
- **Scanline texture** — green CRT line pattern over the 3D scene

## Quick Start

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## File Structure

```
veridoc-hero/
├── app/
│   ├── layout.jsx          # Global styles, fonts, grain overlay
│   └── page.jsx            # Root page
├── components/
│   ├── HeroSection.jsx     # Main assembly — nav, headline, CTAs
│   ├── HeroCanvas.jsx      # Mounts Three.js engine (client-only)
│   ├── HudOverlay.jsx      # HUD panels + phase indicator + counters
│   ├── QueryFeed.jsx       # Live Q&A simulation with typewriter
│   ├── MarqueeStrip.jsx    # Bottom scrolling status bar
│   └── CustomCursor.jsx    # Spring-following cursor dot + ring
├── lib/
│   └── SceneEngine.js      # Entire Three.js scene (800+ lines)
├── package.json
├── next.config.js
└── jsconfig.json
```

## Interactions

| Action | Effect |
|--------|--------|
| Move mouse | Camera parallax — graph tilts toward cursor |
| Click anywhere | Bursts all pulses to 3× speed + fires query beam → answering sequence |
| Page load | Singularity → Big Bang explosion sequence |
| Auto every 8s | Full query cycle fires automatically |

## Customization

### Colors (`lib/SceneEngine.js` top of file)
```js
const COLORS = {
  green:  new THREE.Color(0x00FF88),  // Primary accent
  amber:  new THREE.Color(0xFFAA00),  // Citations, BM25
  cyan:   new THREE.Color(0x00DDFF),  // Secondary
  violet: new THREE.Color(0xAA44FF),  // Clusters
}
```

### Clusters (`CLUSTER_DEFS` array)
Change the `label`, `color`, `center` and `r` (radius) per topic cluster.

### Phase Timing (`_startPhaseSequence`)
Adjust the `setTimeout` delays to change how long each phase lasts.

### Node/Edge density
- `NODE_COUNT` — number of chunk nodes (default: 560)
- `EDGE_COUNT`  — max edges (default: 1100)
- `DUST_COUNT`  — background particles (default: 2200)

## Performance Notes

- Uses `THREE.Points` with custom shaders (not instanced mesh) — very GPU efficient
- Edges sync to node positions every frame but only flush color updates every 4 frames
- `Math.min(window.devicePixelRatio, 2)` caps pixel ratio for mobile performance
- Dynamic import of `SceneEngine.js` ensures WebGL never runs server-side
