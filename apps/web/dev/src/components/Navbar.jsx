import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Menu, X } from 'lucide-react'
import LogoSVG from './LogoSVG'

const NAV_LINKS = [
  { to: '/technology',   label: 'Technology' },
  { to: '/architecture', label: 'Architecture' },
  { to: '/privacy',      label: 'Privacy & Safety' },
  { to: '/use-cases',    label: 'Use Cases' },
  { to: '/about',        label: 'About' },
]

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
            Affective AI
          </span>
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-7">
          {NAV_LINKS.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="nav-link"
              style={{ color: pathname === to ? 'white' : undefined }}
            >
              {label}
            </Link>
          ))}
        </div>

        {/* Desktop CTA */}
        <div className="hidden md:flex items-center gap-3">
          <Link to="/contact" className="btn-secondary text-xs px-4 py-2">
            Investor Inquiry
          </Link>
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
          {NAV_LINKS.map(({ to, label }) => (
            <Link
              key={to}
              to={to}
              className="text-sm font-medium py-2"
              style={{ color: pathname === to ? 'white' : 'rgba(255,255,255,0.7)' }}
            >
              {label}
            </Link>
          ))}
          <div className="pt-2 flex flex-col gap-2 border-t" style={{ borderColor: 'rgba(123,47,247,0.15)' }}>
            <Link to="/contact" className="btn-secondary text-sm justify-center">Investor Inquiry</Link>
            <Link to="/contact" className="btn-primary text-sm justify-center">Request Demo</Link>
          </div>
        </div>
      )}
    </nav>
  )
}
