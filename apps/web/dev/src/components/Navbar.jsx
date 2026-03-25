import { useState, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X, Github, Linkedin, ChevronDown, Heart, Shield, Layers, BarChart2 } from 'lucide-react'
import LogoSVG from './LogoSVG'

const NAV_LINKS = [
  { to: '/platform',     label: 'Platform' },
  {
    label: 'Solutions',
    children: [
      { to: '/careflow',   label: 'CareFlow', desc: 'Healthcare Operations', icon: Heart, color: '#10B981' },
      { to: '/secureflow', label: 'SecureFlow', desc: 'Cybersecurity / Secure Facilities', icon: Shield, color: '#F59E0B' },
      { to: '/dashboard',  label: 'Live Dashboard', desc: 'Simulated Ops Demo', icon: BarChart2, color: '#7B2FF7' },
    ],
  },
  { to: '/technology',   label: 'Technology' },
  { to: '/architecture', label: 'Architecture' },
  { to: '/governance',   label: 'Governance' },
  { to: '/about',        label: 'About' },
]

function SolutionsDropdown({ item, pathname }) {
  const [dropOpen, setDropOpen] = useState(false)
  const ref = useRef(null)
  const isActive = item.children.some(c => pathname === c.to)

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setDropOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className="relative">
      <button
        className="nav-link flex items-center gap-1"
        style={{ color: isActive ? 'white' : undefined }}
        onClick={() => setDropOpen(!dropOpen)}
      >
        {item.label} <ChevronDown size={13} style={{ transition: 'transform 0.2s', transform: dropOpen ? 'rotate(180deg)' : 'none' }} />
      </button>
      {dropOpen && (
        <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 w-64 rounded-xl py-2 z-50"
          style={{
            background: 'rgba(13,13,32,0.97)',
            border: '1px solid rgba(123,47,247,0.25)',
            backdropFilter: 'blur(20px)',
            boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
          }}>
          {item.children.map(({ to, label, desc, icon: Icon, color }) => (
            <Link key={to} to={to} onClick={() => setDropOpen(false)}
              className="flex items-start gap-3 px-4 py-3 transition-all duration-200"
              style={{ color: pathname === to ? color : 'rgba(255,255,255,0.75)' }}
              onMouseOver={e => e.currentTarget.style.background = 'rgba(123,47,247,0.08)'}
              onMouseOut={e => e.currentTarget.style.background = 'transparent'}>
              <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5"
                style={{ background: `${color}15`, border: `1px solid ${color}30` }}>
                <Icon size={15} style={{ color }} />
              </div>
              <div>
                <div className="text-sm font-semibold">{label}</div>
                <div className="text-xs mt-0.5" style={{ color: 'rgba(255,255,255,0.40)' }}>{desc}</div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => { setOpen(false) }, [pathname])

  return (
    <nav
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
      style={{
        background: scrolled
          ? 'rgba(8,8,24,0.92)'
          : 'transparent',
        backdropFilter: scrolled ? 'blur(16px)' : 'none',
        WebkitBackdropFilter: scrolled ? 'blur(16px)' : 'none',
        borderBottom: scrolled ? '1px solid rgba(123,47,247,0.15)' : '1px solid transparent',
      }}
    >
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <LogoSVG size={36} showText={false} />
          <span
            className="font-bold text-lg tracking-tight"
            style={{
              background: 'linear-gradient(135deg, #D4166A 0%, #7B2FF7 50%, #00B4D8 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
            }}
          >
            ReachyOps AI
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-6">
          {NAV_LINKS.map((item) => (
            item.children ? (
              <SolutionsDropdown key={item.label} item={item} pathname={pathname} />
            ) : (
              <Link
                key={item.to}
                to={item.to}
                className="nav-link"
                style={{ color: pathname === item.to ? 'white' : undefined }}
              >
                {item.label}
              </Link>
            )
          ))}
        </div>

        {/* Desktop social + CTA */}
        <div className="hidden md:flex items-center gap-3">
          <a
            href="https://github.com/RustyBee2016/project-reachy-emotion"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub repository"
            className="p-2 rounded-lg transition-colors"
            style={{ color: 'rgba(255,255,255,0.55)' }}
            onMouseOver={e => e.currentTarget.style.color = 'white'}
            onMouseOut={e => e.currentTarget.style.color = 'rgba(255,255,255,0.55)'}
          >
            <Github size={18} />
          </a>
          <a
            href="https://www.linkedin.com/in/russell-bray-485721172/"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="LinkedIn profile"
            className="p-2 rounded-lg transition-colors"
            style={{ color: 'rgba(255,255,255,0.55)' }}
            onMouseOver={e => e.currentTarget.style.color = '#0A66C2'}
            onMouseOut={e => e.currentTarget.style.color = 'rgba(255,255,255,0.55)'}
          >
            <Linkedin size={18} />
          </a>
          <Link to="/contact" className="btn-primary text-xs px-4 py-2">
            Request Demo
          </Link>
        </div>

        {/* Mobile hamburger */}
        <button
          className="md:hidden p-2 rounded-lg transition-colors"
          style={{ color: 'rgba(255,255,255,0.8)' }}
          onClick={() => setOpen(!open)}
          aria-label="Toggle menu"
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile menu */}
      {open && (
        <div
          className="md:hidden absolute top-16 left-0 right-0 px-6 py-4 flex flex-col gap-4"
          style={{
            background: 'rgba(8,8,24,0.97)',
            borderBottom: '1px solid rgba(123,47,247,0.20)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
          }}
        >
          {NAV_LINKS.map((item) => (
            item.children ? (
              <div key={item.label} className="flex flex-col gap-1">
                <span className="text-xs font-semibold tracking-widest uppercase py-2" style={{ color: 'rgba(255,255,255,0.35)' }}>{item.label}</span>
                {item.children.map(({ to, label, icon: Icon, color }) => (
                  <Link key={to} to={to} className="flex items-center gap-2 text-sm font-medium py-1.5 pl-2" style={{ color: pathname === to ? color : 'rgba(255,255,255,0.7)' }}>
                    <Icon size={14} style={{ color }} /> {label}
                  </Link>
                ))}
              </div>
            ) : (
              <Link
                key={item.to}
                to={item.to}
                className="text-sm font-medium py-2"
                style={{ color: pathname === item.to ? 'white' : 'rgba(255,255,255,0.7)' }}
              >
                {item.label}
              </Link>
            )
          ))}
          <div className="pt-2 flex flex-col gap-2 border-t" style={{ borderColor: 'rgba(123,47,247,0.15)' }}>
            <Link to="/contact" className="btn-primary text-sm justify-center">Request Demo</Link>
            <div className="flex items-center gap-3 pt-1">
              <a
                href="https://github.com/RustyBee2016/project-reachy-emotion"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-sm py-1"
                style={{ color: 'rgba(255,255,255,0.55)' }}
              >
                <Github size={16} /> GitHub
              </a>
              <a
                href="https://www.linkedin.com/in/russell-bray-485721172/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 text-sm py-1"
                style={{ color: 'rgba(255,255,255,0.55)' }}
              >
                <Linkedin size={16} /> LinkedIn
              </a>
            </div>
          </div>
        </div>
      )}
    </nav>
  )
}
