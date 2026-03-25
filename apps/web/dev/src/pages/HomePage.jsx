import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, ChevronRight, Eye, Brain, Zap, Shield, Lock,
  Activity, BarChart2, Cpu, GitBranch, RefreshCw, Users,
  Heart, BookOpen, ShoppingBag, CheckCircle2,
  TrendingUp, Database, Layers, Bot, Sparkles
} from 'lucide-react'
import LogoSVG from '../components/LogoSVG'
import { Reveal, useCounter } from '../hooks/useReveal'
import { GradientOrbs, GridOverlay, ParticleField, AnimatedBorderCard } from '../components/AnimatedBackground'
import EQShowcase from '../components/EQGauge'

/* ─── Helpers ─── */
const G = ({ children, className = '' }) => (
  <span className={className} style={{
    background: 'linear-gradient(135deg, #D4166A 0%, #7B2FF7 50%, #00B4D8 100%)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
  }}>{children}</span>
)

const SectionTag = ({ children, color = 'rgba(123,47,247', icon: Icon }) => (
  <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-widest uppercase"
    style={{ border: `1px solid ${color},0.35)`, color: `${color},0.85)`, background: `${color},0.08)` }}>
    {Icon && <Icon size={12} />}
    {children}
  </div>
)

/* ─── Hero Waveform Visualization ─── */
function HeroWaveform() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    let animId, t = 0
    const dpr = window.devicePixelRatio || 1

    const resize = () => {
      canvas.width = canvas.offsetWidth * dpr
      canvas.height = canvas.offsetHeight * dpr
      ctx.scale(dpr, dpr)
    }
    resize()

    const w = () => canvas.offsetWidth
    const h = () => canvas.offsetHeight

    const draw = () => {
      t += 0.02
      ctx.clearRect(0, 0, w(), h())
      const cx = w() / 2, cy = h() / 2

      // Concentric pulse rings
      for (let i = 0; i < 4; i++) {
        const phase = (t * 0.5 + i * 0.8) % 3
        const r = phase * 80
        const alpha = Math.max(0, 0.25 - phase * 0.08)
        ctx.beginPath()
        ctx.arc(cx, cy, r, 0, Math.PI * 2)
        ctx.strokeStyle = `rgba(123,47,247,${alpha})`
        ctx.lineWidth = 1.5
        ctx.stroke()
      }

      // Waveform arcs — 3 emotion channels
      const channels = [
        { color: '0,180,216', amp: 35, freq: 2.5, phase: 0 },
        { color: '212,22,106', amp: 25, freq: 3.2, phase: 2 },
        { color: '123,47,247', amp: 30, freq: 1.8, phase: 4 },
      ]

      channels.forEach(({ color, amp, freq, phase }) => {
        ctx.beginPath()
        for (let x = 0; x < w(); x += 2) {
          const nx = (x / w()) * Math.PI * freq
          const y = cy + Math.sin(nx + t + phase) * amp * Math.sin(x / w() * Math.PI)
          x === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
        }
        ctx.strokeStyle = `rgba(${color},0.35)`
        ctx.lineWidth = 2
        ctx.stroke()

        // Glow layer
        ctx.strokeStyle = `rgba(${color},0.10)`
        ctx.lineWidth = 8
        ctx.stroke()
      })

      // Center glow dot
      const glowAlpha = 0.4 + Math.sin(t * 2) * 0.15
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 30)
      grad.addColorStop(0, `rgba(123,47,247,${glowAlpha})`)
      grad.addColorStop(1, 'transparent')
      ctx.beginPath()
      ctx.arc(cx, cy, 30, 0, Math.PI * 2)
      ctx.fillStyle = grad
      ctx.fill()

      animId = requestAnimationFrame(draw)
    }
    draw()
    window.addEventListener('resize', resize)
    return () => { cancelAnimationFrame(animId); window.removeEventListener('resize', resize) }
  }, [])

  return <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" style={{ opacity: 0.7 }} />
}

/* ─── Floating Detection Panel ─── */
function FloatingDetection() {
  const [active, setActive] = useState(0)
  const scenarios = [
    { emotions: [{ l: 'happy', c: 0.87, clr: '#00B4D8' }, { l: 'sad', c: 0.06, clr: '#D4166A' }, { l: 'neutral', c: 0.07, clr: '#7B2FF7' }], gesture: 'WAVE', latency: 38 },
    { emotions: [{ l: 'happy', c: 0.12, clr: '#00B4D8' }, { l: 'sad', c: 0.78, clr: '#D4166A' }, { l: 'neutral', c: 0.10, clr: '#7B2FF7' }], gesture: 'EMPATHY', latency: 41 },
    { emotions: [{ l: 'happy', c: 0.09, clr: '#00B4D8' }, { l: 'sad', c: 0.05, clr: '#D4166A' }, { l: 'neutral', c: 0.86, clr: '#7B2FF7' }], gesture: 'LISTEN', latency: 36 },
  ]

  useEffect(() => {
    const id = setInterval(() => setActive(p => (p + 1) % scenarios.length), 3000)
    return () => clearInterval(id)
  }, [])

  const s = scenarios[active]
  return (
    <div className="rounded-2xl p-5 w-full max-w-sm animate-shimmer" style={{
      background: 'rgba(13,13,32,0.92)', border: '1px solid rgba(123,47,247,0.30)',
      boxShadow: '0 0 60px rgba(123,47,247,0.15), 0 20px 60px rgba(0,0,0,0.4)',
      backdropFilter: 'blur(20px)',
    }}>
      <div className="flex items-center justify-between mb-5">
        <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.35)' }}>Emotion Signal</span>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-xs text-green-400 font-mono">Live</span>
        </div>
      </div>
      {s.emotions.map(({ l, c, clr }) => (
        <div key={l} className="mb-3.5">
          <div className="flex justify-between mb-1.5">
            <span className="text-xs font-semibold capitalize" style={{ color: c > 0.5 ? 'white' : 'rgba(255,255,255,0.40)' }}>{l}</span>
            <span className="text-xs font-mono font-bold" style={{ color: clr }}>{(c * 100).toFixed(0)}%</span>
          </div>
          <div className="h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.06)' }}>
            <div className="h-full rounded-full" style={{
              width: `${c * 100}%`, background: `linear-gradient(90deg, ${clr}60, ${clr})`,
              boxShadow: c > 0.5 ? `0 0 12px ${clr}50` : 'none',
              transition: 'width 0.8s cubic-bezier(0.16,1,0.3,1)',
            }} />
          </div>
        </div>
      ))}
      <div className="mt-5 pt-4 grid grid-cols-3 gap-3 text-center" style={{ borderTop: '1px solid rgba(123,47,247,0.15)' }}>
        <div>
          <div className="text-sm font-bold font-mono" style={{ color: '#00B4D8' }}>[{s.gesture}]</div>
          <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>Gesture</div>
        </div>
        <div>
          <div className="text-sm font-bold font-mono" style={{ color: '#7B2FF7' }}>{s.latency}ms</div>
          <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>Latency</div>
        </div>
        <div>
          <div className="text-sm font-bold font-mono" style={{ color: '#D4166A' }}>0.047</div>
          <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>ECE</div>
        </div>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: HERO
   ═══════════════════════════════════════════════════════════ */
function Hero() {
  return (
    <section className="relative min-h-screen flex items-center pt-20 pb-16 overflow-hidden">
      {/* Layered background */}
      <div className="absolute inset-0" style={{
        background: 'radial-gradient(ellipse 70% 55% at 50% -5%, rgba(123,47,247,0.30) 0%, transparent 55%), radial-gradient(ellipse 40% 30% at 80% 70%, rgba(0,180,216,0.12) 0%, transparent 50%), radial-gradient(ellipse 35% 30% at 15% 65%, rgba(212,22,106,0.15) 0%, transparent 50%), #080818'
      }} />
      <GridOverlay opacity={0.025} />
      <ParticleField count={35} />
      <HeroWaveform />

      <div className="relative max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-14 items-center z-10">
        {/* Left — copy */}
        <div>
          <Reveal delay={0}>
            <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full text-xs font-semibold tracking-widest uppercase mb-8"
              style={{ border: '1px solid rgba(123,47,247,0.40)', color: 'rgba(123,47,247,0.90)', background: 'rgba(123,47,247,0.08)', backdropFilter: 'blur(8px)' }}>
              <Sparkles size={13} style={{ color: '#7B2FF7' }} />
              Emotional Intelligence for Embodied AI
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <h1 className="text-5xl lg:text-7xl font-black tracking-tight leading-[1.05] mb-7">
              <span style={{ color: 'rgba(255,255,255,0.95)' }}>Robots that</span>
              <br />
              <G className="text-glow-purple">understand</G>
              <br />
              <span style={{ color: 'rgba(255,255,255,0.95)' }}>how you feel</span>
            </h1>
          </Reveal>

          <Reveal delay={0.2}>
            <p className="text-lg lg:text-xl leading-relaxed mb-10 max-w-lg" style={{ color: 'rgba(255,255,255,0.55)' }}>
              The first <strong style={{ color: 'rgba(255,255,255,0.85)' }}>privacy-first emotional intelligence platform</strong> for
              companion robotics. Real-time emotion recognition, calibrated confidence,
              and empathetic gesture response — running entirely on-premise.
            </p>
          </Reveal>

          <Reveal delay={0.3}>
            <div className="flex flex-wrap gap-3 mb-12">
              <Link to="/contact" className="btn-primary text-base px-7 py-3.5">
                Request Demo <ArrowRight size={17} />
              </Link>
              <Link to="/technology" className="btn-secondary text-base px-7 py-3.5">
                How It Works <ChevronRight size={17} />
              </Link>
              <Link to="/contact" className="btn-outline-cyan text-base px-7 py-3.5">
                Investor Inquiry
              </Link>
            </div>
          </Reveal>

          <Reveal delay={0.4}>
            <div className="flex items-center gap-8">
              {[
                { val: '< 42ms', label: 'Edge latency', color: '#D4166A' },
                { val: 'F1 0.87', label: 'Classification', color: '#7B2FF7' },
                { val: '100%', label: 'On-premise', color: '#00B4D8' },
              ].map(({ val, label, color }) => (
                <div key={label}>
                  <div className="text-2xl font-black font-mono mb-0.5" style={{ color, textShadow: `0 0 20px ${color}40` }}>{val}</div>
                  <div className="text-xs tracking-wide" style={{ color: 'rgba(255,255,255,0.35)' }}>{label}</div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>

        {/* Right — floating detection UI */}
        <Reveal delay={0.3} direction="scale">
          <div className="flex justify-center lg:justify-end">
            <div className="animate-float">
              <FloatingDetection />
            </div>
          </div>
        </Reveal>
      </div>

      {/* Scroll indicator */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex flex-col items-center gap-2 z-10">
        <span className="text-xs tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.25)' }}>Scroll</span>
        <div className="w-5 h-8 rounded-full border border-white/20 flex justify-center pt-1.5">
          <div className="w-1 h-2 rounded-full bg-white/40 animate-bounce" />
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: PRODUCT OVERVIEW — Detect · Interpret · Respond
   ═══════════════════════════════════════════════════════════ */
function ProductOverview() {
  const cards = [
    { icon: Eye, color: '#D4166A', title: 'Detect', sub: 'Perceive emotion in real time', body: 'EfficientNet-B0 fine-tuned on VGGFace2 + AffectNet classifies happy, sad, and neutral states with calibrated confidence in under 42ms on edge hardware.' },
    { icon: Brain, color: '#7B2FF7', title: 'Interpret', sub: 'Convert signals into emotional context', body: 'The EQ layer maps raw scores to confidence degrees, Ekman PPE taxonomy, and calibration metrics — deciding when to act, soften, abstain, or escalate.' },
    { icon: Zap, color: '#00B4D8', title: 'Respond', sub: 'Drive embodied empathetic action', body: 'Gesture cues and emotion-conditioned LLM prompts enable Reachy Mini to respond with appropriate physical gestures and contextual dialogue.' },
  ]
  return (
    <section className="py-28 relative">
      <GradientOrbs />
      <div className="relative max-w-7xl mx-auto px-6 z-10">
        <Reveal>
          <div className="text-center mb-16">
            <SectionTag>The Platform</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-5 tracking-tight">
              From perception to <G>empathetic response</G>
            </h2>
            <p className="text-base max-w-xl mx-auto" style={{ color: 'rgba(255,255,255,0.50)' }}>
              A complete embodied AI system: video-based emotion recognition, calibrated confidence scoring, and gesture-aware robotic response.
            </p>
          </div>
        </Reveal>
        <div className="grid md:grid-cols-3 gap-6">
          {cards.map(({ icon: Icon, color, title, sub, body }, i) => (
            <Reveal key={title} delay={i * 0.12}>
              <AnimatedBorderCard>
                <div className="flex flex-col gap-5 h-full">
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: `${color}15`, border: `1px solid ${color}35` }}>
                    <Icon size={28} style={{ color }} />
                  </div>
                  <div>
                    <h3 className="text-2xl font-black mb-1.5" style={{ color }}>{title}</h3>
                    <p className="text-sm font-semibold mb-3" style={{ color: 'rgba(255,255,255,0.75)' }}>{sub}</p>
                    <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.48)' }}>{body}</p>
                  </div>
                </div>
              </AnimatedBorderCard>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: EQ SHOWCASE — The Centerpiece
   ═══════════════════════════════════════════════════════════ */
function EQSection() {
  return (
    <section className="py-28 relative" style={{ background: 'rgba(6,6,18,0.95)' }}>
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-16">
            <SectionTag color="rgba(212,22,106" icon={Brain}>Emotional Quotient</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-5 tracking-tight leading-tight">
              The intelligence layer that makes<br />robots <G>emotionally trustworthy</G>
            </h2>
            <p className="text-base max-w-2xl mx-auto" style={{ color: 'rgba(255,255,255,0.50)' }}>
              EQ isn't a feature — it's the foundation. Calibration metrics quantify reliability.
              Confidence thresholds determine when to act. Abstention logic handles uncertainty.
              This is what separates emotion <em>detection</em> from emotion <em>understanding</em>.
            </p>
          </div>
        </Reveal>
        <Reveal delay={0.15}>
          <EQShowcase />
        </Reveal>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: DIFFERENTIATORS
   ═══════════════════════════════════════════════════════════ */
function Differentiators() {
  const items = [
    { icon: Lock, color: '#D4166A', title: 'Privacy-First by Design', body: 'No raw video leaves the local environment. Inference, storage, retention, and deployment are designed for institutions that cannot depend on cloud processing.', tag: 'On-Premise' },
    { icon: Bot, color: '#7B2FF7', title: 'Built for Embodied AI', body: 'This is not sentiment analysis in a dashboard. Emotion recognition connects directly to robotic behavior, gesture execution, and embodied interaction design.', tag: 'Robotics' },
    { icon: Activity, color: '#00B4D8', title: 'Trustworthy Predictions', body: 'Confidence is a product feature. Calibration metrics (ECE, Brier) determine when the system should act, soften, abstain, or escalate. Reliability over accuracy.', tag: 'Calibrated' },
    { icon: GitBranch, color: '#00C8A0', title: 'Auditable Agentic Pipeline', body: 'Ten cooperating agents create a reproducible improvement loop: ingest, label, promote, reconcile, train, evaluate, deploy, privacy, observe, and gesture.', tag: '10 Agents' },
  ]
  return (
    <section className="py-28 relative">
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-16">
            <SectionTag>Why Affective AI</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Four moats. <G>One mission.</G>
            </h2>
          </div>
        </Reveal>
        <div className="grid sm:grid-cols-2 gap-6">
          {items.map(({ icon: Icon, color, title, body, tag }, i) => (
            <Reveal key={title} delay={i * 0.1}>
              <AnimatedBorderCard>
                <div className="flex gap-5">
                  <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center mt-0.5" style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
                    <Icon size={24} style={{ color }} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2.5 mb-2.5">
                      <h3 className="font-bold text-lg" style={{ color: 'white' }}>{title}</h3>
                      <span className="text-xs px-2.5 py-0.5 rounded-full font-mono font-semibold" style={{ background: `${color}12`, color, border: `1px solid ${color}25` }}>{tag}</span>
                    </div>
                    <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.48)' }}>{body}</p>
                  </div>
                </div>
              </AnimatedBorderCard>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: PIPELINE — How It Works
   ═══════════════════════════════════════════════════════════ */
function HowItWorks() {
  const steps = [
    { n: '01', color: '#D4166A', title: 'Capture', desc: 'Local video interaction ingested with sha256 checksum, metadata extraction, and thumbnail generation.' },
    { n: '02', color: '#A520B8', title: 'Classify', desc: 'EfficientNet-B0 infers emotion with calibrated confidence in under 42ms on Jetson edge hardware.' },
    { n: '03', color: '#7B2FF7', title: 'Calibrate', desc: 'ECE & Brier reliability checks run. The system decides: act, soften, abstain, or escalate.' },
    { n: '04', color: '#3893E8', title: 'Decide', desc: 'PPE/EQ layer selects expressiveness tier and LLM prompt template based on emotional context.' },
    { n: '05', color: '#00B4D8', title: 'Act', desc: 'Reachy Mini executes the mapped gesture (WAVE, HUG, CELEBRATE…) with contextual dialogue.' },
  ]
  return (
    <section className="py-28" style={{ background: 'rgba(9,9,20,0.90)' }}>
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-16">
            <SectionTag icon={Zap}>Pipeline</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              From emotion signal to <G>empathetic action</G>
            </h2>
            <p className="text-sm max-w-lg mx-auto" style={{ color: 'rgba(255,255,255,0.42)' }}>
              Five stages. Under 42 milliseconds. Designed for real-world uncertainty.
            </p>
          </div>
        </Reveal>

        <div className="relative">
          {/* Animated connector */}
          <div className="hidden md:block absolute top-10 left-0 right-0 h-0.5 overflow-hidden">
            <div style={{
              height: '100%', width: '200%',
              background: 'linear-gradient(90deg, transparent, #D4166A, #7B2FF7, #00B4D8, transparent)',
              animation: 'shimmer 4s ease-in-out infinite',
            }} />
          </div>

          <div className="grid md:grid-cols-5 gap-6">
            {steps.map(({ n, color, title, desc }, i) => (
              <Reveal key={n} delay={i * 0.1}>
                <div className="flex flex-col items-center text-center gap-4">
                  <div className="relative w-20 h-20 rounded-2xl flex flex-col items-center justify-center z-10 group transition-all duration-300 hover:scale-105"
                    style={{ background: `${color}12`, border: `2px solid ${color}50`, boxShadow: `0 0 30px ${color}20` }}>
                    <span className="text-xs font-mono" style={{ color: `${color}80` }}>{n}</span>
                    <span className="text-base font-black" style={{ color }}>{title}</span>
                    {/* Pulse ring on hover */}
                    <div className="absolute inset-0 rounded-2xl animate-pulse-ring opacity-0 group-hover:opacity-100 transition-opacity"
                      style={{ border: `1px solid ${color}30` }} />
                  </div>
                  <p className="text-xs leading-relaxed max-w-[180px]" style={{ color: 'rgba(255,255,255,0.45)' }}>{desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: AGENT ARCHITECTURE
   ═══════════════════════════════════════════════════════════ */
const AGENTS = [
  { n: '01', name: 'Ingest', icon: Database, color: '#D4166A', desc: 'Video intake, sha256, metadata extraction, thumbnail generation.' },
  { n: '02', name: 'Label', icon: Eye, color: '#C21899', desc: '3-class human-in-the-loop classification and curation.' },
  { n: '03', name: 'Promote', icon: RefreshCw, color: '#A820D8', desc: 'Controlled media movement between filesystem stages.' },
  { n: '04', name: 'Reconcile', icon: GitBranch, color: '#8B2AEF', desc: 'Detect drift, orphans, and duplicates. Rebuild manifests.' },
  { n: '05', name: 'Train', icon: Cpu, color: '#7B2FF7', desc: 'EfficientNet-B0 fine-tuning, Gate A validation, ONNX export.' },
  { n: '06', name: 'Evaluate', icon: BarChart2, color: '#5040E8', desc: 'F1, ECE, Brier, confusion matrix on balanced test set.' },
  { n: '07', name: 'Deploy', icon: Layers, color: '#2A60D8', desc: 'TensorRT conversion, shadow → canary → production rollout.' },
  { n: '08', name: 'Privacy', icon: Lock, color: '#0A90C8', desc: 'TTL purges, deny-by-default policy, GDPR-compliant deletion.' },
  { n: '09', name: 'Observe', icon: Activity, color: '#00B4D8', desc: 'Cross-agent metrics, Prometheus + Grafana dashboards.' },
  { n: '10', name: 'Gesture', icon: Zap, color: '#00C8A0', desc: 'Physical gesture execution on Reachy Mini via gRPC.' },
]

function AgentArchitecture() {
  return (
    <section className="py-28 relative">
      <GradientOrbs />
      <div className="relative max-w-7xl mx-auto px-6 z-10">
        <Reveal>
          <div className="text-center mb-16">
            <SectionTag icon={GitBranch}>Agentic System</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              <G>10 cooperating agents</G>
              <br />
              <span className="text-2xl lg:text-3xl font-semibold" style={{ color: 'rgba(255,255,255,0.60)' }}>
                One auditable, reproducible loop
              </span>
            </h2>
          </div>
        </Reveal>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {AGENTS.map(({ n, name, icon: Icon, color, desc }, i) => (
            <Reveal key={n} delay={i * 0.06}>
              <div className="group relative p-5 rounded-2xl transition-all duration-300 cursor-default h-full"
                style={{ background: 'rgba(13,13,32,0.80)', border: '1px solid rgba(123,47,247,0.18)' }}
                onMouseOver={e => { e.currentTarget.style.borderColor = `${color}60`; e.currentTarget.style.transform = 'translateY(-4px)'; e.currentTarget.style.boxShadow = `0 8px 32px ${color}20` }}
                onMouseOut={e => { e.currentTarget.style.borderColor = 'rgba(123,47,247,0.18)'; e.currentTarget.style.transform = 'translateY(0)'; e.currentTarget.style.boxShadow = 'none' }}>
                <div className="flex items-center gap-2.5 mb-3">
                  <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
                    <Icon size={17} style={{ color }} />
                  </div>
                  <span className="text-xs font-mono font-bold" style={{ color: `${color}90` }}>{n}</span>
                </div>
                <h4 className="text-sm font-bold mb-2" style={{ color: 'rgba(255,255,255,0.90)' }}>{name}</h4>
                <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.38)' }}>{desc}</p>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.3}>
          <div className="mt-10 text-center">
            <Link to="/architecture" className="btn-secondary">
              Explore Full Architecture <ArrowRight size={15} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: TECHNICAL PROOF — Animated KPIs
   ═══════════════════════════════════════════════════════════ */
function KpiCard({ val, label, sub, color, suffix = '' }) {
  const numericVal = parseFloat(val.replace(/[^0-9.]/g, ''))
  const prefix = val.match(/^[^0-9.]*/)?.[0] || ''
  const [ref, count] = useCounter(numericVal * 100, 1800)

  return (
    <div ref={ref} className="kpi-card group hover:scale-[1.03] transition-transform duration-300"
      style={{ boxShadow: `0 0 0 0 ${color}00` }}
      onMouseOver={e => e.currentTarget.style.boxShadow = `0 4px 30px ${color}25`}
      onMouseOut={e => e.currentTarget.style.boxShadow = `0 0 0 0 ${color}00`}>
      <div className="text-3xl font-black mb-1.5 font-mono" style={{ color, textShadow: `0 0 20px ${color}30` }}>
        {prefix}{(count / 100).toFixed(numericVal % 1 === 0 ? 0 : numericVal < 1 ? 2 : 1)}{suffix}
      </div>
      <div className="text-xs font-semibold mb-0.5" style={{ color: 'rgba(255,255,255,0.75)' }}>{label}</div>
      <div className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>{sub}</div>
    </div>
  )
}

function TechProof() {
  return (
    <section className="py-28" style={{ background: 'rgba(9,9,20,0.90)' }}>
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-16">
            <SectionTag color="rgba(0,180,216" icon={TrendingUp}>Performance</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              <G>Validated performance</G>, not benchmarks
            </h2>
            <p className="text-sm max-w-xl mx-auto" style={{ color: 'rgba(255,255,255,0.42)' }}>
              3× latency headroom. Calibrated, not just accurate. Gate-validated before deployment.
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-14">
            <KpiCard val="≥0.84" label="Macro F1" sub="Gate A threshold" color="#D4166A" />
            <KpiCard val="≥0.85" label="Balanced Acc." sub="Gate A threshold" color="#A820D8" />
            <KpiCard val="≤42" label="p50 Latency" sub="Edge inference" color="#7B2FF7" suffix="ms" />
            <KpiCard val="25" label="Throughput" sub="Decisions/sec" color="#3893E8" suffix="+/s" />
            <KpiCard val="≤2.5" label="GPU Memory" sub="Jetson Xavier NX" color="#00B4D8" suffix=" GB" />
            <KpiCard val="99.9" label="Availability" sub="System uptime" color="#00C8A0" suffix="%" />
          </div>
        </Reveal>

        <div className="grid md:grid-cols-3 gap-6">
          {[
            { icon: TrendingUp, color: '#D4166A', title: 'Calibration', points: ['ECE ≤ 0.08 ensures reliable confidence', 'Brier score ≤ 0.16 validated per class', 'MCE monitoring for tail-case reliability', 'Abstain logic at threshold < 0.60'] },
            { icon: GitBranch, color: '#7B2FF7', title: 'Traceability', points: ['SHA-256 dataset hashing per training run', 'MLflow experiment lineage + artifacts', 'ZFS snapshots of training checkpoints', 'Alembic DB migration audit trail'] },
            { icon: Shield, color: '#00B4D8', title: 'Deployment Safety', points: ['Shadow stage: zero user exposure', 'Canary stage: limited rollout', 'Gate B: FPS ≥ 25, latency ≤ 120ms', 'Automatic rollback on Gate B failure'] },
          ].map(({ icon: Icon, color, title, points }, i) => (
            <Reveal key={title} delay={0.15 + i * 0.1}>
              <AnimatedBorderCard>
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
                    <Icon size={22} style={{ color }} />
                  </div>
                  <h3 className="font-bold text-lg" style={{ color: 'white' }}>{title}</h3>
                </div>
                <ul className="flex flex-col gap-2.5">
                  {points.map(p => (
                    <li key={p} className="flex items-start gap-2.5 text-sm" style={{ color: 'rgba(255,255,255,0.48)' }}>
                      <CheckCircle2 size={14} style={{ color, marginTop: '2px', flexShrink: 0 }} />
                      {p}
                    </li>
                  ))}
                </ul>
              </AnimatedBorderCard>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: PRIVACY & SAFETY
   ═══════════════════════════════════════════════════════════ */
function PrivacySafety() {
  const features = [
    'Local-only inference — no cloud egress ever',
    'Encrypted SSD with PostgreSQL metadata',
    'TTL-based automatic media purge (7 days)',
    'GDPR-aligned deletion with audit logs',
    'mTLS / JWT auth + RBAC access control',
    'Static LAN IPs, no public exposure',
    'Structured JSONL audit logs, rotated',
    'Fail-closed behavior on uncertainty',
  ]
  return (
    <section className="py-28 relative">
      <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
        <Reveal>
          <div>
            <SectionTag color="rgba(212,22,106" icon={Shield}>Privacy & Safety</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-5 tracking-tight leading-tight">
              <G>Privacy-first architecture</G> for emotionally sensitive AI
            </h2>
            <p className="text-base leading-relaxed mb-8" style={{ color: 'rgba(255,255,255,0.50)' }}>
              Emotion data is among the most personal information a system can process.
              Affective AI is built from the ground up with zero-cloud, zero-exposure principles.
              No surveillance. No cloud dependencies. Just local, trustworthy intelligence.
            </p>
            <Link to="/privacy" className="btn-primary">
              View Privacy Architecture <ArrowRight size={15} />
            </Link>
          </div>
        </Reveal>
        <Reveal delay={0.15}>
          <ul className="grid sm:grid-cols-2 gap-3">
            {features.map((f, i) => (
              <li key={i} className="flex items-start gap-3 p-4 rounded-xl text-sm transition-all duration-300"
                style={{ background: 'rgba(13,13,32,0.70)', border: '1px solid rgba(212,22,106,0.12)', color: 'rgba(255,255,255,0.58)' }}
                onMouseOver={e => { e.currentTarget.style.borderColor = 'rgba(212,22,106,0.35)'; e.currentTarget.style.background = 'rgba(212,22,106,0.06)' }}
                onMouseOut={e => { e.currentTarget.style.borderColor = 'rgba(212,22,106,0.12)'; e.currentTarget.style.background = 'rgba(13,13,32,0.70)' }}>
                <Lock size={14} style={{ color: '#D4166A', flexShrink: 0, marginTop: '3px' }} />
                {f}
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: USE CASES
   ═══════════════════════════════════════════════════════════ */
function UseCases() {
  const cases = [
    { icon: Heart, color: '#D4166A', title: 'Companion Robotics', desc: 'Supportive, socially aware interactions for daily companionship, elderly care, and mental health support. Privacy constraints are non-negotiable in home settings.' },
    { icon: Activity, color: '#7B2FF7', title: 'Healthcare', desc: 'Assistive interaction, therapy support, and emotional wellness monitoring with strict privacy guarantees and calibrated, auditable predictions.' },
    { icon: BookOpen, color: '#00B4D8', title: 'Education', desc: 'Adaptive engagement and emotionally aware learning environments that detect disengagement, frustration, and positive reinforcement moments.' },
    { icon: ShoppingBag, color: '#00C8A0', title: 'Customer Experience', desc: 'Hospitality, retail, and service interactions where emotion context creates meaningful differentiation without privacy liability.' },
  ]
  return (
    <section className="py-28" style={{ background: 'rgba(6,6,18,0.95)' }}>
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-16">
            <SectionTag icon={Users}>Applications</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Where <G>emotional intelligence</G> creates real value
            </h2>
            <p className="text-sm max-w-xl mx-auto" style={{ color: 'rgba(255,255,255,0.42)' }}>
              Especially valuable where emotional context matters but privacy constraints are non-negotiable.
            </p>
          </div>
        </Reveal>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {cases.map(({ icon: Icon, color, title, desc }, i) => (
            <Reveal key={title} delay={i * 0.1}>
              <AnimatedBorderCard className="h-full">
                <div className="flex flex-col gap-5 h-full">
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
                    <Icon size={28} style={{ color }} />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg mb-2" style={{ color: 'white' }}>{title}</h3>
                    <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.48)' }}>{desc}</p>
                  </div>
                  <div className="mt-auto pt-3">
                    <Link to="/use-cases" className="text-xs font-semibold inline-flex items-center gap-1.5 transition-colors"
                      style={{ color: `${color}90` }}
                      onMouseOver={e => e.currentTarget.style.color = color}
                      onMouseOut={e => e.currentTarget.style.color = `${color}90`}>
                      Learn more <ArrowRight size={12} />
                    </Link>
                  </div>
                </div>
              </AnimatedBorderCard>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: REACHYOPS AI — ENTERPRISE VERTICALS
   ═══════════════════════════════════════════════════════════ */
function EnterpriseVerticals() {
  const verticals = [
    {
      name: 'CareFlow',
      subtitle: 'Healthcare Operations',
      color: '#10B981',
      icon: Heart,
      desc: 'A governed AI operations assistant for clinics, outpatient centers, and care environments. Reduces front-desk friction, improves patient routing, and enables staff escalation — with human judgment always in the loop.',
      features: ['Arrival detection & greeting', 'Queue-aware reassurance', 'Distress escalation to staff', 'Real-time operator dashboard'],
      link: '/careflow',
    },
    {
      name: 'SecureFlow',
      subtitle: 'Cybersecurity / Secure Facilities',
      color: '#F59E0B',
      icon: Shield,
      desc: 'A governed AI incident-assistance platform for secure offices, labs, and SOC-adjacent environments. Faster anomaly detection, approval-gated response, and complete audit trails.',
      features: ['After-hours anomaly detection', 'Policy-gated escalation', 'Supervisor approval workflows', 'Incident logging & compliance'],
      link: '/secureflow',
    },
  ]

  return (
    <section className="py-28 relative">
      <GradientOrbs />
      <div className="relative max-w-7xl mx-auto px-6 z-10">
        <Reveal>
          <div className="text-center mb-16">
            <SectionTag icon={Layers}>Enterprise Editions</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-5 tracking-tight">
              One platform. <G>Two flagship verticals.</G>
            </h2>
            <p className="text-base max-w-2xl mx-auto" style={{ color: 'rgba(255,255,255,0.50)' }}>
              ReachyOps AI adapts the same governed physical-AI architecture to two high-demand markets.
              Same core stack. Different workflow logic. Different policy model. Different operator dashboard.
            </p>
          </div>
        </Reveal>

        <div className="grid lg:grid-cols-2 gap-8 mb-10">
          {verticals.map(({ name, subtitle, color, icon: Icon, desc, features, link }, i) => (
            <Reveal key={name} delay={i * 0.12}>
              <div className="rounded-2xl p-8 h-full transition-all duration-300"
                style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${color}25` }}
                onMouseOver={e => { e.currentTarget.style.borderColor = `${color}50`; e.currentTarget.style.boxShadow = `0 8px 40px ${color}15` }}
                onMouseOut={e => { e.currentTarget.style.borderColor = `${color}25`; e.currentTarget.style.boxShadow = 'none' }}>
                <div className="flex items-center gap-4 mb-5">
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: `${color}15`, border: `1px solid ${color}35` }}>
                    <Icon size={28} style={{ color }} />
                  </div>
                  <div>
                    <h3 className="text-2xl font-black" style={{ color }}>{name}</h3>
                    <span className="text-xs font-semibold tracking-wide uppercase" style={{ color: 'rgba(255,255,255,0.45)' }}>{subtitle}</span>
                  </div>
                </div>
                <p className="text-sm leading-relaxed mb-5" style={{ color: 'rgba(255,255,255,0.55)' }}>{desc}</p>
                <ul className="flex flex-col gap-2 mb-6">
                  {features.map(f => (
                    <li key={f} className="flex items-center gap-2.5 text-sm" style={{ color: 'rgba(255,255,255,0.60)' }}>
                      <CheckCircle2 size={14} style={{ color, flexShrink: 0 }} />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link to={link} className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white text-sm transition-all duration-200"
                  style={{ background: `linear-gradient(135deg, ${color} 0%, ${color}CC 100%)`, boxShadow: `0 4px 20px ${color}30` }}>
                  Explore {name} <ArrowRight size={15} />
                </Link>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.25}>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/platform" className="btn-secondary text-sm px-6 py-3">
              Platform Architecture <ArrowRight size={15} />
            </Link>
            <Link to="/dashboard" className="btn-secondary text-sm px-6 py-3">
              Live Dashboard Demo <ArrowRight size={15} />
            </Link>
            <Link to="/governance" className="btn-secondary text-sm px-6 py-3">
              Governance Matrix <ArrowRight size={15} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   SECTION: FINAL CTA
   ═══════════════════════════════════════════════════════════ */
function CTASection() {
  return (
    <section className="py-32 relative overflow-hidden">
      <div className="absolute inset-0" style={{
        background: 'radial-gradient(ellipse 80% 70% at 50% 50%, rgba(123,47,247,0.20) 0%, transparent 60%), radial-gradient(ellipse 50% 40% at 30% 80%, rgba(212,22,106,0.12) 0%, transparent 50%)'
      }} />
      <ParticleField count={20} />

      <div className="relative max-w-3xl mx-auto px-6 text-center z-10">
        <Reveal>
          <div className="mb-6">
            <LogoSVG size={70} showText={false} />
          </div>
        </Reveal>
        <Reveal delay={0.1}>
          <h2 className="text-5xl lg:text-6xl font-black tracking-tight mb-7 leading-tight">
            Governed physical AI
            <br />
            for <G>enterprise operations</G>
          </h2>
        </Reveal>
        <Reveal delay={0.2}>
          <p className="text-lg mb-12 max-w-xl mx-auto" style={{ color: 'rgba(255,255,255,0.55)' }}>
            ReachyOps AI combines edge perception, agentic orchestration, embodied interaction,
            and privacy-first governance into a platform that adapts to any vertical.
          </p>
        </Reveal>
        <Reveal delay={0.3}>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/contact" className="btn-primary text-base px-9 py-4">
              Request a Demo <ArrowRight size={18} />
            </Link>
            <Link to="/platform" className="btn-secondary text-base px-9 py-4">
              Platform Architecture
            </Link>
            <Link to="/dashboard" className="btn-outline-cyan text-base px-9 py-4">
              Live Dashboard
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ═══════════════════════════════════════════════════════════
   PAGE EXPORT
   ═══════════════════════════════════════════════════════════ */
export default function HomePage() {
  return (
    <>
      <Hero />
      <ProductOverview />
      <EQSection />
      <Differentiators />
      <HowItWorks />
      <AgentArchitecture />
      <TechProof />
      <PrivacySafety />
      <UseCases />
      <EnterpriseVerticals />
      <CTASection />
    </>
  )
}
