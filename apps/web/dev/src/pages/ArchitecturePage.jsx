import { Link } from 'react-router-dom'
import { ArrowRight, Server, Monitor, Cpu, Bot, Database, GitBranch, Layers, Activity } from 'lucide-react'
import { Reveal } from '../hooks/useReveal'
import { GradientOrbs } from '../components/AnimatedBackground'

const G = ({ children }) => (
  <span style={{
    background: 'linear-gradient(135deg, #D4166A 0%, #7B2FF7 50%, #00B4D8 100%)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
  }}>{children}</span>
)

/* Node topology diagram */
function TopologyDiagram() {
  const nodes = [
    { id: 'ubuntu1', label: 'Ubuntu 1', sub: '10.0.4.130', icon: Server, color: '#D4166A', desc: 'FastAPI · PostgreSQL · n8n · Training' },
    { id: 'ubuntu2', label: 'Ubuntu 2', sub: '10.0.4.140', icon: Monitor, color: '#7B2FF7', desc: 'Streamlit UI · Nginx · HTTPS' },
    { id: 'jetson', label: 'Jetson Xavier NX', sub: '10.0.4.150', icon: Cpu, color: '#00B4D8', desc: 'TensorRT · DeepStream · Live Inference' },
    { id: 'reachy', label: 'Reachy Mini', sub: 'gRPC', icon: Bot, color: '#00C8A0', desc: 'Gesture Agent · Reachy SDK' },
  ]
  const connections = [
    { from: 'ubuntu2', to: 'ubuntu1', label: 'FastAPI REST' },
    { from: 'ubuntu1', to: 'jetson', label: 'SCP / SSH' },
    { from: 'jetson', to: 'reachy', label: 'gRPC cues' },
    { from: 'ubuntu1', to: 'ubuntu2', label: 'WebSocket events' },
  ]
  return (
    <div className="rounded-2xl p-6" style={{ background: 'rgba(11,11,24,0.90)', border: '1px solid rgba(123,47,247,0.20)' }}>
      <div className="text-xs font-semibold tracking-widest uppercase mb-5" style={{ color: 'rgba(255,255,255,0.35)' }}>
        System Topology — Static LAN
      </div>
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {nodes.map(({ label, sub, icon: Icon, color, desc }) => (
          <div key={label} className="rounded-xl p-4 text-center" style={{ background: `${color}0A`, border: `1px solid ${color}30` }}>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-3" style={{ background: `${color}18` }}>
              <Icon size={20} style={{ color }} />
            </div>
            <div className="text-sm font-bold mb-0.5" style={{ color: 'rgba(255,255,255,0.85)' }}>{label}</div>
            <div className="text-xs font-mono mb-2" style={{ color }}>{sub}</div>
            <div className="text-xs leading-relaxed" style={{ color: 'rgba(255,255,255,0.40)' }}>{desc}</div>
          </div>
        ))}
      </div>
      {/* Connections */}
      <div className="flex flex-col gap-2">
        <div className="text-xs font-semibold tracking-widest uppercase mb-1" style={{ color: 'rgba(255,255,255,0.30)' }}>
          Data Flows
        </div>
        {connections.map(({ from, to, label }) => (
          <div key={`${from}-${to}`} className="flex items-center gap-2 text-xs" style={{ color: 'rgba(255,255,255,0.50)' }}>
            <span className="font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(123,47,247,0.12)', color: '#7B2FF7' }}>{from}</span>
            <span style={{ color: 'rgba(255,255,255,0.25)' }}>──▶</span>
            <span className="font-mono px-2 py-0.5 rounded" style={{ background: 'rgba(0,180,216,0.10)', color: '#00B4D8' }}>{to}</span>
            <span style={{ color: 'rgba(255,255,255,0.30)' }}>·</span>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* Data flow: video pipeline */
function DataFlowPipeline() {
  const stages = [
    { label: 'Ingest', desc: 'Upload / generate video', color: '#D4166A', path: '/videos/temp/' },
    { label: 'Label', desc: '3-class human review', color: '#A820D8', path: 'happy|sad|neutral' },
    { label: 'Promote', desc: 'Move to train dataset', color: '#7B2FF7', path: '/videos/train/<label>/' },
    { label: 'Extract', desc: 'Frame extraction + split', color: '#3893E8', path: '/train/run/<id>/' },
    { label: 'Train', desc: 'EfficientNet-B0 finetune', color: '#00B4D8', path: 'MLflow + Gate A' },
    { label: 'Deploy', desc: 'TensorRT → Jetson', color: '#00C8A0', path: 'shadow→canary→prod' },
  ]
  return (
    <div className="rounded-2xl p-6" style={{ background: 'rgba(11,11,24,0.90)', border: '1px solid rgba(123,47,247,0.20)' }}>
      <div className="text-xs font-semibold tracking-widest uppercase mb-5" style={{ color: 'rgba(255,255,255,0.35)' }}>
        ML Pipeline — Video to Deployment
      </div>
      <div className="relative">
        <div className="hidden lg:block absolute top-7 left-0 right-0 h-0.5"
          style={{ background: 'linear-gradient(90deg, #D4166A, #7B2FF7, #00B4D8)', opacity: 0.3 }} />
        <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
          {stages.map(({ label, desc, color, path }, i) => (
            <div key={label} className="flex flex-col items-center text-center gap-2">
              <div className="relative w-14 h-14 rounded-xl flex flex-col items-center justify-center z-10"
                style={{ background: `${color}15`, border: `1px solid ${color}45` }}>
                <span className="text-xs font-mono" style={{ color: `${color}80` }}>0{i + 1}</span>
                <span className="text-xs font-bold" style={{ color }}>{label}</span>
              </div>
              <p className="text-xs" style={{ color: 'rgba(255,255,255,0.45)' }}>{desc}</p>
              <code className="text-xs font-mono px-1.5 py-0.5 rounded" style={{ background: `${color}12`, color: `${color}90`, fontSize: '9px' }}>
                {path}
              </code>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

/* Agent orchestration flow */
function AgentFlow() {
  const groups = [
    {
      label: 'Data Pipeline',
      color: '#D4166A',
      agents: ['01 Ingest', '02 Label', '03 Promote', '04 Reconcile'],
    },
    {
      label: 'ML Pipeline',
      color: '#7B2FF7',
      agents: ['05 Train', '06 Evaluate', '07 Deploy'],
    },
    {
      label: 'Operations',
      color: '#00B4D8',
      agents: ['08 Privacy', '09 Observe', '10 Gesture'],
    },
  ]
  return (
    <div className="rounded-2xl p-6" style={{ background: 'rgba(11,11,24,0.90)', border: '1px solid rgba(123,47,247,0.20)' }}>
      <div className="text-xs font-semibold tracking-widest uppercase mb-5" style={{ color: 'rgba(255,255,255,0.35)' }}>
        n8n Agent Orchestration — Ubuntu 1
      </div>
      <div className="grid md:grid-cols-3 gap-5">
        {groups.map(({ label, color, agents }) => (
          <div key={label} className="rounded-xl p-4" style={{ background: `${color}08`, border: `1px solid ${color}25` }}>
            <div className="text-xs font-semibold mb-3 tracking-wide" style={{ color }}>{label}</div>
            <div className="flex flex-col gap-2">
              {agents.map(a => (
                <div key={a} className="flex items-center gap-2 text-xs py-1.5 px-3 rounded-lg" style={{ background: 'rgba(255,255,255,0.04)', color: 'rgba(255,255,255,0.60)' }}>
                  <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
                  {a}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="mt-4 pt-4 flex flex-wrap gap-3 text-xs" style={{ borderTop: '1px solid rgba(123,47,247,0.12)' }}>
        {[['Orchestration', 'n8n'], ['Retry Policy', 'Exponential backoff, max 5'], ['Idempotency', 'Idempotency-Key on all writes'], ['DLQ', 'Human review on retry exhaustion']].map(([k, v]) => (
          <div key={k} className="flex gap-1.5">
            <span style={{ color: 'rgba(255,255,255,0.35)' }}>{k}:</span>
            <span style={{ color: 'rgba(255,255,255,0.65)' }}>{v}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* Storage layout */
function StorageLayout() {
  const dirs = [
    { path: '/media/project_data/reachy_emotion/videos/', type: 'root', color: '#7B2FF7' },
    { path: '  temp/', type: 'dir', color: '#D4166A', desc: 'Incoming videos (TTL 7d)' },
    { path: '  train/', type: 'dir', color: '#00B4D8', desc: 'Labeled training videos' },
    { path: '    happy/ · sad/ · neutral/', type: 'sub', color: '#00C8A0', desc: '3-class dirs' },
    { path: '    run/<run_id>/train_ds_<id>/', type: 'sub', color: '#3893E8', desc: 'Per-run frame splits' },
    { path: '    run/<run_id>/valid_ds_<id>/', type: 'sub', color: '#3893E8', desc: 'Per-run validation split' },
    { path: '  test/', type: 'dir', color: '#00B4D8', desc: 'Unlabeled test set' },
    { path: '  thumbs/', type: 'dir', color: '#7B2FF7', desc: 'Generated JPG thumbnails' },
    { path: '  manifests/', type: 'dir', color: '#D4166A', desc: 'JSON dataset manifests' },
  ]
  return (
    <div className="rounded-xl p-4 font-mono text-xs" style={{ background: 'rgba(6,6,18,0.95)', border: '1px solid rgba(123,47,247,0.18)' }}>
      <div className="text-xs font-semibold tracking-widest uppercase mb-3" style={{ color: 'rgba(255,255,255,0.30)', fontFamily: 'Inter, sans-serif' }}>
        Filesystem Layout
      </div>
      <div className="flex flex-col gap-1">
        {dirs.map(({ path, color, desc }) => (
          <div key={path} className="flex items-center justify-between gap-4">
            <span style={{ color }}>{path}</span>
            {desc && <span style={{ color: 'rgba(255,255,255,0.30)', fontSize: '10px', fontFamily: 'Inter, sans-serif' }}>{desc}</span>}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function ArchitecturePage() {
  return (
    <div className="pt-20">
      {/* Hero */}
      <section className="py-20 relative overflow-hidden" style={{
        background: 'radial-gradient(ellipse 60% 50% at 50% 0%, rgba(123,47,247,0.22) 0%, transparent 60%), #080818'
      }}>
        <GradientOrbs />
        <div className="relative max-w-4xl mx-auto px-6 text-center z-10">
          <Reveal>
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-semibold tracking-widest uppercase mb-6"
              style={{ border: '1px solid rgba(123,47,247,0.35)', color: 'rgba(123,47,247,0.85)', background: 'rgba(123,47,247,0.08)' }}>
              System Architecture
            </div>
          </Reveal>
          <Reveal delay={0.1}>
            <h1 className="text-5xl font-black mb-5 tracking-tight">
              Designed for <G>local control</G>, predictable deployment
            </h1>
          </Reveal>
          <Reveal delay={0.2}>
            <p className="text-lg max-w-2xl mx-auto" style={{ color: 'rgba(255,255,255,0.55)' }}>
              A four-node, static-LAN topology with explicit agent boundaries,
              immutable audit trails, and zero cloud dependencies.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Content */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-6 flex flex-col gap-8">
          <Reveal><TopologyDiagram /></Reveal>
          <Reveal delay={0.1}><DataFlowPipeline /></Reveal>
          <div className="grid lg:grid-cols-2 gap-8">
            <Reveal><AgentFlow /></Reveal>
            <Reveal delay={0.15}><div className="flex flex-col gap-5">
              <StorageLayout />
              {/* DB stack */}
              <div className="rounded-2xl p-5" style={{ background: 'rgba(11,11,24,0.90)', border: '1px solid rgba(123,47,247,0.20)' }}>
                <div className="text-xs font-semibold tracking-widest uppercase mb-4" style={{ color: 'rgba(255,255,255,0.35)' }}>
                  Database Stack
                </div>
                <div className="flex flex-col gap-2 text-xs">
                  {[
                    ['Engine', 'PostgreSQL 16', '#00B4D8'],
                    ['Host', '10.0.4.130:5432', '#7B2FF7'],
                    ['Database', 'reachy_emotion', '#D4166A'],
                    ['Role', 'reachy_dev', '#00C8A0'],
                    ['Migrations', 'Alembic (SQLAlchemy)', '#00B4D8'],
                    ['Tables', '9 ORM-managed + 3 legacy', '#7B2FF7'],
                    ['Tracking', 'MLflow (file-based)', '#D4166A'],
                  ].map(([k, v, c]) => (
                    <div key={k} className="flex items-center justify-between py-1.5 px-3 rounded-lg" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(123,47,247,0.08)' }}>
                      <span style={{ color: 'rgba(255,255,255,0.40)' }}>{k}</span>
                      <span className="font-mono" style={{ color: c }}>{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div></Reveal>
          </div>
        </div>
      </section>

      {/* SLOs */}
      <section className="py-16" style={{ background: 'rgba(9,9,20,0.90)' }}>
        <div className="max-w-7xl mx-auto px-6">
          <Reveal>
          <h2 className="text-2xl font-black mb-8 tracking-tight text-center">
            Observability <G>SLOs</G>
          </h2>
          </Reveal>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: 'Planner p50', val: '≤ 2s', color: '#D4166A' },
              { label: 'Planner p95', val: '≤ 5s', color: '#7B2FF7' },
              { label: 'Error budget', val: '< 1%/wk', color: '#00B4D8' },
              { label: 'Trace propagation', val: 'correlation_id', color: '#00C8A0' },
            ].map(({ label, val, color }) => (
              <div key={label} className="kpi-card">
                <div className="text-xl font-black font-mono mb-1" style={{ color }}>{val}</div>
                <div className="text-xs" style={{ color: 'rgba(255,255,255,0.45)' }}>{label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="py-16">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <Reveal>
          <div className="flex flex-wrap justify-center gap-3">
            <Link to="/technology" className="btn-primary">Deep Dive Technology <ArrowRight size={15} /></Link>
            <Link to="/privacy" className="btn-secondary">Privacy Architecture</Link>
          </div>
          </Reveal>
        </div>
      </section>
    </div>
  )
}
