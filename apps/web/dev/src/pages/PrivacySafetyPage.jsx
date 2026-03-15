import { Link } from 'react-router-dom'
import { ArrowRight, Shield, Lock, Eye, Database, Clock, AlertCircle, CheckCircle2, Server } from 'lucide-react'
import { Reveal } from '../hooks/useReveal'
import { GradientOrbs } from '../components/AnimatedBackground'

const G = ({ children }) => (
  <span style={{
    background: 'linear-gradient(135deg, #D4166A 0%, #7B2FF7 50%, #00B4D8 100%)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
  }}>{children}</span>
)

const Card = ({ children, className = '' }) => (
  <div className={`rounded-2xl p-6 ${className}`} style={{
    background: 'linear-gradient(145deg, rgba(212,22,106,0.06) 0%, rgba(123,47,247,0.04) 100%)',
    border: '1px solid rgba(212,22,106,0.18)',
  }}>
    {children}
  </div>
)

/* Threat model comparison */
function ThreatComparison() {
  const rows = [
    ['Cloud inference', 'Raw video sent to external API', '❌', '✅ Never leaves LAN'],
    ['Model training', 'Uploaded to remote GPU cluster', '❌', '✅ Local GPU workstation'],
    ['Video storage', 'Object storage (S3/GCS)', '❌', '✅ Encrypted local SSD'],
    ['User analytics', 'Third-party tracking pixels', '❌', '✅ No external analytics'],
    ['API keys in transit', 'Bearer tokens over internet', '❌', '✅ mTLS on LAN only'],
  ]
  return (
    <div className="rounded-2xl overflow-hidden" style={{ border: '1px solid rgba(212,22,106,0.20)' }}>
      <div className="px-5 py-3 flex items-center gap-2" style={{ background: 'rgba(212,22,106,0.08)', borderBottom: '1px solid rgba(212,22,106,0.15)' }}>
        <Shield size={14} style={{ color: '#D4166A' }} />
        <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: '#D4166A' }}>Privacy Threat Model</span>
      </div>
      <div className="divide-y" style={{ '--tw-divide-opacity': 1 }}>
        <div className="grid grid-cols-4 text-xs font-semibold px-5 py-2.5" style={{ background: 'rgba(255,255,255,0.03)', color: 'rgba(255,255,255,0.35)', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <span>Concern</span>
          <span>Typical Cloud Approach</span>
          <span className="text-center">Cloud</span>
          <span>Affective AI</span>
        </div>
        {rows.map(([concern, cloud, cloudBadge, local]) => (
          <div key={concern} className="grid grid-cols-4 text-xs px-5 py-3 items-start" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
            <span className="font-medium" style={{ color: 'rgba(255,255,255,0.75)' }}>{concern}</span>
            <span style={{ color: 'rgba(255,255,255,0.40)' }}>{cloud}</span>
            <span className="text-center text-base">{cloudBadge}</span>
            <span style={{ color: '#00C8A0' }}>{local}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* Retention policy visual */
function RetentionPolicy() {
  const stages = [
    { stage: 'Ingest → temp/', ttl: '7 days', action: 'Auto-purge', color: '#D4166A' },
    { stage: 'temp/ → train/', ttl: 'Permanent', action: 'Human approved', color: '#7B2FF7' },
    { stage: 'train/ labels', ttl: 'Permanent', action: 'Audit logged', color: '#00B4D8' },
    { stage: 'thumbs/', ttl: '7 days', action: 'Purged with parent', color: '#D4166A' },
    { stage: 'Purge request', ttl: 'Immediate', action: 'DB + FS deleted', color: '#00C8A0' },
  ]
  return (
    <div className="rounded-2xl p-5" style={{ background: 'rgba(11,11,24,0.90)', border: '1px solid rgba(212,22,106,0.18)' }}>
      <div className="text-xs font-semibold tracking-widest uppercase mb-4" style={{ color: 'rgba(255,255,255,0.35)' }}>
        Data Retention Policy
      </div>
      <div className="flex flex-col gap-2">
        {stages.map(({ stage, ttl, action, color }) => (
          <div key={stage} className="flex items-center gap-3 p-3 rounded-xl text-xs" style={{ background: 'rgba(255,255,255,0.03)', border: `1px solid ${color}18` }}>
            <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
            <span className="font-mono flex-1" style={{ color: 'rgba(255,255,255,0.65)' }}>{stage}</span>
            <span className="px-2 py-0.5 rounded font-semibold" style={{ background: `${color}18`, color }}>{ttl}</span>
            <span style={{ color: 'rgba(255,255,255,0.40)' }}>{action}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function PrivacySafetyPage() {
  const principles = [
    {
      icon: Server, color: '#D4166A', title: 'Local-Only Inference',
      body: 'All video processing and emotion classification occurs on-premise. Raw video frames never leave the local network. Ubuntu 1 handles all compute; Jetson Xavier NX handles edge inference.',
      bullets: ['No cloud API calls for inference', 'Static LAN IPs (10.0.4.x) only', 'Firewall blocks external egress', 'No internet dependency at runtime'],
    },
    {
      icon: Lock, color: '#7B2FF7', title: 'Access Control',
      body: 'All service-to-service communication uses mTLS authentication. The web UI requires JWT tokens. Role-based access control enforces principle of least privilege.',
      bullets: ['mTLS for inter-service calls', 'JWT with short expiry on UI', 'RBAC: viewer / curator / admin', 'Nginx reverse proxy + HTTPS'],
    },
    {
      icon: Clock, color: '#00B4D8', title: 'Data Minimization',
      body: 'Temporary video files are automatically purged after configurable TTL. Only necessary metadata is stored. Full purge procedures destroy both filesystem and database records.',
      bullets: ['Default TTL: 7 days for temp/', 'SHA-256 hash stored, not content', 'Manual purge via UI or API', 'PostgreSQL soft-delete + vacuum'],
    },
    {
      icon: Eye, color: '#00C8A0', title: 'Audit & Transparency',
      body: 'Every promotion, training run, deployment, and purge event is logged with timestamp, actor, and outcome. Structured JSONL logs are rotated and retained per policy.',
      bullets: ['Structured JSONL audit logs', 'PostgreSQL audit_log table', 'Promotion event correlation_id', 'Reconciler validates DB ↔ FS'],
    },
  ]

  const complianceItems = [
    'No PII transmitted outside LAN',
    'Right to erasure: full purge on request',
    'Data minimization by TTL enforcement',
    'Consent implied by local use context',
    'Access logs for accountability',
    'Encryption at rest (encrypted SSD)',
    'No third-party analytics or tracking',
    'Fail-closed on policy uncertainty',
  ]

  return (
    <div className="pt-20">
      {/* Hero */}
      <section className="py-20 relative overflow-hidden" style={{
        background: 'radial-gradient(ellipse 60% 50% at 50% 0%, rgba(212,22,106,0.20) 0%, transparent 60%), #080818'
      }}>
        <GradientOrbs />
        <div className="relative max-w-4xl mx-auto px-6 text-center z-10">
          <Reveal>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-widest uppercase mb-6"
              style={{ border: '1px solid rgba(212,22,106,0.35)', color: 'rgba(212,22,106,0.85)', background: 'rgba(212,22,106,0.08)' }}>
              <Shield size={12} /> Privacy & Safety
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <h1 className="text-5xl font-black mb-5 tracking-tight">
              <G>Privacy-first architecture</G>
              <br />for emotionally sensitive AI
            </h1>
          </Reveal>
          <Reveal delay={0.2}>
            <p className="text-lg max-w-2xl mx-auto" style={{ color: 'rgba(255,255,255,0.55)' }}>
              Emotion data is among the most personal information a system can process.
              Affective AI is built from the ground up with zero-cloud, zero-exposure principles.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Four principles */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-6">
          <Reveal>
            <h2 className="text-3xl font-black mb-10 tracking-tight text-center">
              Four <G>core privacy principles</G>
            </h2>
          </Reveal>
          <div className="grid sm:grid-cols-2 gap-6">
            {principles.map(({ icon: Icon, color, title, body, bullets }, i) => (
              <Reveal key={title} delay={i * 0.1}><Card>
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-11 h-11 rounded-xl flex items-center justify-center" style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
                    <Icon size={22} style={{ color }} />
                  </div>
                  <h3 className="font-bold text-base" style={{ color: 'white' }}>{title}</h3>
                </div>
                <p className="text-sm leading-relaxed mb-4" style={{ color: 'rgba(255,255,255,0.50)' }}>{body}</p>
                <ul className="flex flex-col gap-1.5">
                  {bullets.map(b => (
                    <li key={b} className="flex items-start gap-2 text-xs" style={{ color: 'rgba(255,255,255,0.55)' }}>
                      <CheckCircle2 size={12} style={{ color, marginTop: '2px', flexShrink: 0 }} />
                      {b}
                    </li>
                  ))}
                </ul>
              </Card></Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Threat model */}
      <section className="py-10 pb-20">
        <div className="max-w-7xl mx-auto px-6">
          <Reveal>
            <h2 className="text-2xl font-black mb-8 tracking-tight text-center">
              <G>Threat model</G> — cloud vs. on-premise
            </h2>
          </Reveal>
          <Reveal delay={0.1}><ThreatComparison /></Reveal>
        </div>
      </section>

      {/* Retention + Compliance */}
      <section className="py-20" style={{ background: 'rgba(9,9,20,0.90)' }}>
        <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-10">
          <Reveal>
          <div>
            <h2 className="text-2xl font-black mb-6 tracking-tight">
              Data <G>Retention Policy</G>
            </h2>
            <RetentionPolicy />
          </div>
          </Reveal>
          <Reveal delay={0.15}>
          <div>
            <h2 className="text-2xl font-black mb-6 tracking-tight">
              <G>Compliance</G> posture
            </h2>
            <div className="rounded-2xl p-5" style={{ background: 'rgba(11,11,24,0.90)', border: '1px solid rgba(123,47,247,0.20)' }}>
              <div className="text-xs font-semibold tracking-widest uppercase mb-4" style={{ color: 'rgba(255,255,255,0.35)' }}>
                Privacy Compliance Checklist
              </div>
              <ul className="grid sm:grid-cols-2 gap-2">
                {complianceItems.map(item => (
                  <li key={item} className="flex items-start gap-2 text-xs p-2.5 rounded-xl" style={{ background: 'rgba(255,255,255,0.03)', color: 'rgba(255,255,255,0.60)', border: '1px solid rgba(0,180,216,0.10)' }}>
                    <CheckCircle2 size={12} style={{ color: '#00B4D8', marginTop: '2px', flexShrink: 0 }} />
                    {item}
                  </li>
                ))}
              </ul>
              <div className="mt-4 p-3 rounded-xl text-xs" style={{ background: 'rgba(212,22,106,0.08)', border: '1px solid rgba(212,22,106,0.20)', color: 'rgba(255,255,255,0.50)' }}>
                <div className="flex items-center gap-2 mb-1">
                  <AlertCircle size={12} style={{ color: '#D4166A' }} />
                  <span className="font-semibold" style={{ color: '#D4166A' }}>Fail-closed policy</span>
                </div>
                On uncertainty about any privacy policy, the system defaults to denying access, refusing processing, and alerting the maintainer for human review.
              </div>
            </div>
          </div>
          </Reveal>
        </div>
      </section>

      <section className="py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <Reveal>
            <h3 className="text-2xl font-black mb-4 tracking-tight">
              Questions about data handling?
            </h3>
            <div className="flex flex-wrap justify-center gap-3">
              <Link to="/contact" className="btn-primary">Contact Us <ArrowRight size={15} /></Link>
              <Link to="/architecture" className="btn-secondary">View Full Architecture</Link>
            </div>
          </Reveal>
        </div>
      </section>
    </div>
  )
}
