import { Link } from 'react-router-dom'
import {
  ArrowRight, Shield, Lock, CheckCircle2, Eye, AlertTriangle,
  Users, FileText, Heart, Activity, GitBranch, Layers,
  UserCheck, Bell, Clock, Zap
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
    <section className="relative min-h-[60vh] flex items-center pt-24 pb-16 overflow-hidden">
      <div className="absolute inset-0" style={{
        background: 'radial-gradient(ellipse 70% 55% at 50% -5%, rgba(123,47,247,0.20) 0%, transparent 55%), #080818'
      }} />
      <GridOverlay opacity={0.02} />

      <div className="relative max-w-4xl mx-auto px-6 text-center z-10">
        <Reveal delay={0}>
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full text-xs font-semibold tracking-widest uppercase mb-6"
            style={{ border: '1px solid rgba(123,47,247,0.40)', color: 'rgba(123,47,247,0.90)', background: 'rgba(123,47,247,0.08)' }}>
            <Shield size={13} style={{ color: '#7B2FF7' }} />
            Governance Framework
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <h1 className="text-5xl lg:text-6xl font-black tracking-tight leading-[1.08] mb-6">
            <span style={{ color: 'rgba(255,255,255,0.95)' }}>Every action</span>{' '}
            <G>governed</G>,{' '}
            <span style={{ color: 'rgba(255,255,255,0.95)' }}>every decision</span>{' '}
            <G>logged</G>
          </h1>
        </Reveal>

        <Reveal delay={0.2}>
          <p className="text-lg leading-relaxed max-w-2xl mx-auto" style={{ color: 'rgba(255,255,255,0.55)' }}>
            ReachyOps AI enforces bounded autonomy across both CareFlow and SecureFlow.
            The governance matrix below shows exactly what the system can do, what requires approval,
            and what it will never do.
          </p>
        </Reveal>
      </div>
    </section>
  )
}

/* ─── Governance Matrix ─── */
function GovernanceMatrix() {
  const categories = [
    {
      category: 'Detection & Classification',
      items: [
        { action: 'Camera-based presence detection', care: 'auto', secure: 'auto', risk: 'low' },
        { action: 'Emotion / anomaly classification', care: 'auto', secure: 'auto', risk: 'low' },
        { action: 'Structured event creation', care: 'auto', secure: 'auto', risk: 'low' },
        { action: 'Severity scoring', care: 'auto', secure: 'auto', risk: 'low' },
      ]
    },
    {
      category: 'Communication',
      items: [
        { action: 'Ricci greeting / acknowledgment', care: 'auto', secure: 'auto', risk: 'low' },
        { action: 'Wait-time status update', care: 'auto', secure: 'n/a', risk: 'low' },
        { action: 'Area closure announcement', care: 'n/a', secure: 'auto', risk: 'low' },
        { action: 'Calm de-escalation messaging', care: 'auto', secure: 'auto', risk: 'medium' },
      ]
    },
    {
      category: 'Notification & Escalation',
      items: [
        { action: 'Staff / supervisor notification', care: 'auto', secure: 'auto', risk: 'medium' },
        { action: 'Dashboard alert update', care: 'auto', secure: 'auto', risk: 'low' },
        { action: 'High-priority escalation', care: 'approval', secure: 'approval', risk: 'high' },
        { action: 'External notification (email/SMS)', care: 'approval', secure: 'approval', risk: 'high' },
      ]
    },
    {
      category: 'Physical Actions',
      items: [
        { action: 'Gesture execution (greet, comfort)', care: 'auto', secure: 'auto', risk: 'low' },
        { action: 'Door unlock / access grant', care: 'never', secure: 'never', risk: 'critical' },
        { action: 'Access revocation', care: 'never', secure: 'never', risk: 'critical' },
        { action: 'Physical intervention', care: 'never', secure: 'never', risk: 'critical' },
      ]
    },
    {
      category: 'Data & Privacy',
      items: [
        { action: 'Audit log writing', care: 'auto', secure: 'auto', risk: 'low' },
        { action: 'Video recording start/stop', care: 'approval', secure: 'approval', risk: 'high' },
        { action: 'Data retention override', care: 'approval', secure: 'approval', risk: 'high' },
        { action: 'Raw video transmission', care: 'never', secure: 'never', risk: 'critical' },
      ]
    },
  ]

  const statusStyle = (status) => {
    switch (status) {
      case 'auto': return { bg: 'rgba(16,185,129,0.12)', color: '#10B981', border: 'rgba(16,185,129,0.25)', label: 'Automatic' }
      case 'approval': return { bg: 'rgba(245,158,11,0.12)', color: '#F59E0B', border: 'rgba(245,158,11,0.25)', label: 'Approval Required' }
      case 'never': return { bg: 'rgba(239,68,68,0.12)', color: '#EF4444', border: 'rgba(239,68,68,0.25)', label: 'Never Permitted' }
      case 'n/a': return { bg: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.3)', border: 'rgba(255,255,255,0.08)', label: 'N/A' }
      default: return { bg: 'transparent', color: 'rgba(255,255,255,0.3)', border: 'transparent', label: status }
    }
  }

  const riskColor = (risk) => {
    switch (risk) {
      case 'low': return '#10B981'
      case 'medium': return '#F59E0B'
      case 'high': return '#EF4444'
      case 'critical': return '#DC2626'
      default: return 'rgba(255,255,255,0.3)'
    }
  }

  return (
    <section className="py-20 relative">
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-12">
            <SectionTag icon={FileText}>Governance Matrix</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              What the system <G>can and cannot do</G>
            </h2>
          </div>
        </Reveal>

        {/* Legend */}
        <Reveal delay={0.05}>
          <div className="flex flex-wrap justify-center gap-4 mb-8">
            {['auto', 'approval', 'never'].map(key => {
              const s = statusStyle(key)
              return (
                <div key={key} className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold"
                  style={{ background: s.bg, border: `1px solid ${s.border}`, color: s.color }}>
                  {key === 'auto' && <CheckCircle2 size={12} />}
                  {key === 'approval' && <UserCheck size={12} />}
                  {key === 'never' && <Lock size={12} />}
                  {s.label}
                </div>
              )
            })}
          </div>
        </Reveal>

        {categories.map(({ category, items }, ci) => (
          <Reveal key={category} delay={0.1 + ci * 0.05}>
            <div className="mb-6">
              <h3 className="text-sm font-bold tracking-widest uppercase mb-3 px-2" style={{ color: 'rgba(255,255,255,0.5)' }}>
                {category}
              </h3>
              <div className="rounded-2xl overflow-hidden" style={{ border: '1px solid rgba(123,47,247,0.15)' }}>
                {/* Column headers */}
                <div className="grid grid-cols-[2fr_1fr_1fr_0.7fr] py-3 px-4 text-xs font-semibold tracking-widest uppercase"
                  style={{ background: 'rgba(22,22,56,0.90)', color: 'rgba(255,255,255,0.4)' }}>
                  <div>Action</div>
                  <div className="text-center flex items-center justify-center gap-1"><Heart size={10} style={{ color: '#10B981' }} /> CareFlow</div>
                  <div className="text-center flex items-center justify-center gap-1"><Shield size={10} style={{ color: '#F59E0B' }} /> SecureFlow</div>
                  <div className="text-center">Risk</div>
                </div>
                {items.map(({ action, care, secure, risk }, i) => {
                  const cs = statusStyle(care)
                  const ss = statusStyle(secure)
                  return (
                    <div key={action} className="grid grid-cols-[2fr_1fr_1fr_0.7fr] py-3 px-4 text-sm items-center" style={{
                      background: i % 2 === 0 ? 'rgba(13,13,32,0.60)' : 'rgba(13,13,32,0.40)',
                      borderTop: '1px solid rgba(123,47,247,0.06)',
                    }}>
                      <div style={{ color: 'rgba(255,255,255,0.7)' }}>{action}</div>
                      <div className="text-center">
                        <span className="inline-flex px-2.5 py-1 rounded-full text-xs font-semibold"
                          style={{ background: cs.bg, color: cs.color, border: `1px solid ${cs.border}` }}>
                          {cs.label}
                        </span>
                      </div>
                      <div className="text-center">
                        <span className="inline-flex px-2.5 py-1 rounded-full text-xs font-semibold"
                          style={{ background: ss.bg, color: ss.color, border: `1px solid ${ss.border}` }}>
                          {ss.label}
                        </span>
                      </div>
                      <div className="text-center">
                        <span className="text-xs font-mono font-bold uppercase" style={{ color: riskColor(risk) }}>
                          {risk}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  )
}

/* ─── Approval Flow ─── */
function ApprovalFlow() {
  const steps = [
    { icon: Eye, title: 'Event Detected', desc: 'Jetson perception layer classifies the event with confidence score.', color: '#D4166A' },
    { icon: AlertTriangle, title: 'Policy Evaluated', desc: 'n8n workflow checks rules, severity, and autonomy boundaries.', color: '#F59E0B' },
    { icon: UserCheck, title: 'Approval Requested', desc: 'If action exceeds autonomy, operator is notified with context.', color: '#7B2FF7' },
    { icon: CheckCircle2, title: 'Decision Logged', desc: 'Approval, rejection, or modification recorded with rationale.', color: '#00B4D8' },
    { icon: Zap, title: 'Action Executed', desc: 'Only approved actions proceed. Ricci communicates the outcome.', color: '#10B981' },
    { icon: FileText, title: 'Audit Sealed', desc: 'Complete decision chain archived for compliance review.', color: '#00C8A0' },
  ]

  return (
    <section className="py-20" style={{ background: 'rgba(9,9,20,0.90)' }}>
      <div className="max-w-6xl mx-auto px-6">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={GitBranch}>Approval Pipeline</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              From event to action: <G>every step governed</G>
            </h2>
          </div>
        </Reveal>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {steps.map(({ icon: Icon, title, desc, color }, i) => (
            <Reveal key={title} delay={i * 0.08}>
              <div className="flex gap-4 p-5 rounded-2xl h-full" style={{ background: 'rgba(13,13,32,0.70)', border: `1px solid ${color}20` }}>
                <div className="flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
                  <Icon size={20} style={{ color }} />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className="text-xs font-mono font-bold" style={{ color }}>{String(i + 1).padStart(2, '0')}</span>
                    <h3 className="font-bold text-sm" style={{ color: 'white' }}>{title}</h3>
                  </div>
                  <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.45)' }}>{desc}</p>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}

/* ─── Compliance Mapping ─── */
function ComplianceMapping() {
  const frameworks = [
    {
      name: 'GDPR / Data Privacy', color: '#D4166A',
      controls: [
        'No raw video egress — local-only processing',
        'TTL-based automatic media purge (7 days)',
        'Right to deletion with audit confirmation',
        'Structured JSONL logs with retention policies',
      ]
    },
    {
      name: 'SOC 2 / Audit Trail', color: '#7B2FF7',
      controls: [
        'Every system action logged with timestamp and context',
        'Approval chain preserved with operator identity',
        'Immutable audit records in PostgreSQL',
        'Reconciler agent detects and reports anomalies',
      ]
    },
    {
      name: 'Least Privilege / RBAC', color: '#00B4D8',
      controls: [
        'mTLS/JWT authentication on all service calls',
        'Role-based access control for operator actions',
        'Bearer tokens required for all mutate endpoints',
        'No public network exposure — static LAN only',
      ]
    },
  ]

  return (
    <section className="py-20 relative">
      <GradientOrbs />
      <div className="relative max-w-7xl mx-auto px-6 z-10">
        <Reveal>
          <div className="text-center mb-14">
            <SectionTag icon={Shield}>Compliance Alignment</SectionTag>
            <h2 className="text-4xl lg:text-5xl font-black mt-5 mb-4 tracking-tight">
              Built for <G>enterprise compliance</G>
            </h2>
          </div>
        </Reveal>

        <div className="grid lg:grid-cols-3 gap-6">
          {frameworks.map(({ name, color, controls }, i) => (
            <Reveal key={name} delay={i * 0.1}>
              <AnimatedBorderCard>
                <h3 className="font-bold text-lg mb-5" style={{ color }}>{name}</h3>
                <ul className="flex flex-col gap-3">
                  {controls.map(c => (
                    <li key={c} className="flex items-start gap-2.5 text-sm" style={{ color: 'rgba(255,255,255,0.55)' }}>
                      <CheckCircle2 size={14} style={{ color, marginTop: '2px', flexShrink: 0 }} />
                      {c}
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

/* ─── CTA ─── */
function CTA() {
  return (
    <section className="py-20">
      <div className="max-w-4xl mx-auto px-6 text-center">
        <Reveal>
          <h2 className="text-3xl lg:text-4xl font-black mb-6 tracking-tight">
            Governance isn't a feature. <G>It's the foundation.</G>
          </h2>
          <p className="text-base max-w-xl mx-auto mb-8" style={{ color: 'rgba(255,255,255,0.50)' }}>
            Every vertical, every action, every decision — governed by the same framework.
            That's what makes ReachyOps AI enterprise-ready.
          </p>
        </Reveal>
        <Reveal delay={0.1}>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/dashboard" className="btn-primary text-base px-7 py-3.5">
              View Live Dashboard <ArrowRight size={17} />
            </Link>
            <Link to="/platform" className="btn-secondary text-base px-7 py-3.5">
              Platform Architecture <ArrowRight size={15} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

/* ═══ PAGE ═══ */
export default function GovernancePage() {
  return (
    <>
      <Hero />
      <GovernanceMatrix />
      <ApprovalFlow />
      <ComplianceMapping />
      <CTA />
    </>
  )
}
