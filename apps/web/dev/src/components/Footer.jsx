import { Link } from 'react-router-dom'
import LogoSVG from './LogoSVG'
import { Mail, Shield, Cpu, GitBranch } from 'lucide-react'

const LINKS = {
  Platform: [
    { to: '/technology',   label: 'Technology' },
    { to: '/architecture', label: 'Architecture' },
    { to: '/privacy',      label: 'Privacy & Safety' },
  ],
  Company: [
    { to: '/use-cases', label: 'Use Cases' },
    { to: '/about',     label: 'About' },
    { to: '/contact',   label: 'Contact' },
  ],
  Resources: [
    { to: '/contact', label: 'Investor Inquiry' },
    { to: '/contact', label: 'Request Demo' },
    { to: '/technology', label: 'Technical Overview' },
  ],
}

export default function Footer() {
  return (
    <footer
      className="relative pt-16 pb-8"
      style={{ borderTop: '1px solid rgba(123,47,247,0.15)' }}
    >
      {/* Glow */}
      <div
        className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-px"
        style={{ background: 'linear-gradient(90deg, transparent, rgba(123,47,247,0.5), transparent)' }}
      />

      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-10 mb-12">
          {/* Brand */}
          <div className="md:col-span-2">
            <Link to="/" className="flex items-center gap-3 mb-4">
              <LogoSVG size={36} showText={false} />
              <span
                className="font-bold text-xl"
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
            <p className="text-sm leading-relaxed mb-4" style={{ color: 'rgba(255,255,255,0.45)' }}>
              Privacy-first emotion recognition meets empathetic robotics.
              Your companion that truly understands how you feel.
            </p>
            <div className="flex items-center gap-2 text-xs" style={{ color: 'rgba(255,255,255,0.35)' }}>
              <Mail size={13} />
              <a href="mailto:rustybee255@gmail.com" className="hover:text-white transition-colors">
                rustybee255@gmail.com
              </a>
            </div>

            {/* Trust badges */}
            <div className="flex gap-3 mt-5">
              {[
                { icon: Shield, label: 'Privacy-First' },
                { icon: Cpu, label: 'Edge AI' },
                { icon: GitBranch, label: 'Open Research' },
              ].map(({ icon: Icon, label }) => (
                <span
                  key={label}
                  className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
                  style={{
                    border: '1px solid rgba(123,47,247,0.25)',
                    color: 'rgba(255,255,255,0.5)',
                    background: 'rgba(123,47,247,0.06)',
                  }}
                >
                  <Icon size={10} />
                  {label}
                </span>
              ))}
            </div>
          </div>

          {/* Nav columns */}
          {Object.entries(LINKS).map(([heading, items]) => (
            <div key={heading}>
              <h4 className="text-xs font-semibold tracking-widest uppercase mb-4" style={{ color: 'rgba(255,255,255,0.35)' }}>
                {heading}
              </h4>
              <ul className="flex flex-col gap-2.5">
                {items.map(({ to, label }) => (
                  <li key={label}>
                    <Link
                      to={to}
                      className="text-sm transition-colors"
                      style={{ color: 'rgba(255,255,255,0.50)' }}
                      onMouseOver={e => e.target.style.color = 'rgba(255,255,255,0.90)'}
                      onMouseOut={e => e.target.style.color = 'rgba(255,255,255,0.50)'}
                    >
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div
          className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs"
          style={{
            borderTop: '1px solid rgba(123,47,247,0.12)',
            color: 'rgba(255,255,255,0.30)',
          }}
        >
          <span>© {new Date().getFullYear()} Affective AI — Emotionally Intelligent Robotics</span>
          <span className="font-mono" style={{ color: 'rgba(123,47,247,0.50)' }}>
            v0.09.1 · Reachy_Local_08.4.2 · Research / Educational Use
          </span>
        </div>
      </div>
    </footer>
  )
}
