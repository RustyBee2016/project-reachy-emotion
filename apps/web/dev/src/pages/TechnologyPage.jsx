import { Link } from 'react-router-dom'
import { ArrowRight, Cpu, Brain, Zap, BarChart2, Activity, CheckCircle2, ChevronRight } from 'lucide-react'
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
    background: 'linear-gradient(145deg, rgba(123,47,247,0.08) 0%, rgba(0,180,216,0.04) 100%)',
    border: '1px solid rgba(123,47,247,0.20)',
  }}>
    {children}
  </div>
)

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
