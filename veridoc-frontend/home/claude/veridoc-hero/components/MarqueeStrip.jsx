'use client'

const ITEMS = [
  'SOURCE GROUNDED', 'ZERO HALLUCINATIONS', 'CITATION ON EVERY ANSWER',
  'HYBRID SEARCH', 'CROSS-ENCODER RERANKER', 'HyDE RETRIEVAL',
  'FAISS + BM25 FUSION', 'MEMORY AWARE', 'CPU SAFE',
  'PRIVATE BY DESIGN', 'OPEN SOURCE STACK', 'FREE TIER AVAILABLE',
]

export default function MarqueeStrip() {
  const doubled = [...ITEMS, ...ITEMS]
  return (
    <div style={{
      position: 'absolute',
      bottom: 0, left: 0, right: 0,
      height: 34,
      background: 'rgba(0,255,136,0.04)',
      borderTop: '1px solid rgba(0,255,136,0.08)',
      display: 'flex', alignItems: 'center',
      overflow: 'hidden',
      zIndex: 20,
      pointerEvents: 'none',
    }}>
      <div style={{
        display: 'flex',
        animation: 'marqueeScroll 38s linear infinite',
        whiteSpace: 'nowrap',
        willChange: 'transform',
      }}>
        {doubled.map((item, i) => (
          <span key={i} style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9,
            color: 'rgba(0,255,136,0.4)',
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            padding: '0 24px',
            flexShrink: 0,
          }}>
            {item}
            <span style={{ color: 'rgba(0,255,136,0.15)', margin: '0 8px' }}>●</span>
          </span>
        ))}
      </div>
    </div>
  )
}
