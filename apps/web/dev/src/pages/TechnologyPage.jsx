import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Cpu, Brain, Zap, BarChart2, Activity, CheckCircle2, ChevronRight, Bot } from 'lucide-react'
import { Reveal } from '../hooks/useReveal'
import { GradientOrbs } from '../components/AnimatedBackground'
import GestureModulationShowcase from '../components/GestureModulationShowcase'

const G = ({ children }) => (
  <span style={{
    background: 'linear-gradient(135deg, #D4166A 0%, #7B2FF7 50%, #00B4D8 100%)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
  }}>{children}</span>
)

const Card = ({ children, className = '' }) => (
  <div className={`rounded-2xl p-6 ${className}`} style={{
    background: 'linear-gradient(145deg, rgba(123,47,247,0.08) 0%, rgba(0,180,216,0.04) 100%)',
    border: '1px solid rgba(123,47,247,0.20)',
  }}>
    {children}
  </div>
)

/* ── Ekman Taxonomy Grid ── */
const EKMAN_MAP = [
  { emotion: 'joy',       phase1: 'happy',   color: '#00B4D8', intensity: 'high',   strategy: 'amplify_positive', tone: 'warm · celebratory',  deEsc: false, gestures: ['WAVE','CELEBRATE','EXCITED','THUMBS_UP'] },
  { emotion: 'sadness',  phase1: 'sad',     color: '#D4166A', intensity: 'high',   strategy: 'provide_support',  tone: 'gentle · empathetic',  deEsc: false, gestures: ['EMPATHY','COMFORT','HUG','SAD_ACK'] },
  { emotion: 'neutral',  phase1: 'neutral', color: '#7B2FF7', intensity: 'low',    strategy: 'engage_openly',    tone: 'calm · curious',       deEsc: false, gestures: ['NOD','LISTEN','THINK','WAVE'] },
  { emotion: 'anger',    phase1: 'neutral', color: '#FF6B35', intensity: 'medium', strategy: 'de_escalate',      tone: 'calm · measured',      deEsc: true,  gestures: ['LISTEN','NOD','NEUTRAL'] },
  { emotion: 'fear',     phase1: 'sad',     color: '#A820D8', intensity: 'medium', strategy: 'reassure',         tone: 'reassuring · steady',  deEsc: false, gestures: ['COMFORT','HUG','LISTEN'] },
  { emotion: 'disgust',  phase1: 'neutral', color: '#6B7280', intensity: 'low',    strategy: 'redirect',         tone: 'neutral · redirecting', deEsc: false, gestures: ['NOD','NEUTRAL','LISTEN'] },
  { emotion: 'contempt', phase1: 'neutral', color: '#9CA3AF', intensity: 'low',    strategy: 'de_escalate',      tone: 'calm · non-reactive',  deEsc: true,  gestures: ['LISTEN','NOD'] },
  { emotion: 'surprise', phase1: 'happy',   color: '#00C8A0', intensity: 'high',   strategy: 'match_and_explore','tone': 'excited · inquisitive', deEsc: false, gestures: ['EXCITED','WAVE','CELEBRATE'] },
]

function EkmanTaxonomyGrid() {
  const [active, setActive] = useState(null)
  return (
    <div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        {EKMAN_MAP.map(({ emotion, phase1, color, intensity, strategy, tone, deEsc, gestures }) => (
          <div
            key={emotion}
            className="rounded-xl p-4 cursor-pointer"
            style={{
              background: active === emotion ? `${color}10` : 'rgba(11,11,24,0.85)',
              border: `1px solid ${active === emotion ? color + '55' : color + '22'}`,
              transition: 'all 0.2s ease',
            }}
            onClick={() => setActive(active === emotion ? null : emotion)}
            onMouseOver={e => { if (active !== emotion) e.currentTarget.style.borderColor = `${color}44` }}
            onMouseOut={e => { if (active !== emotion) e.currentTarget.style.borderColor = `${color}22` }}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-bold capitalize" style={{ color }}>{emotion}</span>
              <div className="flex items-center gap-1.5">
                {deEsc && (
                  <span className="text-xs px-1.5 py-0.5 rounded font-semibold"
                    style={{ background: 'rgba(255,107,53,0.12)', color: '#FF6B35', border: '1px solid rgba(255,107,53,0.25)', fontSize: '9px' }}>de-esc</span>
                )}
                <span className="text-xs font-mono" style={{ color: `${color}99` }}>{intensity}</span>
              </div>
            </div>
            <div className="text-xs mb-2" style={{ color: 'rgba(255,255,255,0.32)' }}>
              Phase 1 map: <span className="font-mono" style={{ color: 'rgba(255,255,255,0.55)' }}>{phase1}</span>
            </div>
            <div className="text-xs font-mono mb-2" style={{ color: 'rgba(255,255,255,0.28)' }}>{strategy}</div>
            {active === emotion && (
              <div className="mt-3 pt-3" style={{ borderTop: `1px solid ${color}20` }}>
                <div className="text-xs mb-2" style={{ color: 'rgba(255,255,255,0.40)' }}>LLM tone: <span style={{ color }}>{tone}</span></div>
                <div className="flex flex-wrap gap-1">
                  {gestures.map(g => (
                    <span key={g} className="text-xs font-mono px-1.5 py-0.5 rounded"
                      style={{ background: `${color}10`, color, border: `1px solid ${color}22` }}>[{g}]</span>
                  ))}
                </div>
              </div>
            )}
            {active !== emotion && (
              <div className="flex flex-wrap gap-1 mt-1">
                {gestures.slice(0, 2).map(g => (
                  <span key={g} className="font-mono" style={{ color: `${color}70`, fontSize: '10px' }}>[{g}]</span>
                ))}
                {gestures.length > 2 && <span style={{ color: 'rgba(255,255,255,0.20)', fontSize: '10px' }}>+{gestures.length - 2}</span>}
              </div>
            )}
          </div>
        ))}
      </div>
      <p className="text-xs" style={{ color: 'rgba(255,255,255,0.25)' }}>
        Click any class to expand its LLM tone profile and full gesture keyword set.
        Phase 1 column shows the 3-class detection that triggers each Ekman interpretation via the PPE layer.
      </p>
    </div>
  )
}

/* ── Confidence Tier Demo ── */
const CONF_TIERS = [
  {
    label: 'Low confidence', conf: 0.47, tier: 1, tierLabel: 'Abstain', color: '#6B7280',
    ekman: 'unknown', gesture: 'NEUTRAL',
    llm: 'Let me make sure I understand. Can you share a little more about what you\'re feeling right now?',
    note: 'Abstention: system acknowledges without committing to an emotion interpretation.',
  },
  {
    label: 'Moderate confidence', conf: 0.74, tier: 3, tierLabel: 'Moderate', color: '#A820D8',
    ekman: 'sadness', gesture: 'LISTEN',
    llm: 'That sounds difficult. I\'m here with you and I hear how you\'re feeling.',
    note: 'Mid-tier: proportional gesture, empathetic but not overstated.',
  },
  {
    label: 'High confidence', conf: 0.91, tier: 5, tierLabel: 'Full', color: '#00B4D8',
    ekman: 'joy', gesture: 'CELEBRATE',
    llm: 'That\'s wonderful! I\'m genuinely excited to share this moment with you — let\'s celebrate!',
    note: 'Peak tier: full expressiveness, maximum gesture, celebratory LLM tone.',
  },
]

function ConfidenceTierDemo() {
  const [active, setActive] = useState(1)
  return (
    <div className="flex flex-col gap-6">
      {/* Column selector for mobile */}
      <div className="flex gap-2 lg:hidden">
        {CONF_TIERS.map((ct, i) => (
          <button key={i} onClick={() => setActive(i)}
            className="flex-1 py-2 px-3 rounded-xl text-xs font-bold transition-all"
            style={{
              background: active === i ? `${ct.color}18` : 'rgba(255,255,255,0.03)',
              border: `1px solid ${active === i ? ct.color + '55' : 'rgba(255,255,255,0.08)'}`,
              color: active === i ? ct.color : 'rgba(255,255,255,0.40)',
            }}>
            {ct.tierLabel}
          </button>
        ))}
      </div>

      {/* Three-column grid */}
      <div className="grid lg:grid-cols-3 gap-4">
        {CONF_TIERS.map((ct, i) => (
          <div
            key={i}
            className="rounded-2xl p-5 flex flex-col gap-4"
            style={{
              background: 'rgba(11,11,24,0.88)',
              border: `1px solid ${ct.color}30`,
              opacity: window.innerWidth < 1024 && active !== i ? 0.35 : 1,
              transition: 'opacity 0.3s, border-color 0.3s',
            }}
          >
            {/* Confidence badge */}
            <div className="flex items-center justify-between">
              <div>
                <div className="text-xs uppercase tracking-widest font-semibold mb-1" style={{ color: 'rgba(255,255,255,0.28)' }}>Confidence</div>
                <div className="text-3xl font-black font-mono" style={{ color: ct.color }}>{(ct.conf * 100).toFixed(0)}%</div>
              </div>
              <div className="text-right">
                <div className="text-xs uppercase tracking-widest font-semibold mb-1" style={{ color: 'rgba(255,255,255,0.28)' }}>Tier</div>
                <div className="text-lg font-black" style={{ color: ct.color }}>{ct.tier} — {ct.tierLabel}</div>
              </div>
            </div>

            {/* Tier bar */}
            <div className="flex gap-1.5">
              {[1,2,3,4,5].map(j => (
                <div key={j} className="flex-1 h-1.5 rounded-full transition-all duration-500" style={{
                  background: j <= ct.tier ? ct.color : 'rgba(255,255,255,0.08)',
                  boxShadow: j <= ct.tier ? `0 0 6px ${ct.color}50` : 'none',
                }} />
              ))}
            </div>

            {/* Ekman PPE */}
            <div className="rounded-xl p-3" style={{ background: 'rgba(0,0,0,0.22)', border: `1px solid ${ct.color}15` }}>
              <div className="text-xs uppercase tracking-widest mb-1" style={{ color: 'rgba(255,255,255,0.25)' }}>PPE → Ekman</div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold capitalize" style={{ color: ct.color }}>{ct.ekman}</span>
                <span className="text-xs font-mono px-2 py-0.5 rounded"
                  style={{ background: `${ct.color}10`, color: ct.color, border: `1px solid ${ct.color}20` }}>[ {ct.gesture} ]</span>
              </div>
            </div>

            {/* LLM response */}
            <div className="rounded-xl p-3 flex-1" style={{ background: 'rgba(0,0,0,0.18)', border: `1px solid ${ct.color}15` }}>
              <div className="text-xs uppercase tracking-widest mb-2" style={{ color: 'rgba(255,255,255,0.25)' }}>LLM Response</div>
              <p className="text-sm italic leading-relaxed" style={{ color: 'rgba(255,255,255,0.72)' }}>
                “{ct.llm}”
              </p>
            </div>

            {/* Note */}
            <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.30)' }}>{ct.note}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

/* Mock: Confusion Matrix */
function ConfusionMatrix() {
  const data = [
    ['', 'Pred: Happy', 'Pred: Sad', 'Pred: Neutral'],
    ['True: Happy', '94%', '3%', '3%'],
    ['True: Sad', '4%', '91%', '5%'],
    ['True: Neutral', '2%', '4%', '94%'],
  ]
  const bgMap = { '94%': 'rgba(0,180,216,0.25)', '91%': 'rgba(0,180,216,0.22)', '3%': 'rgba(212,22,106,0.10)', '4%': 'rgba(212,22,106,0.12)', '5%': 'rgba(212,22,106,0.13)', '2%': 'rgba(212,22,106,0.08)' }
  return (
    <div className="screen-mock w-full">
      <div className="screen-titlebar">
        <span className="dot-red" /><span className="dot-yellow" /><span className="dot-green" />
        <span className="text-xs font-mono ml-3" style={{ color: 'rgba(255,255,255,0.40)' }}>Evaluation Agent — Confusion Matrix</span>
      </div>
      <div className="p-5">
        <div className="grid grid-cols-4 gap-1 text-xs">
          {data.map((row, ri) => row.map((cell, ci) => (
            <div key={`${ri}-${ci}`}
              className="rounded-lg p-2 text-center font-mono"
              style={{
                background: ri === 0 || ci === 0 ? 'rgba(255,255,255,0.04)' : (bgMap[cell] || 'transparent'),
                color: ri === 0 || ci === 0 ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.85)',
                fontWeight: (ri > 0 && ci > 0 && ri === ci) ? '700' : '400',
                fontSize: ri === 0 || ci === 0 ? '10px' : '13px',
              }}
            >
              {cell}
            </div>
          )))}
        </div>
        <div className="mt-4 grid grid-cols-3 gap-3 text-xs">
          {[['Macro F1', '0.871', '#00B4D8'], ['Balanced Acc', '0.874', '#7B2FF7'], ['ECE', '0.047', '#D4166A']].map(([k, v, c]) => (
            <div key={k} className="rounded-lg p-2 text-center" style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${c}25` }}>
              <div className="font-bold font-mono" style={{ color: c }}>{v}</div>
              <div style={{ color: 'rgba(255,255,255,0.40)' }}>{k}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* Mock: Training Run */
function TrainingRun() {
  const epochs = [0.72, 0.78, 0.81, 0.83, 0.85, 0.86, 0.87, 0.871]
  return (
    <div className="screen-mock w-full">
      <div className="screen-titlebar">
        <span className="dot-red" /><span className="dot-yellow" /><span className="dot-green" />
        <span className="text-xs font-mono ml-3" style={{ color: 'rgba(255,255,255,0.40)' }}>Training Orchestrator — MLflow Run</span>
      </div>
      <div className="p-5">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.55)' }}>run_20260311_001</div>
            <div className="text-xs font-mono" style={{ color: 'rgba(123,47,247,0.70)' }}>EfficientNet-B0 · HSEmotion · 3-class</div>
          </div>
          <span className="text-xs px-2 py-0.5 rounded-full font-semibold text-green-400" style={{ background: 'rgba(74,222,128,0.12)', border: '1px solid rgba(74,222,128,0.25)' }}>
            Gate A PASS
          </span>
        </div>
        <div className="mb-3">
          <div className="text-xs mb-1.5" style={{ color: 'rgba(255,255,255,0.40)' }}>F1 Score per Epoch</div>
          <div className="flex items-end gap-1.5 h-12">
            {epochs.map((v, i) => (
              <div key={i} className="flex-1 rounded-t transition-all" style={{
                height: `${(v - 0.65) / 0.25 * 100}%`,
                background: i === epochs.length - 1 ? 'linear-gradient(180deg,#7B2FF7,#D4166A)' : 'rgba(123,47,247,0.30)',
              }} />
            ))}
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2 text-xs">
          {[['Dataset hash', 'a3f2b9...'], ['Backbone', 'Frozen → Unfrozen (epoch 5)'], ['Augmentation', 'Mixup α=0.4'], ['Precision', 'FP16 mixed']].map(([k, v]) => (
            <div key={k} className="rounded-lg p-2" style={{ background: 'rgba(13,13,32,0.80)', border: '1px solid rgba(123,47,247,0.12)' }}>
              <div style={{ color: 'rgba(255,255,255,0.35)' }}>{k}</div>
              <div className="font-mono truncate" style={{ color: 'rgba(255,255,255,0.70)' }}>{v}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function TechnologyPage() {
  return (
    <div className="pt-20">
      {/* Hero */}
      <section className="py-20 relative overflow-hidden" style={{
        background: 'radial-gradient(ellipse 60% 50% at 50% 0%, rgba(123,47,247,0.25) 0%, transparent 60%), #080818'
      }}>
        <GradientOrbs />
        <div className="relative max-w-4xl mx-auto px-6 text-center z-10">
          <Reveal>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-widest uppercase mb-6"
              style={{ border: '1px solid rgba(123,47,247,0.35)', color: 'rgba(123,47,247,0.85)', background: 'rgba(123,47,247,0.08)' }}>
              Technical Deep Dive
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <h1 className="text-5xl font-black mb-5 tracking-tight">
              <G>Full-stack embodied ML</G>
            </h1>
          </Reveal>
          <Reveal delay={0.2}>
            <p className="text-lg max-w-2xl mx-auto" style={{ color: 'rgba(255,255,255,0.55)' }}>
              Affective AI is engineered as a complete system: perception, calibration,
              orchestration, deployment, and robotic response.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Emotion Recognition Engine */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-12 items-start">
            <Reveal>
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase mb-5"
                style={{ border: '1px solid rgba(0,180,216,0.35)', color: 'rgba(0,180,216,0.85)', background: 'rgba(0,180,216,0.08)' }}>
                <Cpu size={11} /> Recognition Engine
              </div>
              <h2 className="text-3xl font-black mb-5 tracking-tight">
                EfficientNet-B0 + <G>HSEmotion</G>
              </h2>
              <p className="text-sm leading-relaxed mb-6" style={{ color: 'rgba(255,255,255,0.55)' }}>
                The core model is EfficientNet-B0 fine-tuned from HSEmotion pretrained weights
                (<code className="font-mono text-xs px-1 py-0.5 rounded" style={{ background: 'rgba(123,47,247,0.15)', color: '#00B4D8' }}>enet_b0_8_best_vgaf</code>)
                trained on VGGFace2 + AffectNet. Fine-tuned for 3-class emotion classification
                using a two-phase strategy: frozen backbone then selective unfreezing.
              </p>
              <div className="grid sm:grid-cols-2 gap-3 mb-6">
                {[
                  ['Model', 'EfficientNet-B0', '#D4166A'],
                  ['Pretrain', 'VGGFace2 + AffectNet', '#7B2FF7'],
                  ['Classes', 'happy · sad · neutral', '#00B4D8'],
                  ['Precision', 'FP16 mixed (TensorRT)', '#00C8A0'],
                  ['Augmentation', 'Mixup α=0.4', '#D4166A'],
                  ['LR Schedule', 'Cosine + warmup', '#7B2FF7'],
                ].map(([k, v, c]) => (
                  <div key={k} className="rounded-xl p-3" style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${c}20` }}>
                    <div className="text-xs mb-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>{k}</div>
                    <div className="text-sm font-semibold" style={{ color: 'rgba(255,255,255,0.80)' }}>{v}</div>
                  </div>
                ))}
              </div>
              <div className="rounded-xl p-4" style={{ background: 'rgba(13,13,32,0.80)', border: '1px solid rgba(123,47,247,0.20)' }}>
                <div className="text-xs font-semibold mb-2" style={{ color: 'rgba(255,255,255,0.50)' }}>Two-Phase Training Strategy</div>
                <div className="flex flex-col gap-2 text-xs" style={{ color: 'rgba(255,255,255,0.60)' }}>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded font-mono" style={{ background: 'rgba(212,22,106,0.15)', color: '#D4166A' }}>Phase 1</span>
                    Epochs 1–5 · Frozen backbone · Classifier head only
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded font-mono" style={{ background: 'rgba(0,180,216,0.15)', color: '#00B4D8' }}>Phase 2</span>
                    Epochs 6–20 · Unfreeze blocks.5, blocks.6, conv_head
                  </div>
                </div>
              </div>
            </div>
            </Reveal>
            <Reveal delay={0.2} direction="left">
            <div className="flex flex-col gap-4">
              <ConfusionMatrix />
              <TrainingRun />
            </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="section-divider max-w-7xl mx-auto" />

      {/* Emotional Intelligence Layer */}
      <section className="py-20 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase mb-5"
            style={{ border: '1px solid rgba(212,22,106,0.35)', color: 'rgba(212,22,106,0.85)', background: 'rgba(212,22,106,0.08)' }}>
            <Brain size={11} /> Emotional Intelligence Layer
          </div>
          <Reveal>
          <h2 className="text-3xl font-black mb-3 tracking-tight">Beyond accuracy: <G>Emotional Quotient</G></h2>
          <p className="text-sm mb-10 max-w-2xl" style={{ color: 'rgba(255,255,255,0.50)' }}>
            Calibration metrics ensure predictions are trustworthy, not just accurate.
            The EQ layer converts raw classifications into nuanced behavioral guidance.
          </p>
          </Reveal>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {[
              {
                color: '#D4166A', title: 'Degree',
                desc: 'Continuous confidence scores (0–1) measuring emotion intensity. Drives 5-tier expressiveness selection.',
                detail: 'conf > 0.60 to act · conf < 0.60 abstains',
              },
              {
                color: '#7B2FF7', title: 'PPE',
                desc: '8-class Ekman taxonomy mapping. Raw 3-class outputs map to full Ekman for nuanced interaction design.',
                detail: 'happy → joy/surprise · sad → sadness/fear',
              },
              {
                color: '#00B4D8', title: 'EQ Calibration',
                desc: 'ECE, Brier score, and MCE provide continuous reliability monitoring across all three emotion classes.',
                detail: 'ECE ≤ 0.08 · Brier ≤ 0.16 · MCE monitored',
              },
              {
                color: '#00C8A0', title: 'Gesture Modulation',
                desc: '5-tier expressiveness system maps confidence levels to gesture intensity. Low confidence → subtle response.',
                detail: 'Tier 1–5 from minimal to full celebrate',
              },
            ].map(({ color, title, desc, detail }) => (
              <Card key={title}>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-4" style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
                  <span className="text-lg font-black" style={{ color }}>{title[0]}</span>
                </div>
                <h3 className="font-bold text-sm mb-2" style={{ color: 'white' }}>{title}</h3>
                <p className="text-xs leading-relaxed mb-3" style={{ color: 'rgba(255,255,255,0.48)' }}>{desc}</p>
                <div className="text-xs font-mono px-2 py-1.5 rounded-lg" style={{ background: `${color}12`, color, border: `1px solid ${color}20` }}>
                  {detail}
                </div>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="section-divider max-w-7xl mx-auto" />

      {/* Ekman 8-Class Taxonomy */}
      <section className="py-20 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase mb-5"
            style={{ border: '1px solid rgba(168,32,216,0.35)', color: 'rgba(168,32,216,0.85)', background: 'rgba(168,32,216,0.08)' }}>
            <Brain size={11} /> PPE — Ekman Taxonomy
          </div>
          <Reveal>
          <h2 className="text-3xl font-black mb-3 tracking-tight">
            8-class <G>Ekman behavioral map</G>
          </h2>
          <p className="text-sm mb-8 max-w-2xl" style={{ color: 'rgba(255,255,255,0.50)' }}>
            Phase 1 produces 3-class scores. The PPE layer (Personality, Perception, Expression) maps
            each to a full 8-class Ekman profile — defining LLM tone, gesture keywords, de-escalation
            policy, and expressiveness intensity before any response is generated.
          </p>
          </Reveal>
          <Reveal delay={0.1}>
          <EkmanTaxonomyGrid />
          </Reveal>
        </div>
      </section>

      {/* Divider */}
      <div className="section-divider max-w-7xl mx-auto" />

      {/* Confidence Tier Demo */}
      <section className="py-20 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase mb-5"
            style={{ border: '1px solid rgba(0,180,216,0.35)', color: 'rgba(0,180,216,0.85)', background: 'rgba(0,180,216,0.08)' }}>
            <BarChart2 size={11} /> Confidence-Conditioned Response
          </div>
          <Reveal>
          <h2 className="text-3xl font-black mb-3 tracking-tight">
            Same emotion. <G>Different confidence. Different world.</G>
          </h2>
          <p className="text-sm mb-8 max-w-2xl" style={{ color: 'rgba(255,255,255,0.50)' }}>
            The EQ Degree layer continuously modulates the robot’s response based on classifier
            confidence — not just <em>what</em> was detected, but <em>how certain</em> the system is.
            Below: the same ‘sad’ detection at three different confidence levels generates
            completely different gesture tiers, Ekman class assignments, and LLM responses.
          </p>
          </Reveal>
          <Reveal delay={0.1}>
          <ConfidenceTierDemo />
          </Reveal>
        </div>
      </section>

      {/* Divider */}
      <div className="section-divider max-w-7xl mx-auto" />

      {/* Gesture Modulation Engine */}
      <section className="py-20 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase mb-5"
            style={{ border: '1px solid rgba(0,200,160,0.35)', color: 'rgba(0,200,160,0.85)', background: 'rgba(0,200,160,0.08)' }}>
            <Bot size={11} /> Gesture Modulation Engine
          </div>
          <Reveal>
          <h2 className="text-3xl font-black mb-3 tracking-tight">
            <G>5-tier expressiveness</G> — powered by gesture_modulator.py
          </h2>
          <p className="text-sm mb-8 max-w-2xl" style={{ color: 'rgba(255,255,255,0.50)' }}>
            Confidence scores drive a 5-tier expressiveness engine that maps directly to
            Reachy Mini’s physical gesture vocabulary. From a subtle NOD at 62% to a full
            CELEBRATE at 95% — every motion is proportional, deliberate, and calibrated.
          </p>
          </Reveal>
          <Reveal delay={0.1}>
          <div className="rounded-2xl p-6 sm:p-8" style={{
            background: 'linear-gradient(145deg, rgba(11,11,24,0.95) 0%, rgba(8,8,20,0.98) 100%)',
            border: '1px solid rgba(123,47,247,0.20)',
            boxShadow: '0 32px 80px rgba(0,0,0,0.45)',
          }}>
            <GestureModulationShowcase />
          </div>
          </Reveal>
        </div>
      </section>

      {/* Divider */}
      <div className="section-divider max-w-7xl mx-auto" />

      {/* Edge Deployment */}
      <section className="py-20 relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <Reveal>
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase mb-5"
                style={{ border: '1px solid rgba(0,200,160,0.35)', color: 'rgba(0,200,160,0.85)', background: 'rgba(0,200,160,0.08)' }}>
                <Zap size={11} /> Edge Deployment
              </div>
              <h2 className="text-3xl font-black mb-5 tracking-tight">
                <G>TensorRT + DeepStream</G> on Jetson Xavier NX
              </h2>
              <p className="text-sm leading-relaxed mb-6" style={{ color: 'rgba(255,255,255,0.55)' }}>
                The trained ONNX model is converted to a TensorRT FP16 engine for edge deployment.
                DeepStream SDK handles the real-time video pipeline, providing a 3× latency margin
                over the 120ms budget.
              </p>
              <div className="flex flex-col gap-3">
                {[
                  { label: 'ONNX → TensorRT (FP16)', sub: 'trtexec on Jetson Xavier NX 16GB', color: '#D4166A' },
                  { label: 'DeepStream SDK pipeline', sub: 'Real-time video stream + inference', color: '#7B2FF7' },
                  { label: 'Engine file', sub: '/opt/reachy/models/emotion_efficientnet.engine', color: '#00B4D8' },
                  { label: 'Staged rollout', sub: 'Shadow → Canary → Production', color: '#00C8A0' },
                ].map(({ label, sub, color }) => (
                  <div key={label} className="flex items-start gap-3 p-3 rounded-xl" style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${color}20` }}>
                    <div className="w-2 h-2 rounded-full mt-1.5 flex-shrink-0" style={{ background: color, boxShadow: `0 0 6px ${color}` }} />
                    <div>
                      <div className="text-sm font-semibold" style={{ color: 'rgba(255,255,255,0.80)' }}>{label}</div>
                      <div className="text-xs font-mono mt-0.5" style={{ color: 'rgba(255,255,255,0.40)' }}>{sub}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            </Reveal>
            <Reveal delay={0.15} direction="left">
            <div className="grid grid-cols-2 gap-4">
              {[
                { val: '≤ 42ms', label: 'p50 Latency', color: '#D4166A', sub: '3× safety margin' },
                { val: '25+ FPS', label: 'Throughput', color: '#7B2FF7', sub: 'Gate B requirement' },
                { val: '≤ 2.5 GB', label: 'GPU Memory', color: '#00B4D8', sub: 'Xavier NX budget' },
                { val: 'FP16', label: 'Precision', color: '#00C8A0', sub: 'TensorRT engine' },
              ].map(({ val, label, color, sub }) => (
                <div key={label} className="kpi-card">
                  <div className="text-3xl font-black font-mono mb-1" style={{ color }}>{val}</div>
                  <div className="text-xs font-semibold mb-0.5" style={{ color: 'rgba(255,255,255,0.75)' }}>{label}</div>
                  <div className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>{sub}</div>
                </div>
              ))}
              {/* Gate status */}
              <div className="col-span-2 rounded-2xl p-4" style={{ background: 'linear-gradient(135deg, rgba(123,47,247,0.10), rgba(0,180,216,0.06))', border: '1px solid rgba(123,47,247,0.22)' }}>
                <div className="text-xs font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.50)' }}>Quality Gates</div>
                <div className="flex flex-col gap-2">
                  {[
                    ['Gate A', 'F1 ≥ 0.84, Balanced Acc ≥ 0.85, ECE ≤ 0.08', true],
                    ['Gate B', 'FPS ≥ 25, Latency p50 ≤ 120ms, GPU ≤ 2.5 GB', true],
                    ['Gate C', 'User satisfaction ≥ target (canary phase)', false],
                  ].map(([gate, desc, done]) => (
                    <div key={gate} className="flex items-center gap-2 text-xs">
                      <CheckCircle2 size={13} style={{ color: done ? '#00B4D8' : 'rgba(255,255,255,0.25)', flexShrink: 0 }} />
                      <span className="font-semibold w-14" style={{ color: done ? '#00B4D8' : 'rgba(255,255,255,0.40)' }}>{gate}</span>
                      <span style={{ color: 'rgba(255,255,255,0.45)' }}>{desc}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            </Reveal>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <Reveal>
          <h3 className="text-2xl font-black mb-4 tracking-tight">
            Want the full technical specification?
          </h3>
          <div className="flex flex-wrap justify-center gap-3">
            <Link to="/architecture" className="btn-primary">View Architecture <ArrowRight size={15} /></Link>
            <Link to="/contact" className="btn-secondary">Request Technical Brief</Link>
          </div>
          </Reveal>
        </div>
      </section>
    </div>
  )
}
