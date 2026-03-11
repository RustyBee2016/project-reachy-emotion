import { useEffect, useRef } from 'react'

export function GradientOrbs() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none" aria-hidden="true">
      {/* Large purple orb — top right */}
      <div
        className="absolute rounded-full blur-3xl"
        style={{
          width: '600px', height: '600px',
          top: '-15%', right: '-10%',
          background: 'radial-gradient(circle, rgba(123,47,247,0.18) 0%, transparent 70%)',
          animation: 'orbFloat1 20s ease-in-out infinite',
        }}
      />
      {/* Pink orb — bottom left */}
      <div
        className="absolute rounded-full blur-3xl"
        style={{
          width: '500px', height: '500px',
          bottom: '-10%', left: '-8%',
          background: 'radial-gradient(circle, rgba(212,22,106,0.14) 0%, transparent 70%)',
          animation: 'orbFloat2 25s ease-in-out infinite',
        }}
      />
      {/* Cyan orb — center */}
      <div
        className="absolute rounded-full blur-3xl"
        style={{
          width: '400px', height: '400px',
          top: '40%', left: '50%',
          transform: 'translateX(-50%)',
          background: 'radial-gradient(circle, rgba(0,180,216,0.10) 0%, transparent 70%)',
          animation: 'orbFloat3 18s ease-in-out infinite',
        }}
      />
    </div>
  )
}

export function GridOverlay({ opacity = 0.03 }) {
  return (
    <div
      className="absolute inset-0 pointer-events-none"
      aria-hidden="true"
      style={{
        opacity,
        backgroundImage: `
          linear-gradient(rgba(123,47,247,0.8) 1px, transparent 1px),
          linear-gradient(90deg, rgba(123,47,247,0.8) 1px, transparent 1px)
        `,
        backgroundSize: '80px 80px',
        maskImage: 'radial-gradient(ellipse 60% 50% at 50% 50%, black, transparent)',
        WebkitMaskImage: 'radial-gradient(ellipse 60% 50% at 50% 50%, black, transparent)',
      }}
    />
  )
}

export function ParticleField({ count = 30 }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animId

    const resize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio
      canvas.height = canvas.offsetHeight * window.devicePixelRatio
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio)
    }
    resize()
    window.addEventListener('resize', resize)

    const w = () => canvas.offsetWidth
    const h = () => canvas.offsetHeight

    const colors = ['rgba(123,47,247,', 'rgba(212,22,106,', 'rgba(0,180,216,']
    const particles = Array.from({ length: count }, () => ({
      x: Math.random() * w(),
      y: Math.random() * h(),
      r: Math.random() * 1.5 + 0.5,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      color: colors[Math.floor(Math.random() * 3)],
      alpha: Math.random() * 0.5 + 0.15,
      pulseSpeed: Math.random() * 0.02 + 0.005,
      pulseOffset: Math.random() * Math.PI * 2,
    }))

    let t = 0
    const draw = () => {
      t += 1
      ctx.clearRect(0, 0, w(), h())

      particles.forEach(p => {
        p.x += p.vx
        p.y += p.vy
        if (p.x < 0) p.x = w()
        if (p.x > w()) p.x = 0
        if (p.y < 0) p.y = h()
        if (p.y > h()) p.y = 0

        const pulse = Math.sin(t * p.pulseSpeed + p.pulseOffset) * 0.3 + 0.7
        const a = p.alpha * pulse

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
        ctx.fillStyle = `${p.color}${a.toFixed(2)})`
        ctx.fill()

        ctx.beginPath()
        ctx.arc(p.x, p.y, p.r * 3, 0, Math.PI * 2)
        ctx.fillStyle = `${p.color}${(a * 0.15).toFixed(3)})`
        ctx.fill()
      })

      // Draw connection lines between nearby particles
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x
          const dy = particles[i].y - particles[j].y
          const dist = Math.sqrt(dx * dx + dy * dy)
          if (dist < 120) {
            const lineAlpha = (1 - dist / 120) * 0.08
            ctx.beginPath()
            ctx.moveTo(particles[i].x, particles[i].y)
            ctx.lineTo(particles[j].x, particles[j].y)
            ctx.strokeStyle = `rgba(123,47,247,${lineAlpha})`
            ctx.lineWidth = 0.5
            ctx.stroke()
          }
        }
      }

      animId = requestAnimationFrame(draw)
    }
    draw()

    return () => {
      cancelAnimationFrame(animId)
      window.removeEventListener('resize', resize)
    }
  }, [count])

  return (
    <canvas
      ref={canvasRef}
      className="absolute inset-0 w-full h-full pointer-events-none"
      aria-hidden="true"
      style={{ opacity: 0.6 }}
    />
  )
}

export function AnimatedBorderCard({ children, className = '', style = {} }) {
  return (
    <div className={`relative group ${className}`} style={style}>
      {/* Animated gradient border */}
      <div
        className="absolute -inset-px rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"
        style={{
          background: 'linear-gradient(135deg, #D4166A, #7B2FF7, #00B4D8, #7B2FF7, #D4166A)',
          backgroundSize: '300% 300%',
          animation: 'borderRotate 4s linear infinite',
        }}
      />
      {/* Inner */}
      <div
        className="relative rounded-2xl p-6 h-full transition-all duration-300"
        style={{
          background: 'linear-gradient(145deg, rgba(13,13,32,0.95) 0%, rgba(8,8,24,0.98) 100%)',
        }}
      >
        {children}
      </div>
    </div>
  )
}
