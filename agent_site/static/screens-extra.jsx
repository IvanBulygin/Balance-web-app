// ===== screens-extra.jsx =====
// Additional screens beyond the original 7.
// Each component is exported on `window`. Uses tokens already defined
// in Balance App v2.html: --brand, --accent, --grad-balance, --ink-*, --rule, etc.
// Screens here:
//   SignInScreen, IntakeScreen, AddSuppScreen, RemindersScreen,
//   ChatHistoryScreen, LabsScreen, ProfileScreen, PaywallScreen

const _GRAD = 'linear-gradient(135deg,#56b6c6 0%,#3fa9f5 18%,#559bf0 36%,#8e77e2 56%,#e978da 78%,#f3a9fd 100%)';

// Tabbar reused — match the existing screens' tabbar pattern.
const ExtraTabbar = ({ active = 'home' }) => {
  const { Icon } = window;
  const items = [
    { k: 'home',  label: 'Today',    I: Icon.Home  },
    { k: 'ask',   label: 'Ask',      I: Icon.Spark },
    { k: 'stack', label: 'Stack',    I: Icon.Stack },
    { k: 'learn', label: 'Learn',    I: Icon.Book  },
    { k: 'me',    label: 'Profile',  I: Icon.User  },
  ];
  return (
    <div className="tabbar" style={{padding:'10px 18px 26px', display:'flex', justifyContent:'space-between'}}>
      {items.map(it => (
        <div key={it.k} className={'tab-item'+(it.k===active?' active':'')}>
          <it.I size={22} c={it.k===active?'var(--brand)':'var(--ink-4)'}/>
          <div>{it.label}</div>
        </div>
      ))}
    </div>
  );
};

// Tiny inline components
const Pill = ({ children, tone='soft', style={} }) => {
  const tones = {
    soft:   { background:'var(--brand-soft)', color:'var(--brand)' },
    accent: { background:'var(--accent-soft)', color:'var(--brand)' },
    dark:   { background:'var(--brand)',      color:'white' },
    light:  { background:'#f4f3f8',           color:'#4a4858' },
    grad:   { background:_GRAD,               color:'white' },
  };
  return (
    <span style={{
      display:'inline-flex', alignItems:'center', gap:5,
      padding:'4px 10px', borderRadius:999, fontSize:11, fontWeight:600,
      letterSpacing:'0.02em', ...tones[tone], ...style,
    }}>{children}</span>
  );
};

// ──────────────────────────────────────────────────────────────────────────
// 08 · Sign in
// ──────────────────────────────────────────────────────────────────────────
const SignInScreen = () => {
  const { BalLogo } = window;
  return (
    <div className="screen-root" style={{background:'var(--bg)'}}>
      <div className="scroll" style={{height:'100%', position:'relative'}}>
        {/* Status bar */}
        <div style={{height:54}}/>
        {/* Gradient orb backdrop */}
        <div style={{
          position:'absolute', top:-80, left:-80, width:340, height:340,
          background:'radial-gradient(circle, rgba(243,169,253,0.45) 0%, rgba(142,119,226,0.15) 45%, transparent 70%)',
          filter:'blur(18px)', pointerEvents:'none',
        }}/>
        <div style={{
          position:'absolute', top:80, right:-110, width:280, height:280,
          background:'radial-gradient(circle, rgba(86,182,198,0.35) 0%, rgba(63,169,245,0.10) 50%, transparent 75%)',
          filter:'blur(20px)', pointerEvents:'none',
        }}/>

        <div style={{padding:'16px 22px 0', position:'relative'}}>
          <BalLogo size={32} variant="full"/>
        </div>

        {/* Hero */}
        <div style={{padding:'72px 26px 0', position:'relative'}}>
          <div style={{fontSize:11, letterSpacing:'0.18em', textTransform:'uppercase',
            color:'var(--brand)', fontWeight:700, marginBottom:14}}>
            Welcome
          </div>
          <div className="serif" style={{fontSize:46, lineHeight:1.05, color:'var(--ink)', letterSpacing:'-0.025em'}}>
            What does your<br/>
            <em style={{
              background:_GRAD, WebkitBackgroundClip:'text', backgroundClip:'text', color:'transparent',
            }}>body need</em><br/>today?
          </div>
          <div style={{fontSize:15, color:'var(--ink-3)', marginTop:18, lineHeight:1.5, maxWidth:'90%'}}>
            Ask anything about sleep, stress, energy, or recovery. We search the evidence and rank a stack — with dose, timing, and grade.
          </div>
        </div>

        {/* Auth buttons */}
        <div style={{padding:'40px 22px 0', display:'flex', flexDirection:'column', gap:10, position:'relative'}}>
          <button style={{
            border:'none', height:54, borderRadius:16, fontSize:15, fontWeight:600,
            background:'var(--brand)', color:'white',
            display:'flex', alignItems:'center', justifyContent:'center', gap:10,
            boxShadow:'0 8px 24px rgba(85,33,229,0.28)',
          }}>
            <span style={{
              width:18, height:18, borderRadius:5, background:'white',
              display:'inline-flex', alignItems:'center', justifyContent:'center',
            }}>
              <span style={{fontSize:11, color:'#0E0B2E', fontWeight:800}}></span>
            </span>
            Continue with Apple
          </button>

          <button style={{
            border:'1px solid var(--rule)', height:54, borderRadius:16,
            fontSize:15, fontWeight:600, color:'var(--ink)', background:'white',
            display:'flex', alignItems:'center', justifyContent:'center', gap:10,
          }}>
            <span style={{
              width:18, height:18, borderRadius:'50%',
              background:'conic-gradient(#4285f4 0%,#34a853 25%,#fbbc05 60%,#ea4335 90%,#4285f4 100%)',
            }}/>
            Continue with Google
          </button>

          <button style={{
            border:'1px solid var(--rule)', height:54, borderRadius:16,
            fontSize:15, fontWeight:500, color:'var(--ink-2)', background:'transparent',
            display:'flex', alignItems:'center', justifyContent:'center', gap:8,
          }}>
            Continue with email
          </button>
        </div>

        {/* Footer */}
        <div style={{padding:'56px 26px 30px', position:'relative'}}>
          <div style={{fontSize:11, color:'var(--ink-4)', lineHeight:1.6, textAlign:'center'}}>
            By continuing you agree to our <span style={{color:'var(--brand)', fontWeight:600}}>Terms</span> and <span style={{color:'var(--brand)', fontWeight:600}}>Privacy</span>.
          </div>
          <div style={{fontSize:11, color:'var(--ink-4)', marginTop:14, textAlign:'center', lineHeight:1.5}}>
            Not medical advice. For personal health decisions, consult a qualified professional.
          </div>
        </div>
      </div>
    </div>
  );
};
window.SignInScreen = SignInScreen;

// ──────────────────────────────────────────────────────────────────────────
// 09 · Intake quiz — goals
// ──────────────────────────────────────────────────────────────────────────
const IntakeScreen = () => {
  const { Icon } = window;
  const goals = [
    { k:'Sleep deeper',     I:Icon.Moon,    sel:true,  d:'Fall asleep · stay asleep' },
    { k:'Steady energy',    I:Icon.Sun,     sel:true,  d:'No 3pm crash' },
    { k:'Lower stress',     I:Icon.Heart,   sel:true,  d:'Calm without sedation' },
    { k:'Build muscle',     I:Icon.Dumbbell,sel:false, d:'Strength & recovery' },
    { k:'Sharpen focus',    I:Icon.Brain,   sel:false, d:'Cognition · attention' },
    { k:'Healthier skin',   I:Icon.Droplet, sel:false, d:'Hydration · barrier' },
    { k:'Joint comfort',    I:Icon.Bone,    sel:false, d:'Fall asleep · stay asleep' },
    { k:'Stronger immunity',I:Icon.Shield,  sel:false, d:'Daily defense' },
  ];
  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom:130}}>
        <div style={{height:54}}/>

        {/* Header */}
        <div style={{padding:'10px 22px 0', display:'flex', alignItems:'center', justifyContent:'space-between'}}>
          <Icon.Back size={20} c="var(--ink-2)"/>
          <div style={{fontSize:11, fontWeight:600, color:'var(--ink-3)', letterSpacing:'0.08em'}}>2 of 5</div>
          <div style={{fontSize:13, color:'var(--brand)', fontWeight:500}}>Skip</div>
        </div>

        {/* Progress */}
        <div style={{padding:'18px 22px 0'}}>
          <div style={{height:4, borderRadius:4, background:'#ece5fc', overflow:'hidden'}}>
            <div style={{width:'40%', height:'100%', background:_GRAD}}/>
          </div>
        </div>

        {/* Title */}
        <div style={{padding:'30px 22px 0'}}>
          <div className="serif" style={{fontSize:30, lineHeight:1.1, color:'var(--ink)', letterSpacing:'-0.02em'}}>
            Pick the goals you want<br/>Balance to <em style={{
              background:_GRAD, WebkitBackgroundClip:'text', backgroundClip:'text', color:'transparent',
            }}>focus on</em>.
          </div>
          <div style={{fontSize:13, color:'var(--ink-3)', marginTop:10, lineHeight:1.5}}>
            Choose up to four. We'll prioritize evidence and recommendations around these.
          </div>
        </div>

        {/* Goals grid */}
        <div style={{padding:'22px 18px 0', display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
          {goals.map((g,i) => (
            <div key={i} style={{
              padding:'14px 14px 12px', borderRadius:18,
              background: g.sel ? 'var(--brand)' : 'white',
              border: g.sel ? 'none' : '1px solid var(--rule)',
              color: g.sel ? 'white' : 'var(--ink)',
              position:'relative',
              boxShadow: g.sel ? '0 6px 18px rgba(85,33,229,0.18)' : 'none',
            }}>
              <div style={{
                width:36, height:36, borderRadius:11,
                background: g.sel ? 'rgba(255,255,255,0.16)' : 'var(--brand-soft)',
                display:'flex', alignItems:'center', justifyContent:'center', marginBottom:10,
              }}>
                <g.I size={19} c={g.sel ? 'white' : 'var(--brand)'}/>
              </div>
              <div style={{fontSize:14, fontWeight:600, letterSpacing:'-0.01em'}}>{g.k}</div>
              <div style={{fontSize:11, opacity: g.sel ? 0.78 : 1, color: g.sel?'white':'var(--ink-3)', marginTop:2, lineHeight:1.4}}>{g.d}</div>
              {g.sel && (
                <div style={{position:'absolute', top:11, right:11, width:20, height:20, borderRadius:'50%',
                  background:'white', display:'flex', alignItems:'center', justifyContent:'center'}}>
                  <Icon.Check size={11} c="var(--brand)"/>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Footer CTA */}
      <div style={{
        position:'absolute', left:0, right:0, bottom:0,
        padding:'14px 22px 30px',
        background:'linear-gradient(to top, white 60%, rgba(255,255,255,0))',
      }}>
        <button style={{
          width:'100%', height:54, borderRadius:16, border:'none',
          background:'var(--brand)', color:'white', fontSize:15, fontWeight:600,
          boxShadow:'0 8px 22px rgba(85,33,229,0.26)',
          display:'flex', alignItems:'center', justifyContent:'center', gap:8,
        }}>
          Continue · 3 selected
          <Icon.Chevron size={14} c="white"/>
        </button>
      </div>
    </div>
  );
};
window.IntakeScreen = IntakeScreen;

// ──────────────────────────────────────────────────────────────────────────
// 10 · Add to stack — product picker
// ──────────────────────────────────────────────────────────────────────────
const AddSuppScreen = () => {
  const { Icon } = window;
  const recs = [
    { n:'Magnesium glycinate', maker:'Pure Encapsulations', dose:'120 mg · 2 caps', g:'A', form:'Capsule', sel:true, why:'Best for sleep & relaxation' },
    { n:'Magnesium citrate',   maker:'Thorne',              dose:'150 mg · 1 cap',  g:'B', form:'Capsule', why:'Faster onset · GI side effects' },
    { n:'Magnesium L-threonate',maker:'Magtein',            dose:'2000 mg · 3 caps', g:'B', form:'Capsule', why:'Crosses BBB · cognition' },
    { n:'Magnesium oxide',     maker:'Generic',             dose:'400 mg · 1 cap',  g:'C', form:'Capsule', why:'Cheap · poor absorption' },
  ];
  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom:120}}>
        <div style={{height:54}}/>

        <div style={{padding:'10px 22px 0', display:'flex', alignItems:'center', justifyContent:'space-between'}}>
          <Icon.Back size={20} c="var(--ink-2)"/>
          <div style={{fontSize:14, fontWeight:600}}>Add to stack</div>
          <div style={{width:20}}/>
        </div>

        {/* Search */}
        <div style={{padding:'18px 18px 0'}}>
          <div style={{
            display:'flex', alignItems:'center', gap:10, padding:'12px 14px',
            background:'#f4f3f8', borderRadius:14,
          }}>
            <Icon.Search size={17} c="var(--ink-3)"/>
            <div style={{fontSize:14, color:'var(--ink)', fontWeight:500}}>Magnesium</div>
            <div style={{flex:1}}/>
            <div style={{fontSize:12, color:'var(--ink-3)'}}>4 forms</div>
          </div>
        </div>

        {/* Filter chips */}
        <div style={{padding:'12px 18px 0', display:'flex', gap:6, overflow:'hidden'}}>
          <Pill tone="dark">All</Pill>
          <Pill tone="light">Capsule</Pill>
          <Pill tone="light">Powder</Pill>
          <Pill tone="light">Liquid</Pill>
          <Pill tone="light">Vegan</Pill>
        </div>

        {/* Section title */}
        <div style={{padding:'20px 22px 8px', display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
          <div className="serif" style={{fontSize:18, color:'var(--ink)'}}>Recommended forms</div>
          <div style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'0.06em'}}>BY EVIDENCE</div>
        </div>

        {/* Cards */}
        <div style={{padding:'0 18px', display:'flex', flexDirection:'column', gap:10}}>
          {recs.map((r,i) => (
            <div key={i} className="bal-card" style={{
              padding:14,
              border: r.sel ? '2px solid var(--brand)' : '1px solid var(--rule)',
              boxShadow: r.sel ? '0 8px 24px rgba(85,33,229,0.12)' : 'var(--sh-1)',
              position:'relative',
            }}>
              <div style={{display:'flex', alignItems:'flex-start', gap:12}}>
                {/* "Pill" thumbnail */}
                <div style={{
                  width:46, height:46, borderRadius:14,
                  background: r.g==='A' ? _GRAD : r.g==='B' ? 'linear-gradient(135deg,#e978da,#8e77e2)' : '#e7e7eb',
                  display:'flex', alignItems:'center', justifyContent:'center',
                  flexShrink:0,
                }}>
                  <div style={{width:18, height:30, borderRadius:18, background:'rgba(255,255,255,0.3)', border:'1.5px solid rgba(255,255,255,0.7)'}}/>
                </div>
                <div style={{flex:1, minWidth:0}}>
                  <div style={{display:'flex', alignItems:'center', gap:6}}>
                    <div style={{fontSize:14, fontWeight:600, color:'var(--ink)', letterSpacing:'-0.01em'}}>{r.n}</div>
                    <div className={`ev-badge ${r.g.toLowerCase()}`}>{r.g}</div>
                  </div>
                  <div style={{fontSize:12, color:'var(--ink-3)', marginTop:1}}>{r.maker}</div>
                  <div style={{fontSize:12, color:'var(--ink-2)', marginTop:8, lineHeight:1.4}}>{r.why}</div>
                  <div style={{display:'flex', alignItems:'center', gap:6, marginTop:9}}>
                    <Pill tone="light" style={{fontSize:10}}>{r.form}</Pill>
                    <Pill tone="light" style={{fontSize:10}}>{r.dose}</Pill>
                  </div>
                </div>
                <div style={{
                  width:24, height:24, borderRadius:'50%',
                  background: r.sel ? 'var(--brand)' : 'transparent',
                  border: r.sel ? 'none' : '1.6px solid var(--rule)',
                  display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
                }}>
                  {r.sel && <Icon.Check size={12} c="white"/>}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CTA */}
      <div style={{position:'absolute', left:0, right:0, bottom:0, padding:'14px 22px 30px',
        background:'linear-gradient(to top, white 60%, rgba(255,255,255,0))'}}>
        <button style={{
          width:'100%', height:54, borderRadius:16, border:'none',
          background:'var(--brand)', color:'white', fontSize:15, fontWeight:600,
          boxShadow:'0 8px 22px rgba(85,33,229,0.26)',
        }}>
          Add to my stack
        </button>
      </div>
    </div>
  );
};
window.AddSuppScreen = AddSuppScreen;

// ──────────────────────────────────────────────────────────────────────────
// 11 · Reminders / Schedule
// ──────────────────────────────────────────────────────────────────────────
const RemindersScreen = () => {
  const { Icon } = window;
  const blocks = [
    { time:'7:00 AM', title:'With breakfast', items:[
      {n:'Vitamin D3', d:'2000 IU', g:'A', done:true},
      {n:'Omega-3 EPA',d:'1 g',     g:'A', done:true},
    ]},
    { time:'12:30 PM', title:'After lunch', items:[
      {n:'Creatine',   d:'5 g',     g:'A', done:true},
    ]},
    { time:'9:00 PM', title:'Before bed', items:[
      {n:'Magnesium glycinate', d:'300 mg', g:'A', done:false, next:true},
      {n:'Ashwagandha',         d:'600 mg', g:'B', done:false},
      {n:'L-Theanine',          d:'200 mg', g:'B', done:false},
    ]},
  ];

  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom:120}}>
        <div style={{height:54}}/>

        {/* Header */}
        <div style={{padding:'10px 22px 0', display:'flex', alignItems:'center', justifyContent:'space-between'}}>
          <Icon.Back size={20} c="var(--ink-2)"/>
          <div style={{fontSize:14, fontWeight:600}}>Reminders</div>
          <Icon.Plus size={20} c="var(--brand)"/>
        </div>

        <div style={{padding:'24px 22px 0'}}>
          <div className="serif" style={{fontSize:32, lineHeight:1.05, letterSpacing:'-0.02em'}}>
            Six pings,<br/><em style={{
              background:_GRAD, WebkitBackgroundClip:'text', backgroundClip:'text', color:'transparent',
            }}>three windows</em>.
          </div>
          <div style={{fontSize:13, color:'var(--ink-3)', marginTop:10, lineHeight:1.5}}>
            Grouped by meal · Balance batches reminders so you don't get pinged 8× a day.
          </div>
        </div>

        {/* Today summary */}
        <div style={{padding:'22px 18px 0'}}>
          <div className="bal-card" style={{padding:'14px 16px', display:'flex', alignItems:'center', gap:14}}>
            <div style={{width:46, height:46, borderRadius:'50%', background:_GRAD,
              display:'flex', alignItems:'center', justifyContent:'center', color:'white', fontWeight:700, fontFamily:"'Priego','Fraunces',serif"}}>
              4/6
            </div>
            <div style={{flex:1}}>
              <div style={{fontSize:13, fontWeight:600}}>Today's plan</div>
              <div style={{fontSize:12, color:'var(--ink-3)', marginTop:2}}>Next: Magnesium · in 2h 14m</div>
            </div>
            <div style={{
              padding:'6px 12px', borderRadius:14,
              background:'var(--brand-soft)', color:'var(--brand)',
              fontSize:12, fontWeight:600,
            }}>Edit</div>
          </div>
        </div>

        {/* Time blocks */}
        <div style={{padding:'22px 18px 0', display:'flex', flexDirection:'column', gap:14}}>
          {blocks.map((b,bi) => (
            <div key={bi}>
              <div style={{display:'flex', alignItems:'baseline', justifyContent:'space-between', padding:'0 4px 8px'}}>
                <div className="mono" style={{fontSize:12, fontWeight:600, color:'var(--ink-3)', letterSpacing:'0.04em'}}>{b.time}</div>
                <div style={{fontSize:12, color:'var(--ink-3)', fontWeight:500}}>{b.title}</div>
              </div>
              <div className="bal-card" style={{padding:'4px 0'}}>
                {b.items.map((it,ii) => (
                  <div key={ii} style={{display:'flex', alignItems:'center', padding:'12px 16px',
                    borderBottom: ii<b.items.length-1?'0.5px solid var(--rule)':'none'}}>
                    <div style={{
                      width:22, height:22, borderRadius:'50%',
                      background: it.done?'var(--brand)':'transparent',
                      border: it.done?'none':'1.6px solid var(--rule)',
                      display:'flex', alignItems:'center', justifyContent:'center', marginRight:12, flexShrink:0,
                    }}>
                      {it.done && <Icon.Check size={11} c="white"/>}
                    </div>
                    <div style={{flex:1, minWidth:0}}>
                      <div style={{fontSize:14, fontWeight:500, color: it.done?'var(--ink-3)':'var(--ink)',
                        textDecoration: it.done?'line-through':'none'}}>{it.n}</div>
                      <div style={{fontSize:12, color:'var(--ink-3)', marginTop:1}}>{it.d}</div>
                    </div>
                    {it.next && <Pill tone="grad" style={{marginRight:8, fontSize:10}}>NEXT</Pill>}
                    <div className={`ev-badge ${it.g.toLowerCase()}`}>{it.g}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
window.RemindersScreen = RemindersScreen;

// ──────────────────────────────────────────────────────────────────────────
// 12 · Chat history
// ──────────────────────────────────────────────────────────────────────────
const ChatHistoryScreen = () => {
  const { Icon, BalLogoMark } = window;
  const sections = [
    { date:'Today', items:[
      {q:'Best magnesium for sleep?', a:'Glycinate · 300mg · 45min before bed', t:'2:14 PM'},
      {q:'Why does creatine bloat me?', a:'Loading phase · drop to 3g/day', t:'9:30 AM'},
    ]},
    { date:'Yesterday', items:[
      {q:'Ashwagandha and SSRIs?', a:'Caution · talk to your doctor first', t:'10:42 PM'},
      {q:'Vitamin D dosage in winter', a:'2000–4000 IU · pair with K2', t:'8:11 AM'},
    ]},
    { date:'This week', items:[
      {q:'Caffeine cutoff for deep sleep', a:'~10h half-life · stop by noon', t:'Mon'},
      {q:'Omega-3 EPA vs DHA balance', a:'2:1 EPA:DHA for mood', t:'Sun'},
      {q:'Probiotic strains for IBS', a:'L. plantarum 299v · B. infantis', t:'Sun'},
    ]},
  ];

  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom:130}}>
        <div style={{height:54}}/>
        <div style={{padding:'10px 22px 0', display:'flex', alignItems:'center', justifyContent:'space-between'}}>
          <Icon.Back size={20} c="var(--ink-2)"/>
          <div style={{fontSize:14, fontWeight:600}}>Conversations</div>
          <Icon.Search size={18} c="var(--ink-2)"/>
        </div>

        <div style={{padding:'24px 22px 0'}}>
          <div className="serif" style={{fontSize:32, lineHeight:1.05, letterSpacing:'-0.02em'}}>
            Everything you<br/>asked Balance.
          </div>
        </div>

        {/* New chat button */}
        <div style={{padding:'18px 18px 0'}}>
          <div className="bal-card" style={{
            padding:'14px 16px', display:'flex', alignItems:'center', gap:12,
            background:_GRAD, border:'none', color:'white',
            boxShadow:'0 10px 26px rgba(85,33,229,0.22)',
          }}>
            <BalLogoMark size={36}/>
            <div style={{flex:1}}>
              <div style={{fontSize:14, fontWeight:600}}>Start a new conversation</div>
              <div style={{fontSize:12, opacity:0.85, marginTop:2}}>Ask about anything · 17 guides</div>
            </div>
            <Icon.Chevron size={16} c="white"/>
          </div>
        </div>

        {/* Sections */}
        <div style={{padding:'24px 18px 0', display:'flex', flexDirection:'column', gap:18}}>
          {sections.map((s,i) => (
            <div key={i}>
              <div style={{padding:'0 4px 10px', fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase',
                color:'var(--ink-3)', fontWeight:600}}>{s.date}</div>
              <div className="bal-card" style={{padding:'4px 0'}}>
                {s.items.map((it,ii) => (
                  <div key={ii} style={{padding:'14px 16px', display:'flex', alignItems:'flex-start', gap:12,
                    borderBottom: ii<s.items.length-1?'0.5px solid var(--rule)':'none'}}>
                    <div style={{
                      width:30, height:30, borderRadius:9,
                      background:'var(--brand-soft)', flexShrink:0,
                      display:'flex', alignItems:'center', justifyContent:'center',
                    }}>
                      <Icon.Spark size={14} c="var(--brand)"/>
                    </div>
                    <div style={{flex:1, minWidth:0}}>
                      <div style={{fontSize:14, fontWeight:500, color:'var(--ink)', letterSpacing:'-0.005em'}}>{it.q}</div>
                      <div style={{fontSize:12, color:'var(--ink-3)', marginTop:3, lineHeight:1.4,
                        overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{it.a}</div>
                    </div>
                    <div style={{fontSize:11, color:'var(--ink-4)', flexShrink:0, marginTop:2}}>{it.t}</div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
window.ChatHistoryScreen = ChatHistoryScreen;

// ──────────────────────────────────────────────────────────────────────────
// 13 · Labs / biomarkers upload
// ──────────────────────────────────────────────────────────────────────────
const LabsScreen = () => {
  const { Icon } = window;
  const markers = [
    { n:'Vitamin D, 25-OH', v:'28', u:'ng/mL', range:'30–80',  status:'low',    note:'Insufficient · supplement 2000 IU'},
    { n:'Ferritin',         v:'42', u:'ng/mL', range:'30–200', status:'ok',     note:'Within range · monitor'},
    { n:'B12',              v:'612',u:'pg/mL', range:'200–900',status:'ok',     note:'Healthy'},
    { n:'Omega-3 Index',    v:'3.8',u:'%',    range:'>8%',    status:'low',    note:'Add EPA-rich fish oil'},
    { n:'hs-CRP',           v:'2.4',u:'mg/L', range:'<1.0',   status:'high',   note:'Elevated · investigate'},
    { n:'HbA1c',            v:'5.4',u:'%',    range:'<5.7',   status:'ok',     note:'Optimal'},
  ];
  const tone = (s) => s==='low' ? '#e978da' : s==='high' ? '#c43f7a' : '#7ac97f';

  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom:120}}>
        <div style={{height:54}}/>
        <div style={{padding:'10px 22px 0', display:'flex', alignItems:'center', justifyContent:'space-between'}}>
          <Icon.Back size={20} c="var(--ink-2)"/>
          <div style={{fontSize:14, fontWeight:600}}>Lab results</div>
          <Icon.Plus size={20} c="var(--brand)"/>
        </div>

        {/* Upload card */}
        <div style={{padding:'18px 18px 0'}}>
          <div className="bal-card" style={{
            padding:'18px 18px 16px',
            background:'linear-gradient(135deg, #ece5fc 0%, #fde2f8 100%)',
            border:'none', position:'relative', overflow:'hidden',
          }}>
            <div style={{position:'absolute', right:-30, top:-30, width:140, height:140, borderRadius:'50%',
              background:'rgba(255,255,255,0.5)', filter:'blur(6px)'}}/>
            <div style={{position:'relative'}}>
              <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', fontWeight:700, color:'var(--brand)'}}>
                Latest · Mar 14
              </div>
              <div className="serif" style={{fontSize:24, color:'var(--ink)', marginTop:8, lineHeight:1.15, letterSpacing:'-0.02em'}}>
                4 of 6 markers in range
              </div>
              <div style={{fontSize:13, color:'var(--ink-2)', marginTop:6, lineHeight:1.45}}>
                Two areas to focus on: Vitamin D and Omega-3 Index. Tap a marker for plan.
              </div>
              <div style={{display:'flex', gap:8, marginTop:14}}>
                <button style={{
                  border:'none', height:38, padding:'0 14px', borderRadius:12,
                  background:'var(--brand)', color:'white', fontSize:13, fontWeight:600,
                }}>Upload new results</button>
                <button style={{
                  border:'1px solid rgba(85,33,229,0.18)', height:38, padding:'0 14px', borderRadius:12,
                  background:'rgba(255,255,255,0.6)', color:'var(--brand)', fontSize:13, fontWeight:600,
                }}>Connect lab</button>
              </div>
            </div>
          </div>
        </div>

        {/* Markers */}
        <div style={{padding:'22px 22px 8px', display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
          <div className="serif" style={{fontSize:18, color:'var(--ink)'}}>Biomarkers</div>
          <div style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'0.06em'}}>BY PRIORITY</div>
        </div>

        <div style={{padding:'0 18px', display:'flex', flexDirection:'column', gap:8}}>
          {markers.map((m,i) => (
            <div key={i} className="bal-card" style={{padding:'14px 16px'}}>
              <div style={{display:'flex', alignItems:'center', gap:12}}>
                <div style={{width:6, height:36, borderRadius:3, background: tone(m.status), flexShrink:0}}/>
                <div style={{flex:1, minWidth:0}}>
                  <div style={{display:'flex', alignItems:'baseline', gap:6}}>
                    <div style={{fontSize:14, fontWeight:600, color:'var(--ink)'}}>{m.n}</div>
                    <div style={{fontSize:11, color:'var(--ink-3)', fontWeight:500}}>· ref {m.range}</div>
                  </div>
                  <div style={{fontSize:12, color:'var(--ink-3)', marginTop:3, lineHeight:1.4}}>{m.note}</div>
                </div>
                <div style={{textAlign:'right', flexShrink:0}}>
                  <div className="mono" style={{fontSize:18, fontWeight:600, color:'var(--ink)', letterSpacing:'-0.02em'}}>{m.v}</div>
                  <div style={{fontSize:10, color:'var(--ink-3)', marginTop:1}}>{m.u}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
window.LabsScreen = LabsScreen;

// ──────────────────────────────────────────────────────────────────────────
// 14 · Profile / Settings
// ──────────────────────────────────────────────────────────────────────────
const ProfileScreen = () => {
  const { Icon, BalLogo } = window;
  const sections = [
    { title:'Health', items:[
      { n:'Goals',          v:'Sleep · Energy · Stress', I:Icon.Spark },
      { n:'Lab results',    v:'Last upload Mar 14',       I:Icon.Heart },
      { n:'Conditions & meds', v:'2 entered',             I:Icon.Shield },
    ]},
    { title:'Plan & data', items:[
      { n:'Subscription',   v:'Plus · annual',            I:Icon.Bookmark, badge:'PLUS' },
      { n:'Reminders',      v:'3 windows · 6 pings',      I:Icon.Sun },
      { n:'Connected apps', v:'Apple Health · Oura',      I:Icon.Stack },
    ]},
    { title:'Account', items:[
      { n:'Sign out',       v:'',                          I:Icon.User, danger:true },
    ]},
  ];

  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom:120}}>
        <div style={{height:54}}/>

        <div style={{padding:'10px 22px 0', display:'flex', alignItems:'center', justifyContent:'space-between'}}>
          <BalLogo size={22} variant="full"/>
          <div style={{fontSize:13, color:'var(--brand)', fontWeight:600}}>Edit</div>
        </div>

        {/* Identity card */}
        <div style={{padding:'24px 18px 0'}}>
          <div className="bal-card" style={{padding:'22px 20px', display:'flex', alignItems:'center', gap:16}}>
            <div style={{
              width:64, height:64, borderRadius:'50%', background:_GRAD,
              display:'flex', alignItems:'center', justifyContent:'center',
              color:'white', fontFamily:"'Priego','Fraunces',serif", fontSize:26, fontWeight:700,
              boxShadow:'0 6px 20px rgba(85,33,229,0.20)',
            }}>S</div>
            <div style={{flex:1}}>
              <div className="serif" style={{fontSize:20, color:'var(--ink)', letterSpacing:'-0.01em'}}>Sam Maddox</div>
              <div style={{fontSize:12, color:'var(--ink-3)', marginTop:2}}>sam@hello.co · joined Mar '24</div>
              <div style={{display:'flex', gap:6, marginTop:8}}>
                <Pill tone="grad" style={{fontSize:10}}>PLUS</Pill>
                <Pill tone="light" style={{fontSize:10}}>9-day streak</Pill>
              </div>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div style={{padding:'14px 18px 0', display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:8}}>
          {[
            {n:'In stack', v:'12'},
            {n:'Asked',    v:'47'},
            {n:'Logged',   v:'186'},
          ].map((s,i)=>(
            <div key={i} className="bal-card" style={{padding:'14px 12px', textAlign:'center'}}>
              <div className="serif" style={{fontSize:24, color:'var(--ink)'}}>{s.v}</div>
              <div style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'0.04em', marginTop:2, textTransform:'uppercase', fontWeight:600}}>{s.n}</div>
            </div>
          ))}
        </div>

        {/* Sections */}
        {sections.map((sec,si) => (
          <div key={si} style={{padding:'22px 18px 0'}}>
            <div style={{padding:'0 4px 8px', fontSize:11, letterSpacing:'0.1em',
              textTransform:'uppercase', color:'var(--ink-3)', fontWeight:600}}>{sec.title}</div>
            <div className="bal-card" style={{padding:'4px 0'}}>
              {sec.items.map((it,ii) => (
                <div key={ii} style={{display:'flex', alignItems:'center', gap:12, padding:'13px 16px',
                  borderBottom: ii<sec.items.length-1?'0.5px solid var(--rule)':'none'}}>
                  <div style={{
                    width:32, height:32, borderRadius:10,
                    background: it.danger ? '#fde2e2' : 'var(--brand-soft)',
                    display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
                  }}>
                    <it.I size={16} c={it.danger ? '#c43f3f' : 'var(--brand)'}/>
                  </div>
                  <div style={{flex:1, minWidth:0}}>
                    <div style={{fontSize:14, fontWeight:500, color: it.danger?'#c43f3f':'var(--ink)'}}>{it.n}</div>
                    {it.v && <div style={{fontSize:12, color:'var(--ink-3)', marginTop:1}}>{it.v}</div>}
                  </div>
                  {it.badge && <Pill tone="grad" style={{fontSize:10, marginRight:6}}>{it.badge}</Pill>}
                  {!it.danger && <Icon.Chevron size={14} c="var(--ink-4)"/>}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
window.ProfileScreen = ProfileScreen;

// ──────────────────────────────────────────────────────────────────────────
// 15 · Paywall · Plus
// ──────────────────────────────────────────────────────────────────────────
const PaywallScreen = () => {
  const { Icon, BalLogo } = window;
  const features = [
    { n:'Unlimited Ask',           d:'Search the evidence as much as you want', I:Icon.Spark },
    { n:'Personalized stacks',     d:'Based on labs, goals, and meds',          I:Icon.Stack },
    { n:'Full 17 guides',          d:'Deep dives on every topic',                I:Icon.Book },
    { n:'AI weekly recap',         d:'What worked · what to try',               I:Icon.Heart },
    { n:'Lab integration',         d:'Upload Quest, Labcorp, InsideTracker',    I:Icon.Shield },
  ];

  return (
    <div className="screen-root" style={{background:'#0E0B2E', color:'white'}}>
      <div className="scroll" style={{height:'100%', position:'relative'}}>
        {/* Status bar */}
        <div style={{height:54}}/>
        {/* Top blob */}
        <div style={{
          position:'absolute', top:-100, left:'50%', width:520, height:520,
          marginLeft:-260, borderRadius:'50%',
          background:'radial-gradient(circle, rgba(243,169,253,0.5) 0%, rgba(142,119,226,0.3) 30%, rgba(63,169,245,0.18) 55%, transparent 75%)',
          filter:'blur(30px)', pointerEvents:'none',
        }}/>

        {/* Header */}
        <div style={{padding:'10px 22px 0', position:'relative', display:'flex', alignItems:'center', justifyContent:'space-between'}}>
          <Icon.Back size={20} c="rgba(255,255,255,0.65)"/>
          <BalLogo size={20} variant="full" color="white"/>
          <div style={{fontSize:13, color:'rgba(255,255,255,0.55)', fontWeight:500}}>Restore</div>
        </div>

        {/* Hero */}
        <div style={{padding:'70px 26px 0', position:'relative', textAlign:'center'}}>
          <div style={{
            display:'inline-block', padding:'6px 14px', borderRadius:99,
            background:'rgba(255,255,255,0.08)', border:'1px solid rgba(255,255,255,0.14)',
            fontSize:11, letterSpacing:'0.16em', textTransform:'uppercase', fontWeight:700,
            color:'rgba(255,255,255,0.85)',
          }}>
            Balance <span style={{
              background:_GRAD, WebkitBackgroundClip:'text', backgroundClip:'text', color:'transparent',
            }}>Plus</span>
          </div>
          <div className="serif" style={{fontSize:42, lineHeight:1.05, marginTop:18, letterSpacing:'-0.025em', color:'white'}}>
            Get the full<br/>
            <em style={{
              background:_GRAD, WebkitBackgroundClip:'text', backgroundClip:'text', color:'transparent',
            }}>science engine</em>.
          </div>
          <div style={{fontSize:14, color:'rgba(255,255,255,0.65)', marginTop:14, lineHeight:1.5, padding:'0 8px'}}>
            Unlimited questions, personalized stacks, lab integration, and weekly AI recaps.
          </div>
        </div>

        {/* Features */}
        <div style={{padding:'40px 22px 0', position:'relative', display:'flex', flexDirection:'column', gap:12}}>
          {features.map((f,i) => (
            <div key={i} style={{display:'flex', alignItems:'flex-start', gap:14, padding:'4px 4px'}}>
              <div style={{
                width:38, height:38, borderRadius:11, background:'rgba(255,255,255,0.08)',
                border:'1px solid rgba(255,255,255,0.12)', flexShrink:0,
                display:'flex', alignItems:'center', justifyContent:'center',
              }}>
                <f.I size={18} c="white"/>
              </div>
              <div style={{flex:1}}>
                <div style={{fontSize:14, fontWeight:600, letterSpacing:'-0.01em'}}>{f.n}</div>
                <div style={{fontSize:12, color:'rgba(255,255,255,0.6)', marginTop:2, lineHeight:1.45}}>{f.d}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Plan toggle */}
        <div style={{padding:'30px 22px 0', position:'relative'}}>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
            <div style={{
              padding:'14px 14px 12px', borderRadius:18,
              border:'1px solid rgba(255,255,255,0.18)',
              background:'rgba(255,255,255,0.04)',
            }}>
              <div style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase', color:'rgba(255,255,255,0.6)', fontWeight:600}}>Monthly</div>
              <div className="serif" style={{fontSize:24, color:'white', marginTop:4}}>$14.99</div>
              <div style={{fontSize:11, color:'rgba(255,255,255,0.55)', marginTop:2}}>billed monthly</div>
            </div>
            <div style={{
              padding:'14px 14px 12px', borderRadius:18,
              border:'2px solid #f3a9fd',
              background:'rgba(243,169,253,0.10)',
              position:'relative',
            }}>
              <div style={{
                position:'absolute', top:-10, right:12, padding:'3px 8px', borderRadius:6,
                background:_GRAD, color:'white', fontSize:10, fontWeight:700, letterSpacing:'0.06em',
              }}>SAVE 50%</div>
              <div style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase', color:'rgba(255,255,255,0.85)', fontWeight:700}}>Annual</div>
              <div className="serif" style={{fontSize:24, color:'white', marginTop:4}}>$89</div>
              <div style={{fontSize:11, color:'rgba(255,255,255,0.7)', marginTop:2}}>$7.42 / month</div>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div style={{padding:'24px 22px 30px', position:'relative'}}>
          <button style={{
            width:'100%', height:56, borderRadius:18, border:'none',
            background:_GRAD, color:'white', fontSize:15, fontWeight:700, letterSpacing:'-0.01em',
            boxShadow:'0 16px 40px rgba(243,169,253,0.30)',
          }}>
            Start 7-day free trial
          </button>
          <div style={{textAlign:'center', fontSize:11, color:'rgba(255,255,255,0.5)', marginTop:12, lineHeight:1.5}}>
            Cancel anytime · billed after trial · auto-renews
          </div>
        </div>
      </div>
    </div>
  );
};
window.PaywallScreen = PaywallScreen;
