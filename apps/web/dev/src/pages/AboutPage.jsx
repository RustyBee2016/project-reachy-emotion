import { Link } from 'react-router-dom'
import { ArrowRight, ExternalLink, Cpu, Brain, Shield, GitBranch, Layers, Bot, Heart } from 'lucide-react'
import { Reveal } from '../hooks/useReveal'
import { GradientOrbs } from '../components/AnimatedBackground'

const REPO_URL = 'https://github.com/RustyBee2016/project-reachy-emotion'

const G = ({ children }) => (
  <span style={{
    background: 'linear-gradient(135deg, #D4166A 0%, #7B2FF7 50%, #00B4D8 100%)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
  }}>{children}</span>
)

const PHASES = [
  {
    n: '01', color: '#D4166A', title: 'Phase 1 — Offline ML Classification',
    status: 'Active',
    desc: 'Foundation infrastructure: web app, EfficientNet-B0 training pipeline, FastAPI gateway, MLflow tracking, Gate A validation. 15 labeled videos (5 per class), training pipeline validated.',
    items: ['EfficientNet-B0 + HSEmotion weights', 'FastAPI Media Mover service', 'Streamlit curation UI', 'n8n agentic orchestration (10 agents)', 'Gate A: F1 ≥ 0.84, ECE ≤ 0.08', 'PostgreSQL + Alembic schema'],
  },
  {
    n: '02', color: '#7B2FF7', title: 'Phase 2 — Emotional Intelligence Layer',
    status: 'Active',
    desc: 'Degree, PPE, and EQ layers that translate raw classification scores into nuanced behavioral guidance. Gesture modulation and LLM prompt conditioning.',
    items: ['Confidence degree scoring (0–1)', '8-class Ekman PPE taxonomy mapping', 'ECE / Brier / MCE EQ calibration', '5-tier gesture modulation engine', 'Emotion-conditioned LLM prompts', 'gesture_modulator.py integration'],
  },
  {
    n: '03', color: '#00B4D8', title: 'Phase 3 — Edge Deployment & Real-Time',
    status: 'Planned',
    desc: 'Jetson Xavier NX deployment with TensorRT conversion, DeepStream pipeline, Gates B & C validation, and a staged shadow→canary→production rollout.',
    items: ['ONNX → TensorRT FP16 conversion', 'DeepStream real-time pipeline', 'Gate B: FPS ≥ 25, latency ≤ 120ms', 'Gate C: user satisfaction target', 'Staged rollout with auto-rollback', 'Reachy Mini gesture execution'],
  },
]

const STACK = [
  { icon: Brain, color: '#D4166A', label: 'Model', val: 'EfficientNet-B0 + HSEmotion (VGGFace2 + AffectNet)' },
  { icon: Cpu, color: '#7B2FF7', label: 'Runtime', val: 'PyTorch → ONNX → TensorRT FP16' },
  { icon: Layers, color: '#00B4D8', label: 'Orchestration', val: 'n8n · 10 cooperating agents' },
  { icon: GitBranch, color: '#00C8A0', label: 'Tracking', val: 'MLflow · Alembic · SHA-256 dataset hashing' },
  { icon: Shield, color: '#D4166A', label: 'Privacy', val: 'On-premise · mTLS · TTL purge · RBAC' },
  { icon: Bot, color: '#7B2FF7', label: 'Hardware', val: 'Reachy Mini · Jetson Xavier NX 16GB' },
]

export default function AboutPage() {
  return (
    <div className="pt-20">
      {/* Hero */}
      <section className="py-20 relative overflow-hidden" style={{
        background: 'radial-gradient(ellipse 60% 50% at 50% 0%, rgba(123,47,247,0.22) 0%, transparent 60%), #080818'
      }}>
        <GradientOrbs />
        <div className="relative max-w-4xl mx-auto px-6 text-center z-10">
          <Reveal>
            <div className="mb-8 flex flex-col items-center gap-4">
              {/* Logo centrepiece with glow halo */}
              <div className="relative inline-flex items-center justify-center">
                <div className="absolute inset-0 rounded-full" style={{
                  background: 'radial-gradient(circle, rgba(212,22,106,0.28) 0%, rgba(123,47,247,0.18) 45%, transparent 70%)',
                  filter: 'blur(18px)',
                  transform: 'scale(1.6)',
                }} />
                <div className="relative p-5 rounded-3xl" style={{
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(212,22,106,0.22)',
                  boxShadow: '0 0 60px rgba(212,22,106,0.20), 0 0 30px rgba(123,47,247,0.15)',
                }}>
                  <img
                    src="/affective-ai-logo.png"
                    alt="Affective AI"
                    style={{ width: 110, height: 110, objectFit: 'contain' }}
                  />
                </div>
              </div>
              {/* Brand wordmark + tagline */}
              <div>
                <div className="text-4xl font-black tracking-tight mb-1" style={{
                  background: 'linear-gradient(135deg, #D4166A 0%, #7B2FF7 50%, #00B4D8 100%)',
                  WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
                }}>
                  Affective AI
                </div>
                <div className="text-xs font-semibold tracking-[0.28em] uppercase" style={{ color: 'rgba(255,255,255,0.35)' }}>
                  Emotionally Intelligent Robotics
                </div>
              </div>
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <h1 className="text-4xl font-black mb-5 tracking-tight">
              About the <G>Project</G>
            </h1>
          </Reveal>
          <Reveal delay={0.2}>
            <p className="text-lg max-w-2xl mx-auto leading-relaxed" style={{ color: 'rgba(255,255,255,0.55)' }}>
              We are building the foundation layer for emotionally intelligent robotics —
              a platform that combines edge AI perception, privacy-first architecture, and
              embodied empathetic response.
            </p>
          </Reveal>
          <Reveal delay={0.3}>
            <div className="mt-8 flex flex-wrap justify-center gap-4">
              <a
                href={REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-primary flex items-center gap-2"
                style={{ padding: '0.85rem 1.6rem' }}
              >
                View ML Lab Repo
                <ExternalLink size={16} />
              </a>
              <Link to="/contact" className="btn-secondary flex items-center gap-2" style={{ padding: '0.85rem 1.6rem' }}>
                Partner / Collaborate
                <ArrowRight size={16} />
              </Link>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Mission */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-6 grid lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase mb-5"
              style={{ border: '1px solid rgba(212,22,106,0.35)', color: 'rgba(212,22,106,0.85)', background: 'rgba(212,22,106,0.08)' }}>
              <Heart size={11} /> Mission
            </div>
            <h2 className="text-3xl font-black mb-5 tracking-tight">
              Making robots that <G>genuinely understand</G> how you feel
            </h2>
            <p className="text-sm leading-relaxed mb-4" style={{ color: 'rgba(255,255,255,0.55)' }}>
              The gap between technically capable robots and emotionally intelligent companions
              is not a hardware problem. It's a perception and response architecture problem.
            </p>
            <p className="text-sm leading-relaxed mb-4" style={{ color: 'rgba(255,255,255,0.55)' }}>
              Affective AI addresses this with a complete embodied AI system: from video-based
              emotion recognition to gesture-aware robotic response, with calibrated confidence
              metrics ensuring the system knows when to act and when to hold back.
            </p>
            <p className="text-sm leading-relaxed" style={{ color: 'rgba(255,255,255,0.55)' }}>
              Everything runs on-premise. No cloud exposure. No external dependencies. No surveillance-
              adjacent data flows. Just emotionally aware, locally trustworthy AI.
            </p>
          </div>
          <div className="rounded-2xl p-6" style={{
            background: 'linear-gradient(145deg, rgba(123,47,247,0.08) 0%, rgba(0,180,216,0.04) 100%)',
            border: '1px solid rgba(123,47,247,0.20)',
          }}>
            <div className="text-xs font-semibold tracking-widest uppercase mb-5" style={{ color: 'rgba(255,255,255,0.35)' }}>
              Core Values
            </div>
            {[
              { val: 'Privacy-first', desc: 'Emotion data stays where it belongs—on-premise, under institutional control.', color: '#D4166A' },
              { val: 'Trustworthy', desc: 'Calibration metrics (ECE, Brier) quantify reliability. Abstain logic handles uncertainty.', color: '#7B2FF7' },
              { val: 'Reproducible', desc: 'Dataset hashing, MLflow lineage, and Alembic migrations make every result auditable.', color: '#00B4D8' },
              { val: 'Human-in-the-loop', desc: 'Promotion, deployment, and policy changes require explicit human approval.', color: '#00C8A0' },
            ].map(({ val, desc, color }) => (
              <div key={val} className="flex gap-3 mb-4 last:mb-0">
                <div className="w-1 rounded-full flex-shrink-0" style={{ background: color }} />
                <div>
                  <div className="text-sm font-bold mb-0.5" style={{ color: 'white' }}>{val}</div>
                  <div className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.48)' }}>{desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Project phases */}
      <section className="py-20" style={{ background: 'rgba(9,9,20,0.90)' }}>
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-black mb-10 tracking-tight text-center">
            Project <G>Roadmap</G>
          </h2>
          <div className="flex flex-col gap-6">
            {PHASES.map(({ n, color, title, status, desc, items }) => (
              <div key={n} className="rounded-2xl p-6" style={{
                background: `linear-gradient(145deg, ${color}07 0%, rgba(0,0,0,0) 100%)`,
                border: `1px solid ${color}22`,
              }}>
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl flex items-center justify-center font-black text-sm" style={{ background: `${color}18`, color }}>
                      {n}
                    </div>
                    <div>
                      <h3 className="font-bold text-base" style={{ color: 'white' }}>{title}</h3>
                    </div>
                  </div>
                  <span className="text-xs px-3 py-1 rounded-full font-semibold flex-shrink-0" style={{
                    background: status === 'Active' ? 'rgba(74,222,128,0.12)' : 'rgba(212,22,106,0.12)',
                    color: status === 'Active' ? '#4ade80' : '#D4166A',
                    border: `1px solid ${status === 'Active' ? 'rgba(74,222,128,0.30)' : 'rgba(212,22,106,0.35)'}`,
                  }}>
                    {status}
                  </span>
                </div>
                <p className="text-sm leading-relaxed mb-4" style={{ color: 'rgba(255,255,255,0.50)' }}>{desc}</p>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {items.map(item => (
                    <div key={item} className="flex items-center gap-2 text-xs py-1.5 px-3 rounded-lg" style={{
                      background: 'rgba(255,255,255,0.03)',
                      color: 'rgba(255,255,255,0.55)',
                    }}>
                      <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
                      {item}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Tech stack */}
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-6">
          <h2 className="text-3xl font-black mb-10 tracking-tight text-center">
            <G>Technology</G> stack
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {STACK.map(({ icon: Icon, color, label, val }) => (
              <div key={label} className="flex items-start gap-4 rounded-2xl p-5" style={{
                background: 'rgba(11,11,24,0.90)',
                border: `1px solid ${color}20`,
              }}>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
                  <Icon size={20} style={{ color }} />
                </div>
                <div>
                  <div className="text-xs font-semibold tracking-widest uppercase mb-1" style={{ color: `${color}80` }}>{label}</div>
                  <div className="text-sm" style={{ color: 'rgba(255,255,255,0.70)' }}>{val}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Team / origin */}
      <section className="py-16" style={{ background: 'rgba(9,9,20,0.90)' }}>
        <div className="max-w-3xl mx-auto px-6 text-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase mb-6"
            style={{ border: '1px solid rgba(123,47,247,0.35)', color: 'rgba(123,47,247,0.85)', background: 'rgba(123,47,247,0.08)' }}>
            Origin
          </div>
          <h2 className="text-2xl font-black mb-5 tracking-tight">
            From research project to <G>deployable platform</G>
          </h2>
          <p className="text-sm leading-relaxed mb-4" style={{ color: 'rgba(255,255,255,0.55)' }}>
            Affective AI emerged from Project Reachy (v0.09.1 / Reachy_Local_08.4.2)—
            a deep research effort into privacy-first emotion recognition for companion robotics.
            The system is designed, built, and operated by Russell Bray with a focus on
            rigorous engineering discipline and reproducible research.
          </p>
          <p className="text-sm leading-relaxed mb-8" style={{ color: 'rgba(255,255,255,0.45)' }}>
            The platform is offered for research, educational, and institutional use.
            Investment partnerships and clinical collaborations are actively sought.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link to="/contact" className="btn-primary">Get in Touch <ArrowRight size={15} /></Link>
            <Link to="/technology" className="btn-secondary">Technical Overview</Link>
          </div>
        </div>
      </section>
    </div>
  )
}
