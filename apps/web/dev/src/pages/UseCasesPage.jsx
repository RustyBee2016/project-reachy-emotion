import { Link } from 'react-router-dom'
import { ArrowRight, Heart, Activity, BookOpen, ShoppingBag, Users, Shield, Zap, CheckCircle2 } from 'lucide-react'
import { Reveal } from '../hooks/useReveal'
import { GradientOrbs } from '../components/AnimatedBackground'

const G = ({ children }) => (
  <span style={{
    background: 'linear-gradient(135deg, #D4166A 0%, #7B2FF7 50%, #00B4D8 100%)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
  }}>{children}</span>
)

const USE_CASES = [
  {
    icon: Heart,
    color: '#D4166A',
    title: 'Companion Robotics',
    tagline: 'Presence that understands',
    market: 'Elderly care · Mental health · Daily companionship',
    body: `Loneliness and emotional isolation are pressing challenges in aging populations and mental health contexts. Affective AI enables companion robots to detect emotional state and respond with appropriate gestures and dialogue—creating meaningful, consistent support interactions.`,
    features: [
      'Real-time emotion detection during conversation',
      'Gesture-aware empathetic responses (HUG, EMPATHY, LISTEN)',
      'Confidence-based response modulation avoids over-expression',
      'Privacy-first: no recordings leave the home environment',
      'Continuous model improvement from local interactions',
    ],
    why: 'Privacy constraints are non-negotiable in home and care settings. On-premise processing means residents never become training data for external services.',
  },
  {
    icon: Activity,
    color: '#7B2FF7',
    title: 'Healthcare & Therapy',
    tagline: 'Assistive intelligence for clinical settings',
    market: 'Patient monitoring · Therapy support · Emotional wellness',
    body: `Clinical environments demand rigorous data governance alongside genuine empathetic capability. Affective AI combines the two: real-time emotional state detection with GDPR-aligned local data handling, calibrated confidence scores, and structured audit trails.`,
    features: [
      'Calibrated ECE / Brier score for trustworthy clinical signals',
      'Audit trail: every interaction logged with correlation_id',
      'Gate A validation ensures prediction reliability before deployment',
      'Abstain logic when confidence < 0.60—no overconfident diagnoses',
      'Role-based access control for clinical staff vs. patients',
    ],
    why: 'Healthcare AI must be explainable and auditable. Affective AI provides calibration metrics, structured logs, and fail-closed behavior that clinical settings require.',
  },
  {
    icon: BookOpen,
    color: '#00B4D8',
    title: 'Education',
    tagline: 'Adaptive learning that responds to state',
    market: 'K-12 · Higher ed · Special needs · Corporate training',
    body: `Student engagement, frustration, and understanding are difficult to measure from behavior alone. Affective AI adds an emotional intelligence layer to educational robots: detecting when a student is confused, disengaged, or happy, and adapting pacing and tone accordingly.`,
    features: [
      'Neutral emotion class catches baseline disengagement early',
      'Sad / frustrated detection triggers supportive gesture cues',
      'Happy detection reinforces positive learning moments',
      'Expressiveness tier adjusts robot energy to student state',
      'Local processing protects minor student data completely',
    ],
    why: 'Student data is among the most sensitive in any sector. Affective AI\'s on-premise architecture ensures institutional compliance with FERPA, COPPA, and GDPR-K.',
  },
  {
    icon: ShoppingBag,
    color: '#00C8A0',
    title: 'Customer Experience',
    tagline: 'Empathetic service at scale',
    market: 'Hospitality · Retail · Service robots',
    body: `Service interactions that miss emotional cues feel transactional. Affective AI enables hospitality and retail robots to respond to visible emotional state—adapting tone, gesture, and conversational pacing to create interactions that feel genuinely attentive.`,
    features: [
      'Real-time detection adapts service approach mid-interaction',
      'Happy detection enables celebratory moments (CELEBRATE, WAVE)',
      'Neutral state triggers helpful, informative mode',
      'Sad / frustrated triggers empathetic de-escalation',
      'Runs on-premise: no customer video sent to cloud vendors',
    ],
    why: 'Customer-facing deployments must handle emotional nuance without creating privacy liabilities. Local inference eliminates the exposure risk of cloud emotion APIs.',
  },
]

export default function UseCasesPage() {
  return (
    <div className="pt-20">
      {/* Hero */}
      <section className="py-20 relative overflow-hidden" style={{
        background: 'radial-gradient(ellipse 60% 50% at 50% 0%, rgba(0,180,216,0.18) 0%, transparent 60%), #080818'
      }}>
        <GradientOrbs />
        <div className="relative max-w-4xl mx-auto px-6 text-center z-10">
          <Reveal>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-widest uppercase mb-6"
              style={{ border: '1px solid rgba(0,180,216,0.35)', color: 'rgba(0,180,216,0.85)', background: 'rgba(0,180,216,0.08)' }}>
              Applications
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <h1 className="text-5xl font-black mb-5 tracking-tight">
              Where <G>emotional intelligence</G>
              <br />creates real value
            </h1>
          </Reveal>
          <Reveal delay={0.2}>
            <p className="text-lg max-w-2xl mx-auto" style={{ color: 'rgba(255,255,255,0.55)' }}>
              Especially valuable where emotional context matters but privacy constraints
              are non-negotiable.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Use case cards */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-6 flex flex-col gap-16">
          {USE_CASES.map(({ icon: Icon, color, title, tagline, market, body, features, why }, i) => (
            <Reveal key={title}>
            <div className={`grid lg:grid-cols-2 gap-12 items-start ${i % 2 === 1 ? 'lg:flex-row-reverse' : ''}`}>
              <div className={i % 2 === 1 ? 'lg:order-2' : ''}>
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 rounded-2xl flex items-center justify-center" style={{ background: `${color}18`, border: `1px solid ${color}35` }}>
                    <Icon size={26} style={{ color }} />
                  </div>
                  <div>
                    <div className="text-xs font-semibold tracking-widest uppercase mb-0.5" style={{ color: `${color}90` }}>
                      {market}
                    </div>
                    <h2 className="text-2xl font-black" style={{ color: 'white' }}>{title}</h2>
                  </div>
                </div>
                <p className="text-base font-semibold mb-4" style={{ color: `${color}80` }}>{tagline}</p>
                <p className="text-sm leading-relaxed mb-6" style={{ color: 'rgba(255,255,255,0.55)' }}>{body}</p>
                <ul className="flex flex-col gap-2">
                  {features.map(f => (
                    <li key={f} className="flex items-start gap-2 text-sm" style={{ color: 'rgba(255,255,255,0.60)' }}>
                      <CheckCircle2 size={14} style={{ color, flexShrink: 0, marginTop: '2px' }} />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
              <div className={`rounded-2xl p-6 ${i % 2 === 1 ? 'lg:order-1' : ''}`} style={{
                background: `linear-gradient(145deg, ${color}08 0%, rgba(0,0,0,0) 100%)`,
                border: `1px solid ${color}20`,
              }}>
                <div className="flex items-center gap-2 mb-4">
                  <Shield size={14} style={{ color }} />
                  <span className="text-xs font-semibold tracking-widest uppercase" style={{ color: `${color}80` }}>
                    Why privacy matters here
                  </span>
                </div>
                <p className="text-sm leading-relaxed mb-6" style={{ color: 'rgba(255,255,255,0.55)' }}>{why}</p>
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { val: '0%', label: 'Cloud egress', sub: 'Zero data leaves LAN' },
                    { val: '< 42ms', label: 'Latency', sub: 'Real-time responsiveness' },
                  ].map(({ val, label, sub }) => (
                    <div key={label} className="rounded-xl p-3 text-center" style={{ background: 'rgba(255,255,255,0.04)', border: `1px solid ${color}18` }}>
                      <div className="text-xl font-black font-mono" style={{ color }}>{val}</div>
                      <div className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.65)' }}>{label}</div>
                      <div className="text-xs" style={{ color: 'rgba(255,255,255,0.30)' }}>{sub}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* Summary strip */}
      <section className="py-16" style={{ background: 'rgba(9,9,20,0.90)' }}>
        <div className="max-w-7xl mx-auto px-6">
          <Reveal>
          <h2 className="text-2xl font-black mb-8 text-center tracking-tight">
            The <G>common denominator</G> across all use cases
          </h2>
          </Reveal>
          <div className="grid sm:grid-cols-3 gap-5">
            {[
              { icon: Shield, color: '#D4166A', title: 'Privacy is a requirement', desc: 'Every vertical listed has regulatory or ethical constraints on how emotion data is handled. On-premise is the only viable approach.' },
              { icon: Zap, color: '#7B2FF7', title: 'Latency enables presence', desc: 'Real-time response at < 42ms latency means robotic gestures can accompany the interaction, not follow it seconds later.' },
              { icon: Users, color: '#00B4D8', title: 'Calibration builds trust', desc: 'ECE and Brier score validation means practitioners can trust when the system acts and understand when it abstains.' },
            ].map(({ icon: Icon, color, title, desc }) => (
              <div key={title} className="rounded-2xl p-5 flex flex-col gap-3" style={{
                background: `linear-gradient(145deg, ${color}08 0%, rgba(0,0,0,0) 100%)`,
                border: `1px solid ${color}20`,
              }}>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
                  <Icon size={20} style={{ color }} />
                </div>
                <h3 className="font-bold text-sm" style={{ color: 'white' }}>{title}</h3>
                <p className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.50)' }}>{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <Reveal>
          <h3 className="text-2xl font-black mb-4 tracking-tight">
            Interested in a specific deployment?
          </h3>
          <div className="flex flex-wrap justify-center gap-3">
            <Link to="/contact" className="btn-primary">Discuss Your Use Case <ArrowRight size={15} /></Link>
            <Link to="/technology" className="btn-secondary">Technical Specifications</Link>
          </div>
          </Reveal>
        </div>
      </section>
    </div>
  )
}
