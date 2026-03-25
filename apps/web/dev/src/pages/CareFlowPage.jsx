import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, Heart, Users, Clock, Bell, Shield, Activity,
  CheckCircle2, BarChart2, Eye, Brain, Zap, MessageCircle,
  AlertTriangle, TrendingUp, Cpu, GitBranch, Layers
} from 'lucide-react'
import { Reveal } from '../hooks/useReveal'
import { GradientOrbs, GridOverlay, ParticleField, AnimatedBorderCard } from '../components/AnimatedBackground'

const CARE = '#10B981'
const CARE_DIM = 'rgba(16,185,129'

const G = ({ children, className = '' }) => (
  <span className={className} style={{
    background: `linear-gradient(135deg, ${CARE} 0%, #00B4D8 100%)`,
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
  }}>{children}</span>
)

const SectionTag = ({ children, icon: Icon }) => (
  <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-widest uppercase"
    style={{ border: `1px solid ${CARE_DIM},0.35)`, color: `${CARE_DIM},0.85)`, background: `${CARE_DIM},0.08)` }}>
    {Icon && <Icon size={12} />}
    {children}
  </div>
)

/* ─── Hero ─── */
function Hero() {
  return (
    <section className="relative min-h-[85vh] flex items-center pt-24 pb-20 overflow-hidden">
      <div className="absolute inset-0" style={{
        background: `radial-gradient(ellipse 70% 55% at 50% -5%, ${CARE_DIM},0.25) 0%, transparent 55%), radial-gradient(ellipse 40% 30% at 80% 70%, rgba(0,180,216,0.12) 0%, transparent 50%), #080818`
      }} />
      <GridOverlay opacity={0.02} />
      <ParticleField count={25} />

      <div className="relative max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-14 items-center z-10">
        <div>
          <Reveal delay={0}>
            <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full text-xs font-semibold tracking-widest uppercase mb-6"
              style={{ border: `1px solid ${CARE_DIM},0.40)`, color: `${CARE_DIM},0.90)`, background: `${CARE_DIM},0.08)` }}>
              <Heart size={13} style={{ color: CARE }} />
              ReachyOps CareFlow
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <h1 className="text-5xl lg:text-6xl font-black tracking-tight leading-[1.08] mb-6">
              <span style={{ color: 'rgba(255,255,255,0.95)' }}>Healthcare AI that</span><br />
              <G>respects boundaries</G><br />
              <span style={{ color: 'rgba(255,255,255,0.95)' }}>and reduces friction</span>
            </h1>
          </Reveal>

          <Reveal delay={0.2}>
            <p className="text-lg leading-relaxed mb-8 max-w-lg" style={{ color: 'rgba(255,255,255,0.55)' }}>
              A governed AI operations assistant for clinics, outpatient centers, and care environments.
              Improves front-desk throughput, patient routing, and staff escalation — with
              <strong style={{ color: 'rgba(255,255,255,0.85)' }}> human judgment always in the loop</strong>.
            </p>
          </Reveal>

          <Reveal delay={0.3}>
            <div className="flex flex-wrap gap-3 mb-10">
              <Link to="/dashboard" className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-white text-base transition-all duration-200"
                style={{ background: `linear-gradient(135deg, ${CARE} 0%, #059669 100%)`, boxShadow: `0 4px 20px ${CARE_DIM},0.35)` }}>
                View Live Demo <ArrowRight size={17} />
              </Link>
              <Link to="/platform" className="btn-secondary text-base px-7 py-3.5">
                Platform Architecture
              </Link>
            </div>
          </Reveal>

          <Reveal delay={0.4}>
            <div className="flex items-center gap-8">
              {[
                { val: '< 3s', label: 'Acknowledgment', color: CARE },
                { val: '87%', label: 'Queue visibility', color: '#00B4D8' },
                { val: '100%', label: 'Audit coverage', color: '#7B2FF7' },
              ].map(({ val, label, color }) => (
                <div key={label}>
                  <div className="text-2xl font-black font-mono mb-0.5" style={{ color, textShadow: `0 0 20px ${color}40` }}>{val}</div>
                  <div className="text-xs tracking-wide" style={{ color: 'rgba(255,255,255,0.35)' }}>{label}</div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>

        {/* Right — Simulated CareFlow Panel */}
        <Reveal delay={0.3} direction="scale">
          <div className="flex justify-center lg:justify-end">
            <CareFlowPanel />
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ─── Simulated CareFlow Panel ─── */
function CareFlowPanel() {
  const [step, setStep] = useState(0)
  const steps = [
    { status: 'Arrival Detected', detail: 'Patient entering lobby zone', icon: Eye, severity: 'info' },
    { status: 'Event Created', detail: 'arrival_evt_0847 → Postgres', icon: Activity, severity: 'info' },
    { status: 'Ricci Greeting', detail: '"Welcome. Front desk notified."', icon: MessageCircle, severity: 'success' },
    { status: 'Staff Notified', detail: 'Nurse station alert dispatched', icon: Bell, severity: 'success' },
    { status: 'Dashboard Updated', detail: 'Queue position: #3 — est. 8 min', icon: BarChart2, severity: 'info' },
  ]

  useEffect(() => {
    const id = setInterval(() => setStep(p => (p + 1) % steps.length), 2500)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="rounded-2xl p-5 w-full max-w-sm animate-shimmer" style={{
      background: 'rgba(13,13,32,0.92)', border: `1px solid ${CARE_DIM},0.30)`,
      boxShadow: `0 0 60px ${CARE_DIM},0.15), 0 20px 60px rgba(0,0,0,0.4)`,
      backdropFilter: 'blur(20px)',
    }}>
      <div className="flex items-center justify-between mb-5">
        <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.35)' }}>CareFlow Event Stream</span>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: CARE }} />
          <span className="text-xs font-mono" style={{ color: CARE }}>Live</span>
        </div>
      </div>

      {steps.map(({ status, detail, icon: Icon, severity }, i) => {
        const isActive = i === step
        const isPast = i < step
        return (
          <div key={i} className="flex items-start gap-3 mb-3 transition-all duration-500" style={{
            opacity: isActive ? 1 : isPast ? 0.5 : 0.25,
            transform: isActive ? 'translateX(4px)' : 'translateX(0)',
          }}>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5" style={{
              background: isActive ? `${CARE_DIM},0.18)` : 'rgba(255,255,255,0.04)',
              border: `1px solid ${isActive ? `${CARE_DIM},0.40)` : 'rgba(255,255,255,0.08)'}`,
            }}>
              <Icon size={14} style={{ color: isActive ? CARE : 'rgba(255,255,255,0.3)' }} />
            </div>
            <div>
              <div className="text-xs font-bold" style={{ color: isActive ? 'white' : 'rgba(255,255,255,0.4)' }}>{status}</div>
              <div className="text-xs" style={{ color: isActive ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.25)' }}>{detail}</div>
            </div>
            {isActive && (
              <div className="ml-auto flex-shrink-0">
                <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: severity === 'success' ? CARE : '#00B4D8' }} />
              </div>
            )}
          </div>
        )
      })}

      <div className="mt-4 pt-3 grid grid-cols-3 gap-3 text-center" style={{ borderTop: `1px solid ${CARE_DIM},0.15)` }}>
        <div>
          <div className="text-sm font-bold font-mono" style={{ color: CARE }}>2.1s</div>
          <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>Ack Time</div>
        </div>
        <div>
          <div className="text-sm font-bold font-mono" style={{ color: '#00B4D8' }}>3</div>
          <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>In Queue</div>
        </div>
        <div>
          <div className="text-sm font-bold font-mono" style={{ color: '#7B2FF7' }}>0</div>
          <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>Escalations</div>
        </div>
      </div>
    </div>
  )
}

/* ─── Problem Statement ─── */
function ProblemStatement() {
  const problems = [
    { icon: Clock, title: 'Front-desk friction', desc: 'Patients wait without acknowledgment. Staff are overwhelmed with simultaneous arrivals and routing questions.' },
    { icon: Users, title: 'Poor queue awareness', desc: 'No real-time visibility into wait states. Patients grow frustrated. Staff cannot prioritize.' },
    { icon: AlertTriangle, title: 'Delayed escalation', desc: 'Distressed visitors go unnoticed. Human handoff happens too late or not at all.' },
    { icon: MessageCircle, title: 'Communication gaps', desc: 'Wayfinding, intake questions, and status updates require constant staff attention.' },
  ]

  return (
    <section className="py-24 relative">
      <GradientOrbs />
      <div className="relative max-w-7xl mx-auto px-6 z-10">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={AlertTriangle}>The Problem</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Healthcare leaders don't just need <G>"AI"</G>
            </h2>
            <p className="text-base max-w-2xl mx-auto" style={{ color: 'rgba(255,255,255,0.50)' }}>
              Deloitte's 2026 healthcare outlook frames agentic AI as a way to embed intelligence into
              core operations — connecting consumer, clinical, back-office, and payment journeys.
              CareFlow addresses the operational gap.
            </p>
          </div>
        </Reveal>
        <div className="grid sm:grid-cols-2 gap-6">
          {problems.map(({ icon: Icon, title, desc }, i) => (
            <Reveal key={title} delay={i * 0.1}>
              <AnimatedBorderCard>
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: `${CARE_DIM},0.12)`, border: `1px solid ${CARE_DIM},0.25)` }}>
                    <Icon size={22} style={{ color: CARE }} />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg mb-2" style={{ color: 'white' }}>{title}</h3>
                    <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.48)' }}>{desc}</p>
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

/* ─── Role of Ricci ─── */
function RicciRole() {
  const capabilities = [
    'Greets arriving patients and visitors',
    'Acknowledges arrival and explains wait-state',
    'Provides wayfinding and next-step guidance',
    'Asks low-risk clarifying intake questions',
    'Offers reassurance during extended waits',
    'Escalates to staff when emotion, delay, or ambiguity is high',
  ]
  const boundaries = [
    'Does not diagnose or provide medical advice',
    'Does not access sensitive patient records',
    'Does not make triage decisions independently',
    'Does not override staff instructions',
  ]

  return (
    <section className="py-24" style={{ background: 'rgba(6,6,18,0.95)' }}>
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={Heart}>Embodied Interaction</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Ricci is <G>useful without being dangerous</G>
            </h2>
            <p className="text-base max-w-xl mx-auto" style={{ color: 'rgba(255,255,255,0.50)' }}>
              The robot handles the front-of-house interaction layer. It does not replace clinical judgment.
              It reduces friction and gives staff back their time.
            </p>
          </div>
        </Reveal>

        <div className="grid md:grid-cols-2 gap-8">
          <Reveal delay={0.1}>
            <div className="rounded-2xl p-8" style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${CARE_DIM},0.20)` }}>
              <h3 className="text-xl font-bold mb-5 flex items-center gap-3" style={{ color: CARE }}>
                <CheckCircle2 size={22} /> What Ricci Does
              </h3>
              <ul className="flex flex-col gap-3">
                {capabilities.map(c => (
                  <li key={c} className="flex items-start gap-3 text-sm" style={{ color: 'rgba(255,255,255,0.65)' }}>
                    <CheckCircle2 size={14} style={{ color: CARE, marginTop: '2px', flexShrink: 0 }} />
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>

          <Reveal delay={0.2}>
            <div className="rounded-2xl p-8" style={{ background: 'rgba(13,13,32,0.80)', border: '1px solid rgba(212,22,106,0.20)' }}>
              <h3 className="text-xl font-bold mb-5 flex items-center gap-3" style={{ color: '#D4166A' }}>
                <Shield size={22} /> Bounded Autonomy
              </h3>
              <ul className="flex flex-col gap-3">
                {boundaries.map(b => (
                  <li key={b} className="flex items-start gap-3 text-sm" style={{ color: 'rgba(255,255,255,0.65)' }}>
                    <Shield size={14} style={{ color: '#D4166A', marginTop: '2px', flexShrink: 0 }} />
                    {b}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}

/* ─── Use Cases ─── */
function UseCases() {
  const cases = [
    {
      letter: 'A', title: 'Arrival & Acknowledgment', color: CARE,
      steps: [
        'Camera detects patient/visitor arrival in lobby zone',
        'Event sent to backend via FastAPI gateway',
        'Ricci says: "Welcome. I\'ve notified the front desk."',
        'Operator dashboard updates with new arrival',
        'Staff notification dispatched to nurse station',
      ]
    },
    {
      letter: 'B', title: 'Wait-Time Reassurance', color: '#00B4D8',
      steps: [
        'Patient wait exceeds configured threshold (e.g. 12 min)',
        'Backend checks queue state and estimated time',
        'Ricci provides calm status update to patient',
        'If threshold exceeded further, escalation to staff',
        'All interactions logged with timestamps',
      ]
    },
    {
      letter: 'C', title: 'Distress Escalation', color: '#7B2FF7',
      steps: [
        'Perception layer detects frustration/distress signals',
        'Backend marks interaction as high-touch',
        'Ricci adjusts tone: "Let me get someone for you."',
        'Human attendant notified with context summary',
        'Incident logged for quality review',
      ]
    },
  ]

  return (
    <section className="py-24 relative">
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={Zap}>MVP Use Cases</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Three scenarios that <G>sell themselves</G>
            </h2>
          </div>
        </Reveal>

        <div className="grid lg:grid-cols-3 gap-6">
          {cases.map(({ letter, title, color, steps }, i) => (
            <Reveal key={letter} delay={i * 0.12}>
              <div className="rounded-2xl p-6 h-full" style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${color}30` }}>
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center font-black text-lg" style={{ background: `${color}15`, border: `1px solid ${color}40`, color }}>
                    {letter}
                  </div>
                  <h3 className="font-bold text-lg" style={{ color: 'white' }}>{title}</h3>
                </div>
                <ol className="flex flex-col gap-3">
                  {steps.map((s, j) => (
                    <li key={j} className="flex items-start gap-3 text-sm" style={{ color: 'rgba(255,255,255,0.55)' }}>
                      <span className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold mt-0.5"
                        style={{ background: `${color}15`, color, border: `1px solid ${color}30` }}>
                        {j + 1}
                      </span>
                      {s}
                    </li>
                  ))}
                </ol>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── Architecture Overview ─── */
function ArchOverview() {
  const layers = [
    { icon: Eye, label: 'Jetson Edge', desc: 'Camera detection, EfficientNet-B0 inference, presence/arrival events', color: CARE },
    { icon: Cpu, label: 'Control Plane', desc: 'FastAPI gateway, policy engine, n8n workflow orchestration', color: '#00B4D8' },
    { icon: Layers, label: 'Data Layer', desc: 'PostgreSQL event ledger, audit logs, queue state, MLflow tracking', color: '#7B2FF7' },
    { icon: MessageCircle, label: 'Ricci Layer', desc: 'Greeting, reassurance, wayfinding, escalation via gesture + dialogue', color: '#D4166A' },
    { icon: BarChart2, label: 'Operator Dashboard', desc: 'Real-time queue view, arrival feed, escalation alerts, KPI metrics', color: '#F59E0B' },
  ]

  return (
    <section className="py-24" style={{ background: 'rgba(9,9,20,0.90)' }}>
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={GitBranch}>System Architecture</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Five layers. <G>One governed pipeline.</G>
            </h2>
            <p className="text-sm max-w-lg mx-auto" style={{ color: 'rgba(255,255,255,0.42)' }}>
              Same core architecture as ReachyOps AI, tuned for healthcare workflow logic and patient-facing interaction.
            </p>
          </div>
        </Reveal>

        <div className="flex flex-col gap-4">
          {layers.map(({ icon: Icon, label, desc, color }, i) => (
            <Reveal key={label} delay={i * 0.08}>
              <div className="flex items-center gap-5 p-5 rounded-2xl transition-all duration-300"
                style={{ background: 'rgba(13,13,32,0.70)', border: `1px solid ${color}20` }}
                onMouseOver={e => { e.currentTarget.style.borderColor = `${color}50`; e.currentTarget.style.transform = 'translateX(8px)' }}
                onMouseOut={e => { e.currentTarget.style.borderColor = `${color}20`; e.currentTarget.style.transform = 'translateX(0)' }}>
                <div className="w-12 h-12 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
                  <Icon size={22} style={{ color }} />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-base mb-1" style={{ color: 'white' }}>{label}</h3>
                  <p className="text-sm" style={{ color: 'rgba(255,255,255,0.48)' }}>{desc}</p>
                </div>
                <div className="hidden sm:flex items-center gap-2">
                  <span className="text-xs font-mono px-3 py-1 rounded-full" style={{ background: `${color}10`, color, border: `1px solid ${color}25` }}>
                    Layer {i + 1}
                  </span>
                </div>
              </div>
            </Reveal>
          ))}
        </div>

        <Reveal delay={0.4}>
          <div className="mt-8 text-center">
            <Link to="/platform" className="btn-secondary">
              Full Platform Architecture <ArrowRight size={15} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ─── KPIs ─── */
function KPIs() {
  const kpis = [
    { val: '< 3s', label: 'Acknowledgment Time', desc: 'Time from arrival detection to Ricci greeting', color: CARE },
    { val: '87%', label: 'Queue Visibility', desc: 'Staff awareness of current patient count', color: '#00B4D8' },
    { val: '< 45s', label: 'Escalation Response', desc: 'Distress detection to human handoff', color: '#7B2FF7' },
    { val: '4.2/5', label: 'Reassurance Score', desc: 'Patient-reported interaction quality', color: '#D4166A' },
    { val: '-38%', label: 'Staff Interruptions', desc: 'Reduction in routine front-desk queries', color: '#F59E0B' },
    { val: '100%', label: 'Audit Coverage', desc: 'All interactions logged with full context', color: CARE },
  ]

  return (
    <section className="py-24 relative">
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={TrendingUp}>Performance KPIs</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Metrics that matter to <G>operations leaders</G>
            </h2>
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            {kpis.map(({ val, label, desc, color }) => (
              <div key={label} className="kpi-card group hover:scale-[1.03] transition-transform duration-300"
                style={{ borderColor: `${color}22` }}
                onMouseOver={e => e.currentTarget.style.boxShadow = `0 4px 30px ${color}25`}
                onMouseOut={e => e.currentTarget.style.boxShadow = 'none'}>
                <div className="text-2xl font-black mb-1.5 font-mono" style={{ color, textShadow: `0 0 20px ${color}30` }}>{val}</div>
                <div className="text-xs font-semibold mb-0.5" style={{ color: 'rgba(255,255,255,0.75)' }}>{label}</div>
                <div className="text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>{desc}</div>
              </div>
            ))}
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ─── Skills Demonstrated ─── */
function SkillsDemo() {
  const skills = [
    { icon: Brain, title: 'Agentic Workflow Design', desc: 'Multi-agent orchestration with policy-gated decisions and human approval loops.' },
    { icon: Eye, title: 'Edge Computer Vision', desc: 'Real-time detection on Jetson Xavier NX with TensorRT-optimized EfficientNet-B0.' },
    { icon: Heart, title: 'Embodied AI UX', desc: 'Physical robot interaction designed for comfort, trust, and appropriate escalation.' },
    { icon: Activity, title: 'Event-Driven Operations', desc: 'Structured events, queue state management, and real-time dashboard telemetry.' },
    { icon: Users, title: 'Human-in-the-Loop', desc: 'Staff escalation, approval gates, and operator override at every critical junction.' },
    { icon: Shield, title: 'Enterprise-Safe Architecture', desc: 'GDPR-aligned, audit-complete, privacy-first with bounded autonomy.' },
  ]

  return (
    <section className="py-24" style={{ background: 'rgba(6,6,18,0.95)' }}>
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={Layers}>Skills Demonstrated</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              What CareFlow proves <G>you can build</G>
            </h2>
          </div>
        </Reveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {skills.map(({ icon: Icon, title, desc }, i) => (
            <Reveal key={title} delay={i * 0.08}>
              <AnimatedBorderCard>
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${CARE_DIM},0.12)`, border: `1px solid ${CARE_DIM},0.25)` }}>
                    <Icon size={20} style={{ color: CARE }} />
                  </div>
                  <div>
                    <h3 className="font-bold text-base mb-1.5" style={{ color: 'white' }}>{title}</h3>
                    <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.48)' }}>{desc}</p>
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

/* ─── Buyer Story ─── */
function BuyerStory() {
  const buyers = [
    'Clinic administrators',
    'Patient access leaders',
    'Hospital operations teams',
    'Digital transformation groups',
    'MedTech solution teams',
  ]

  return (
    <section className="py-24 relative">
      <div className="max-w-5xl mx-auto px-6 text-center">
        <Reveal>
          <SectionTag icon={TrendingUp}>Market Fit</SectionTag>
          <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-6 tracking-tight">
            Built for the people who <G>buy AI in healthcare</G>
          </h2>
          <p className="text-base max-w-2xl mx-auto mb-10" style={{ color: 'rgba(255,255,255,0.50)' }}>
            CareFlow solves problems that operations leaders already have budget for.
            It demonstrates healthcare workflow design, bounded autonomy, and change-management-friendly deployment.
          </p>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="flex flex-wrap justify-center gap-3 mb-12">
            {buyers.map(b => (
              <span key={b} className="px-5 py-2.5 rounded-full text-sm font-medium" style={{
                background: `${CARE_DIM},0.08)`, border: `1px solid ${CARE_DIM},0.25)`, color: CARE,
              }}>
                {b}
              </span>
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/dashboard" className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-white text-base transition-all duration-200"
              style={{ background: `linear-gradient(135deg, ${CARE} 0%, #059669 100%)`, boxShadow: `0 4px 20px ${CARE_DIM},0.35)` }}>
              View Live Demo <ArrowRight size={17} />
            </Link>
            <Link to="/secureflow" className="btn-secondary text-base px-7 py-3.5">
              See SecureFlow Edition <ArrowRight size={15} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ═══ PAGE ═══ */
export default function CareFlowPage() {
  return (
    <>
      <Hero />
      <ProblemStatement />
      <RicciRole />
      <UseCases />
      <ArchOverview />
      <KPIs />
      <SkillsDemo />
      <BuyerStory />
    </>
  )
}
