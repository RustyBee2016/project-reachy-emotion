import { useEffect, useRef, useState } from 'react'

export function useReveal(options = {}) {
  const ref = useRef(null)
  const [visible, setVisible] = useState(false)
  const { threshold = 0.15, once = true, rootMargin = '0px 0px -60px 0px' } = options

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          if (once) obs.unobserve(el)
        } else if (!once) {
          setVisible(false)
        }
      },
      { threshold, rootMargin }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold, once, rootMargin])

  return [ref, visible]
}

export function Reveal({ children, delay = 0, direction = 'up', className = '', style = {}, as = 'div' }) {
  const [ref, visible] = useReveal()
  const Tag = as

  const transforms = {
    up: 'translateY(40px)',
    down: 'translateY(-40px)',
    left: 'translateX(40px)',
    right: 'translateX(-40px)',
    scale: 'scale(0.92)',
    none: 'none',
  }

  return (
    <Tag
      ref={ref}
      className={className}
      style={{
        ...style,
        opacity: visible ? 1 : 0,
        transform: visible ? 'none' : transforms[direction],
        transition: `opacity 0.7s cubic-bezier(0.16,1,0.3,1) ${delay}s, transform 0.7s cubic-bezier(0.16,1,0.3,1) ${delay}s`,
        willChange: 'opacity, transform',
      }}
    >
      {children}
    </Tag>
  )
}

export function useCounter(end, duration = 2000, startOnVisible = true) {
  const [count, setCount] = useState(0)
  const [ref, visible] = useReveal({ once: true })
  const started = useRef(false)

  useEffect(() => {
    if (!startOnVisible || !visible || started.current) return
    started.current = true
    const startTime = performance.now()
    const tick = (now) => {
      const elapsed = now - startTime
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(Math.round(eased * end))
      if (progress < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [visible, end, duration, startOnVisible])

  return [ref, count]
}
