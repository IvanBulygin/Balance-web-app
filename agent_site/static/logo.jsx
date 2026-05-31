// ===== logo.jsx =====
// Balance AI wordmark + logo mark (the "A" with brand spectrum gradient).
// Two variants:
//   <BalLogo size={N} variant="full"  />  → BALANCE^AI wordmark
//   <BalLogo size={N} variant="mark"  />  → just the gradient "A" inside a circle
//   <BalLogo size={N} variant="mono"  />  → wordmark in single ink color
//
// Spectrum stops match the brand: cyan → blue → indigo → violet → magenta → pink

const _BAL_GRAD = 'linear-gradient(135deg,#56b6c6 0%,#3fa9f5 18%,#559bf0 36%,#8e77e2 56%,#e978da 78%,#f3a9fd 100%)';

// The Balance "Ā" mark — a flat-topped trapezoid (altar/table) glyph.
// Exact reproduction of the brand logo: wide cap bar on top, two splayed
// legs forming a truncated triangle, and the A-crossbar near the top.
const BalMarkGlyph = ({ size = 40, gradId }) => {
  const W = 120,H = 120;
  const w = size,h = size * (H / W);
  const uid = React.useMemo(() => 'mg' + Math.random().toString(36).slice(2, 7), []);
  const g = gradId || uid;
  return (
    <svg width={w} height={h} viewBox={`0 0 ${W} ${H}`} fill="none"
    style={{ display: 'block', overflow: 'visible' }}>
      <defs>
        <linearGradient id={g} gradientUnits="userSpaceOnUse" x1="60" y1="8" x2="60" y2="112">
          <stop offset="0%" stopColor="#E978DA" />
          <stop offset="50%" stopColor="#8E77E2" />
          <stop offset="100%" stopColor="#3FA9F5" />
        </linearGradient>
      </defs>
      {/* open trapezoid (truncated triangle / table) — flat open top, splayed legs */}
      <path d="M50 40 L24 106 L96 106 L70 40"
      stroke={`url(#${g})`} strokeWidth="11"
      strokeLinejoin="round" strokeLinecap="round" />
      {/* wide flat cap bar floating on top */}
      <path d="M18 14 L102 14"
      stroke={`url(#${g})`} strokeWidth="13" strokeLinecap="round" />
    </svg>);

};

const BalLogoMark = ({ size = 36, glow = false, dark = false }) => {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%',
      background: dark ? '#0E0B2E' : 'white',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: glow ? '0 6px 22px rgba(85,33,229,0.28)' : 'none',
      flexShrink: 0
    }}>
      <BalMarkGlyph size={size * 0.6} />
    </div>);

};

const BalLogo = ({
  size = 36,
  variant = 'full', // 'full' | 'mark' | 'mono'
  glow = false,
  color = '#0E0B2E',
  showAi = true,
  align = 'center'
}) => {
  if (variant === 'mark') return <BalLogoMark size={size} glow={glow} />;

  const uid = React.useMemo(() => 'bl' + Math.random().toString(36).slice(2, 7), []);
  const fontSize = size;
  const aiSize = Math.max(8, size * 0.34);
  // glyph replaces the 2nd "A" — sized to cap height, sits on the baseline
  const glyphW = fontSize * 0.74;

  const aiFill = variant === 'mono' ?
  { color } :
  { background: _BAL_GRAD, WebkitBackgroundClip: 'text', backgroundClip: 'text', color: 'transparent' };

  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: fontSize * 0.04, lineHeight: 1,
      fontFamily: "'Priego','Fraunces',Georgia,serif", fontWeight: 700,
      letterSpacing: '0.02em', fontSize, color,
      whiteSpace: 'nowrap'
    }}>
      <span style={{ transform: `translateY(${fontSize * 0.05}px)` }}>BAL</span>
      {/* gradient altar glyph in place of the 2nd A */}
      <span style={{ display: 'inline-flex', alignItems: 'center' }}>
        <BalMarkGlyph size={glyphW} />
      </span>
      <span style={{ transform: `translateY(${fontSize * 0.05}px)` }}>NCE</span>
      {showAi &&
      <sup style={{
        fontSize: aiSize,
        marginLeft: fontSize * 0.04,
        alignSelf: 'flex-start',
        fontWeight: 700,
        letterSpacing: '0.02em',
        ...aiFill
      }}>AI</sup>
      }
    </div>);

};

window.BalLogo = BalLogo;
window.BalLogoMark = BalLogoMark;