'use client'

import { useEffect, useRef, useState } from 'react'

const FEED_DATA = [
  {
    q: 'What is the recommended treatment protocol?',
    a: 'ACE inhibitors are first-line at 5mg daily, titrated up monthly.',
    cites: ['p.7', 'p.12'],
    method: 'HYBRID',
    retriever: 'FAISS + BM25',
  },
  {
    q: 'Summarize key findings of section 3.',
    a: 'Three independent risk factors identified: age > 65, BMI > 30, prior MI.',
    cites: ['p.3', 'p.4', 'p.5'],
    method: 'HyDE',
    retriever: 'SEMANTIC',
  },
  {
    q: 'Maximum daily dosage?',
    a: 'Do not exceed 10mg/day. Renal impairment requires dose reduction.',
    cites: ['p.9'],
    method: 'BM25',
    retriever: 'KEYWORD',
  },
  {
    q: 'Are there contraindications for renal patients?',
    a: 'Contraindicated: GFR < 30 mL/min. Monitor creatinine quarterly.',
    cites: ['p.14', 'p.15'],
    method: 'HYBRID',
    retriever: 'RERANKED',
  },
  {
    q: 'What does section 7 say about biomarkers?',
    a: "I don't see this information in the uploaded documents.",
    cites: [],
    method: 'GUARDRAIL',
    retriever: 'REFUSED',
    noMatch: true,
  },
]

function TypeWriter({ text, speed = 18, onDone }) {
  const [displayed, setDisplayed] = useState('')
  const idx = useRef(0)
  useEffect(() => {
    idx.current = 0
    setDisplayed('')
    const iv = setInterval(() => {
      idx.current++
      setDisplayed(text.slice(0, idx.current))
      if (idx.current >= text.length) {
        clearInterval(iv)
        onDone?.()
      }
    }, speed)
    return () => clearInterval(iv)
  }, [text, speed])
  return <>{displayed}</>
}

function FeedItem({ item, visible }) {
  const [showAnswer, setShowAnswer] = useState(false)

  useEffect(() => {
    if (visible) {
      setShowAnswer(false)
      const t = setTimeout(() => setShowAnswer(true), 800)
      return () => clearTimeout(t)
    }
  }, [visible, item])

  const methodColor = item.noMatch
    ? '#FF3344'
    : item.method === 'BM25' ? '#FFAA00'
    : item.method === 'HyDE' ? '#AA44FF'
    : '#00FF88'

  return (
    <div
      style={{
        borderLeft: `2px solid ${methodColor}`,
        background: 'rgba(8,8,20,0.88)',
        border: `1px solid rgba(255,255,255,0.06)`,
        borderLeftWidth: 2,
        borderLeftColor: methodColor,
        padding: '12px 14px',
        backdropFilter: 'blur(12px)',
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : 'translateY(10px)',
        transition: 'opacity 0.5s ease, transform 0.5s ease',
      }}
    >
      {/* Question */}
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
        color: '#aaa',
        marginBottom: 6,
        lineHeight: 1.5,
      }}>
        <span style={{ color: '#555', marginRight: 6 }}>{'>'}</span>
        {visible && <TypeWriter text={`"${item.q}"`} speed={14} />}
      </div>

      {/* Answer */}
      {showAnswer && (
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          color: item.noMatch ? '#FF3344' : '#ccc',
          lineHeight: 1.7,
          marginBottom: 6,
        }}>
          <TypeWriter text={item.a} speed={10} />
        </div>
      )}

      {/* Citations */}
      {showAnswer && item.cites.length > 0 && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 6 }}>
          {item.cites.map((c) => (
            <span key={c} style={{
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 9,
              color: '#FFAA00',
              background: 'rgba(255,170,0,0.08)',
              border: '1px solid rgba(255,170,0,0.25)',
              padding: '2px 7px',
              letterSpacing: '0.06em',
            }}>
              [{c}]
            </span>
          ))}
        </div>
      )}

      {/* Status */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9,
        color: methodColor,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
      }}>
        <span style={{
          width: 5, height: 5, borderRadius: '50%',
          background: methodColor,
          display: 'inline-block',
          animation: 'feedPulse 1.5s ease-in-out infinite',
        }} />
        {item.retriever} · {item.method}
      </div>
    </div>
  )
}

export default function QueryFeed() {
  const [activeIndex, setActiveIndex] = useState(0)
  const [history, setHistory] = useState([FEED_DATA[0]])

  useEffect(() => {
    let i = 1
    const iv = setInterval(() => {
      const next = FEED_DATA[i % FEED_DATA.length]
      setHistory((h) => [...h.slice(-1), next])
      setActiveIndex(i)
      i++
    }, 4200)
    return () => clearInterval(iv)
  }, [])

  return (
    <div style={{
      position: 'absolute',
      bottom: 52,
      right: 48,
      width: 340,
      zIndex: 20,
      pointerEvents: 'none',
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9,
        color: '#444',
        letterSpacing: '0.18em',
        textTransform: 'uppercase',
        marginBottom: 10,
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <span style={{
          width: 4, height: 4, borderRadius: '50%',
          background: '#00FF88',
          animation: 'feedPulse 1.2s ease-in-out infinite',
          display: 'inline-block',
        }} />
        LIVE RETRIEVAL SIMULATION
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {history.map((item, i) => (
          <FeedItem
            key={`${i}-${item.q}`}
            item={item}
            visible={i === history.length - 1}
          />
        ))}
      </div>
    </div>
  )
}
