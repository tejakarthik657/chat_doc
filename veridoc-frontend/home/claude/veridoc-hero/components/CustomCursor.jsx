'use client'

import { useEffect, useRef, useState } from 'react'

export default function CustomCursor() {
  const dotRef  = useRef(null)
  const ringRef = useRef(null)
  const [isHover, setIsHover] = useState(false)

  useEffect(() => {
    let mx = 0, my = 0, rx = 0, ry = 0
    let rafId

    const onMove = (e) => { mx = e.clientX; my = e.clientY }
    const onOver  = (e) => {
      if (e.target.closest('button, a, [data-cursor]')) setIsHover(true)
    }
    const onOut   = () => setIsHover(false)

    function follow() {
      rx += (mx - rx) * 0.11
      ry += (my - ry) * 0.11
      if (dotRef.current) {
        dotRef.current.style.left = mx + 'px'
        dotRef.current.style.top  = my + 'px'
      }
      if (ringRef.current) {
        ringRef.current.style.left = rx + 'px'
        ringRef.current.style.top  = ry + 'px'
      }
      rafId = requestAnimationFrame(follow)
    }

    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseover', onOver)
    window.addEventListener('mouseout',  onOut)
    follow()
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseover', onOver)
      window.removeEventListener('mouseout',  onOut)
      cancelAnimationFrame(rafId)
    }
  }, [])

  return (
    <>
      <div ref={dotRef} style={{
        position: 'fixed',
        width: isHover ? 18 : 10,
        height: isHover ? 18 : 10,
        background: isHover ? '#FFAA00' : '#00FF88',
        borderRadius: '50%',
        pointerEvents: 'none',
        zIndex: 9999,
        transform: 'translate(-50%, -50%)',
        transition: 'width 0.2s, height 0.2s, background 0.2s',
        mixBlendMode: 'screen',
      }} />
      <div ref={ringRef} style={{
        position: 'fixed',
        width: isHover ? 44 : 32,
        height: isHover ? 44 : 32,
        border: `1px solid rgba(${isHover ? '255,170,0' : '0,255,136'},0.4)`,
        borderRadius: '50%',
        pointerEvents: 'none',
        zIndex: 9998,
        transform: 'translate(-50%, -50%)',
        transition: 'width 0.25s, height 0.25s, border-color 0.25s',
      }} />
    </>
  )
}
