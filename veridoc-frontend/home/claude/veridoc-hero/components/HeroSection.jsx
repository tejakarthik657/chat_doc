'use client'

import { useCallback, useState } from 'react'
import dynamic from 'next/dynamic'
import HudOverlay  from './HudOverlay'
import QueryFeed   from './QueryFeed'
import MarqueeStrip from './MarqueeStrip'
import { PHASES }  from '@/lib/SceneEngine'

// Canvas must be client-only (no SSR for WebGL)
const HeroCanvas = dynamic(() => import('./HeroCanvas'), { ssr: false })

const NAV_LINKS = ['How it works', 'Features', 'Pricing', 'Docs']

export default function HeroSection() {
  const [phase, setPhase] = useState(PHASES.SINGULARITY)
  const [headlineVisible, setHeadlineVisible] = useState(true)

  const handlePhaseChange = useCallback((p) => {
    setPhase(p)
  }, [])

  const isEarly = phase === PHASES.SINGULARITY || phase === PHASES.EXPLODING

  return (
    <section style={{
      position: 'relative',
      width: '100vw',
      height: '100vh',
      overflow: 'hidden',
      background: '#02020A',
      cursor: 'none',
    }}>
      {/* ── Three.js Canvas ─────────────────────────────── */}
      <HeroCanvas onPhaseChange={handlePhaseChange} />

      {/* ── Vignette overlay ────────────────────────────── */}
      <div style={{
        position: 'absolute', inset: 0, zIndex: 5,
        background: 'radial-gradient(ellipse at 50% 50%, transparent 40%, rgba(2,2,10,0.7) 100%)',
        pointerEvents: 'none',
      }} />

      {/* ── Scanline texture ────────────────────────────── */}
      <div style={{
        position: 'absolute', inset: 0, zIndex: 6,
        backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,136,0.012) 2px, rgba(0,255,136,0.012) 4px)',
        pointerEvents: 'none',
      }} />

      {/* ── NAV ─────────────────────────────────────────── */}
      <nav style={{
        position: 'absolute', top: 0, left: 0, right: 0,
        zIndex: 30,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '22px 48px',
        background: 'linear-gradient(to bottom, rgba(2,2,10,0.85), transparent)',
        backdropFilter: 'blur(4px)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 13, fontWeight: 500,
          color: '#F0F0F5',
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
        }}>
          <span style={{
            width: 8, height: 8,
            background: '#00FF88',
            borderRadius: '50%',
            animation: 'feedPulse 2s ease-in-out infinite',
            display: 'inline-block',
          }} />
          VERIDOC
        </div>

        <ul style={{
          display: 'flex', gap: 40, listStyle: 'none',
          margin: 0, padding: 0,
        }}>
          {NAV_LINKS.map((l) => (
            <li key={l}>
              <a href="#" style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 11,
                color: '#4B5563',
                textDecoration: 'none',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                transition: 'color 0.2s',
              }}
                onMouseEnter={e => e.target.style.color = '#F0F0F5'}
                onMouseLeave={e => e.target.style.color = '#4B5563'}
              >{l}</a>
            </li>
          ))}
        </ul>

        <button style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 11, fontWeight: 500,
          color: '#000',
          background: '#00FF88',
          border: 'none',
          padding: '10px 26px',
          cursor: 'none',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          transition: 'background 0.2s, transform 0.15s',
        }}
          onMouseEnter={e => { e.target.style.background = '#4ADE80'; e.target.style.transform = 'translateY(-1px)' }}
          onMouseLeave={e => { e.target.style.background = '#00FF88'; e.target.style.transform = 'translateY(0)' }}
        >
          Start Free
        </button>
      </nav>

      {/* ── HUD Overlays ─────────────────────────────────── */}
      {!isEarly && <HudOverlay phase={phase} />}

      {/* ── HERO HEADLINE ────────────────────────────────── */}
      <div style={{
        position: 'absolute', inset: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        zIndex: 15,
        pointerEvents: 'none',
      }}>
        <div style={{
          textAlign: 'center',
          maxWidth: 860,
          padding: '0 32px',
          opacity: isEarly ? 0 : 1,
          transform: isEarly ? 'translateY(24px) scale(0.97)' : 'translateY(0) scale(1)',
          transition: 'opacity 1.2s cubic-bezier(0.16,1,0.3,1), transform 1.2s cubic-bezier(0.16,1,0.3,1)',
        }}>
          {/* Eyebrow */}
          <div style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 11,
            color: '#00FF88',
            letterSpacing: '0.22em',
            textTransform: 'uppercase',
            marginBottom: 28,
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14,
            animation: 'fadeUp 0.9s cubic-bezier(0.16,1,0.3,1) 0.4s both',
          }}>
            <span style={{ width: 36, height: 1, background: 'rgba(0,255,136,0.4)', display: 'inline-block' }} />
            Source-Grounded Document Intelligence
            <span style={{ width: 36, height: 1, background: 'rgba(0,255,136,0.4)', display: 'inline-block' }} />
          </div>

          {/* Headline */}
          <h1 style={{
            fontFamily: "'DM Serif Display', serif",
            fontSize: 'clamp(48px, 7.5vw, 104px)',
            lineHeight: 1.04,
            fontWeight: 400,
            color: '#F0F0F5',
            margin: 0,
            animation: 'fadeUp 0.9s cubic-bezier(0.16,1,0.3,1) 0.55s both',
          }}>
            Your documents.
            <br />
            <span style={{
              color: '#00FF88',
              fontStyle: 'italic',
              textShadow: '0 0 60px rgba(0,255,136,0.35)',
            }}>
              Finally, honest answers.
            </span>
          </h1>

          {/* Sub */}
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 13,
            color: '#4B5563',
            letterSpacing: '0.04em',
            margin: '30px auto 52px',
            maxWidth: 520,
            lineHeight: 1.85,
            animation: 'fadeUp 0.9s cubic-bezier(0.16,1,0.3,1) 0.7s both',
          }}>
            Every answer is{' '}
            <span style={{ color: '#FFAA00' }}>grounded in your PDF</span>
            {'. '}Every claim has a page number.
            If the answer isn't there —{' '}
            <span style={{ color: '#FF3344' }}>we say so</span>.
          </p>

          {/* CTAs */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16,
            pointerEvents: 'all',
            animation: 'fadeUp 0.9s cubic-bezier(0.16,1,0.3,1) 0.85s both',
          }}>
            <button
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 12, fontWeight: 500,
                color: '#000',
                background: '#00FF88',
                border: 'none',
                padding: '18px 42px',
                cursor: 'none',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = '#4ADE80'
                e.currentTarget.style.transform  = 'translateY(-2px)'
                e.currentTarget.style.boxShadow  = '0 20px 50px rgba(0,255,136,0.3)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = '#00FF88'
                e.currentTarget.style.transform  = 'translateY(0)'
                e.currentTarget.style.boxShadow  = 'none'
              }}
            >
              Upload Your First Document →
            </button>

            <button
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: 12, fontWeight: 400,
                color: '#00FF88',
                background: 'transparent',
                border: '1px solid rgba(0,255,136,0.3)',
                padding: '17px 38px',
                cursor: 'none',
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = '#00FF88'
                e.currentTarget.style.background  = 'rgba(0,255,136,0.06)'
                e.currentTarget.style.transform   = 'translateY(-2px)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'rgba(0,255,136,0.3)'
                e.currentTarget.style.background  = 'transparent'
                e.currentTarget.style.transform   = 'translateY(0)'
              }}
            >
              See How It Works
            </button>
          </div>

          {/* Click hint */}
          <p style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 9,
            color: '#1F2937',
            letterSpacing: '0.16em',
            textTransform: 'uppercase',
            marginTop: 28,
            animation: 'fadeUp 0.9s cubic-bezier(0.16,1,0.3,1) 1.1s both',
          }}>
            Click the graph to fire a retrieval query
          </p>
        </div>
      </div>

      {/* ── Query Feed ───────────────────────────────────── */}
      {!isEarly && <QueryFeed />}

      {/* ── Scroll Hint ──────────────────────────────────── */}
      <div style={{
        position: 'absolute',
        bottom: 46, left: '50%',
        transform: 'translateX(-50%)',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
        zIndex: 20,
        pointerEvents: 'none',
        opacity: isEarly ? 0 : 1,
        transition: 'opacity 1s ease 2s',
      }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9, color: '#1F2937',
          letterSpacing: '0.2em', textTransform: 'uppercase',
        }}>scroll</span>
        <div style={{
          width: 1, height: 38,
          background: 'linear-gradient(to bottom, #1F2937, transparent)',
          animation: 'scrollPulse 2.2s ease-in-out infinite',
        }} />
      </div>

      {/* ── Marquee ──────────────────────────────────────── */}
      <MarqueeStrip />
    </section>
  )
}
