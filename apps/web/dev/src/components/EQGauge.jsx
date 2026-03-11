import { useState, useEffect, useRef } from 'react'
import { useReveal } from '../hooks/useReveal'

function ArcGauge({ value, max, label, unit, color, size = 120, strokeWidth = 8 }) {
  const [ref, visible] = useReveal({ once: true })
  const [animValue, setAnimValue] = useState(0)

  useEffect(() => {
    if (!visible) return
    const start = performance.now()
    const tick = (now) => {
      const p = Math.min((now - start) / 1500, 1)
      const eased = 1 - Math.pow(1 - p, 4)
      setAnimValue(eased * value)
      if (p < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [visible, value])

  const r = (size - strokeWidth) / 2
  const circ = Math.PI * r
  const pct = animValue / max
  const dashOffset = circ * (1 - pct)

  return (
    <div ref={ref} className="flex flex-col items-center gap-2">
      <svg width={size} height={size / 2 + 12} viewBox={`0 0 ${size} ${size / 2 + 12}`}>
        <defs>
          <linearGradient id={`gauge-${label}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} />
          </linearGradient>
          <filter id={`glow-${label}`}>
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {/* Track */}
        <path
          d={`M ${strokeWidth / 2} ${size / 2} A ${r} ${r} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={`M ${strokeWidth / 2} ${size / 2} A ${r} ${r} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
          fill="none"
          stroke={`url(#gauge-${label})`}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={dashOffset}
          filter={`url(#glow-${label})`}
          style={{ transition: 'stroke-dashoffset 0.05s linear' }}
        />
        {/* Value text */}
        <text
          x={size / 2}
          y={size / 2 - 4}
          textAnchor="middle"
          fill={color}
          fontSize="20"
          fontWeight="800"
          fontFamily="'JetBrains Mono', monospace"
        >
          {animValue.toFixed(label === 'ECE' || label === 'Brier' ? 3 : 2)}
        </text>
        <text
          x={size / 2}
          y={size / 2 + 14}
          textAnchor="middle"
          fill="rgba(255,255,255,0.35)"
          fontSize="9"
          fontWeight="500"
          fontFamily="Inter, sans-serif"
        >
          {unit}
        </text>
      </svg>
      <span className="text-xs font-semibold" style={{ color }}>{label}</span>
    </div>
  )
}

function EmotionBar({ label, confidence, color, delay = 0 }) {
  const [ref, visible] = useReveal({ once: true })
  const [width, setWidth] = useState(0)

  useEffect(() => {
    if (!visible) return
    const timer = setTimeout(() => setWidth(confidence * 100), delay)
    return () => clearTimeout(timer)
  }, [visible, confidence, delay])

  return (
    <div ref={ref}>
      <div className="flex justify-between mb-1.5">
        <span className="text-sm font-semibold capitalize" style={{ color: 'rgba(255,255,255,0.80)' }}>
          {label}
        </span>
        <span className="text-sm font-mono font-bold" style={{ color }}>
          {(confidence * 100).toFixed(0)}%
        </span>
      </div>
      <div className="h-2.5 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <div
          className="h-full rounded-full"
          style={{
            width: `${width}%`,
            background: `linear-gradient(90deg, ${color}80, ${color})`,
            boxShadow: `0 0 16px ${color}50`,
            transition: 'width 1.2s cubic-bezier(0.16,1,0.3,1)',
          }}
        />
      </div>
    </div>
  )
}

function GestureIndicator({ gesture, confidence, tier }) {
  const tierColors = ['#555', '#D4166A', '#A820D8', '#7B2FF7', '#00B4D8', '#00C8A0']
  const tierLabels = ['Silent', 'Minimal', 'Subtle', 'Moderate', 'Expressive', 'Full']

  return (
    <div className="rounded-xl p-4" style={{ background: 'rgba(0,0,0,0.30)', border: '1px solid rgba(123,47,247,0.15)' }}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase tracking-widest font-semibold" style={{ color: 'rgba(255,255,255,0.35)' }}>
          Gesture Output
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full font-mono font-semibold"
          style={{ background: `${tierColors[tier]}20`, color: tierColors[tier], border: `1px solid ${tierColors[tier]}40` }}>
          Tier {tier} — {tierLabels[tier]}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <div className="text-2xl font-black font-mono" style={{ color: '#00B4D8' }}>[{gesture}]</div>
        <div className="flex-1">
          <div className="flex gap-1">
            {[1, 2, 3, 4, 5].map(i => (
              <div key={i} className="flex-1 h-1.5 rounded-full" style={{
                background: i <= tier ? tierColors[tier] : 'rgba(255,255,255,0.08)',
                boxShadow: i <= tier ? `0 0 6px ${tierColors[tier]}40` : 'none',
                transition: 'all 0.5s ease',
              }} />
            ))}
          </div>
          <div className="text-xs mt-1.5 font-mono" style={{ color: 'rgba(255,255,255,0.40)' }}>
            conf {confidence.toFixed(2)} → expressiveness tier {tier}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function EQShowcase() {
  const [activeEmotion, setActiveEmotion] = useState(0)

  const scenarios = [
    {
      label: 'Happy interaction',
      emotions: [
        { label: 'happy', confidence: 0.87, color: '#00B4D8' },
        { label: 'sad', confidence: 0.06, color: '#D4166A' },
        { label: 'neutral', confidence: 0.07, color: '#7B2FF7' },
      ],
      ece: 0.042, brier: 0.118, f1: 0.871, balanced: 0.874,
      gesture: 'WAVE', tier: 4,
    },
    {
      label: 'Sad interaction',
      emotions: [
        { label: 'happy', confidence: 0.08, color: '#00B4D8' },
        { label: 'sad', confidence: 0.79, color: '#D4166A' },
        { label: 'neutral', confidence: 0.13, color: '#7B2FF7' },
      ],
      ece: 0.055, brier: 0.142, f1: 0.871, balanced: 0.874,
      gesture: 'EMPATHY', tier: 4,
    },
    {
      label: 'Low confidence',
      emotions: [
        { label: 'happy', confidence: 0.38, color: '#00B4D8' },
        { label: 'sad', confidence: 0.29, color: '#D4166A' },
        { label: 'neutral', confidence: 0.33, color: '#7B2FF7' },
      ],
      ece: 0.072, brier: 0.158, f1: 0.871, balanced: 0.874,
      gesture: 'LISTEN', tier: 1,
    },
  ]

  useEffect(() => {
    const id = setInterval(() => setActiveEmotion(p => (p + 1) % scenarios.length), 5000)
    return () => clearInterval(id)
  }, [])

  const s = scenarios[activeEmotion]

  return (
    <div className="grid lg:grid-cols-5 gap-6 items-start">
      {/* Left: control panel */}
      <div className="lg:col-span-2 flex flex-col gap-4">
        <div className="text-xs uppercase tracking-widest font-semibold mb-1" style={{ color: 'rgba(255,255,255,0.30)' }}>
          Interaction Scenario
        </div>
        {scenarios.map((sc, i) => (
          <button
            key={i}
            onClick={() => setActiveEmotion(i)}
            className="flex items-center gap-3 p-4 rounded-xl text-left transition-all duration-300 w-full"
            style={{
              background: i === activeEmotion
                ? 'linear-gradient(135deg, rgba(123,47,247,0.14) 0%, rgba(0,180,216,0.08) 100%)'
                : 'rgba(255,255,255,0.02)',
              border: `1px solid ${i === activeEmotion ? 'rgba(123,47,247,0.45)' : 'rgba(255,255,255,0.06)'}`,
              transform: i === activeEmotion ? 'translateX(6px)' : 'none',
            }}
          >
            <div className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{
              background: i === activeEmotion ? sc.emotions[0].color : 'rgba(255,255,255,0.15)',
              boxShadow: i === activeEmotion ? `0 0 10px ${sc.emotions[0].color}60` : 'none',
            }} />
            <div>
              <div className="text-sm font-semibold" style={{ color: i === activeEmotion ? 'white' : 'rgba(255,255,255,0.50)' }}>
                {sc.label}
              </div>
              <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>
                Top: {sc.emotions[0].label} @ {(sc.emotions[0].confidence * 100).toFixed(0)}%
                → [{sc.gesture}]
              </div>
            </div>
          </button>
        ))}

        {/* Confidence threshold indicator */}
        <div className="rounded-xl p-4 mt-2" style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid rgba(123,47,247,0.12)' }}>
          <div className="text-xs uppercase tracking-widest font-semibold mb-2" style={{ color: 'rgba(255,255,255,0.30)' }}>
            Abstention Logic
          </div>
          <div className="relative h-3 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <div className="absolute top-0 left-0 h-full" style={{ width: '60%', background: 'rgba(212,22,106,0.15)' }} />
            <div className="absolute top-0 h-full" style={{ left: '60%', right: 0, background: 'rgba(0,180,216,0.12)' }} />
            <div className="absolute top-0 w-0.5 h-full bg-white" style={{ left: '60%', opacity: 0.4 }} />
            {/* Confidence marker */}
            <div
              className="absolute top-0 w-2 h-full rounded-full"
              style={{
                left: `${Math.max(s.emotions[0].confidence, s.emotions[1].confidence, s.emotions[2].confidence) * 100}%`,
                transform: 'translateX(-50%)',
                background: Math.max(s.emotions[0].confidence, s.emotions[1].confidence, s.emotions[2].confidence) >= 0.6 ? '#00B4D8' : '#D4166A',
                boxShadow: `0 0 8px ${Math.max(s.emotions[0].confidence, s.emotions[1].confidence, s.emotions[2].confidence) >= 0.6 ? '#00B4D8' : '#D4166A'}60`,
                transition: 'left 0.8s ease',
              }}
            />
          </div>
          <div className="flex justify-between mt-1.5 text-xs font-mono" style={{ color: 'rgba(255,255,255,0.30)' }}>
            <span>0.0</span>
            <span style={{ color: 'rgba(255,255,255,0.45)' }}>threshold 0.60</span>
            <span>1.0</span>
          </div>
        </div>
      </div>

      {/* Right: live EQ dashboard */}
      <div className="lg:col-span-3">
        <div className="rounded-2xl overflow-hidden" style={{
          background: 'linear-gradient(145deg, rgba(13,13,32,0.95) 0%, rgba(8,8,24,0.98) 100%)',
          border: '1px solid rgba(123,47,247,0.25)',
          boxShadow: '0 24px 80px rgba(0,0,0,0.5), 0 0 60px rgba(123,47,247,0.08)',
        }}>
          {/* Titlebar */}
          <div className="flex items-center gap-2 px-5 py-3" style={{ background: 'rgba(22,22,48,0.90)', borderBottom: '1px solid rgba(123,47,247,0.15)' }}>
            <div className="w-3 h-3 rounded-full bg-red-500 opacity-80" />
            <div className="w-3 h-3 rounded-full bg-yellow-400 opacity-80" />
            <div className="w-3 h-3 rounded-full bg-green-400 opacity-80" />
            <span className="text-xs font-mono ml-2" style={{ color: 'rgba(255,255,255,0.40)' }}>
              EQ Dashboard — Emotional Intelligence Layer
            </span>
            <div className="ml-auto flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-xs text-green-400">Live</span>
            </div>
          </div>

          <div className="p-6">
            {/* Emotion bars */}
            <div className="flex flex-col gap-3 mb-6">
              {s.emotions.map((em, i) => (
                <EmotionBar key={em.label} {...em} delay={i * 150} />
              ))}
            </div>

            {/* Calibration gauges */}
            <div className="grid grid-cols-4 gap-2 mb-5">
              <ArcGauge value={s.f1} max={1} label="F1" unit="macro" color="#00B4D8" size={100} strokeWidth={6} />
              <ArcGauge value={s.balanced} max={1} label="Balanced" unit="accuracy" color="#7B2FF7" size={100} strokeWidth={6} />
              <ArcGauge value={s.ece} max={0.15} label="ECE" unit="calibration" color="#D4166A" size={100} strokeWidth={6} />
              <ArcGauge value={s.brier} max={0.25} label="Brier" unit="reliability" color="#00C8A0" size={100} strokeWidth={6} />
            </div>

            {/* Gesture output */}
            <GestureIndicator gesture={s.gesture} confidence={Math.max(...s.emotions.map(e => e.confidence))} tier={s.tier} />
          </div>
        </div>
      </div>
    </div>
  )
}
