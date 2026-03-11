export default function LogoSVG({ size = 44, showText = true }) {
  return (
    <svg
      viewBox={showText ? "0 0 220 80" : "0 0 80 80"}
      width={showText ? size * (220 / 80) : size}
      height={size}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="heartGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#D4166A" />
          <stop offset="45%" stopColor="#7B2FF7" />
          <stop offset="100%" stopColor="#00B4D8" />
        </linearGradient>
        <linearGradient id="textGradA" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor="#D4166A" />
          <stop offset="50%" stopColor="#7B2FF7" />
          <stop offset="100%" stopColor="#00B4D8" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="1.5" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Heart shape */}
      <path
        d="M40 68 C40 68 8 48 8 26 A16 16 0 0 1 40 22 A16 16 0 0 1 72 26 C72 48 40 68 40 68Z"
        fill="url(#heartGrad)"
        filter="url(#glow)"
      />

      {/* Robot face - white circle */}
      <circle cx="40" cy="36" r="11" fill="white" opacity="0.95" />

      {/* Left eye (open, blue) */}
      <circle cx="36" cy="34" r="3.5" fill="#7B2FF7" />
      <circle cx="36" cy="34" r="2" fill="#00B4D8" />
      <circle cx="37" cy="33" r="0.8" fill="white" opacity="0.9" />

      {/* Right eye (winking / closed) */}
      <path d="M41 34 Q43.5 32.5 46 34" stroke="#555" strokeWidth="1.5" fill="none" strokeLinecap="round" />

      {/* Smile */}
      <path d="M35 39 Q40 43 45 39" stroke="#888" strokeWidth="1.2" fill="none" strokeLinecap="round" />

      {/* Robot head ears/sides */}
      <rect x="28" y="31" width="3" height="6" rx="1.5" fill="rgba(255,255,255,0.6)" />
      <rect x="49" y="31" width="3" height="6" rx="1.5" fill="rgba(255,255,255,0.6)" />

      {/* Circuit nodes on left */}
      <circle cx="18" cy="28" r="2" fill="#D4166A" opacity="0.85" />
      <circle cx="14" cy="36" r="1.5" fill="#D4166A" opacity="0.7" />
      <circle cx="18" cy="44" r="2" fill="#D4166A" opacity="0.85" />
      <line x1="20" y1="28" x2="27" y2="32" stroke="#D4166A" strokeWidth="1" opacity="0.6" />
      <line x1="16" y1="36" x2="27" y2="36" stroke="#D4166A" strokeWidth="1" opacity="0.6" />
      <line x1="20" y1="44" x2="27" y2="40" stroke="#D4166A" strokeWidth="1" opacity="0.6" />

      {/* Brain swirl on right */}
      <path d="M55 26 Q60 24 62 28 Q64 32 60 34 Q64 36 62 40 Q60 44 55 44"
        stroke="#00B4D8" strokeWidth="1.5" fill="none" opacity="0.75" strokeLinecap="round" />
      <path d="M57 30 Q60 29 61 32 Q62 34 59 35"
        stroke="#00B4D8" strokeWidth="1" fill="none" opacity="0.6" strokeLinecap="round" />

      {showText && (
        <>
          {/* "Affective" text */}
          <text
            x="90"
            y="44"
            fontFamily="Inter, system-ui, sans-serif"
            fontSize="26"
            fontWeight="700"
            fill="url(#textGradA)"
            letterSpacing="-0.5"
          >
            Affective
          </text>
          {/* "AI" text */}
          <text
            x="90"
            y="68"
            fontFamily="Inter, system-ui, sans-serif"
            fontSize="14"
            fontWeight="500"
            fill="rgba(255,255,255,0.55)"
            letterSpacing="4"
          >
            EMOTIONALLY INTELLIGENT ROBOTICS
          </text>
        </>
      )}
    </svg>
  )
}
