'use client'

import { useEffect, useState } from 'react'
import { PHASES } from '@/lib/SceneEngine'

const PHASE_LABELS = {
  [PHASES.SINGULARITY]: { label: 'INITIALIZING', color: '#00DDFF', desc: 'Collapsing knowledge space...' },
  [PHASES.EXPLODING]:   { label: 'INDEXING',      color: '#00FF88', desc: 'Embedding knowledge graph...' },
  [PHASES.GALAXY]:      { label: 'READY',         color: '#00FF88', desc: 'Hybrid search active' },
  [PHASES.QUERYING]:    { label: 'SEARCHING',     color: '#FFAA00', desc: 'Firing retrieval beam...' },
  [PHASES.RETRIEVING]:  { label: 'RERANKING',     color: '#AA44FF', desc: 'Cross-encoder scoring...' },
  [PHASES.ANSWERING]:   { label: 'GROUNDED',      color: '#00FF88', desc: 'Answer crystallized ✓' },
}

function AnimatedCounter({ target, duration = 1400, suffix = '', prefix = '' }) {
  const [val, setVal] = useState(0)
  useEffect(() => {
    let start = null
    const from = 0
    function step(ts) {
      if (!start) start = ts
      const progress = Math.min((ts - start) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setVal(Math.floor(from + (target - from) * eased))
      if (progress < 1) requestAnimationFrame(step)
    }
    requestAnimationFrame(step)
  }, [target, duration])
  return <>{prefix}{val.toLocaleString()}{suffix}</>
}

function HudBlock({ children, style }) {
  return (
    <div style={{
      position: 'absolute',
      fontFamily: "'JetBrains Mono', monospace",
      fontSize: 11,
      color: '#4B5563',
      letterSpacing: '0.06em',
      zIndex: 20,
      pointerEvents: 'none',
      ...style,
    }}>
      {children}
    </div>
  )
}

function HudLine({ dot, dotColor = '#00FF88', label, value, pulse }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 7 }}>
      <span style={{
        width: 5, height: 5, borderRadius: '50%',
        background: dotColor, flexShrink: 0,
        animation: pulse ? 'feedPulse 2s ease-in-out infinite' : 'none',
      }} />
      <span style={{ color: '#374151' }}>{label}</span>
      <span style={{ color: '#F0F0F5', fontWeight: 500 }}>{value}</span>
    </div>
  )
}

function HudRule({ dir = 'left' }) {
  return (
    <div style={{
      width: 110, height: 1,
      background: `linear-gradient(to ${dir === 'left' ? 'right' : 'left'}, #00FF88, transparent)`,
      opacity: 0.35, marginBottom: 11,
      marginLeft: dir === 'right' ? 'auto' : 0,
    }} />
  )
}

export default function HudOverlay({ phase }) {
  const [qps, setQps] = useState('—')
  const [latency, setLatency] = useState('—')
  const [tick, setTick] = useState(0)

  const phaseInfo = PHASE_LABELS[phase] || PHASE_LABELS[PHASES.GALAXY]

  useEffect(() => {
    const iv = setInterval(() => {
      setQps((Math.random() * 3.2 + 0.8).toFixed(1))
      setLatency((Math.random() * 0.8 + 0.6).toFixed(2) + 's')
      setTick(t => t + 1)
    }, 2200)
    return () => clearInterval(iv)
  }, [])

  return (
    <>
      {/* TOP LEFT */}
      <HudBlock style={{ top: 88, left: 48 }}>
        <HudRule />
        <HudLine dot label="NODES" value={<AnimatedCounter target={2847} />} pulse />
        <HudLine dot dotColor="#00DDFF" label="EDGES" value={<AnimatedCounter target={8391} duration={1800} />} />
        <HudLine dot dotColor="#FFAA00" label="QUERIES/S" value={qps} pulse />
        <HudLine dot dotColor="#AA44FF" label="CLUSTERS" value="8" />
      </HudBlock>

      {/* TOP RIGHT */}
      <HudBlock style={{ top: 88, right: 48, textAlign: 'right' }}>
        <HudRule dir="right" />
        <HudLine dot label="RETRIEVAL" value="98.7%" />
        <HudLine dot dotColor="#FF3344" label="HALLUCINATIONS" value="0" />
        <HudLine dot dotColor="#00DDFF" label="LATENCY AVG" value={latency} pulse />
        <HudLine dot dotColor="#FFAA00" label="RERANKER" value="ACTIVE" />
      </HudBlock>

      {/* BOTTOM LEFT */}
      <HudBlock style={{ bottom: 52, left: 48 }}>
        <HudLine dot label="EMBED MODEL" value="all-MiniLM-L6-v2" />
        <HudLine dot dotColor="#00DDFF" label="VECTOR STORE" value="FAISS + BM25" />
        <HudLine dot dotColor="#FFAA00" label="RERANKER" value="ms-marco-MiniLM" />
        <HudLine dot dotColor="#AA44FF" label="HyDE" value="ENABLED" />
      </HudBlock>

      {/* PHASE STATUS — center bottom */}
      <div style={{
        position: 'absolute',
        bottom: 52, left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 20,
        pointerEvents: 'none',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5,
      }}>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          color: phaseInfo.color,
          letterSpacing: '0.22em',
          textTransform: 'uppercase',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: phaseInfo.color,
            animation: 'feedPulse 1s ease-in-out infinite',
            display: 'inline-block',
          }} />
          {phaseInfo.label}
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: phaseInfo.color,
            animation: 'feedPulse 1s ease-in-out infinite 0.3s',
            display: 'inline-block',
          }} />
        </div>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9, color: '#374151',
          letterSpacing: '0.1em',
        }}>
          {phaseInfo.desc}
        </div>
      </div>
    </>
  )
}
