import { useState } from 'react'
import { Mail, MessageSquare, TrendingUp, BookOpen, CheckCircle2, ArrowRight } from 'lucide-react'
import LogoSVG from '../components/LogoSVG'
import { Reveal } from '../hooks/useReveal'
import { GradientOrbs } from '../components/AnimatedBackground'

const G = ({ children }) => (
  <span style={{
    background: 'linear-gradient(135deg, #D4166A 0%, #7B2FF7 50%, #00B4D8 100%)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
  }}>{children}</span>
)

const INQUIRY_TYPES = [
  { id: 'demo', icon: MessageSquare, color: '#7B2FF7', label: 'Request Demo', desc: 'See the platform in action with a guided walkthrough.' },
  { id: 'investor', icon: TrendingUp, color: '#D4166A', label: 'Investor Inquiry', desc: 'Discuss partnership and investment opportunities.' },
  { id: 'technical', icon: BookOpen, color: '#00B4D8', label: 'Technical Brief', desc: 'Receive the full technical specification document.' },
  { id: 'collaboration', icon: Mail, color: '#00C8A0', label: 'Research Collaboration', desc: 'Academic or clinical research partnership discussion.' },
]

export default function ContactPage() {
  const [selected, setSelected] = useState('demo')
  const [form, setForm] = useState({ name: '', email: '', org: '', message: '' })
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = (e) => {
    e.preventDefault()
    setSubmitted(true)
  }

  const inputStyle = {
    width: '100%',
    background: 'rgba(11,11,24,0.90)',
    border: '1px solid rgba(123,47,247,0.25)',
    borderRadius: '12px',
    padding: '12px 16px',
    color: 'rgba(255,255,255,0.85)',
    fontSize: '14px',
    outline: 'none',
    transition: 'border-color 0.2s',
    fontFamily: 'Inter, sans-serif',
  }

  const labelStyle = {
    display: 'block',
    fontSize: '12px',
    fontWeight: '600',
    marginBottom: '6px',
    color: 'rgba(255,255,255,0.50)',
    letterSpacing: '0.05em',
  }

  return (
    <div className="pt-20">
      {/* Hero */}
      <section className="py-20 relative overflow-hidden" style={{
        background: 'radial-gradient(ellipse 60% 50% at 50% 0%, rgba(123,47,247,0.22) 0%, transparent 60%), #080818'
      }}>
        <GradientOrbs />
        <div className="relative max-w-3xl mx-auto px-6 text-center z-10">
          <Reveal>
            <h1 className="text-5xl font-black mb-5 tracking-tight">
              Let's <G>connect</G>
            </h1>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="text-lg" style={{ color: 'rgba(255,255,255,0.55)' }}>
              Whether you're an investor, a technical partner, or a potential collaborator—
              we want to hear from you.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Form */}
      <section className="py-20">
        <div className="max-w-6xl mx-auto px-6 grid lg:grid-cols-5 gap-10">

          {/* Sidebar */}
          <div className="lg:col-span-2">
            <h2 className="text-xl font-black mb-6 tracking-tight">
              What are you <G>interested in?</G>
            </h2>
            <div className="flex flex-col gap-3 mb-8">
              {INQUIRY_TYPES.map(({ id, icon: Icon, color, label, desc }) => (
                <button
                  key={id}
                  onClick={() => setSelected(id)}
                  className="flex items-start gap-3 p-4 rounded-2xl text-left transition-all duration-200"
                  style={{
                    background: selected === id
                      ? `linear-gradient(145deg, ${color}12 0%, rgba(0,0,0,0) 100%)`
                      : 'rgba(11,11,24,0.60)',
                    border: `1px solid ${selected === id ? color + '45' : 'rgba(123,47,247,0.15)'}`,
                    transform: selected === id ? 'translateX(4px)' : 'none',
                  }}
                >
                  <div className="w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
                    <Icon size={18} style={{ color }} />
                  </div>
                  <div>
                    <div className="text-sm font-bold" style={{ color: selected === id ? 'white' : 'rgba(255,255,255,0.65)' }}>{label}</div>
                    <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.38)' }}>{desc}</div>
                  </div>
                </button>
              ))}
            </div>

            {/* Direct contact */}
            <div className="rounded-2xl p-5" style={{ background: 'rgba(11,11,24,0.90)', border: '1px solid rgba(123,47,247,0.20)' }}>
              <div className="text-xs font-semibold tracking-widest uppercase mb-3" style={{ color: 'rgba(255,255,255,0.35)' }}>
                Direct Contact
              </div>
              <div className="flex items-center gap-2 text-sm mb-1">
                <Mail size={13} style={{ color: '#7B2FF7' }} />
                <a href="mailto:rustybee255@gmail.com" className="transition-colors" style={{ color: 'rgba(255,255,255,0.60)' }}
                  onMouseOver={e => e.target.style.color = 'white'}
                  onMouseOut={e => e.target.style.color = 'rgba(255,255,255,0.60)'}
                >
                  rustybee255@gmail.com
                </a>
              </div>
              <div className="text-xs mt-2" style={{ color: 'rgba(255,255,255,0.35)' }}>
                Russell Bray · Affective AI · v0.09.1
              </div>
            </div>
          </div>

          {/* Form */}
          <div className="lg:col-span-3">
            {!submitted ? (
              <div className="rounded-2xl p-8" style={{ background: 'rgba(11,11,24,0.90)', border: '1px solid rgba(123,47,247,0.22)' }}>
                <h3 className="text-xl font-black mb-6 tracking-tight" style={{ color: 'white' }}>
                  Send a message
                </h3>
                <form onSubmit={handleSubmit}>
                  <div className="grid sm:grid-cols-2 gap-5 mb-5">
                    <div>
                      <label style={labelStyle}>Name</label>
                      <input
                        type="text"
                        required
                        placeholder="Your name"
                        value={form.name}
                        onChange={e => setForm({ ...form, name: e.target.value })}
                        style={inputStyle}
                        onFocus={e => e.target.style.borderColor = 'rgba(123,47,247,0.60)'}
                        onBlur={e => e.target.style.borderColor = 'rgba(123,47,247,0.25)'}
                      />
                    </div>
                    <div>
                      <label style={labelStyle}>Email</label>
                      <input
                        type="email"
                        required
                        placeholder="you@organisation.com"
                        value={form.email}
                        onChange={e => setForm({ ...form, email: e.target.value })}
                        style={inputStyle}
                        onFocus={e => e.target.style.borderColor = 'rgba(123,47,247,0.60)'}
                        onBlur={e => e.target.style.borderColor = 'rgba(123,47,247,0.25)'}
                      />
                    </div>
                  </div>
                  <div className="mb-5">
                    <label style={labelStyle}>Organisation / Institution</label>
                    <input
                      type="text"
                      placeholder="Company, fund, or university"
                      value={form.org}
                      onChange={e => setForm({ ...form, org: e.target.value })}
                      style={inputStyle}
                      onFocus={e => e.target.style.borderColor = 'rgba(123,47,247,0.60)'}
                      onBlur={e => e.target.style.borderColor = 'rgba(123,47,247,0.25)'}
                    />
                  </div>
                  <div className="mb-5">
                    <label style={labelStyle}>Inquiry type</label>
                    <div className="grid grid-cols-2 gap-2">
                      {INQUIRY_TYPES.map(({ id, label, color }) => (
                        <button
                          type="button"
                          key={id}
                          onClick={() => setSelected(id)}
                          className="py-2 px-3 rounded-xl text-xs font-semibold transition-all"
                          style={{
                            background: selected === id ? `${color}18` : 'rgba(255,255,255,0.04)',
                            border: `1px solid ${selected === id ? color + '50' : 'rgba(255,255,255,0.08)'}`,
                            color: selected === id ? color : 'rgba(255,255,255,0.50)',
                          }}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="mb-6">
                    <label style={labelStyle}>Message</label>
                    <textarea
                      rows={5}
                      required
                      placeholder="Tell us about your interest, organisation, or specific questions..."
                      value={form.message}
                      onChange={e => setForm({ ...form, message: e.target.value })}
                      style={{ ...inputStyle, resize: 'vertical', minHeight: '120px' }}
                      onFocus={e => e.target.style.borderColor = 'rgba(123,47,247,0.60)'}
                      onBlur={e => e.target.style.borderColor = 'rgba(123,47,247,0.25)'}
                    />
                  </div>
                  <button type="submit" className="btn-primary w-full justify-center text-base py-4">
                    Send Message <ArrowRight size={16} />
                  </button>
                </form>
              </div>
            ) : (
              <div className="rounded-2xl p-10 text-center flex flex-col items-center gap-5" style={{
                background: 'linear-gradient(145deg, rgba(0,180,216,0.08) 0%, rgba(123,47,247,0.06) 100%)',
                border: '1px solid rgba(0,180,216,0.25)',
              }}>
                <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: 'rgba(0,180,216,0.15)', border: '1px solid rgba(0,180,216,0.35)' }}>
                  <CheckCircle2 size={32} style={{ color: '#00B4D8' }} />
                </div>
                <div>
                  <h3 className="text-2xl font-black mb-2" style={{ color: 'white' }}>Message sent</h3>
                  <p className="text-sm" style={{ color: 'rgba(255,255,255,0.55)' }}>
                    Thanks, {form.name}. We'll be in touch at {form.email}.
                  </p>
                </div>
                <button
                  onClick={() => { setSubmitted(false); setForm({ name: '', email: '', org: '', message: '' }) }}
                  className="btn-secondary text-sm"
                >
                  Send another message
                </button>
              </div>
            )}

            {/* Investor highlights */}
            {selected === 'investor' && !submitted && (
              <div className="mt-6 rounded-2xl p-5" style={{ background: 'rgba(212,22,106,0.06)', border: '1px solid rgba(212,22,106,0.22)' }}>
                <div className="text-xs font-semibold tracking-widest uppercase mb-3" style={{ color: 'rgba(212,22,106,0.80)' }}>
                  Investor Highlights
                </div>
                <div className="grid sm:grid-cols-2 gap-2 text-xs">
                  {[
                    'Privacy-first moat: no viable cloud substitute for regulated sectors',
                    'Edge deployment: $0 per-inference cloud cost at scale',
                    'Addressable markets: healthcare, education, companion robotics',
                    '10-agent reproducible platform: defensible IP in architecture',
                    'Gate A validated: F1 0.87 on 3-class classification',
                    'Extensible to multimodal: audio, text, wearables in pipeline',
                  ].map(item => (
                    <div key={item} className="flex items-start gap-2 p-2.5 rounded-xl" style={{ background: 'rgba(255,255,255,0.03)', color: 'rgba(255,255,255,0.60)' }}>
                      <div className="w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1" style={{ background: '#D4166A' }} />
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
