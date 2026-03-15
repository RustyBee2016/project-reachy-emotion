import { useState } from 'react'
import { ExternalLink } from 'lucide-react'

const TIERS = [
  {
    tier: 1, label: 'Minimal', sublabel: 'Abstain', confRange: '< 0.60',
    color: '#6B7280',
    desc: 'Confidence below threshold. System withholds active gesture — avoiding misleading empathetic signals when uncertain.',
    gesture: 'NEUTRAL', gestureFull: 'Silent — no active expression',
    prompt: '"Let me make sure I understand what you\'re feeling right now..."',
    headAngle: 0, antennaL: -12, antennaR: 12, bodyScale: 0.97,
    amplitude: '0.25×', speed: 'none', abstain: true,
  },
  {
    tier: 2, label: 'Subtle', sublabel: 'Gentle', confRange: '0.60–0.69',
    color: '#D4166A',
    desc: 'Low expressiveness. A gentle NOD. Head dips slightly. Listening posture signals acknowledgment without assertion.',
    gesture: 'NOD', gestureFull: 'NOD — quiet head acknowledgment',
    prompt: '"I hear you. That sounds important to you..."',
    headAngle: 7, antennaL: -5, antennaR: 5, bodyScale: 0.99,
    amplitude: '0.50×', speed: 'slow', abstain: false,
  },
  {
    tier: 3, label: 'Moderate', sublabel: 'Standard', confRange: '0.70–0.79',
    color: '#A820D8',
    desc: 'Proportional engagement. LISTEN or COMFORT. Head turns attentively, antennas at neutral active stance.',
    gesture: 'LISTEN', gestureFull: 'LISTEN — attentive orientation',
    prompt: '"That\'s meaningful to share. I\'m fully here with you..."',
    headAngle: 16, antennaL: 5, antennaR: -5, bodyScale: 1.01,
    amplitude: '0.75×', speed: 'normal', abstain: false,
  },
  {
    tier: 4, label: 'Expressive', sublabel: 'High', confRange: '0.80–0.89',
    color: '#7B2FF7',
    desc: 'Strong confidence. WAVE or EMPATHY. Head rotates toward user, antennas raised and visibly active.',
    gesture: 'WAVE', gestureFull: 'WAVE — directed engagement',
    prompt: '"I\'m genuinely glad you\'re sharing this with me today!"',
    headAngle: 24, antennaL: 18, antennaR: -18, bodyScale: 1.03,
    amplitude: 'full', speed: 'normal', abstain: false,
  },
  {
    tier: 5, label: 'Full', sublabel: 'Maximum', confRange: '≥ 0.90',
    color: '#00B4D8',
    desc: 'Peak confidence. CELEBRATE or EXCITED. Maximum body animation — antennas animated, full joyful expression unleashed.',
    gesture: 'CELEBRATE', gestureFull: 'CELEBRATE — maximum expressiveness',
    prompt: '"This is wonderful! I\'m so happy to share this moment with you!"',
    headAngle: 32, antennaL: 30, antennaR: -30, bodyScale: 1.06,
    amplitude: 'full', speed: 'fast', abstain: false,
  },
]

const EMOTION_ROWS = [
  { emotion: 'happy',    ekman: 'joy · contentment',   color: '#00B4D8', gestures: ['WAVE', 'CELEBRATE', 'THUMBS_UP', 'EXCITED'], tier: 4, strategy: 'amplify_positive' },
  { emotion: 'sad',      ekman: 'sadness · grief',      color: '#D4166A', gestures: ['EMPATHY', 'COMFORT', 'HUG', 'SAD_ACK'],     tier: 4, strategy: 'provide_support' },
  { emotion: 'neutral',  ekman: 'neutral · reserved',   color: '#7B2FF7', gestures: ['NOD', 'LISTEN', 'THINK', 'WAVE'],           tier: 2, strategy: 'engage_openly' },
  { emotion: 'anger',    ekman: 'anger (Ekman PPE)',    color: '#FF6B35', gestures: ['LISTEN', 'NOD', 'NEUTRAL'],                  tier: 2, strategy: 'de_escalate', deEscalate: true },
  { emotion: 'fear',     ekman: 'fear (Ekman PPE)',     color: '#A820D8', gestures: ['COMFORT', 'HUG', 'LISTEN'],                  tier: 3, strategy: 'reassure' },
  { emotion: 'surprise', ekman: 'surprise (Ekman PPE)', color: '#00C8A0', gestures: ['EXCITED', 'WAVE', 'CELEBRATE'],              tier: 5, strategy: 'match_and_explore' },
  { emotion: 'disgust',  ekman: 'disgust (Ekman PPE)',  color: '#6B7280', gestures: ['NOD', 'NEUTRAL', 'LISTEN'],                  tier: 2, strategy: 'redirect' },
  { emotion: 'contempt', ekman: 'contempt (Ekman PPE)', color: '#9CA3AF', gestures: ['LISTEN', 'NOD'],                             tier: 2, strategy: 'de_escalate', deEscalate: true },
]

function ReachyMiniSVG({ tier }) {
  const t = TIERS[tier - 1]
  const { headAngle, antennaL, antennaR, bodyScale, color } = t
  const isPulsing = tier >= 4

  return (
    <div className="relative flex flex-col items-center select-none">
      <svg
        width="170" height="215"
        viewBox="0 0 170 215"
        aria-label="Reachy Mini robot illustration"
        style={{ filter: `drop-shadow(0 0 22px ${color}45)`, transition: 'filter 0.7s ease' }}
      >
        {/* ── Body ── */}
        <ellipse
          cx="85" cy="170" rx="35" ry="40"
          fill="rgba(218,218,228,0.94)"
          style={{
            transform: `scale(${bodyScale})`,
            transformOrigin: '85px 170px',
            transition: 'transform 0.7s cubic-bezier(0.34,1.56,0.64,1)',
          }}
        />
        <ellipse cx="75" cy="155" rx="13" ry="16" fill="rgba(255,255,255,0.38)" />
        <ellipse cx="85" cy="207" rx="33" ry="5" fill="rgba(170,170,185,0.55)" />

        {/* ── Neck ── */}
        <rect x="78" y="118" width="14" height="16" rx="4" fill="rgba(195,195,210,0.85)" />

        {/* ── Head group (rotates) ── */}
        <g style={{
          transform: `rotate(${headAngle}deg)`,
          transformOrigin: '85px 102px',
          transition: 'transform 0.75s cubic-bezier(0.34,1.56,0.64,1)',
        }}>
          {/* Head */}
          <rect x="50" y="70" width="70" height="54" rx="18" fill="rgba(222,222,232,0.96)" />
          <rect x="57" y="75" width="28" height="18" rx="7" fill="rgba(255,255,255,0.42)" />

          {/* Left eye */}
          <circle cx="70" cy="100" r="13" fill="rgba(18,18,32,0.94)" />
          <circle cx="70" cy="100" r="10" fill="rgba(8,8,20,1)" />
          <circle cx="74" cy="96"  r="2.5" fill="rgba(255,255,255,0.18)" />
          <circle cx="70" cy="100" r="12.5" fill="none" stroke={color} strokeWidth="1.5"
            style={{ opacity: 0.65, transition: 'stroke 0.6s' }} />

          {/* Right eye */}
          <circle cx="100" cy="100" r="13" fill="rgba(18,18,32,0.94)" />
          <circle cx="100" cy="100" r="10" fill="rgba(8,8,20,1)" />
          <circle cx="104" cy="96"  r="2.5" fill="rgba(255,255,255,0.18)" />
          <circle cx="100" cy="100" r="12.5" fill="none" stroke={color} strokeWidth="1.5"
            style={{ opacity: 0.65, transition: 'stroke 0.6s' }} />

          {/* Eye bridge */}
          <rect x="83" y="98" width="4" height="4" rx="2" fill="rgba(55,55,75,0.70)" />

          {/* ── Left antenna (rotates independently) ── */}
          <g style={{
            transform: `rotate(${antennaL}deg)`,
            transformOrigin: '68px 71px',
            transition: 'transform 0.75s cubic-bezier(0.34,1.56,0.64,1)',
          }}>
            <path d="M68,71 C66,65 70,61 68,56 C66,51 70,47 68,42 C66,37 70,33 68,28"
              stroke="rgba(175,175,192,0.92)" strokeWidth="2.2" fill="none" strokeLinecap="round" />
            <circle cx="68" cy="26" r="3.5" fill={color}
              style={{ transition: 'fill 0.6s', filter: isPulsing ? `drop-shadow(0 0 5px ${color})` : 'none' }} />
          </g>

          {/* ── Right antenna ── */}
          <g style={{
            transform: `rotate(${antennaR}deg)`,
            transformOrigin: '102px 71px',
            transition: 'transform 0.75s cubic-bezier(0.34,1.56,0.64,1)',
          }}>
            <path d="M102,71 C100,65 104,61 102,56 C100,51 104,47 102,42 C100,37 104,33 102,28"
              stroke="rgba(175,175,192,0.92)" strokeWidth="2.2" fill="none" strokeLinecap="round" />
            <circle cx="102" cy="26" r="3.5" fill={color}
              style={{ transition: 'fill 0.6s', filter: isPulsing ? `drop-shadow(0 0 5px ${color})` : 'none' }} />
          </g>
        </g>

        {/* ── Halo ring ── */}
        <ellipse cx="85" cy="162" rx="48" ry="52" fill="none" stroke={color} strokeWidth="1"
          style={{ opacity: isPulsing ? 0.22 : 0.08, transition: 'opacity 0.7s, stroke 0.7s' }} />
      </svg>

      {/* Attribution */}
      <p className="text-center mt-2" style={{ color: 'rgba(255,255,255,0.22)', fontSize: '10px', lineHeight: '1.5', maxWidth: '155px' }}>
        Illustration inspired by Reachy Mini<br />
        <a href="https://time.com/collections/best-inventions-special-mentions/7320890/pollen-robotics-reachy-mini/"
          target="_blank" rel="noopener noreferrer"
          style={{ color: 'rgba(255,255,255,0.38)', textDecoration: 'underline' }}>
          Courtesy Pollen Robotics · TIME 2025
        </a>
      </p>
    </div>
  )
}

export default function GestureModulationShowcase() {
  const [activeTier, setActiveTier] = useState(4)
  const t = TIERS[activeTier - 1]

  return (
    <div className="flex flex-col gap-10">

      {/* ── Tier selector + Robot + Detail ── */}
      <div className="grid lg:grid-cols-3 gap-6 items-start">

        {/* Column 1: tier buttons */}
        <div className="flex flex-col gap-2.5">
          <div className="text-xs uppercase tracking-widest font-semibold mb-1"
            style={{ color: 'rgba(255,255,255,0.30)' }}>
            Expressiveness Tier
          </div>
          {TIERS.map(({ tier, label, sublabel, confRange, color }) => (
            <button
              key={tier}
              onClick={() => setActiveTier(tier)}
              className="flex items-center gap-3 p-3.5 rounded-xl text-left w-full"
              style={{
                background: activeTier === tier
                  ? `linear-gradient(135deg, ${color}18 0%, transparent 100%)`
                  : 'rgba(255,255,255,0.02)',
                border: `1px solid ${activeTier === tier ? color + '55' : 'rgba(255,255,255,0.06)'}`,
                transform: activeTier === tier ? 'translateX(4px)' : 'none',
                transition: 'all 0.25s ease',
              }}
            >
              <div className="flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0"
                style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
                <span className="text-xs font-black" style={{ color }}>{tier}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-bold"
                    style={{ color: activeTier === tier ? 'white' : 'rgba(255,255,255,0.50)' }}>
                    {label}
                  </span>
                  <span className="text-xs"
                    style={{ color: activeTier === tier ? color : 'rgba(255,255,255,0.22)' }}>
                    {sublabel}
                  </span>
                </div>
                <div className="text-xs font-mono mt-0.5" style={{ color: 'rgba(255,255,255,0.28)' }}>
                  conf {confRange}
                </div>
              </div>
              <div className="flex items-end gap-0.5">
                {[1,2,3,4,5].map(i => (
                  <div key={i} className="w-1 rounded-full flex-shrink-0" style={{
                    height: `${5 + i * 3}px`,
                    background: i <= tier
                      ? (activeTier === tier ? color : `${color}50`)
                      : 'rgba(255,255,255,0.07)',
                    transition: 'background 0.3s',
                  }} />
                ))}
              </div>
            </button>
          ))}
        </div>

        {/* Column 2: robot */}
        <div className="flex flex-col items-center justify-center gap-4 py-4">
          <ReachyMiniSVG tier={activeTier} />
          <div className="px-5 py-3 rounded-xl text-center"
            style={{ background: `${t.color}12`, border: `1px solid ${t.color}35`, minWidth: '180px' }}>
            <div className="text-base font-black font-mono" style={{ color: t.color }}>
              [{t.gesture}]
            </div>
            <div className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.42)' }}>
              {t.gestureFull}
            </div>
          </div>
          <div className="flex gap-2">
            {[1,2,3,4,5].map(i => (
              <button
                key={i}
                onClick={() => setActiveTier(i)}
                className="rounded-full transition-all duration-300"
                style={{
                  width: activeTier === i ? '28px' : '8px',
                  height: '8px',
                  background: activeTier === i ? t.color : 'rgba(255,255,255,0.15)',
                  boxShadow: activeTier === i ? `0 0 8px ${t.color}60` : 'none',
                }}
              />
            ))}
          </div>
        </div>

        {/* Column 3: detail panel */}
        <div className="flex flex-col gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs px-2.5 py-1 rounded-full font-mono font-semibold"
                style={{ background: `${t.color}18`, color: t.color, border: `1px solid ${t.color}30` }}>
                Tier {activeTier}
              </span>
              <span className="text-sm font-bold" style={{ color: 'rgba(255,255,255,0.80)' }}>
                {t.label} — {t.sublabel}
              </span>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.52)' }}>
              {t.desc}
            </p>
          </div>

          <div className="rounded-xl p-4"
            style={{ background: 'rgba(0,0,0,0.28)', border: `1px solid ${t.color}22` }}>
            <div className="text-xs uppercase tracking-widest font-semibold mb-2"
              style={{ color: 'rgba(255,255,255,0.28)' }}>
              LLM Prompt Tone
            </div>
            <p className="text-sm italic leading-relaxed" style={{ color: t.color }}>
              {t.prompt}
            </p>
          </div>

          <div className="rounded-xl p-4"
            style={{ background: 'rgba(0,0,0,0.20)', border: '1px solid rgba(123,47,247,0.12)' }}>
            <div className="text-xs uppercase tracking-widest font-semibold mb-3"
              style={{ color: 'rgba(255,255,255,0.28)' }}>
              gesture_modulator.py output
            </div>
            <div className="grid grid-cols-2 gap-y-2.5 gap-x-3 text-xs font-mono">
              {[
                ['amplitude', t.amplitude],
                ['speed', t.speed],
                ['head_tilt', `${t.headAngle}°`],
                ['abstain', t.abstain ? 'TRUE' : 'false'],
              ].map(([k, v]) => (
                <div key={k}>
                  <div style={{ color: 'rgba(255,255,255,0.28)' }}>{k}</div>
                  <div style={{
                    color: k === 'abstain' && t.abstain ? '#D4166A'
                      : k === 'abstain' ? 'rgba(255,255,255,0.30)'
                      : t.color
                  }}>
                    {v}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Emotion → Gesture mapping grid ── */}
      <div>
        <div className="text-xs uppercase tracking-widest font-semibold mb-4"
          style={{ color: 'rgba(255,255,255,0.28)' }}>
          All 8 Ekman classes — gesture keyword mapping
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {EMOTION_ROWS.map(({ emotion, ekman, color, gestures, tier, strategy, deEscalate }) => (
            <div
              key={emotion}
              className="rounded-xl p-4"
              style={{
                background: 'rgba(11,11,24,0.85)',
                border: `1px solid ${color}20`,
                transition: 'border-color 0.25s',
              }}
              onMouseOver={e => e.currentTarget.style.borderColor = `${color}55`}
              onMouseOut={e => e.currentTarget.style.borderColor = `${color}20`}
            >
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-sm font-bold capitalize" style={{ color }}>{emotion}</span>
                <div className="flex items-center gap-1.5">
                  {deEscalate && (
                    <span className="text-xs px-1.5 py-0.5 rounded font-semibold"
                      style={{ background: 'rgba(255,107,53,0.12)', color: '#FF6B35', border: '1px solid rgba(255,107,53,0.25)' }}>
                      de-esc
                    </span>
                  )}
                  <span className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.28)' }}>
                    T{tier}
                  </span>
                </div>
              </div>
              <div className="text-xs mb-2.5" style={{ color: 'rgba(255,255,255,0.32)' }}>{ekman}</div>
              <div className="flex flex-wrap gap-1 mb-2">
                {gestures.map(g => (
                  <span key={g} className="text-xs font-mono px-1.5 py-0.5 rounded"
                    style={{ background: `${color}10`, color, border: `1px solid ${color}20` }}>
                    [{g}]
                  </span>
                ))}
              </div>
              <div className="text-xs font-mono" style={{ color: 'rgba(255,255,255,0.22)' }}>
                {strategy}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Attribution footer ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-4"
        style={{ borderTop: '1px solid rgba(123,47,247,0.10)' }}>
        <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.24)', maxWidth: '480px' }}>
          Reachy Mini is open-source hardware by{' '}
          <a href="https://www.pollen-robotics.com" target="_blank" rel="noopener noreferrer"
            style={{ color: 'rgba(255,255,255,0.45)', textDecoration: 'underline' }}>
            Pollen Robotics
          </a>
          {' '}× Hugging Face. Robot design depicted above is an original illustration
          inspired by the Reachy Mini form factor. Robot photos courtesy Pollen Robotics as featured in{' '}
          <a href="https://time.com/collections/best-inventions-special-mentions/7320890/pollen-robotics-reachy-mini/"
            target="_blank" rel="noopener noreferrer"
            style={{ color: 'rgba(255,255,255,0.45)', textDecoration: 'underline' }}>
            TIME Best Inventions 2025
          </a>
          .
        </p>
        <a href="https://github.com/pollen-robotics/reachy_mini" target="_blank" rel="noopener noreferrer"
          className="flex items-center gap-1.5 text-xs whitespace-nowrap"
          style={{ color: 'rgba(123,47,247,0.65)', transition: 'color 0.2s' }}
          onMouseOver={e => e.currentTarget.style.color = 'rgba(123,47,247,1)'}
          onMouseOut={e => e.currentTarget.style.color = 'rgba(123,47,247,0.65)'}>
          <ExternalLink size={11} />
          Reachy Mini SDK — open-source (GitHub)
        </a>
      </div>
    </div>
  )
}
