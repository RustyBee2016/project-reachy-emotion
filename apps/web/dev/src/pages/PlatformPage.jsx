import { Link } from 'react-router-dom'
import {
  ArrowRight, Cpu, Database, GitBranch, Shield, Eye, Brain,
  Zap, Activity, Layers, Lock, RefreshCw, BarChart2, Bot,
  Server, Wifi, HardDrive, CheckCircle2, Heart
} from 'lucide-react'
import { Reveal } from '../hooks/useReveal'
import { GradientOrbs, GridOverlay, ParticleField, AnimatedBorderCard } from '../components/AnimatedBackground'

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

/* ─── Hero ─── */
function Hero() {
  return (
    <section className="relative min-h-[80vh] flex items-center pt-24 pb-20 overflow-hidden">
      <div className="absolute inset-0" style={{
        background: 'radial-gradient(ellipse 70% 55% at 50% -5%, rgba(123,47,247,0.25) 0%, transparent 55%), radial-gradient(ellipse 40% 30% at 80% 70%, rgba(0,180,216,0.12) 0%, transparent 50%), #080818'
      }} />
      <GridOverlay opacity={0.025} />
      <ParticleField count={30} />

      <div className="relative max-w-7xl mx-auto px-6 z-10">
        <div className="max-w-3xl">
          <Reveal delay={0}>
            <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full text-xs font-semibold tracking-widest uppercase mb-6"
              style={{ border: '1px solid rgba(123,47,247,0.40)', color: 'rgba(123,47,247,0.90)', background: 'rgba(123,47,247,0.08)' }}>
              <Layers size={13} style={{ color: '#7B2FF7' }} />
              ReachyOps AI Platform
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <h1 className="text-5xl lg:text-6xl font-black tracking-tight leading-[1.08] mb-6">
              <span style={{ color: 'rgba(255,255,255,0.95)' }}>One governed platform.</span><br />
              <G>Two enterprise verticals.</G>
            </h1>
          </Reveal>

          <Reveal delay={0.2}>
            <p className="text-lg leading-relaxed mb-8 max-w-xl" style={{ color: 'rgba(255,255,255,0.55)' }}>
              ReachyOps AI is a reusable physical-AI operations platform with Ricci/Reachy as the
              embodied interaction layer. The same core architecture powers{' '}
              <strong style={{ color: '#10B981' }}>CareFlow</strong> for healthcare and{' '}
              <strong style={{ color: '#F59E0B' }}>SecureFlow</strong> for cybersecurity — with
              different workflow logic, policy models, and operator dashboards.
            </p>
          </Reveal>

          <Reveal delay={0.3}>
            <div className="flex flex-wrap gap-3">
              <Link to="/careflow" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white text-sm transition-all duration-200"
                style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', boxShadow: '0 4px 20px rgba(16,185,129,0.3)' }}>
                <Heart size={15} /> CareFlow Edition
              </Link>
              <Link to="/secureflow" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white text-sm transition-all duration-200"
                style={{ background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)', boxShadow: '0 4px 20px rgba(245,158,11,0.3)' }}>
                <Shield size={15} /> SecureFlow Edition
              </Link>
              <Link to="/dashboard" className="btn-secondary text-sm px-6 py-3">
                Live Dashboard <ArrowRight size={15} />
              </Link>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}

/* ─── Shared Stack ─── */
function SharedStack() {
  const nodes = [
    {
      icon: Eye, color: '#D4166A', title: 'Jetson Xavier NX', subtitle: 'Edge Perception',
      specs: ['EfficientNet-B0 TensorRT engine', 'DeepStream SDK 6.x pipeline', '< 42ms p50 inference', '30 FPS camera ingestion'],
      detail: 'Handles all real-time visual perception. Emits structured JSON events — never raw video. Runs entirely on-premise at the network edge.',
    },
    {
      icon: Server, color: '#7B2FF7', title: 'Ubuntu Workstation', subtitle: 'Control Plane',
      specs: ['FastAPI gateway (11 routers)', 'n8n orchestration (10 agents)', 'MLflow experiment tracking', 'Media Mover API'],
      detail: 'Central command for workflow orchestration, API routing, model training, and approval-gated decision-making. Houses the ML pipeline.',
    },
    {
      icon: Database, color: '#00B4D8', title: 'PostgreSQL 16', subtitle: 'Event Ledger',
      specs: ['12 Alembic-managed tables', 'Full audit trail for all actions', 'Event, incident, and approval logs', 'SHA-256 dataset hashing'],
      detail: 'Source of truth for metadata, events, approvals, and compliance artifacts. Every system action is recorded with timestamps and context.',
    },
    {
      icon: GitBranch, color: '#00C8A0', title: 'n8n Workflows', subtitle: 'Orchestration',
      specs: ['10 cooperating agents', 'Approval gates with human-in-loop', 'Exponential backoff + jitter retries', 'WebSocket + REST integration'],
      detail: 'The orchestration brain. Routes events through policy evaluation, approval workflows, and notification pipelines with full observability.',
    },
    {
      icon: Bot, color: '#F59E0B', title: 'Ricci / Reachy Mini', subtitle: 'Embodied Interface',
      specs: ['Gesture execution via gRPC', '5-tier confidence modulation', 'Emotion-conditioned LLM dialogue', 'Physical presence and reassurance'],
      detail: 'The user-facing interaction endpoint. Communicates, reassures, and escalates — but never acts beyond its approved script without human approval.',
    },
  ]

  return (
    <section className="py-24 relative">
      <GradientOrbs />
      <div className="relative max-w-7xl mx-auto px-6 z-10">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={Cpu}>Shared Infrastructure</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Five nodes. <G>One reusable stack.</G>
            </h2>
            <p className="text-base max-w-2xl mx-auto" style={{ color: 'rgba(255,255,255,0.50)' }}>
              Both CareFlow and SecureFlow run on the same physical infrastructure with
              different workflow configurations, policy rules, and operator interfaces.
            </p>
          </div>
        </Reveal>

        <div className="flex flex-col gap-6">
          {nodes.map(({ icon: Icon, color, title, subtitle, specs, detail }, i) => (
            <Reveal key={title} delay={i * 0.08}>
              <div className="rounded-2xl p-6 lg:p-8 transition-all duration-300"
                style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${color}20` }}
                onMouseOver={e => e.currentTarget.style.borderColor = `${color}45`}
                onMouseOut={e => e.currentTarget.style.borderColor = `${color}20`}>
                <div className="grid lg:grid-cols-[1fr_2fr] gap-6">
                  <div>
                    <div className="flex items-center gap-4 mb-4">
                      <div className="w-14 h-14 rounded-2xl flex items-center justify-center" style={{ background: `${color}15`, border: `1px solid ${color}35` }}>
                        <Icon size={28} style={{ color }} />
                      </div>
                      <div>
                        <h3 className="text-xl font-black" style={{ color: 'white' }}>{title}</h3>
                        <span className="text-xs font-mono" style={{ color }}>{subtitle}</span>
                      </div>
                    </div>
                    <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.48)' }}>{detail}</p>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3">
                    {specs.map(s => (
                      <div key={s} className="flex items-center gap-2.5 px-4 py-3 rounded-xl text-sm"
                        style={{ background: `${color}08`, border: `1px solid ${color}15`, color: 'rgba(255,255,255,0.65)' }}>
                        <CheckCircle2 size={14} style={{ color, flexShrink: 0 }} />
                        {s}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── Shared Pattern ─── */
function SharedPattern() {
  const steps = [
    { n: '01', title: 'Observe', desc: 'Jetson camera detects presence, emotion, or anomaly in the environment.', color: '#D4166A' },
    { n: '02', title: 'Classify', desc: 'EfficientNet-B0 runs inference with calibrated confidence scoring.', color: '#A520B8' },
    { n: '03', title: 'Event', desc: 'Structured event generated and persisted to PostgreSQL audit ledger.', color: '#7B2FF7' },
    { n: '04', title: 'Policy', desc: 'n8n workflow evaluates rules, severity, and approval requirements.', color: '#3893E8' },
    { n: '05', title: 'Decide', desc: 'System determines allowed actions. Approval requested if needed.', color: '#00B4D8' },
    { n: '06', title: 'Approve', desc: 'Human operator approves, modifies, or rejects the proposed action.', color: '#00C8A0' },
    { n: '07', title: 'Communicate', desc: 'Ricci delivers the response via gesture, dialogue, or announcement.', color: '#10B981' },
    { n: '08', title: 'Log', desc: 'Every step is recorded with timestamps, decisions, and rationale.', color: '#F59E0B' },
  ]

  return (
    <section className="py-24" style={{ background: 'rgba(9,9,20,0.90)' }}>
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={RefreshCw}>Universal Pattern</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Eight steps. <G>Every vertical.</G>
            </h2>
            <p className="text-sm max-w-lg mx-auto" style={{ color: 'rgba(255,255,255,0.42)' }}>
              The observe → classify → event → policy → decide → approve → communicate → log pattern
              is the same for healthcare, security, and any future vertical.
            </p>
          </div>
        </Reveal>

        <div className="relative">
          {/* Connector line */}
          <div className="hidden lg:block absolute top-6 left-0 right-0 h-0.5 overflow-hidden">
            <div style={{
              height: '100%', width: '200%',
              background: 'linear-gradient(90deg, transparent, #D4166A, #7B2FF7, #00B4D8, #10B981, #F59E0B, transparent)',
              animation: 'shimmer 6s ease-in-out infinite',
            }} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-4">
            {steps.map(({ n, title, desc, color }, i) => (
              <Reveal key={n} delay={i * 0.06}>
                <div className="flex flex-col items-center text-center gap-3">
                  <div className="relative w-12 h-12 rounded-xl flex flex-col items-center justify-center z-10 transition-all duration-300 hover:scale-110"
                    style={{ background: `${color}12`, border: `2px solid ${color}50`, boxShadow: `0 0 20px ${color}15` }}>
                    <span className="text-xs font-mono font-bold" style={{ color }}>{n}</span>
                  </div>
                  <h4 className="text-xs font-bold" style={{ color: 'white' }}>{title}</h4>
                  <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.40)' }}>{desc}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

/* ─── Vertical Comparison ─── */
function VerticalComparison() {
  const rows = [
    { label: 'Detection Target', care: 'Patient/visitor arrival', secure: 'After-hours presence / anomaly' },
    { label: 'Event Type', care: 'Arrival, wait, distress', secure: 'Anomaly, incident, breach attempt' },
    { label: 'Policy Model', care: 'Queue-aware, empathy-driven', secure: 'Time-of-day, severity-scored' },
    { label: 'Approval Gates', care: 'Staff escalation for distress', secure: 'Supervisor approval for all actions' },
    { label: 'Ricci Behavior', care: 'Greet, reassure, wayfind', secure: 'Announce, confirm, de-escalate' },
    { label: 'Dashboard Focus', care: 'Queue state, arrivals, KPIs', secure: 'Incidents, severity, approvals' },
    { label: 'Compliance', care: 'HIPAA-adjacent, GDPR', secure: 'SOC 2-adjacent, audit-complete' },
    { label: 'Primary KPI', care: 'Acknowledgment time < 3s', secure: 'Anomaly ack time < 2s' },
  ]

  return (
    <section className="py-24 relative">
      <div className="max-w-5xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={Layers}>Two Editions</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Same platform. <G>Different missions.</G>
            </h2>
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="rounded-2xl overflow-hidden" style={{ border: '1px solid rgba(123,47,247,0.20)' }}>
            {/* Header */}
            <div className="grid grid-cols-3 text-center py-4 px-4" style={{ background: 'rgba(22,22,56,0.90)' }}>
              <div className="text-xs font-semibold tracking-widest uppercase" style={{ color: 'rgba(255,255,255,0.4)' }}>Component</div>
              <div className="text-sm font-bold flex items-center justify-center gap-2" style={{ color: '#10B981' }}>
                <Heart size={14} /> CareFlow
              </div>
              <div className="text-sm font-bold flex items-center justify-center gap-2" style={{ color: '#F59E0B' }}>
                <Shield size={14} /> SecureFlow
              </div>
            </div>
            {/* Rows */}
            {rows.map(({ label, care, secure }, i) => (
              <div key={label} className="grid grid-cols-3 py-3.5 px-4 text-sm" style={{
                background: i % 2 === 0 ? 'rgba(13,13,32,0.60)' : 'rgba(13,13,32,0.40)',
                borderTop: '1px solid rgba(123,47,247,0.08)',
              }}>
                <div className="font-semibold" style={{ color: 'rgba(255,255,255,0.7)' }}>{label}</div>
                <div className="text-center" style={{ color: 'rgba(255,255,255,0.55)' }}>{care}</div>
                <div className="text-center" style={{ color: 'rgba(255,255,255,0.55)' }}>{secure}</div>
              </div>
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Link to="/careflow" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white text-sm transition-all duration-200"
              style={{ background: 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }}>
              <Heart size={15} /> Explore CareFlow <ArrowRight size={15} />
            </Link>
            <Link to="/secureflow" className="inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold text-white text-sm transition-all duration-200"
              style={{ background: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)' }}>
              <Shield size={15} /> Explore SecureFlow <ArrowRight size={15} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ─── 10 Agents ─── */
const AGENTS = [
  { n: '01', name: 'Ingest', icon: Database, color: '#D4166A', desc: 'Video intake, sha256 checksum, metadata extraction, thumbnail generation.' },
  { n: '02', name: 'Label', icon: Eye, color: '#C21899', desc: '3-class human-in-the-loop classification and dataset curation.' },
  { n: '03', name: 'Promote', icon: RefreshCw, color: '#A820D8', desc: 'Controlled media movement between filesystem stages with dry-run preview.' },
  { n: '04', name: 'Reconcile', icon: GitBranch, color: '#8B2AEF', desc: 'Detect filesystem/DB drift, orphans, and duplicates. Rebuild manifests.' },
  { n: '05', name: 'Train', icon: Cpu, color: '#7B2FF7', desc: 'EfficientNet-B0 fine-tuning with MLflow tracking and Gate A validation.' },
  { n: '06', name: 'Evaluate', icon: BarChart2, color: '#5040E8', desc: 'F1, ECE, Brier score, confusion matrix on balanced test set.' },
  { n: '07', name: 'Deploy', icon: Layers, color: '#2A60D8', desc: 'ONNX → TensorRT conversion, shadow → canary → production rollout.' },
  { n: '08', name: 'Privacy', icon: Lock, color: '#0A90C8', desc: 'TTL purges, deny-by-default policy, GDPR-compliant deletion workflows.' },
  { n: '09', name: 'Observe', icon: Activity, color: '#00B4D8', desc: 'Cross-agent metrics, Prometheus + Grafana dashboards, alert budgets.' },
  { n: '10', name: 'Gesture', icon: Zap, color: '#00C8A0', desc: 'Physical gesture execution on Reachy Mini via gRPC SDK interface.' },
]

function AgentGrid() {
  return (
    <section className="py-24" style={{ background: 'rgba(6,6,18,0.95)' }}>
      <div className="max-w-7xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={GitBranch}>Agentic System</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              <G>10 cooperating agents.</G> One auditable loop.
            </h2>
            <p className="text-sm max-w-lg mx-auto" style={{ color: 'rgba(255,255,255,0.42)' }}>
              All orchestrated through n8n with exponential backoff, jitter retries, and human approval gates.
            </p>
          </div>
        </Reveal>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          {AGENTS.map(({ n, name, icon: Icon, color, desc }, i) => (
            <Reveal key={n} delay={i * 0.05}>
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
      </div>
    </section>
  )
}

/* ─── Why Reusable ─── */
function WhyReusable() {
  return (
    <section className="py-24 relative">
      <div className="max-w-5xl mx-auto px-6 text-center">
        <Reveal>
          <SectionTag icon={Brain}>Consulting Value</SectionTag>
          <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-6 tracking-tight">
            One architecture. <G>Infinite verticals.</G>
          </h2>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="grid sm:grid-cols-3 gap-6 mb-12 text-left">
            {[
              { title: 'Reusable Core', desc: 'Same Jetson perception, control plane, Postgres ledger, n8n orchestration, and Ricci interface across every deployment.', color: '#7B2FF7' },
              { title: 'Vertical Skins', desc: 'Different workflow logic, policy models, operator dashboards, and Ricci behavior scripts per industry vertical.', color: '#00B4D8' },
              { title: 'Consulting Story', desc: '"I built a governed physical-AI operations platform and adapted it to two high-demand verticals." That is a solutions architect pitch.', color: '#D4166A' },
            ].map(({ title, desc, color }, i) => (
              <Reveal key={title} delay={0.15 + i * 0.1}>
                <AnimatedBorderCard>
                  <h3 className="font-bold text-lg mb-3" style={{ color }}>{title}</h3>
                  <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.50)' }}>{desc}</p>
                </AnimatedBorderCard>
              </Reveal>
            ))}
          </div>
        </Reveal>

        <Reveal delay={0.3}>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/governance" className="btn-secondary text-base px-7 py-3.5">
              Governance Matrix <ArrowRight size={15} />
            </Link>
            <Link to="/architecture" className="btn-secondary text-base px-7 py-3.5">
              Technical Deep-Dive <ArrowRight size={15} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ─── Network Topology ─── */
function NetworkTopology() {
  const nodes = [
    { label: 'Jetson NX', ip: '10.0.4.150', role: 'Edge Inference', color: '#D4166A' },
    { label: 'Ubuntu 1', ip: '10.0.4.130', role: 'Model Host / Media Mover', color: '#7B2FF7' },
    { label: 'Ubuntu 2', ip: '10.0.4.140', role: 'App Gateway / Orchestrator', color: '#00B4D8' },
  ]

  const connections = [
    { from: 'Jetson → Ubuntu 2', protocol: 'HTTPS :443 + WebSocket', desc: 'Emotion events, cue delivery' },
    { from: 'Ubuntu 2 → Ubuntu 1', protocol: 'HTTPS :8083 + REST', desc: 'Media Mover, LLM inference' },
    { from: 'Ubuntu 1 → Postgres', protocol: 'TCP :5432', desc: 'Metadata, audit, event storage' },
    { from: 'n8n → All Hosts', protocol: 'REST + SSH', desc: 'Orchestration, deployment, monitoring' },
  ]

  return (
    <section className="py-24" style={{ background: 'rgba(9,9,20,0.90)' }}>
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={Wifi}>Network Topology</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Static LAN. <G>Zero public exposure.</G>
            </h2>
          </div>
        </Reveal>

        <div className="grid lg:grid-cols-2 gap-8">
          <Reveal delay={0.1}>
            <div className="flex flex-col gap-4">
              {nodes.map(({ label, ip, role, color }) => (
                <div key={label} className="flex items-center gap-4 p-5 rounded-2xl"
                  style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${color}25` }}>
                  <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: `${color}15`, border: `1px solid ${color}35` }}>
                    <HardDrive size={20} style={{ color }} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <h4 className="font-bold" style={{ color: 'white' }}>{label}</h4>
                      <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: `${color}15`, color }}>{ip}</span>
                    </div>
                    <p className="text-xs mt-1" style={{ color: 'rgba(255,255,255,0.45)' }}>{role}</p>
                  </div>
                </div>
              ))}
            </div>
          </Reveal>

          <Reveal delay={0.2}>
            <div className="flex flex-col gap-4">
              {connections.map(({ from, protocol, desc }) => (
                <div key={from} className="flex items-center gap-4 p-5 rounded-2xl"
                  style={{ background: 'rgba(13,13,32,0.80)', border: '1px solid rgba(123,47,247,0.15)' }}>
                  <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'rgba(123,47,247,0.10)', border: '1px solid rgba(123,47,247,0.25)' }}>
                    <Wifi size={20} style={{ color: '#7B2FF7' }} />
                  </div>
                  <div>
                    <h4 className="font-bold text-sm" style={{ color: 'white' }}>{from}</h4>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(0,180,216,0.12)', color: '#00B4D8' }}>{protocol}</span>
                      <span className="text-xs" style={{ color: 'rgba(255,255,255,0.40)' }}>{desc}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}

/* ═══ PAGE ═══ */
export default function PlatformPage() {
  return (
    <>
      <Hero />
      <SharedStack />
      <SharedPattern />
      <VerticalComparison />
      <AgentGrid />
      <NetworkTopology />
      <WhyReusable />
    </>
  )
}
