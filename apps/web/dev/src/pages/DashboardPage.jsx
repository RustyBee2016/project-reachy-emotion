import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  Heart, Shield, Activity, Eye, Bell, Clock, Users,
  AlertTriangle, CheckCircle2, BarChart2, Zap, Lock,
  ArrowRight, Radio, MessageCircle, FileText
} from 'lucide-react'
import { Reveal } from '../hooks/useReveal'
import { GridOverlay } from '../components/AnimatedBackground'

const CARE_COLOR = '#10B981'
const SEC_COLOR = '#F59E0B'

/* ─── Mode Toggle ─── */
function ModeToggle({ mode, setMode }) {
  return (
    <div className="inline-flex rounded-xl p-1" style={{ background: 'rgba(13,13,32,0.90)', border: '1px solid rgba(123,47,247,0.20)' }}>
      {[
        { key: 'careflow', label: 'CareFlow', icon: Heart, color: CARE_COLOR },
        { key: 'secureflow', label: 'SecureFlow', icon: Shield, color: SEC_COLOR },
      ].map(({ key, label, icon: Icon, color }) => (
        <button key={key} onClick={() => setMode(key)}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all duration-300"
          style={{
            background: mode === key ? `${color}18` : 'transparent',
            color: mode === key ? color : 'rgba(255,255,255,0.45)',
            border: mode === key ? `1px solid ${color}40` : '1px solid transparent',
          }}>
          <Icon size={15} />
          {label}
        </button>
      ))}
    </div>
  )
}

/* ─── Stat Card ─── */
function StatCard({ icon: Icon, label, value, sub, color }) {
  return (
    <div className="flex flex-col items-center justify-center p-5 rounded-2xl text-center transition-all duration-300 hover:scale-[1.03]"
      style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${color}20` }}
      onMouseOver={e => e.currentTarget.style.boxShadow = `0 4px 24px ${color}20`}
      onMouseOut={e => e.currentTarget.style.boxShadow = 'none'}>
      <Icon size={20} style={{ color, marginBottom: '8px' }} />
      <div className="text-2xl font-black font-mono mb-1" style={{ color }}>{value}</div>
      <div className="text-xs font-semibold" style={{ color: 'rgba(255,255,255,0.7)' }}>{label}</div>
      {sub && <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.35)' }}>{sub}</div>}
    </div>
  )
}

/* ─── Event Feed ─── */
function EventFeed({ events, color }) {
  return (
    <div className="rounded-2xl p-5 h-full" style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${color}20` }}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-bold" style={{ color: 'rgba(255,255,255,0.8)' }}>Event Stream</h3>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: color }} />
          <span className="text-xs font-mono" style={{ color }}>Live</span>
        </div>
      </div>
      <div className="flex flex-col gap-2 max-h-80 overflow-hidden">
        {events.map((evt, i) => (
          <div key={i} className="flex items-start gap-3 p-3 rounded-xl transition-all duration-500"
            style={{
              background: i === 0 ? `${color}08` : 'transparent',
              border: `1px solid ${i === 0 ? `${color}25` : 'rgba(255,255,255,0.04)'}`,
              opacity: 1 - i * 0.12,
            }}>
            <div className="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5" style={{
              background: `${evt.sevColor}15`, border: `1px solid ${evt.sevColor}30`,
            }}>
              <evt.icon size={13} style={{ color: evt.sevColor }} />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold truncate" style={{ color: 'rgba(255,255,255,0.8)' }}>{evt.title}</span>
                <span className="text-xs font-mono flex-shrink-0 ml-2" style={{ color: 'rgba(255,255,255,0.3)' }}>{evt.time}</span>
              </div>
              <p className="text-xs mt-0.5 truncate" style={{ color: 'rgba(255,255,255,0.4)' }}>{evt.detail}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ─── Workflow Status ─── */
function WorkflowStatus({ steps, color }) {
  return (
    <div className="rounded-2xl p-5 h-full" style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${color}20` }}>
      <h3 className="text-sm font-bold mb-4" style={{ color: 'rgba(255,255,255,0.8)' }}>Active Workflow</h3>
      <div className="flex flex-col gap-2">
        {steps.map((s, i) => (
          <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg" style={{
            background: s.status === 'active' ? `${color}10` : 'transparent',
            border: `1px solid ${s.status === 'active' ? `${color}30` : 'rgba(255,255,255,0.04)'}`,
          }}>
            <div className="w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0" style={{
              background: s.status === 'done' ? `${color}20` : s.status === 'active' ? `${color}15` : 'rgba(255,255,255,0.04)',
              border: `1px solid ${s.status === 'done' ? `${color}50` : s.status === 'active' ? `${color}40` : 'rgba(255,255,255,0.08)'}`,
            }}>
              {s.status === 'done' ? <CheckCircle2 size={12} style={{ color }} /> :
               s.status === 'active' ? <div className="w-2 h-2 rounded-full animate-pulse" style={{ background: color }} /> :
               <div className="w-2 h-2 rounded-full" style={{ background: 'rgba(255,255,255,0.15)' }} />}
            </div>
            <span className="text-xs font-medium" style={{
              color: s.status === 'done' ? color : s.status === 'active' ? 'white' : 'rgba(255,255,255,0.3)',
            }}>{s.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ─── Mini Chart (Canvas) ─── */
function MiniChart({ data, color, label }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    canvas.width = canvas.offsetWidth * dpr
    canvas.height = canvas.offsetHeight * dpr
    ctx.scale(dpr, dpr)

    const w = canvas.offsetWidth
    const h = canvas.offsetHeight
    const max = Math.max(...data) * 1.15
    const step = w / (data.length - 1)

    ctx.clearRect(0, 0, w, h)

    // Fill gradient
    const grad = ctx.createLinearGradient(0, 0, 0, h)
    grad.addColorStop(0, `${color}30`)
    grad.addColorStop(1, 'transparent')
    ctx.beginPath()
    ctx.moveTo(0, h)
    data.forEach((v, i) => {
      const x = i * step
      const y = h - (v / max) * h * 0.85
      i === 0 ? ctx.lineTo(x, y) : ctx.lineTo(x, y)
    })
    ctx.lineTo(w, h)
    ctx.closePath()
    ctx.fillStyle = grad
    ctx.fill()

    // Line
    ctx.beginPath()
    data.forEach((v, i) => {
      const x = i * step
      const y = h - (v / max) * h * 0.85
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)
    })
    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.stroke()
  }, [data, color])

  return (
    <div className="rounded-2xl p-4" style={{ background: 'rgba(13,13,32,0.80)', border: `1px solid ${color}20` }}>
      <div className="text-xs font-semibold mb-2" style={{ color: 'rgba(255,255,255,0.6)' }}>{label}</div>
      <canvas ref={canvasRef} className="w-full" style={{ height: '60px' }} />
    </div>
  )
}

/* ═══ CAREFLOW DASHBOARD ═══ */
function CareFlowDashboard() {
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 3000)
    return () => clearInterval(id)
  }, [])

  const queueCount = 3 + (tick % 4)
  const ackTime = (1.8 + Math.random() * 1.4).toFixed(1)

  const events = [
    { title: 'Patient Arrival', detail: 'Lobby zone — acknowledged by Ricci', time: '00:0' + (tick % 10), icon: Eye, sevColor: CARE_COLOR },
    { title: 'Staff Notified', detail: 'Nurse station alert dispatched', time: '00:0' + ((tick + 7) % 10), icon: Bell, sevColor: '#00B4D8' },
    { title: 'Wait Update', detail: 'Patient #2 — est. 6 min remaining', time: '00:0' + ((tick + 5) % 10), icon: Clock, sevColor: '#7B2FF7' },
    { title: 'Ricci Greeting', detail: '"Welcome. Please have a seat."', time: '00:0' + ((tick + 3) % 10), icon: MessageCircle, sevColor: CARE_COLOR },
    { title: 'Queue Updated', detail: 'Position #4 added to dashboard', time: '00:0' + ((tick + 1) % 10), icon: Users, sevColor: '#00B4D8' },
    { title: 'Escalation Cleared', detail: 'High-touch resolved — staff handled', time: '00:0' + ((tick + 9) % 10), icon: CheckCircle2, sevColor: CARE_COLOR },
  ]

  const workflow = [
    { label: 'Arrival detected', status: 'done' },
    { label: 'Event created in Postgres', status: 'done' },
    { label: 'n8n routing workflow', status: 'done' },
    { label: 'Ricci greeting triggered', status: 'active' },
    { label: 'Dashboard updated', status: 'pending' },
    { label: 'Staff notification sent', status: 'pending' },
  ]

  const chartData = Array.from({ length: 12 }, (_, i) => 2 + Math.sin(i * 0.5 + tick * 0.3) * 1.5 + Math.random() * 0.5)

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <StatCard icon={Users} label="In Queue" value={queueCount} sub="patients waiting" color={CARE_COLOR} />
        <StatCard icon={Clock} label="Avg Ack Time" value={`${ackTime}s`} sub="arrival to greeting" color="#00B4D8" />
        <StatCard icon={Activity} label="Events Today" value={42 + tick} sub="all logged" color="#7B2FF7" />
        <StatCard icon={Bell} label="Escalations" value={tick % 5 === 0 ? 1 : 0} sub="active now" color="#D4166A" />
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <EventFeed events={events} color={CARE_COLOR} />
        </div>
        <WorkflowStatus steps={workflow} color={CARE_COLOR} />
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        <MiniChart data={chartData} color={CARE_COLOR} label="Acknowledgment Latency (s)" />
        <MiniChart data={chartData.map(v => v * 2.5)} color="#00B4D8" label="Queue Depth" />
        <MiniChart data={chartData.map(v => Math.max(0, v - 1.5))} color="#7B2FF7" label="Escalation Rate" />
      </div>
    </>
  )
}

/* ═══ SECUREFLOW DASHBOARD ═══ */
function SecureFlowDashboard() {
  const [tick, setTick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 3000)
    return () => clearInterval(id)
  }, [])

  const incidents = 2 + (tick % 3)
  const detectTime = (1.2 + Math.random() * 0.8).toFixed(1)

  const events = [
    { title: 'Anomaly Detected', detail: 'After-hours presence — Lab B corridor', time: '00:0' + (tick % 10), icon: AlertTriangle, sevColor: SEC_COLOR },
    { title: 'Policy Triggered', detail: 'Time-of-day rule — approval required', time: '00:0' + ((tick + 7) % 10), icon: Shield, sevColor: '#EF4444' },
    { title: 'Ricci Announcement', detail: '"This area is currently restricted."', time: '00:0' + ((tick + 5) % 10), icon: Radio, sevColor: SEC_COLOR },
    { title: 'Supervisor Notified', detail: 'SOC alert dispatched — INC-284' + tick, time: '00:0' + ((tick + 3) % 10), icon: Bell, sevColor: '#EF4444' },
    { title: 'Approval Pending', detail: 'Escalation awaiting operator review', time: '00:0' + ((tick + 1) % 10), icon: Lock, sevColor: '#7B2FF7' },
    { title: 'Incident Logged', detail: 'Full audit trail created', time: '00:0' + ((tick + 9) % 10), icon: FileText, sevColor: CARE_COLOR },
  ]

  const workflow = [
    { label: 'Anomaly classified', status: 'done' },
    { label: 'Severity scored: HIGH', status: 'done' },
    { label: 'Policy engine evaluated', status: 'done' },
    { label: 'Approval requested', status: 'active' },
    { label: 'Ricci announcement', status: 'pending' },
    { label: 'Incident archived', status: 'pending' },
  ]

  const chartData = Array.from({ length: 12 }, (_, i) => 1 + Math.sin(i * 0.7 + tick * 0.2) * 0.8 + Math.random() * 0.3)

  return (
    <>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
        <StatCard icon={AlertTriangle} label="Active Incidents" value={incidents} sub="under review" color={SEC_COLOR} />
        <StatCard icon={Zap} label="Detect Time" value={`${detectTime}s`} sub="anomaly to alert" color="#EF4444" />
        <StatCard icon={Activity} label="Events Today" value={87 + tick} sub="all audited" color="#7B2FF7" />
        <StatCard icon={Lock} label="Pending Approvals" value={tick % 4 === 0 ? 2 : 1} sub="awaiting operator" color={SEC_COLOR} />
      </div>

      <div className="grid lg:grid-cols-3 gap-6 mb-6">
        <div className="lg:col-span-2">
          <EventFeed events={events} color={SEC_COLOR} />
        </div>
        <WorkflowStatus steps={workflow} color={SEC_COLOR} />
      </div>

      <div className="grid sm:grid-cols-3 gap-4">
        <MiniChart data={chartData} color={SEC_COLOR} label="Detection Latency (s)" />
        <MiniChart data={chartData.map(v => v * 3)} color="#EF4444" label="Incident Volume" />
        <MiniChart data={chartData.map(v => Math.max(0.2, v * 0.6))} color="#7B2FF7" label="Approval Cycle Time" />
      </div>
    </>
  )
}

/* ═══ PAGE ═══ */
export default function DashboardPage() {
  const [mode, setMode] = useState('careflow')
  const color = mode === 'careflow' ? CARE_COLOR : SEC_COLOR

  return (
    <section className="relative min-h-screen pt-24 pb-20 overflow-hidden">
      <div className="absolute inset-0" style={{
        background: `radial-gradient(ellipse 60% 40% at 50% 0%, ${color}15 0%, transparent 60%), #080818`
      }} />
      <GridOverlay opacity={0.015} />

      <div className="relative max-w-7xl mx-auto px-6 z-10">
        <Reveal>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-8">
            <div>
              <h1 className="text-3xl lg:text-4xl font-black tracking-tight mb-2" style={{ color: 'white' }}>
                Operations Dashboard
              </h1>
              <p className="text-sm" style={{ color: 'rgba(255,255,255,0.45)' }}>
                Live simulation — {mode === 'careflow' ? 'Healthcare Operations' : 'Secure Facility Operations'}
              </p>
            </div>
            <ModeToggle mode={mode} setMode={setMode} />
          </div>
        </Reveal>

        {/* Disclaimer */}
        <Reveal delay={0.05}>
          <div className="flex items-center gap-3 px-4 py-3 rounded-xl mb-6" style={{
            background: `${color}08`, border: `1px solid ${color}20`,
          }}>
            <Activity size={14} style={{ color, flexShrink: 0 }} />
            <span className="text-xs" style={{ color: 'rgba(255,255,255,0.55)' }}>
              This dashboard displays simulated data to demonstrate the ReachyOps AI operator experience.
              In production, this connects to the FastAPI gateway and PostgreSQL event ledger via real-time WebSocket feeds.
            </span>
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          {mode === 'careflow' ? <CareFlowDashboard /> : <SecureFlowDashboard />}
        </Reveal>

        <Reveal delay={0.3}>
          <div className="mt-10 flex flex-wrap justify-center gap-4">
            <Link to={mode === 'careflow' ? '/careflow' : '/secureflow'} className="btn-secondary text-sm px-6 py-3">
              {mode === 'careflow' ? 'CareFlow Details' : 'SecureFlow Details'} <ArrowRight size={15} />
            </Link>
            <Link to="/platform" className="btn-secondary text-sm px-6 py-3">
              Platform Architecture <ArrowRight size={15} />
            </Link>
            <Link to="/governance" className="btn-secondary text-sm px-6 py-3">
              Governance Matrix <ArrowRight size={15} />
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
