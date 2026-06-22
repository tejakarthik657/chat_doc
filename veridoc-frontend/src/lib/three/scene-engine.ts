import * as THREE from 'three'

// ─────────────────────────────────────────────────────────────────────────────
//  CONSTANTS
// ─────────────────────────────────────────────────────────────────────────────
const NODE_COUNT = 560
const EDGE_COUNT = 1100
const DUST_COUNT = 2200
const CLUSTER_COUNT = 8
const PULSE_COUNT = 6

export const PHASES = {
    SINGULARITY: 'singularity',   // Everything collapsed to center
    EXPLODING: 'exploding',     // Big bang expansion
    GALAXY: 'galaxy',        // Stable knowledge graph
    QUERYING: 'querying',      // Query beam fires
    RETRIEVING: 'retrieving',    // Nodes light up, reranking
    ANSWERING: 'answering',     // Answer crystallizes
} as const;

export type Phase = typeof PHASES[keyof typeof PHASES];

// ─────────────────────────────────────────────────────────────────────────────
//  COLORS
// ─────────────────────────────────────────────────────────────────────────────
const COLORS = {
    green: new THREE.Color(0x00FF88),
    greenDim: new THREE.Color(0x003322),
    amber: new THREE.Color(0xFFAA00),
    cyan: new THREE.Color(0x00DDFF),
    violet: new THREE.Color(0xAA44FF),
    red: new THREE.Color(0xFF3344),
    white: new THREE.Color(0xFFFFFF),
    bg: new THREE.Color(0x02020A),
}

// Cluster definitions — semantic topic regions
const CLUSTER_DEFS = [
    { label: 'TREATMENT', color: COLORS.green, center: [-20, 9, -4], r: 9 },
    { label: 'DIAGNOSIS', color: COLORS.cyan, center: [18, 11, 4], r: 8 },
    { label: 'DOSAGE', color: COLORS.amber, center: [1, -13, 5], r: 7 },
    { label: 'PROCEDURES', color: COLORS.violet, center: [-15, -9, -7], r: 7 },
    { label: 'LAB RESULTS', color: COLORS.cyan, center: [19, -6, -5], r: 8 },
    { label: 'PROGNOSIS', color: COLORS.green, center: [7, 17, -3], r: 7 },
    { label: 'GENOMICS', color: COLORS.violet, center: [-7, -2, 15], r: 6 },
    { label: 'GENERAL', color: COLORS.amber, center: [3, 2, -16], r: 6 },
]

// ─────────────────────────────────────────────────────────────────────────────
//  HELPERS
// ─────────────────────────────────────────────────────────────────────────────
function gauss(mean: number, std: number) {
    let u = 0, v = 0
    while (!u) u = Math.random()
    while (!v) v = Math.random()
    return mean + std * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v)
}

function rand(a: number, b: number) { return a + Math.random() * (b - a) }
function lerp(a: number, b: number, t: number) { return a + (b - a) * t }

// ─────────────────────────────────────────────────────────────────────────────
//  INTERFACES
// ─────────────────────────────────────────────────────────────────────────────

interface Node {
    id: number;
    cluster: number;
    target: THREE.Vector3;
    current: THREE.Vector3;
    color: THREE.Color;
    size: number;
    phase: number;
    speed: number;
    connections: number[];
    lit: number;
}

interface Edge {
    a: number;
    b: number;
    baseOpacity: number;
    lit: number;
}

interface Pulse {
    mesh: THREE.Mesh;
    halo: THREE.MeshBasicMaterial;
    color: THREE.Color;
    currentNode: number;
    targetNode: number;
    progress: number;
    speed: number;
    active: boolean;
    delay: number;
}

interface SpiralArm {
    mesh: THREE.Mesh;
    mat: THREE.MeshBasicMaterial;
}

// ─────────────────────────────────────────────────────────────────────────────
//  SCENE ENGINE CLASS
// ─────────────────────────────────────────────────────────────────────────────
export class SceneEngine {
    canvas: HTMLCanvasElement;
    onPhaseChange: (phase: Phase) => void;
    phase: Phase;
    phaseT: number;
    clock: THREE.Clock;
    mouse: THREE.Vector2;
    mouseLerp: THREE.Vector2;
    frameCount: number;
    destroyed: boolean;

    renderer!: THREE.WebGLRenderer;
    scene!: THREE.Scene;
    camera!: THREE.PerspectiveCamera;

    nodes!: Node[];
    posArr!: Float32Array;
    colArr!: Float32Array;
    sizeArr!: Float32Array;
    nodeGeom!: THREE.BufferGeometry;
    nodeMat!: THREE.ShaderMaterial;
    nodePoints!: THREE.Points;

    edges!: Edge[];
    edgePosArr!: Float32Array;
    edgeColArr!: Float32Array;
    edgeGeom!: THREE.BufferGeometry;
    edgeLines!: THREE.LineSegments;

    dustMat!: THREE.ShaderMaterial;
    dustPoints!: THREE.Points;

    pulses!: Pulse[];

    singularityRing!: THREE.Mesh;
    singularityMat!: THREE.ShaderMaterial;
    singularityCore!: THREE.Mesh;
    singularityCoreMat!: THREE.ShaderMaterial;
    spiralArms!: SpiralArm[];

    queryBeam!: THREE.Mesh;
    queryBeamMat!: THREE.ShaderMaterial;
    answerCrystal!: THREE.Mesh;
    answerCrystalMat!: THREE.ShaderMaterial;

    wormhole!: THREE.Mesh;
    wormholeMat!: THREE.ShaderMaterial;

    flashPlane!: THREE.Mesh;
    flashMat!: THREE.ShaderMaterial;
    flashScene!: THREE.Scene;
    flashCamera!: THREE.OrthographicCamera;

    // Event handlers
    private _onMouseMove?: (e: MouseEvent) => void;
    private _onResize?: () => void;
    private _onClick?: () => void;
    private _rafId?: number;

    constructor(canvas: HTMLCanvasElement, onPhaseChange?: (phase: Phase) => void) {
        this.canvas = canvas
        this.onPhaseChange = onPhaseChange || (() => { })
        this.phase = PHASES.SINGULARITY
        this.phaseT = 0
        this.clock = new THREE.Clock()
        this.mouse = new THREE.Vector2(0, 0)
        this.mouseLerp = new THREE.Vector2(0, 0)
        this.frameCount = 0
        this.destroyed = false

        this._initRenderer()
        this._initScene()
        this._initNodes()
        this._initEdges()
        this._initDust()
        this._initPulses()
        this._initSingularity()
        this._initQueryBeam()
        this._initWormhole()
        this._initPostFX()
        this._bindEvents()
        this._startPhaseSequence()
        this._animate()
    }

    // To shut down properly
    destroy() {
        this.destroyed = true;
        if (this._rafId) cancelAnimationFrame(this._rafId);

        // Remove listeners
        if (this._onMouseMove) window.removeEventListener('mousemove', this._onMouseMove);
        if (this._onResize) window.removeEventListener('resize', this._onResize);
        if (this._onClick) this.canvas.removeEventListener('click', this._onClick);

        // Dispose resources
        this.renderer.dispose();
        this.nodeGeom.dispose();
        this.nodeMat.dispose();
        // ... dispose other geometries/materials as needed
    }

    // ── Renderer ────────────────────────────────────────────────────────────────
    _initRenderer() {
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true,
            powerPreference: 'high-performance',
        })
        this.renderer.setSize(window.innerWidth, window.innerHeight)
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
        this.renderer.toneMapping = THREE.ACESFilmicToneMapping
        this.renderer.toneMappingExposure = 1.2

        this.scene = new THREE.Scene()
        this.scene.fog = new THREE.FogExp2(0x02020A, 0.008)

        this.camera = new THREE.PerspectiveCamera(65, window.innerWidth / window.innerHeight, 0.1, 500)
        this.camera.position.set(0, 0, 70)
    }

    _initScene() {
        // Just a placeholder for any general scene setup
    }

    // ── Node System ─────────────────────────────────────────────────────────────
    _initNodes() {
        this.nodes = []
        const posArr = new Float32Array(NODE_COUNT * 3)
        const colArr = new Float32Array(NODE_COUNT * 3)
        const sizeArr = new Float32Array(NODE_COUNT)
        const phaseArr = new Float32Array(NODE_COUNT)

        for (let i = 0; i < NODE_COUNT; i++) {
            const ci = i % CLUSTER_COUNT
            const cl = CLUSTER_DEFS[ci]
            const r = cl.r

            const tx = gauss(cl.center[0], r * 0.52)
            const ty = gauss(cl.center[1], r * 0.52)
            const tz = gauss(cl.center[2], r * 0.4)

            const node: Node = {
                id: i, cluster: ci,
                target: new THREE.Vector3(tx, ty, tz),
                current: new THREE.Vector3(0, 0, 0), // start at singularity
                color: cl.color.clone(),
                size: rand(0.07, 0.28),
                phase: rand(0, Math.PI * 2),
                speed: rand(0.08, 0.35),
                connections: [],
                lit: 0,
            }
            this.nodes.push(node)

            posArr[i * 3] = posArr[i * 3 + 1] = posArr[i * 3 + 2] = 0
            colArr[i * 3] = node.color.r * 0.05
            colArr[i * 3 + 1] = node.color.g * 0.05
            colArr[i * 3 + 2] = node.color.b * 0.05
            sizeArr[i] = 0
            phaseArr[i] = node.phase
        }

        this.posArr = posArr
        this.colArr = colArr
        this.sizeArr = sizeArr

        const geom = new THREE.BufferGeometry()
        geom.setAttribute('position', new THREE.BufferAttribute(posArr, 3))
        geom.setAttribute('aColor', new THREE.BufferAttribute(colArr, 3))
        geom.setAttribute('aSize', new THREE.BufferAttribute(sizeArr, 1))
        geom.setAttribute('aPhase', new THREE.BufferAttribute(phaseArr, 1))

        const mat = new THREE.ShaderMaterial({
            uniforms: { uTime: { value: 0 }, uExplosion: { value: 0 } },
            vertexShader: /* glsl */`
                attribute float aSize;
                attribute float aPhase;
                attribute vec3 aColor;
        varying vec3  vColor;
        varying float vAlpha;
        varying float vCore;
        uniform float uTime;
        uniform float uExplosion;

        void main() {
                    vColor = aColor;
          float breathe = 0.85 + 0.15 * sin(uTime * 1.2 + aPhase);
          float glow    = 0.7  + 0.3  * sin(uTime * 2.4 + aPhase * 1.7);
          vAlpha = glow * uExplosion;
          vCore  = breathe;

          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = aSize * breathe * (380.0 / -mv.z);
          gl_Position  = projectionMatrix * mv;
        }
      `,
            fragmentShader: /* glsl */`
        varying vec3  vColor;
        varying float vAlpha;
        varying float vCore;

        void main() {
          vec2  uv = gl_PointCoord - 0.5;
          float d  = length(uv);
          if (d > 0.5) discard;

          float rim  = 1.0 - smoothstep(0.3, 0.5, d);
          float core = 1.0 - smoothstep(0.0, 0.25, d);
          float halo = 1.0 - smoothstep(0.15, 0.5, d);

          vec3 col = vColor * rim + vColor * core * 4.0 + vec3(0.8,1.0,0.9) * core * 2.0;
          float a  = (rim * 0.7 + halo * 0.3) * vAlpha;

          gl_FragColor = vec4(col, a);
        }
      `,
            transparent: true, depthWrite: false,
            blending: THREE.AdditiveBlending, vertexColors: false,
        })

        this.nodeGeom = geom
        this.nodeMat = mat
        this.nodePoints = new THREE.Points(geom, mat)
        this.scene.add(this.nodePoints)
    }

    // ── Edge System ─────────────────────────────────────────────────────────────
    _initEdges() {
        this.edges = []
        const edgePosArr = new Float32Array(EDGE_COUNT * 6)
        const edgeColArr = new Float32Array(EDGE_COUNT * 6)
        let ei = 0

        for (let i = 0; i < NODE_COUNT && ei < EDGE_COUNT; i++) {
            for (let j = i + 1; j < NODE_COUNT && ei < EDGE_COUNT; j++) {
                const ni = this.nodes[i], nj = this.nodes[j]
                const d = ni.target.distanceTo(nj.target)
                const same = ni.cluster === nj.cluster
                if (d < (same ? 10 : 5) && Math.random() < (same ? 0.055 : 0.006)) {
                    this.edges.push({ a: i, b: j, baseOpacity: rand(0.04, 0.10), lit: 0 })
                    ni.connections.push(j)
                    nj.connections.push(i)
                    ei++
                }
            }
        }

        // fill remaining slots
        while (ei < EDGE_COUNT) {
            edgePosArr.fill(0, ei * 6, ei * 6 + 6)
            edgeColArr.fill(0, ei * 6, ei * 6 + 6)
            ei++
        }

        this.edgePosArr = edgePosArr
        this.edgeColArr = edgeColArr

        const geom = new THREE.BufferGeometry()
        geom.setAttribute('position', new THREE.BufferAttribute(edgePosArr, 3))
        geom.setAttribute('color', new THREE.BufferAttribute(edgeColArr, 3))

        const mat = new THREE.LineBasicMaterial({
            vertexColors: true, transparent: true,
            blending: THREE.AdditiveBlending, depthWrite: false,
        })

        this.edgeGeom = geom
        this.edgeLines = new THREE.LineSegments(geom, mat)
        this.scene.add(this.edgeLines)
    }

    // ── Cosmic Dust ─────────────────────────────────────────────────────────────
    _initDust() {
        const pos = new Float32Array(DUST_COUNT * 3)
        const col = new Float32Array(DUST_COUNT * 3)
        const sz = new Float32Array(DUST_COUNT)

        for (let i = 0; i < DUST_COUNT; i++) {
            const theta = Math.random() * Math.PI * 2
            const phi = Math.acos(2 * Math.random() - 1)
            const r = rand(55, 130)
            pos[i * 3] = r * Math.sin(phi) * Math.cos(theta)
            pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta)
            pos[i * 3 + 2] = r * Math.cos(phi)

            const hue = Math.random()
            col[i * 3] = hue < 0.4 ? 0.01 : 0.03
            col[i * 3 + 1] = hue < 0.4 ? 0.04 : 0.06
            col[i * 3 + 2] = hue < 0.4 ? 0.08 : 0.02
            sz[i] = rand(0.4, 2.2)
        }

        const geom = new THREE.BufferGeometry()
        geom.setAttribute('position', new THREE.BufferAttribute(pos, 3))
        geom.setAttribute('aColor', new THREE.BufferAttribute(col, 3))
        geom.setAttribute('aSize', new THREE.BufferAttribute(sz, 1))

        const mat = new THREE.ShaderMaterial({
            uniforms: { uTime: { value: 0 }, uOpacity: { value: 0 } },
            vertexShader: /* glsl */`
                attribute float aSize;
                attribute vec3 aColor;
        varying vec3 vColor;
        uniform float uTime;
        uniform float uOpacity;
        void main() {
                    vColor = aColor * uOpacity;
          vec4 mv = modelViewMatrix * vec4(position, 1.0);
          gl_PointSize = aSize * (220.0 / -mv.z);
          gl_Position  = projectionMatrix * mv;
        }
      `,
            fragmentShader: /* glsl */`
        varying vec3 vColor;
        void main() {
          float d = length(gl_PointCoord - 0.5);
          if (d > 0.5) discard;
          float a = 1.0 - smoothstep(0.2, 0.5, d);
          gl_FragColor = vec4(vColor * 4.0, a * 0.8);
        }
      `,
            transparent: true, depthWrite: false,
            blending: THREE.AdditiveBlending, vertexColors: false,
        })

        this.dustMat = mat
        this.dustPoints = new THREE.Points(geom, mat)
        this.scene.add(this.dustPoints)
    }

    // ── Query Pulses ─────────────────────────────────────────────────────────────
    _initPulses() {
        this.pulses = []
        const colors = [COLORS.green, COLORS.cyan, COLORS.amber, COLORS.violet, COLORS.green, COLORS.cyan]

        for (let p = 0; p < PULSE_COUNT; p++) {
            const col = colors[p]
            const geo = new THREE.SphereGeometry(0.35, 10, 10)
            const mat = new THREE.MeshBasicMaterial({
                color: col, transparent: true, opacity: 0,
                blending: THREE.AdditiveBlending, depthWrite: false,
            })
            const mesh = new THREE.Mesh(geo, mat)

            // Halo ring around each pulse
            const hGeo = new THREE.TorusGeometry(0.7, 0.06, 6, 24)
            const hMat = new THREE.MeshBasicMaterial({
                color: col, transparent: true, opacity: 0,
                blending: THREE.AdditiveBlending, depthWrite: false,
            })
            const halo = new THREE.Mesh(hGeo, hMat)
            mesh.add(halo)

            this.scene.add(mesh)
            this.pulses.push({
                mesh, halo: hMat, color: col,
                currentNode: Math.floor(Math.random() * NODE_COUNT),
                targetNode: 0, progress: 0,
                speed: rand(0.014, 0.026), active: false, delay: p * 600,
            })
        }
    }

    // ── Singularity ──────────────────────────────────────────────────────────────
    _initSingularity() {
        // A glowing accretion disk at origin
        const geo = new THREE.TorusGeometry(3, 0.3, 16, 120)
        const mat = new THREE.ShaderMaterial({
            uniforms: { uTime: { value: 0 }, uIntensity: { value: 1 } },
            vertexShader: /* glsl */`
        varying vec2 vUv;
        void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
      `,
            fragmentShader: /* glsl */`
        uniform float uTime;
        uniform float uIntensity;
        varying vec2 vUv;
        void main() {
          float pulse = 0.6 + 0.4 * sin(uTime * 4.0 + vUv.x * 20.0);
          vec3 col = mix(vec3(0.0,1.0,0.53), vec3(0.0,0.87,1.0), vUv.x);
          float a  = pulse * uIntensity * 0.9;
          gl_FragColor = vec4(col * 2.5, a);
        }
      `,
            transparent: true, depthWrite: false,
            blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
        })
        this.singularityRing = new THREE.Mesh(geo, mat)
        this.singularityMat = mat
        this.scene.add(this.singularityRing)

        // Core sphere — pure white center
        const cGeo = new THREE.SphereGeometry(1.2, 32, 32)
        const cMat = new THREE.ShaderMaterial({
            uniforms: { uTime: { value: 0 }, uIntensity: { value: 1 } },
            vertexShader: /* glsl */`
        void main() { gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
      `,
            fragmentShader: /* glsl */`
        uniform float uTime;
        uniform float uIntensity;
        void main() {
          float p = 0.7 + 0.3 * sin(uTime * 6.0);
          gl_FragColor = vec4(vec3(0.6,1.0,0.8) * 3.0 * p, uIntensity * 0.95);
        }
      `,
            transparent: true, depthWrite: false,
            blending: THREE.AdditiveBlending,
        })
        this.singularityCore = new THREE.Mesh(cGeo, cMat)
        this.singularityCoreMat = cMat
        this.scene.add(this.singularityCore)

        // Spiral arms — 3 TorusKnots for the swirling effect
        this.spiralArms = []
        const armColors = [0x00FF88, 0x00DDFF, 0xFFAA00]
        for (let a = 0; a < 3; a++) {
            const aGeo = new THREE.TorusKnotGeometry(2.5 + a * 0.4, 0.04, 160, 8, 2, 3 + a)
            const aMat = new THREE.MeshBasicMaterial({
                color: armColors[a], transparent: true, opacity: 0.6,
                blending: THREE.AdditiveBlending, depthWrite: false,
            })
            const arm = new THREE.Mesh(aGeo, aMat)
            this.spiralArms.push({ mesh: arm, mat: aMat })
            this.scene.add(arm)
        }
    }

    // ── Query Beam ───────────────────────────────────────────────────────────────
    _initQueryBeam() {
        // A laser-like cylinder that fires through the graph
        const geo = new THREE.CylinderGeometry(0.04, 0.04, 100, 8, 1, true)
        const mat = new THREE.ShaderMaterial({
            uniforms: { uTime: { value: 0 }, uActive: { value: 0 } },
            vertexShader: /* glsl */`
        varying vec2 vUv;
        void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
      `,
            fragmentShader: /* glsl */`
        uniform float uTime;
        uniform float uActive;
        varying vec2 vUv;
        void main() {
          float edge  = 1.0 - abs(vUv.x - 0.5) * 2.0;
          float travel = fract(vUv.y * 3.0 - uTime * 4.0);
          float beam  = smoothstep(0.0, 0.2, travel) * smoothstep(1.0, 0.6, travel);
          vec3  col   = mix(vec3(0.0,1.0,0.53), vec3(0.0,0.87,1.0), vUv.y);
          float a     = edge * beam * uActive * 0.85;
          gl_FragColor = vec4(col * 3.0, a);
        }
      `,
            transparent: true, depthWrite: false,
            blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
        })
        this.queryBeam = new THREE.Mesh(geo, mat)
        this.queryBeamMat = mat
        this.queryBeam.rotation.z = Math.PI / 2
        this.queryBeam.visible = false
        this.scene.add(this.queryBeam)

        // Answer crystallization — a dodecahedron that forms when answer is found
        const aGeo = new THREE.DodecahedronGeometry(2, 0)
        const aMat = new THREE.ShaderMaterial({
            uniforms: { uTime: { value: 0 }, uScale: { value: 0 } },
            vertexShader: /* glsl */`
        uniform float uScale;
        uniform float uTime;
        varying vec3 vNormal;
        void main() {
          vNormal = normalize(normalMatrix * normal);
          vec3 pos = position * uScale;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
        }
      `,
            fragmentShader: /* glsl */`
        uniform float uTime;
        uniform float uScale;
        varying vec3 vNormal;
        void main() {
          float fresnel = pow(1.0 - abs(dot(vNormal, vec3(0.0,0.0,1.0))), 2.5);
          float pulse   = 0.7 + 0.3 * sin(uTime * 3.0);
          vec3  col     = mix(vec3(0.0,1.0,0.53), vec3(1.0,0.67,0.0), fresnel);
          float a       = fresnel * pulse * uScale * 0.9;
          gl_FragColor  = vec4(col * 2.5, a);
        }
      `,
            transparent: true, depthWrite: false,
            blending: THREE.AdditiveBlending, side: THREE.DoubleSide, wireframe: true,
        })
        this.answerCrystal = new THREE.Mesh(aGeo, aMat)
        this.answerCrystalMat = aMat
        this.answerCrystal.visible = false
        this.scene.add(this.answerCrystal)
    }

    // ── Wormhole tunnel ──────────────────────────────────────────────────────────
    _initWormhole() {
        // An open-ended tube that the camera appears to fly through
        const curve = new THREE.CatmullRomCurve3([
            new THREE.Vector3(0, 0, 80),
            new THREE.Vector3(0, 0, 40),
            new THREE.Vector3(0, 0, 0),
            new THREE.Vector3(0, 0, -20),
        ])
        const geo = new THREE.TubeGeometry(curve, 80, 3.5, 12, false)
        const mat = new THREE.ShaderMaterial({
            uniforms: { uTime: { value: 0 }, uProgress: { value: 0 } },
            vertexShader: /* glsl */`
        varying vec2 vUv;
        void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
      `,
            fragmentShader: /* glsl */`
        uniform float uTime;
        uniform float uProgress;
        varying vec2 vUv;
        void main() {
          float ring   = fract(vUv.y * 18.0 - uTime * 3.5);
          float stripe = smoothstep(0.0, 0.15, ring) * smoothstep(0.4, 0.25, ring);
          float edge   = pow(abs(sin(vUv.x * 3.14159)), 0.5);
          vec3  col    = mix(vec3(0.0,0.4,0.2), vec3(0.0,0.6,1.0), vUv.y);
          float a      = stripe * edge * uProgress * 0.45;
          gl_FragColor = vec4(col * 2.0, a);
        }
      `,
            transparent: true, depthWrite: false,
            blending: THREE.AdditiveBlending, side: THREE.BackSide,
        })
        this.wormhole = new THREE.Mesh(geo, mat)
        this.wormholeMat = mat
        this.wormhole.visible = false
        this.scene.add(this.wormhole)
    }

    // ── Post FX (lens flares via custom shader plane) ────────────────────────────
    _initPostFX() {
        // A full-screen flash plane for the big bang moment
        const geo = new THREE.PlaneGeometry(2, 2)
        const mat = new THREE.ShaderMaterial({
            uniforms: { uFlash: { value: 0 } },
            vertexShader: /* glsl */`void main() { gl_Position = vec4(position, 1.0); }`,
            fragmentShader: /* glsl */`
        uniform float uFlash;
        void main() {
          vec3 col = mix(vec3(0.0,1.0,0.53), vec3(1.0), 0.4) * uFlash;
          gl_FragColor = vec4(col, uFlash * 0.95);
        }
      `,
            transparent: true, depthWrite: false, depthTest: false,
            blending: THREE.AdditiveBlending,
        })
        this.flashPlane = new THREE.Mesh(geo, mat)
        this.flashMat = mat
        this.flashPlane.renderOrder = 999
        // Use a separate orthographic scene for the flash
        this.flashScene = new THREE.Scene()
        this.flashCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1)
        this.flashScene.add(this.flashPlane)
    }

    // ── Phase Sequencer ──────────────────────────────────────────────────────────
    _startPhaseSequence() {
        // SINGULARITY (2.5s) → EXPLODING (1.2s) → GALAXY (forever)
        setTimeout(() => this._setPhase(PHASES.EXPLODING), 2500)
        setTimeout(() => this._setPhase(PHASES.GALAXY), 3700)
        // Start querying cycle
        setTimeout(() => this._queryCycle(), 6000)
    }

    _queryCycle() {
        if (this.destroyed) return
        this._setPhase(PHASES.QUERYING)
        setTimeout(() => { if (!this.destroyed) this._setPhase(PHASES.RETRIEVING) }, 1400)
        setTimeout(() => { if (!this.destroyed) this._setPhase(PHASES.ANSWERING) }, 3000)
        setTimeout(() => { if (!this.destroyed) this._setPhase(PHASES.GALAXY) }, 5200)
        setTimeout(() => { if (!this.destroyed) this._queryCycle() }, 8000)
    }

    _setPhase(phase: Phase) {
        this.phase = phase
        this.phaseT = 0
        this.onPhaseChange(phase)

        if (phase === PHASES.EXPLODING) {
            this.wormhole.visible = true
            this.flashMat.uniforms.uFlash.value = 1.0
        }
        if (phase === PHASES.GALAXY) {
            this.wormhole.visible = false
            // Activate pulses
            this.pulses.forEach((p, i) => {
                setTimeout(() => {
                    p.active = true
                    p.currentNode = Math.floor(Math.random() * NODE_COUNT)
                    p.targetNode = this._nextNode(p)
                    if (p.mesh.material && !Array.isArray(p.mesh.material)) {
                        (p.mesh.material as any).opacity = 0.95;
                    }
                }, i * 400)
            })
        }
        if (phase === PHASES.QUERYING) {
            this.queryBeam.visible = true
            this.queryBeamMat.uniforms.uActive.value = 1
            this.answerCrystal.visible = false
        }
        if (phase === PHASES.ANSWERING) {
            this.queryBeam.visible = false
            this.answerCrystal.visible = true
            this.answerCrystalMat.uniforms.uScale.value = 0
        }
        if (phase === PHASES.GALAXY && this.phase === PHASES.ANSWERING) {
            this.answerCrystal.visible = false
        }
    }

    _nextNode(pulse: Pulse) {
        const curr = this.nodes[pulse.currentNode]
        if (!curr.connections.length) return Math.floor(Math.random() * NODE_COUNT)
        return curr.connections[Math.floor(Math.random() * curr.connections.length)]
    }

    // ── Event Binding ─────────────────────────────────────────────────────────────
    _bindEvents() {
        this._onMouseMove = (e: MouseEvent) => {
            this.mouse.x = (e.clientX / window.innerWidth - 0.5) * 2
            this.mouse.y = -(e.clientY / window.innerHeight - 0.5) * 2
        }
        this._onResize = () => {
            this.camera.aspect = window.innerWidth / window.innerHeight
            this.camera.updateProjectionMatrix()
            this.renderer.setSize(window.innerWidth, window.innerHeight)
        }
        this._onClick = () => {
            this.pulses.forEach((p) => {
                const orig = p.speed
                p.speed = 0.07
                setTimeout(() => { p.speed = orig }, 1400)
            })
            this._setPhase(PHASES.QUERYING)
            setTimeout(() => { if (!this.destroyed) this._setPhase(PHASES.RETRIEVING) }, 900)
            setTimeout(() => { if (!this.destroyed) this._setPhase(PHASES.ANSWERING) }, 2400)
            setTimeout(() => { if (!this.destroyed) this._setPhase(PHASES.GALAXY) }, 4400)
        }
        window.addEventListener('mousemove', this._onMouseMove)
        window.addEventListener('resize', this._onResize)
        this.canvas.addEventListener('click', this._onClick)
    }

    // ── Main Animation Loop ───────────────────────────────────────────────────────
    _animate() {
        if (this.destroyed) return
        this._rafId = requestAnimationFrame(() => this._animate())

        const dt = this.clock.getDelta()
        const t = this.clock.elapsedTime
        this.phaseT += dt
        this.frameCount++

        this._updateCamera(t, dt)
        this._updateSingularity(t)
        this._updateNodes(t, dt)
        this._updateEdges()
        this._updateDust(t)
        this._updatePulses(t, dt)
        this._updateQueryBeam(t, dt)
        this._updateWormhole(t, dt)
        this._updateFlash(dt)

        this.renderer.render(this.scene, this.camera)
        this.renderer.render(this.flashScene, this.flashCamera)
    }

    _updateCamera(t: number, dt: number) {
        this.mouseLerp.x += (this.mouse.x - this.mouseLerp.x) * 0.035
        this.mouseLerp.y += (this.mouse.y - this.mouseLerp.y) * 0.035

        let targetZ = 70
        if (this.phase === PHASES.SINGULARITY) targetZ = 62
        if (this.phase === PHASES.EXPLODING) targetZ = 85
        if (this.phase === PHASES.GALAXY) targetZ = 68
        if (this.phase === PHASES.QUERYING) targetZ = 58
        if (this.phase === PHASES.ANSWERING) targetZ = 52

        this.camera.position.x += (this.mouseLerp.x * 8 - this.camera.position.x) * 0.04
        this.camera.position.y += (this.mouseLerp.y * 5 - this.camera.position.y) * 0.04
        this.camera.position.z += (targetZ - this.camera.position.z) * 0.03
        this.camera.lookAt(0, 0, 0)
    }

    _updateSingularity(t: number) {
        this.singularityMat.uniforms.uTime.value = t
        this.singularityCoreMat.uniforms.uTime.value = t

        const isSingularity = this.phase === PHASES.SINGULARITY
        // const isExploding   = this.phase === PHASES.EXPLODING

        // Rings spin and scale
        this.singularityRing.rotation.x = t * 0.7
        this.singularityRing.rotation.z = t * 0.4
        const rs = isSingularity ? 1 + Math.sin(t * 3) * 0.15 : Math.max(0, 1 - this.phaseT * 3)
        this.singularityRing.scale.setScalar(rs)
        this.singularityCore.scale.setScalar(rs * (1 + Math.sin(t * 6) * 0.1))
        this.singularityMat.uniforms.uIntensity.value = rs
        this.singularityCoreMat.uniforms.uIntensity.value = rs

        // Spiral arms
        this.spiralArms.forEach(({ mesh, mat }, i) => {
            mesh.rotation.y = t * (0.5 + i * 0.15)
            mesh.rotation.x = t * (0.2 + i * 0.08)
            mesh.scale.setScalar(rs)
            mat.opacity = rs * (0.4 + i * 0.1)
        })
    }

    _updateNodes(t: number, dt: number) {
        const isSingularity = this.phase === PHASES.SINGULARITY
        const isExploding = this.phase === PHASES.EXPLODING
        const isGalaxy = this.phase === PHASES.GALAXY || this.phase === PHASES.QUERYING
            || this.phase === PHASES.RETRIEVING || this.phase === PHASES.ANSWERING

        const explosionPct = isExploding ? Math.min(this.phaseT / 1.2, 1) : (isGalaxy ? 1 : 0)
        this.nodeMat.uniforms.uExplosion.value = isGalaxy ? 1 : explosionPct

        this.nodes.forEach((node, i) => {
            // Interpolate from singularity to galaxy position
            const tgt = node.target
            let cx, cy, cz

            if (isSingularity) {
                cx = 0; cy = 0; cz = 0
            } else if (isExploding) {
                const eased = explosionPct < 0.5
                    ? 4 * explosionPct * explosionPct * explosionPct
                    : 1 - Math.pow(-2 * explosionPct + 2, 3) / 2
                cx = lerp(0, tgt.x, eased)
                cy = lerp(0, tgt.y, eased)
                cz = lerp(0, tgt.z, eased)
            } else {
                // Gentle float in galaxy
                const fx = Math.sin(t * node.speed + node.phase) * 0.18
                const fy = Math.cos(t * node.speed * 0.8 + node.phase) * 0.18
                cx = tgt.x + fx
                cy = tgt.y + fy
                cz = tgt.z
            }

            node.current.set(cx, cy, cz)
            this.posArr[i * 3] = cx
            this.posArr[i * 3 + 1] = cy
            this.posArr[i * 3 + 2] = cz

            // Size
            const targetSize = isSingularity ? 0 : node.size * 6.5
            this.sizeArr[i] += (targetSize - this.sizeArr[i]) * 0.06

            // Decay node lit state
            if (node.lit > 0) node.lit = Math.max(0, node.lit - dt * 1.5)

            // Color
            const dimF = 0.12
            const litF = node.lit
            this.colArr[i * 3] = node.color.r * (dimF + litF * 0.88)
            this.colArr[i * 3 + 1] = node.color.g * (dimF + litF * 0.88)
            this.colArr[i * 3 + 2] = node.color.b * (dimF + litF * 0.88)
        })

        this.nodeMat.uniforms.uTime.value = t
        this.nodeGeom.attributes.position.needsUpdate = true
        this.nodeGeom.attributes.aColor.needsUpdate = true
        this.nodeGeom.attributes.aSize.needsUpdate = true
    }

    _updateEdges() {
        const isActive = this.phase !== PHASES.SINGULARITY && this.phase !== PHASES.EXPLODING

        this.edges.forEach((e, i) => {
            if (i >= EDGE_COUNT) return
            const na = this.nodes[e.a]
            const nb = this.nodes[e.b]

            // Sync edge positions with node positions
            this.edgePosArr[i * 6] = na.current.x
            this.edgePosArr[i * 6 + 1] = na.current.y
            this.edgePosArr[i * 6 + 2] = na.current.z
            this.edgePosArr[i * 6 + 3] = nb.current.x
            this.edgePosArr[i * 6 + 4] = nb.current.y
            this.edgePosArr[i * 6 + 5] = nb.current.z

            const litV = isActive ? Math.max(na.lit, nb.lit) : 0
            const op = isActive ? lerp(e.baseOpacity, 0.65, litV) : 0

            this.edgeColArr[i * 6] = na.color.r * op
            this.edgeColArr[i * 6 + 1] = na.color.g * op
            this.edgeColArr[i * 6 + 2] = na.color.b * op
            this.edgeColArr[i * 6 + 3] = na.color.r * op
            this.edgeColArr[i * 6 + 4] = na.color.g * op
            this.edgeColArr[i * 6 + 5] = na.color.b * op
        })

        this.edgeGeom.attributes.position.needsUpdate = true
        this.edgeGeom.attributes.color.needsUpdate = true
    }

    _updateDust(t: number) {
        const isVisible = this.phase !== PHASES.SINGULARITY
        const targetOp = isVisible ? 1 : 0
        const cur = this.dustMat.uniforms.uOpacity.value
        this.dustMat.uniforms.uOpacity.value = cur + (targetOp - cur) * 0.02
        this.dustPoints.rotation.y = t * 0.006
        this.dustPoints.rotation.x = t * 0.003
    }

    _updatePulses(t: number, dt: number) {
        this.pulses.forEach((p) => {
            if (!p.active) return

            const start = this.nodes[p.currentNode].current
            const end = this.nodes[p.targetNode].current

            p.progress += p.speed
            if (p.progress >= 1) {
                // Arrived at target node
                p.progress = 0
                p.currentNode = p.targetNode
                p.targetNode = this._nextNode(p)

                // "Hit effect" -> light up the node
                this.nodes[p.currentNode].lit = 1.0
            }

            const pos = new THREE.Vector3().lerpVectors(start, end, p.progress)
            p.mesh.position.copy(pos)

            // Halo pulse
            const s = 1 + Math.sin(t * 10 + p.delay) * 0.2
            p.mesh.scale.setScalar(s)
        })
    }

    _updateQueryBeam(t: number, dt: number) {
        if (!this.queryBeam.visible) return
        this.queryBeamMat.uniforms.uTime.value = t

        const isQuerying = this.phase === PHASES.QUERYING
        const isRetrieving = this.phase === PHASES.RETRIEVING

        // Sweep the beam across the graph
        this.queryBeam.rotation.z = Math.PI / 2 + Math.sin(t * 2.2) * 0.4
        this.queryBeam.rotation.y = t * 0.6

        const targetA = (isQuerying || isRetrieving) ? 1 : 0
        const curA = this.queryBeamMat.uniforms.uActive.value
        this.queryBeamMat.uniforms.uActive.value = curA + (targetA - curA) * 0.08

        // Light up all nodes when retrieving
        if (isRetrieving) {
            const hitCount = Math.floor(rand(2, 6))
            for (let h = 0; h < hitCount; h++) {
                const ni = Math.floor(Math.random() * NODE_COUNT)
                this.nodes[ni].lit = Math.min(1, this.nodes[ni].lit + 0.9)
            }
        }

        // Answer crystal
        if (this.phase === PHASES.ANSWERING) {
            const sc = this.answerCrystalMat.uniforms.uScale.value
            this.answerCrystalMat.uniforms.uScale.value = sc + (1 - sc) * 0.06
            this.answerCrystalMat.uniforms.uTime.value = t
            this.answerCrystal.rotation.x = t * 0.4
            this.answerCrystal.rotation.y = t * 0.6
            this.answerCrystal.position.set(
                Math.sin(t * 0.5) * 3,
                Math.cos(t * 0.4) * 2, 5
            )
        }
    }

    _updateWormhole(t: number, dt: number) {
        if (!this.wormhole.visible) return
        this.wormholeMat.uniforms.uTime.value = t

        const targetP = this.phase === PHASES.EXPLODING ? 1 : 0
        const cur = this.wormholeMat.uniforms.uProgress.value
        this.wormholeMat.uniforms.uProgress.value = cur + (targetP - cur) * 0.04
        if (this.wormholeMat.uniforms.uProgress.value < 0.01) this.wormhole.visible = false
    }

    _updateFlash(dt: number) {
        const cur = this.flashMat.uniforms.uFlash.value
        if (cur > 0.001) {
            this.flashMat.uniforms.uFlash.value = cur * 0.88
            this.renderer.render(this.flashScene, this.flashCamera)
        }
    }
}
