'use client'

import { useEffect, useRef } from 'react'

export default function HeroCanvas({ onPhaseChange }) {
  const canvasRef = useRef(null)
  const engineRef = useRef(null)

  useEffect(() => {
    if (typeof window === 'undefined') return
    let engine = null

    async function init() {
      // Dynamic import keeps Three.js out of SSR
      const { SceneEngine } = await import('@/lib/SceneEngine')
      engine = new SceneEngine(canvasRef.current, onPhaseChange)
      engineRef.current = engine
    }

    init()
    return () => engine?.destroy()
  }, [onPhaseChange])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        display: 'block',
      }}
    />
  )
}
