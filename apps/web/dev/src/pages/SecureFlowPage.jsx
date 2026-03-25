import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, Shield, Lock, AlertTriangle, Eye, Brain, Zap,
  CheckCircle2, BarChart2, Activity, Bell, Cpu, GitBranch,
  Layers, FileText, UserCheck, Radio, Fingerprint
} from 'lucide-react'
import { Reveal } from '../hooks/useReveal'
import { GradientOrbs, GridOverlay, ParticleField, AnimatedBorderCard } from '../components/AnimatedBackground'

const SEC = '#F59E0B'
const SEC_DIM = 'rgba(245,158,11'

const G = ({ children, className = '' }) => (
  <span className={className} style={{
    background: `linear-gradient(135deg, ${SEC} 0%, #EF4444 100%)`,
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
  }}>{children}</span>
)

const SectionTag = ({ children, icon: Icon }) => (
  <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-widest uppercase"
    style={{ border: `1px solid ${SEC_DIM},0.35)`, color: `${SEC_DIM},0.85)`, background: `${SEC_DIM},0.08)` }}>
    {Icon && <Icon size={12} />}
    {children}
  </div>
)

/* ─── Hero ─── */
function Hero() {
  return (
    <section className="relative min-h-[85vh] flex items-center pt-24 pb-20 overflow-hidden">
      <div className="absolute inset-0" style={{
        background: `radial-gradient(ellipse 70% 55% at 50% -5%, ${SEC_DIM},0.20) 0%, transparent 55%), radial-gradient(ellipse 40% 30% at 20% 70%, rgba(239,68,68,0.12) 0%, transparent 50%), #080818`
      }} />
      <GridOverlay opacity={0.02} />
      <ParticleField count={25} />

      <div className="relative max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-14 items-center z-10">
        <div>
          <Reveal delay={0}>
            <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full text-xs font-semibold tracking-widest uppercase mb-6"
              style={{ border: `1px solid ${SEC_DIM},0.40)`, color: `${SEC_DIM},0.90)`, background: `${SEC_DIM},0.08)` }}>
              <Shield size={13} style={{ color: SEC }} />
              ReachyOps SecureFlow
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <h1 className="text-5xl lg:text-6xl font-black tracking-tight leading-[1.08] mb-6">
              <span style={{ color: 'rgba(255,255,255,0.95)' }}>Security AI that</span><br />
              <G>governs itself</G><br />
              <span style={{ color: 'rgba(255,255,255,0.95)' }}>before it acts</span>
            </h1>
          </Reveal>

          <Reveal delay={0.2}>
            <p className="text-lg leading-relaxed mb-8 max-w-lg" style={{ color: 'rgba(255,255,255,0.55)' }}>
              A governed AI incident-assistance platform for secure offices, labs, and SOC-adjacent environments.
              Faster anomaly detection, cleaner escalation, and
              <strong style={{ color: 'rgba(255,255,255,0.85)' }}> approval-gated response — every time</strong>.
            </p>
          </Reveal>

          <Reveal delay={0.3}>
            <div className="flex flex-wrap gap-3 mb-10">
              <Link to="/dashboard" className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-white text-base transition-all duration-200"
                style={{ background: `linear-gradient(135deg, ${SEC} 0%, #D97706 100%)`, boxShadow: `0 4px 20px ${SEC_DIM},0.35)` }}>
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
                { val: '< 2s', label: 'Detection time', color: SEC },
                { val: '0', label: 'Unlogged actions', color: '#EF4444' },
                { val: '100%', label: 'Approval-gated', color: '#7B2FF7' },
              ].map(({ val, label, color }) => (
                <div key={label}>
                  <div className="text-2xl font-black font-mono mb-0.5" style={{ color, textShadow: `0 0 20px ${color}40` }}>{val}</div>
                  <div className="text-xs tracking-wide" style={{ color: 'rgba(255,255,255,0.35)' }}>{label}</div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>

        <Reveal delay={0.3} direction="scale">
          <div className="flex justify-center lg:justify-end">
            <SecureFlowPanel />
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ─── Simulated SecureFlow Panel ─── */
function SecureFlowPanel() {
  const [step, setStep] = useState(0)
  const events = [
    { status: 'Anomaly Detected', detail: 'After-hours presence — Lab B entrance', icon: AlertTriangle, severity: 'warning' },
    { status: 'Policy Check', detail: 'Time-of-day rule triggered — approval required', icon: Shield, severity: 'warning' },
    { status: 'Ricci Response', detail: '"This area is currently closed."', icon: Radio, severity: 'info' },
    { status: 'Supervisor Notified', detail: 'SOC alert dispatched — pending review', icon: Bell, severity: 'warning' },
    { status: 'Incident Logged', detail: 'INC-2847 created — full audit trail', icon: FileText, severity: 'success' },
  ]

  useEffect(() => {
    const id = setInterval(() => setStep(p => (p + 1) % events.length), 2500)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="rounded-2xl p-5 w-full max-w-sm animate-shimmer" style={{
      background: 'rgba(13,13,32,0.92)', border: `1px solid ${SEC_DIM},0.30)`,
      boxShadow: `0 0 60px ${SEC_DIM},0.12), 0 20px 60px rgba(0,0,0,0.4)`,
      backdropFilter: 'blur(20px)',
    }}>
      <div className="flex items-center justify-between mb-5">
        <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.35)' }}>SecureFlow Incident</span>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: SEC }} />
          <span className="text-xs font-mono" style={{ color: SEC }}>Active</span>
        </div>
      </div>

      {events.map(({ status, detail, icon: Icon, severity }, i) => {
        const isActive = i === step
        const isPast = i < step
        const sevColor = severity === 'warning' ? SEC : severity === 'success' ? '#10B981' : '#00B4D8'
        return (
          <div key={i} className="flex items-start gap-3 mb-3 transition-all duration-500" style={{
            opacity: isActive ? 1 : isPast ? 0.5 : 0.25,
            transform: isActive ? 'translateX(4px)' : 'translateX(0)',
          }}>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5" style={{
              background: isActive ? `${sevColor}22` : 'rgba(255,255,255,0.04)',
              border: `1px solid ${isActive ? `${sevColor}55` : 'rgba(255,255,255,0.08)'}`,
            }}>
              <Icon size={14} style={{ color: isActive ? sevColor : 'rgba(255,255,255,0.3)' }} />
            </div>
            <div>
              <div className="text-xs font-bold" style={{ color: isActive ? 'white' : 'rgba(255,255,255,0.4)' }}>{status}</div>
              <div className="text-xs" style={{ color: isActive ? 'rgba(255,255,255,0.6)' : 'rgba(255,255,255,0.25)' }}>{detail}</div>
            </div>
            {isActive && (
              <div className="ml-auto flex-shrink-0">
                <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: sevColor }} />
              </div>
            )}
          </div>
        )
      })}

      <div className="mt-4 pt-3 grid grid-cols-3 gap-3 text-center" style={{ borderTop: `1px solid ${SEC_DIM},0.15)` }}>
        <div>
          <div className="text-sm font-bold font-mono" style={{ color: SEC }}>1.4s</div>
          <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>Detect</div>
        </div>
        <div>
          <div className="text-sm font-bold font-mono" style={{ color: '#EF4444' }}>HIGH</div>
          <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>Severity</div>
        </div>
        <div>
          <div className="text-sm font-bold font-mono" style={{ color: '#7B2FF7' }}>PEND</div>
          <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.30)' }}>Approval</div>
        </div>
      </div>
    </div>
  )
}

/* ─── Problem Statement ─── */
function ProblemStatement() {
  const problems = [
    { icon: AlertTriangle, title: 'Slow anomaly response', desc: 'After-hours events or unauthorized presence detected too late. Manual review creates dangerous lag.' },
    { icon: Lock, title: 'Ungoverned automation', desc: 'AI systems that act without approval erode trust. Security teams need approval gates, not black-box decisions.' },
    { icon: Eye, title: 'Poor operator visibility', desc: 'Alert fatigue and scattered tools reduce situational awareness. Operators miss critical events.' },
    { icon: FileText, title: 'Audit gaps', desc: 'Incomplete incident logs undermine compliance. Every action and non-action must be traceable.' },
  ]

  return (
    <section className="py-24 relative">
      <GradientOrbs />
      <div className="relative max-w-7xl mx-auto px-6 z-10">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={AlertTriangle}>The Problem</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Security teams need <G>governed AI</G>, not more alerts
            </h2>
            <p className="text-base max-w-2xl mx-auto" style={{ color: 'rgba(255,255,255,0.50)' }}>
              The World Economic Forum identifies AI agents as reshaping security operations — while
              Deloitte calls cybersecurity a high-potential enterprise function for agentic AI.
              SecureFlow addresses both the capability and the governance gap.
            </p>
          </div>
        </Reveal>
        <div className="grid sm:grid-cols-2 gap-6">
          {problems.map(({ icon: Icon, title, desc }, i) => (
            <Reveal key={title} delay={i * 0.1}>
              <AnimatedBorderCard>
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: `${SEC_DIM},0.12)`, border: `1px solid ${SEC_DIM},0.25)` }}>
                    <Icon size={22} style={{ color: SEC }} />
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
    'Announces approved incident status to nearby personnel',
    'Asks for supervisor confirmation before next steps',
    'Provides calm status summaries during events',
    'Confirms that alerts were received and routed',
    'Communicates next steps clearly and consistently',
    'Acts as a physically present approval/awareness surface',
  ]
  const boundaries = [
    'Does not unlock doors or revoke access independently',
    'Does not take destructive security actions',
    'Does not override supervisor decisions',
    'Does not expose incident details to unauthorized personnel',
  ]

  return (
    <section className="py-24" style={{ background: 'rgba(6,6,18,0.95)' }}>
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={Shield}>Embodied Security</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Ricci is the <G>trust surface</G>, not the decision-maker
            </h2>
            <p className="text-base max-w-xl mx-auto" style={{ color: 'rgba(255,255,255,0.50)' }}>
              The robot communicates, confirms, and logs. It never acts beyond its approved script
              unless a human approves the escalation.
            </p>
          </div>
        </Reveal>

        <div className="grid md:grid-cols-2 gap-8">
          <Reveal delay={0.1}>
            <div className="rounded-2xl p-8" style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${SEC_DIM},0.20)` }}>
              <h3 className="text-xl font-bold mb-5 flex items-center gap-3" style={{ color: SEC }}>
                <CheckCircle2 size={22} /> What Ricci Does
              </h3>
              <ul className="flex flex-col gap-3">
                {capabilities.map(c => (
                  <li key={c} className="flex items-start gap-3 text-sm" style={{ color: 'rgba(255,255,255,0.65)' }}>
                    <CheckCircle2 size={14} style={{ color: SEC, marginTop: '2px', flexShrink: 0 }} />
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>

          <Reveal delay={0.2}>
            <div className="rounded-2xl p-8" style={{ background: 'rgba(13,13,32,0.80)', border: '1px solid rgba(239,68,68,0.20)' }}>
              <h3 className="text-xl font-bold mb-5 flex items-center gap-3" style={{ color: '#EF4444' }}>
                <Lock size={22} /> Least-Privilege Actions
              </h3>
              <ul className="flex flex-col gap-3">
                {boundaries.map(b => (
                  <li key={b} className="flex items-start gap-3 text-sm" style={{ color: 'rgba(255,255,255,0.65)' }}>
                    <Lock size={14} style={{ color: '#EF4444', marginTop: '2px', flexShrink: 0 }} />
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
      letter: 'A', title: 'After-Hours Presence', color: SEC,
      steps: [
        'Camera detects presence in restricted or closed area',
        'Backend checks policy rules and time-of-day constraints',
        'Ricci announces: "This area is currently closed."',
        'Supervisor notified with event context and camera zone',
        'Incident logged — no further action without approval',
      ]
    },
    {
      letter: 'B', title: 'Approval-Gated Escalation', color: '#EF4444',
      steps: [
        'Suspicious event crosses severity threshold',
        'Ricci asks: "A high-priority event is awaiting review."',
        'Operator reviews on dashboard or nearby control surface',
        'Operator approves or rejects proposed next step',
        'Decision and rationale logged to audit trail',
      ]
    },
    {
      letter: 'C', title: 'Lab Access Anomaly', color: '#7B2FF7',
      steps: [
        'Unexpected person detected near lab entry point',
        'Backend creates incident with severity scoring',
        'Ricci explains that access is being reviewed',
        'No physical action occurs without explicit approval',
        'Full incident timeline preserved for compliance',
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
              Three scenarios that <G>sell trust</G>
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
    { icon: Eye, label: 'Jetson Perception', desc: 'Presence detection, zone monitoring, anomaly classification on edge hardware', color: SEC },
    { icon: Shield, label: 'Policy Engine', desc: 'Time-of-day rules, severity scoring, least-privilege action evaluation', color: '#EF4444' },
    { icon: Cpu, label: 'Orchestration', desc: 'n8n approval workflows, notification routing, escalation state machine', color: '#7B2FF7' },
    { icon: Layers, label: 'Audit Ledger', desc: 'PostgreSQL incident log, decision records, approval chain, compliance artifacts', color: '#00B4D8' },
    { icon: Radio, label: 'Ricci Interface', desc: 'Status announcements, approval requests, calm de-escalation messaging', color: SEC },
  ]

  return (
    <section className="py-24" style={{ background: 'rgba(9,9,20,0.90)' }}>
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={GitBranch}>System Architecture</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Five layers. <G>Zero ungoverned actions.</G>
            </h2>
            <p className="text-sm max-w-lg mx-auto" style={{ color: 'rgba(255,255,255,0.42)' }}>
              Same core architecture as ReachyOps AI, configured for security policy enforcement and incident governance.
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
    { val: '< 2s', label: 'Anomaly Ack Time', desc: 'Detection to first system response', color: SEC },
    { val: '< 30s', label: 'Review Latency', desc: 'Alert to operator acknowledgment', color: '#EF4444' },
    { val: '94%', label: 'Alert Accuracy', desc: 'True positive rate on anomaly events', color: '#7B2FF7' },
    { val: '< 60s', label: 'Approval Cycle', desc: 'Escalation request to decision logged', color: '#00B4D8' },
    { val: '100%', label: 'Audit Complete', desc: 'Every action and non-action logged', color: '#10B981' },
    { val: '0', label: 'Ungated Actions', desc: 'Zero actions taken without approval', color: SEC },
  ]

  return (
    <section className="py-24 relative">
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={BarChart2}>Performance KPIs</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Metrics that matter to <G>security leaders</G>
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
    { icon: Shield, title: 'Policy-Gated Agentic Systems', desc: 'Multi-agent workflows where every action path requires policy evaluation and explicit approval.' },
    { icon: GitBranch, title: 'Secure Workflow Orchestration', desc: 'n8n-based incident state machines with approval gates, notification routing, and rollback paths.' },
    { icon: AlertTriangle, title: 'Event Severity Modeling', desc: 'Rule-based and ML-assisted severity scoring for anomaly prioritization and escalation.' },
    { icon: Fingerprint, title: 'Facilities Security Design', desc: 'Zone-aware detection, time-of-day policies, and physical access monitoring architecture.' },
    { icon: Radio, title: 'Embodied Explainability', desc: 'A physical robot that communicates system state, not a silent camera. Trust through presence.' },
    { icon: UserCheck, title: 'Action Approval Architecture', desc: 'Least-privilege model where the system proposes and humans dispose. Zero autonomous destructive actions.' },
  ]

  return (
    <section className="py-24" style={{ background: 'rgba(6,6,18,0.95)' }}>
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={Layers}>Skills Demonstrated</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              What SecureFlow proves <G>you can architect</G>
            </h2>
          </div>
        </Reveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {skills.map(({ icon: Icon, title, desc }, i) => (
            <Reveal key={title} delay={i * 0.08}>
              <AnimatedBorderCard>
                <div className="flex gap-4">
                  <div className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${SEC_DIM},0.12)`, border: `1px solid ${SEC_DIM},0.25)` }}>
                    <Icon size={20} style={{ color: SEC }} />
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
    'CISO-adjacent innovation teams',
    'SOC leaders',
    'Physical security teams',
    'Secure lab managers',
    'Facilities/security integrators',
  ]

  return (
    <section className="py-24 relative">
      <div className="max-w-5xl mx-auto px-6 text-center">
        <Reveal>
          <SectionTag icon={Activity}>Market Fit</SectionTag>
          <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-6 tracking-tight">
            Built for the teams that <G>demand trust</G>
          </h2>
          <p className="text-base max-w-2xl mx-auto mb-10" style={{ color: 'rgba(255,255,255,0.50)' }}>
            SecureFlow solves the governance gap in security AI. It demonstrates secure-by-design architecture,
            least-privilege action models, and operator-centric explainability.
          </p>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="flex flex-wrap justify-center gap-3 mb-12">
            {buyers.map(b => (
              <span key={b} className="px-5 py-2.5 rounded-full text-sm font-medium" style={{
                background: `${SEC_DIM},0.08)`, border: `1px solid ${SEC_DIM},0.25)`, color: SEC,
              }}>
                {b}
              </span>
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/dashboard" className="inline-flex items-center gap-2 px-7 py-3.5 rounded-xl font-semibold text-white text-base transition-all duration-200"
              style={{ background: `linear-gradient(135deg, ${SEC} 0%, #D97706 100%)`, boxShadow: `0 4px 20px ${SEC_DIM},0.35)` }}>
              View Live Demo <ArrowRight size={17} />
            </Link>
            <Link to="/careflow" className="btn-secondary text-base px-7 py-3.5">
              See CareFlow Edition <ArrowRight size={15} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ═══ PAGE ═══ */
export default function SecureFlowPage() {
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
