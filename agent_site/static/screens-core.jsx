
// ===== icons.jsx =====
// Balance — custom line icons (original, simple geometry)
const Icon = {
  Home: ({size=22, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 11L12 4l9 7"/><path d="M5 10v10h14V10"/>
    </svg>
  ),
  Spark: ({size=22, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5L18 18M6 18l2.5-2.5M15.5 8.5L18 6"/>
      <circle cx="12" cy="12" r="2.2" fill={c} stroke="none"/>
    </svg>
  ),
  Stack: ({size=22, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round">
      <path d="M12 3l8 4-8 4-8-4 8-4z"/>
      <path d="M4 12l8 4 8-4"/>
      <path d="M4 17l8 4 8-4"/>
    </svg>
  ),
  Book: ({size=22, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round">
      <path d="M4 5a2 2 0 012-2h13v16H6a2 2 0 00-2 2V5z"/><path d="M19 3v18"/>
    </svg>
  ),
  User: ({size=22, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-8 8-8s8 3.6 8 8"/>
    </svg>
  ),
  Send: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={c}>
      <path d="M3 12l18-8-8 18-2-8-8-2z"/>
    </svg>
  ),
  Chevron: ({size=14, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 6l6 6-6 6"/>
    </svg>
  ),
  Back: ({size=18, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M15 6l-6 6 6 6"/>
    </svg>
  ),
  Check: ({size=14, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="M5 12l5 5 9-11"/>
    </svg>
  ),
  Plus: ({size=18, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="2" strokeLinecap="round">
      <path d="M12 5v14M5 12h14"/>
    </svg>
  ),
  Search: ({size=18, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.8" strokeLinecap="round">
      <circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>
    </svg>
  ),
  Bookmark: ({size=18, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.6" strokeLinejoin="round" strokeLinecap="round">
      <path d="M6 3h12v18l-6-4-6 4V3z"/>
    </svg>
  ),
  Moon: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={c}><path d="M20 14A8 8 0 019 3a9 9 0 1011 11z"/></svg>
  ),
  Flame: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={c}><path d="M12 2s5 5 5 10a5 5 0 01-10 0c0-2 1-3 1-3s-1 5 2 5 3-4 2-6c3 2 4 5 4 7a6 6 0 11-12 0c0-6 8-13 8-13z"/></svg>
  ),
  Leaf: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={c}><path d="M20 4c-10 0-16 6-16 14 0 1 0 1.5.5 2.5C6 17 10 14 16 12c-5 4-8 7-10 10 8 0 14-5 14-14V4z"/></svg>
  ),
  Brain: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.6"><path d="M9 4a3 3 0 00-3 3 3 3 0 00-2 5 3 3 0 002 5 3 3 0 006 0V4z" fill={c} stroke="none"/><path d="M15 4a3 3 0 013 3 3 3 0 012 5 3 3 0 01-2 5 3 3 0 01-6 0V4z" fill={c} stroke="none" opacity="0.55"/></svg>
  ),
  Heart: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={c}><path d="M12 21s-8-5-8-11a5 5 0 019-3 5 5 0 019 3c0 6-8 11-8 11z" transform="translate(-1 0)"/></svg>
  ),
  Dumbbell: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={c}><rect x="2" y="9" width="3" height="6" rx="1"/><rect x="5" y="7" width="3" height="10" rx="1"/><rect x="8" y="11" width="8" height="2"/><rect x="16" y="7" width="3" height="10" rx="1"/><rect x="19" y="9" width="3" height="6" rx="1"/></svg>
  ),
  Bone: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={c}><path d="M7 4a3 3 0 012 5l3 3-3 3a3 3 0 11-5 2 3 3 0 110-6 3 3 0 013-7zm10 0a3 3 0 00-2 5l3 3-3 3a3 3 0 105 2 3 3 0 100-6 3 3 0 00-3-7z" transform="rotate(45 12 12)"/></svg>
  ),
  Shield: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={c}><path d="M12 2l8 3v7c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V5l8-3z"/></svg>
  ),
  Sun: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={c}><circle cx="12" cy="12" r="4"/><g stroke={c} strokeWidth="2" strokeLinecap="round"><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.5 4.5l2 2M17.5 17.5l2 2M4.5 19.5l2-2M17.5 6.5l2-2"/></g></svg>
  ),
  Droplet: ({size=20, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={c}><path d="M12 3s7 7 7 12a7 7 0 11-14 0c0-5 7-12 7-12z"/></svg>
  ),
  Mic: ({size=18, c='currentColor'}) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={c} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="3" width="6" height="11" rx="3" fill={c}/>
      <path d="M5 11a7 7 0 0014 0M12 18v3"/>
    </svg>
  ),
};

window.Icon = Icon;


// ===== screen-home.jsx =====
// Balance — Home (Today view)
const HomeScreen = () => {
  const { Icon } = window;
  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom: 110}}>
        {/* Status bar spacer */}
        <div style={{height: 54}} />

        {/* Header */}
        <div style={{padding: '14px 22px 8px'}}>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
            <div>
              <div style={{fontSize:12, color:'var(--ink-3)', fontWeight:500, letterSpacing:'0.06em', textTransform:'uppercase'}}>Wed · Apr 22</div>
              <div className="serif" style={{fontSize:34, lineHeight:1.05, marginTop:2, color:'var(--forest-ink)'}}>
                Good morning,<br/><em style={{fontStyle:'italic'}}>Sam</em>.
              </div>
            </div>
            <div style={{width:40, height:40, borderRadius:'50%', background:'var(--forest)', color:'var(--sage-2)', display:'flex', alignItems:'center', justifyContent:'center', fontWeight:600}}>S</div>
          </div>
        </div>

        {/* Focus card — "your buddy says" */}
        <div style={{padding:'16px 18px 0'}}>
          <div className="bal-card" style={{background:'var(--forest)', color:'var(--sage-2)', padding:20, borderRadius:22, position:'relative', overflow:'hidden'}}>
            <div style={{position:'absolute', right:-30, top:-30, width:160, height:160, borderRadius:'50%', background:'rgba(200,220,180,0.08)'}}/>
            <div style={{position:'absolute', right:-60, bottom:-60, width:140, height:140, borderRadius:'50%', background:'rgba(200,220,180,0.05)'}}/>
            {/* Logo mark — top-right */}
            <div style={{position:'absolute', right:18, top:18, pointerEvents:'none'}}>
              <window.BalLogoMark size={36} dark/>
            </div>
            <div style={{position:'relative'}}>
              <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', color:'var(--moss-2)', fontWeight:600}}>Tonight's nudge</div>
              <div className="serif" style={{fontSize:26, lineHeight:1.15, marginTop:10, maxWidth:'74%'}}>
                Take magnesium <em>45 min</em> before bed.
              </div>
              <div style={{fontSize:13, color:'var(--moss-2)', marginTop:10, lineHeight:1.4, maxWidth:'82%'}}>
                You asked about falling asleep yesterday. This is your best first move.
              </div>
              <div style={{display:'flex', gap:8, marginTop:14, alignItems:'center'}}>
                <div className="ev-badge a" style={{background:'var(--sage-2)', color:'var(--forest)'}}>A</div>
                <span style={{fontSize:12, color:'var(--moss-2)'}}>Grade A evidence · 4 RCTs</span>
              </div>
            </div>
          </div>
        </div>

        {/* Ask bar */}
        <div style={{padding:'18px 18px 0'}}>
          <div className="bal-card" style={{padding:'14px 16px', display:'flex', alignItems:'center', gap:12}}>
            <div style={{width:28, height:28, borderRadius:'50%', background:'var(--clay-soft)', display:'flex', alignItems:'center', justifyContent:'center'}}>
              <Icon.Spark size={16} c="var(--clay)"/>
            </div>
            <div style={{flex:1, color:'var(--ink-3)', fontSize:14}}>Ask anything about your health…</div>
            <Icon.Mic size={18} c="var(--ink-3)"/>
          </div>

          {/* Suggested */}
          <div style={{display:'flex', gap:8, marginTop:12, overflow:'hidden'}}>
            <div className="bal-pill light" style={{padding:'7px 12px', fontSize:12}}>Afternoon energy?</div>
            <div className="bal-pill light" style={{padding:'7px 12px', fontSize:12}}>Sore joints</div>
            <div className="bal-pill light" style={{padding:'7px 12px', fontSize:12}}>+</div>
          </div>
        </div>

        {/* Today's stack mini */}
        <div style={{padding:'22px 18px 0'}}>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:10}}>
            <div className="serif" style={{fontSize:22, color:'var(--forest-ink)'}}>Today's stack</div>
            <div style={{fontSize:12, color:'var(--clay)', fontWeight:500}}>3 of 5 done</div>
          </div>

          <div className="bal-card" style={{padding:'4px 0'}}>
            {[
              {n:'Creatine', d:'5 g · morning', done:true, g:'A'},
              {n:'Vitamin D3', d:'2000 IU · with food', done:true, g:'B'},
              {n:'Omega-3 EPA', d:'1 g · lunch', done:true, g:'A'},
              {n:'Magnesium glycinate', d:'300 mg · 9:00 PM', done:false, g:'A', next:true},
              {n:'Ashwagandha', d:'600 mg · 9:00 PM', done:false, g:'B'},
            ].map((it, i, arr) => (
              <div key={i} style={{display:'flex', alignItems:'center', padding:'12px 16px', borderBottom: i<arr.length-1?'0.5px solid var(--rule)':'none'}}>
                <div style={{
                  width:22, height:22, borderRadius:'50%',
                  background: it.done?'var(--forest)':'transparent',
                  border: it.done?'none':'1.6px solid var(--rule)',
                  display:'flex', alignItems:'center', justifyContent:'center', marginRight:12
                }}>
                  {it.done && <Icon.Check size={12} c="var(--sage-2)"/>}
                </div>
                <div style={{flex:1}}>
                  <div style={{fontSize:14, fontWeight:500, color: it.done?'var(--ink-3)':'var(--ink)', textDecoration: it.done?'line-through':'none'}}>{it.n}</div>
                  <div style={{fontSize:12, color:'var(--ink-3)', marginTop:1}}>{it.d}</div>
                </div>
                {it.next && <div className="bal-pill accent" style={{marginRight:8, fontSize:10}}>NEXT</div>}
                <div className={`ev-badge ${it.g.toLowerCase()}`}>{it.g}</div>
              </div>
            ))}
          </div>
        </div>

        {/* What's working */}
        <div style={{padding:'22px 18px 0'}}>
          <div className="serif" style={{fontSize:22, color:'var(--forest-ink)', marginBottom:10}}>What's working</div>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:10}}>
            <div className="bal-card" style={{padding:14}}>
              <div style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'0.08em', textTransform:'uppercase', fontWeight:600}}>Sleep onset</div>
              <div style={{display:'flex', alignItems:'baseline', gap:4, marginTop:6}}>
                <div className="serif" style={{fontSize:30, color:'var(--forest)'}}>−17</div>
                <div style={{fontSize:12, color:'var(--ink-3)'}}>min</div>
              </div>
              <div style={{fontSize:11, color:'var(--ink-3)', marginTop:2}}>8-week avg</div>
              <div style={{display:'flex', alignItems:'flex-end', gap:3, marginTop:10, height:26}}>
                {[30,34,31,40,52,58,63,70].map((h,i)=>(
                  <div key={i} style={{flex:1, height:`${h}%`, background: i>3?'var(--forest)':'var(--sage)', borderRadius:'2px 2px 0 0'}}/>
                ))}
              </div>
            </div>
            <div className="bal-card" style={{padding:14}}>
              <div style={{fontSize:11, color:'var(--ink-3)', letterSpacing:'0.08em', textTransform:'uppercase', fontWeight:600}}>Streak</div>
              <div style={{display:'flex', alignItems:'baseline', gap:4, marginTop:6}}>
                <div className="serif" style={{fontSize:30, color:'var(--clay)'}}>12</div>
                <div style={{fontSize:12, color:'var(--ink-3)'}}>days</div>
              </div>
              <div style={{fontSize:11, color:'var(--ink-3)', marginTop:2}}>Logging daily</div>
              <div style={{display:'flex', gap:3, marginTop:10}}>
                {Array.from({length:7}).map((_,i)=>(
                  <div key={i} style={{flex:1, height:8, borderRadius:2, background: i<6?'var(--clay)':'var(--sage)'}}/>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabbar */}
      <Tabbar active="home" onNav={window.__bal_nav}/>
    </div>
  );
};

const Tabbar = ({active, onNav}) => {
  const { Icon } = window;
  const items = [
    {k:'home', l:'Today', I:Icon.Home},
    {k:'ask', l:'Ask', I:Icon.Spark},
    {k:'stack', l:'Stack', I:Icon.Stack},
    {k:'browse', l:'Learn', I:Icon.Book},
    {k:'me', l:'Me', I:Icon.User},
  ];
  return (
    <div className="tabbar">
      {items.map(it => (
        <div key={it.k} className={`tab-item ${active===it.k?'active':''}`} onClick={()=>onNav&&onNav(it.k)} style={{cursor:'pointer'}}>
          <it.I size={22} c={active===it.k?'var(--forest)':'var(--ink-4)'}/>
          <div>{it.l}</div>
        </div>
      ))}
    </div>
  );
};

window.HomeScreen = HomeScreen;
window.Tabbar = Tabbar;


// ===== screen-ask.jsx =====
// Balance — Ask (chat with AI + ranked answer)
const AskScreen = () => {
  const { Icon } = window;
  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom: 160}}>
        <div style={{height:54}}/>

        {/* Header */}
        <div style={{padding:'8px 18px 8px', display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div onClick={()=>window.__bal_nav&&window.__bal_nav('home')} style={{width:36, height:36, borderRadius:'50%', background:'var(--surface)', display:'flex', alignItems:'center', justifyContent:'center', boxShadow:'var(--sh-1)', cursor:'pointer'}}>
            <Icon.Back size={16} c="var(--ink-2)"/>
          </div>
          <div style={{fontSize:13, color:'var(--ink-3)', fontWeight:500}}>Today's chat</div>
          <div style={{width:36, height:36, borderRadius:'50%', background:'var(--surface)', display:'flex', alignItems:'center', justifyContent:'center', boxShadow:'var(--sh-1)'}}>
            <Icon.Plus size={16} c="var(--ink-2)"/>
          </div>
        </div>

        {/* User message */}
        <div style={{padding:'18px 18px 0', display:'flex', justifyContent:'flex-end'}}>
          <div style={{maxWidth:'80%', background:'var(--forest)', color:'var(--sage-2)', padding:'11px 15px', borderRadius:'20px 20px 4px 20px', fontSize:14, lineHeight:1.4}}>
            What helps me fall asleep faster?
          </div>
        </div>

        {/* AI intro */}
        <div style={{padding:'14px 18px 0'}}>
          <div style={{display:'flex', alignItems:'center', gap:8, marginBottom:8}}>
            <window.BalLogoMark size={28}/>
            <div style={{fontSize:12, fontWeight:600, color:'var(--ink-2)'}}>Balance</div>
            <div style={{fontSize:11, color:'var(--ink-4)'}}>· searched 17 guides</div>
          </div>
          <div className="serif" style={{fontSize:22, lineHeight:1.25, color:'var(--forest-ink)', marginLeft:34}}>
            Start with <em>magnesium glycinate</em>.<br/>If that doesn't land, stack glycine.
          </div>
        </div>

        {/* Ranked answer card */}
        <div style={{padding:'16px 18px 0'}}>
          <div className="bal-card" style={{padding:'4px 0'}}>
            <div style={{padding:'14px 18px 10px', borderBottom:'0.5px solid var(--rule)'}}>
              <div style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--ink-3)', fontWeight:600}}>Top 3 · ranked by evidence</div>
            </div>

            {[
              {rank:1, n:'Magnesium', form:'glycinate', dose:'200–400 mg', time:'45 min pre-bed', g:'A', win:true},
              {rank:2, n:'Melatonin', form:'low dose', dose:'0.3–1 mg', time:'30 min pre-bed', g:'A'},
              {rank:3, n:'Glycine', form:'powder', dose:'3 g', time:'before bed', g:'B'},
            ].map((r, i, arr) => (
              <div key={i} style={{padding:'14px 18px', borderBottom: i<arr.length-1?'0.5px solid var(--rule)':'none', display:'flex', alignItems:'center', gap:14, background: r.win?'var(--surface-2)':'transparent'}}>
                <div className="serif" style={{fontSize:24, color: r.win?'var(--clay)':'var(--ink-4)', width:24, textAlign:'center', lineHeight:1}}>{r.rank}</div>
                <div style={{flex:1}}>
                  <div style={{display:'flex', alignItems:'baseline', gap:6}}>
                    <div style={{fontSize:16, fontWeight:600, color:'var(--forest-ink)'}}>{r.n}</div>
                    <div style={{fontSize:12, color:'var(--ink-3)', fontStyle:'italic'}}>{r.form}</div>
                  </div>
                  <div style={{fontSize:12, color:'var(--ink-2)', marginTop:2}}>
                    <span className="mono">{r.dose}</span> · {r.time}
                  </div>
                </div>
                <div className={`ev-badge ${r.g.toLowerCase()}`}>{r.g}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Explanation blurb */}
        <div style={{padding:'14px 18px 0', marginLeft:34}}>
          <div style={{fontSize:14, color:'var(--ink-2)', lineHeight:1.5}}>
            Magnesium supports GABA — the neurotransmitter that calms the nervous system. 4 RCTs show sleep-onset dropping by ~17 minutes with consistent evening dosing.
          </div>
          <div style={{marginTop:10, fontSize:12, color:'var(--ink-3)'}}>
            <span style={{borderBottom:'1px dashed var(--ink-4)', cursor:'pointer'}}>View studies</span>
          </div>
        </div>

        {/* Quick followups */}
        <div style={{padding:'18px 18px 0'}}>
          <div style={{display:'flex', flexWrap:'wrap', gap:8}}>
            {['Can I take both?','What about L-theanine?','Any side effects?','Stack with my current supps?'].map(q => (
              <div key={q} style={{padding:'8px 14px', background:'var(--surface)', border:'0.5px solid var(--rule)', borderRadius:999, fontSize:13, color:'var(--forest-2)', fontWeight:500}}>{q}</div>
            ))}
          </div>
        </div>

        {/* Add-to-stack CTA */}
        <div style={{padding:'22px 18px 0'}}>
          <div style={{background:'var(--clay)', color:'white', padding:'14px 18px', borderRadius:16, display:'flex', alignItems:'center', justifyContent:'space-between', boxShadow:'0 8px 20px rgba(199,88,58,0.25)'}}>
            <div>
              <div style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase', opacity:0.85, fontWeight:600}}>Recommended</div>
              <div className="serif" style={{fontSize:20, marginTop:2}}>Add Magnesium to my stack</div>
            </div>
            <div style={{width:38, height:38, borderRadius:'50%', background:'rgba(255,255,255,0.2)', display:'flex', alignItems:'center', justifyContent:'center'}}>
              <Icon.Plus size={18} c="white"/>
            </div>
          </div>
        </div>
      </div>

      {/* Composer */}
      <div style={{position:'absolute', bottom:0, left:0, right:0, padding:'12px 16px 24px', background:'linear-gradient(to top, var(--bg) 60%, transparent)'}}>
        <div style={{background:'var(--surface)', borderRadius:22, padding:'12px 14px', display:'flex', alignItems:'center', gap:10, boxShadow:'var(--sh-2)'}}>
          <Icon.Plus size={20} c="var(--ink-3)"/>
          <div style={{flex:1, fontSize:14, color:'var(--ink-3)'}}>Ask a follow-up…</div>
          <div style={{width:34, height:34, borderRadius:'50%', background:'var(--forest)', display:'flex', alignItems:'center', justifyContent:'center'}}>
            <Icon.Send size={16} c="var(--sage-2)"/>
          </div>
        </div>
      </div>
    </div>
  );
};
window.AskScreen = AskScreen;


// ===== screen-stack.jsx =====
// Balance — Stack (my supplements, by goal + stack health)
const StackScreen = () => {
  const { Icon, Tabbar } = window;
  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom: 110}}>
        <div style={{height:54}}/>

        <div style={{padding:'8px 22px 4px', display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
          <div className="serif" style={{fontSize:34, lineHeight:1.1, color:'var(--forest-ink)', paddingBottom:4}}>My stack</div>
          <div style={{fontSize:13, color:'var(--clay)', fontWeight:500}}>Edit</div>
        </div>
        <div style={{padding:'4px 22px 0', fontSize:13, color:'var(--ink-3)'}}>5 supplements · 3 goals</div>

        {/* Stack health card */}
        <div style={{padding:'18px 18px 0'}}>
          <div className="bal-card" style={{padding:18, background:'var(--sage-2)', border:'0.5px solid var(--moss-2)'}}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
              <div>
                <div style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--forest-2)', fontWeight:600}}>Stack health</div>
                <div style={{display:'flex', alignItems:'baseline', gap:8, marginTop:4}}>
                  <div className="serif" style={{fontSize:40, lineHeight:1, color:'var(--forest)'}}>A−</div>
                  <div style={{fontSize:13, color:'var(--forest-2)'}}>4 of 5 grade A</div>
                </div>
              </div>
              <div style={{position:'relative', width:72, height:72}}>
                <svg viewBox="0 0 36 36" style={{transform:'rotate(-90deg)'}}>
                  <circle cx="18" cy="18" r="15" fill="none" stroke="rgba(47,87,67,0.15)" strokeWidth="3"/>
                  <circle cx="18" cy="18" r="15" fill="none" stroke="var(--forest)" strokeWidth="3" strokeDasharray="75 100" strokeLinecap="round" pathLength="100"/>
                </svg>
              </div>
            </div>
            <div style={{display:'flex', gap:8, marginTop:14, padding:'10px 12px', background:'var(--surface)', borderRadius:12}}>
              <div style={{width:4, background:'var(--clay)', borderRadius:2}}/>
              <div style={{flex:1}}>
                <div style={{fontSize:12, fontWeight:600, color:'var(--forest-ink)'}}>Zinc + Magnesium timing</div>
                <div style={{fontSize:12, color:'var(--ink-3)', marginTop:2}}>Take 2h apart for best absorption · <span style={{color:'var(--clay)', fontWeight:500}}>auto-fix</span></div>
              </div>
            </div>
          </div>
        </div>

        {/* Goals */}
        <div style={{padding:'22px 18px 0'}}>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:12}}>
            <div style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--ink-3)', fontWeight:600}}>By goal</div>
          </div>

          {[
            {emoji:<Icon.Moon size={18} c="var(--forest)"/>, g:'Sleep', count:3, items:[
              {n:'Magnesium glycinate', t:'9:00 PM', g:'A', on:true},
              {n:'Glycine', t:'9:00 PM', g:'B', on:true},
              {n:'Ashwagandha', t:'9:00 PM', g:'B', on:false},
            ]},
            {emoji:<Icon.Dumbbell size={18} c="var(--forest)"/>, g:'Muscle', count:1, items:[
              {n:'Creatine', t:'Morning', g:'A', on:true},
            ]},
            {emoji:<Icon.Heart size={18} c="var(--forest)"/>, g:'Heart', count:1, items:[
              {n:'Omega-3 EPA', t:'Lunch', g:'A', on:true},
            ]},
          ].map((goal, gi) => (
            <div key={gi} className="bal-card" style={{padding:'0', marginBottom:12, overflow:'hidden'}}>
              <div style={{padding:'14px 16px 10px', display:'flex', alignItems:'center', gap:10, borderBottom:'0.5px solid var(--rule)', background:'var(--surface-2)'}}>
                <div style={{width:28, height:28, borderRadius:8, background:'var(--sage)', display:'flex', alignItems:'center', justifyContent:'center'}}>{goal.emoji}</div>
                <div className="serif" style={{fontSize:20, color:'var(--forest-ink)', flex:1}}>{goal.g}</div>
                <div style={{fontSize:12, color:'var(--ink-3)'}}>{goal.count} supp{goal.count>1?'s':''}</div>
              </div>
              {goal.items.map((it, i, arr) => (
                <div key={i} style={{padding:'12px 16px', display:'flex', alignItems:'center', gap:12, borderBottom: i<arr.length-1?'0.5px solid var(--rule)':'none'}}>
                  <div style={{width:6, height:6, borderRadius:'50%', background: it.on?'var(--forest)':'var(--ink-4)'}}/>
                  <div style={{flex:1}}>
                    <div style={{fontSize:14, fontWeight:500, color:'var(--forest-ink)'}}>{it.n}</div>
                    <div style={{fontSize:12, color:'var(--ink-3)', marginTop:1}}>{it.t}</div>
                  </div>
                  <div className={`ev-badge ${it.g.toLowerCase()}`}>{it.g}</div>
                </div>
              ))}
            </div>
          ))}

          <div style={{padding:'14px', border:'1.5px dashed var(--rule)', borderRadius:16, textAlign:'center', color:'var(--ink-3)', fontSize:14, fontWeight:500}}>+ Add a goal</div>
        </div>
      </div>

      <Tabbar active="stack" onNav={window.__bal_nav}/>
    </div>
  );
};
window.StackScreen = StackScreen;


// ===== screen-learn.jsx =====
// Balance — Learn (topic browse) and Detail (supplement deep-dive)
const LearnScreen = () => {
  const { Icon, Tabbar } = window;
  const topics = [
    {k:'Sleep', I:Icon.Moon, g:'A', color:'var(--forest)'},
    {k:'Stress', I:Icon.Leaf, g:'A', color:'var(--moss)'},
    {k:'Focus', I:Icon.Brain, g:'B', color:'var(--clay)'},
    {k:'Energy', I:Icon.Sun, g:'A', color:'var(--ochre)'},
    {k:'Muscle', I:Icon.Dumbbell, g:'A', color:'var(--forest-2)'},
    {k:'Fat loss', I:Icon.Flame, g:'B', color:'var(--clay)'},
    {k:'Heart', I:Icon.Heart, g:'A', color:'var(--clay)'},
    {k:'Joints', I:Icon.Bone, g:'B', color:'var(--forest)'},
    {k:'Immunity', I:Icon.Shield, g:'B', color:'var(--moss)'},
    {k:'Skin', I:Icon.Droplet, g:'C', color:'var(--ochre)'},
    {k:'Libido', I:Icon.Spark, g:'B', color:'var(--clay)'},
    {k:'Liver', I:Icon.Leaf, g:'B', color:'var(--forest)'},
  ];
  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom:140}}>
        <div style={{height:54}}/>
        <div style={{padding:'8px 22px'}}>
          <div className="serif" style={{fontSize:34, lineHeight:1, color:'var(--forest-ink)'}}>Learn</div>
          <div style={{fontSize:13, color:'var(--ink-3)', marginTop:4}}>17 evidence-based guides</div>
        </div>

        {/* Search */}
        <div style={{padding:'14px 18px 0'}}>
          <div style={{background:'var(--surface)', borderRadius:14, padding:'10px 14px', display:'flex', alignItems:'center', gap:10, boxShadow:'var(--sh-1)'}}>
            <Icon.Search size={16} c="var(--ink-3)"/>
            <div style={{flex:1, fontSize:14, color:'var(--ink-3)'}}>Search guides or supplements</div>
          </div>
        </div>

        {/* Featured guide */}
        <div style={{padding:'16px 18px 0', cursor:'pointer'}} onClick={()=>window.__bal_nav&&window.__bal_nav('detail')}>
          <div className="bal-card" style={{padding:'0', overflow:'hidden', position:'relative'}}>
            <div style={{padding:'18px 18px 16px', background:'linear-gradient(140deg, var(--sage-2) 0%, var(--moss-2) 100%)', position:'relative', minHeight:140}}>
              <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', color:'var(--forest-2)', fontWeight:600}}>Featured guide</div>
              <div className="serif" style={{fontSize:28, lineHeight:1.18, marginTop:10, color:'var(--forest-ink)', maxWidth:'68%', paddingBottom:4}}>
                The sleep stack, <em>actually</em> explained
              </div>
              <div style={{fontSize:13, color:'var(--forest-2)', marginTop:16}}>6 supplements · 14 studies · 8 min read</div>
              <div style={{position:'absolute', right:-10, bottom:-20, width:130, height:130, borderRadius:'50%', background:'rgba(47,87,67,0.12)'}}/>
              <div style={{position:'absolute', right:24, bottom:18}}>
                <Icon.Moon size={44} c="var(--forest)"/>
              </div>
            </div>
          </div>
        </div>

        {/* Topic grid */}
        <div style={{padding:'22px 18px 0'}}>
          <div style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--ink-3)', fontWeight:600, marginBottom:12}}>All 17 topics</div>
          <div style={{display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:10}}>
            {topics.map((t, i) => (
              <div key={i} className="bal-card" style={{padding:14, aspectRatio:'1', display:'flex', flexDirection:'column', justifyContent:'space-between', cursor:'pointer'}} onClick={()=>window.__bal_nav&&window.__bal_nav('detail')}>
                <div style={{width:32, height:32, borderRadius:10, background: t.g==='A'?'var(--sage)':t.g==='B'?'var(--ochre-soft)':'var(--clay-soft)', display:'flex', alignItems:'center', justifyContent:'center'}}>
                  <t.I size={18} c={t.color}/>
                </div>
                <div>
                  <div style={{fontSize:14, fontWeight:600, color:'var(--forest-ink)'}}>{t.k}</div>
                  <div style={{fontSize:11, color:'var(--ink-3)', marginTop:2}}>Grade {t.g}</div>
                </div>
              </div>
            ))}
          </div>
          <div style={{textAlign:'center', fontSize:12, color:'var(--ink-3)', marginTop:14, fontWeight:500}}>Show all 17 →</div>
        </div>
      </div>
      <Tabbar active="browse" onNav={window.__bal_nav}/>
    </div>
  );
};

// Supplement detail
const DetailScreen = () => {
  const { Icon } = window;
  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom: 110}}>
        {/* Hero */}
        <div style={{background:'linear-gradient(180deg, var(--forest) 0%, var(--forest-2) 100%)', color:'var(--sage-2)', padding:'54px 0 26px', position:'relative', overflow:'hidden'}}>
          <div style={{position:'absolute', right:-40, top:20, width:200, height:200, borderRadius:'50%', background:'rgba(200,220,180,0.08)'}}/>
          <div style={{position:'relative', padding:'12px 18px 0', display:'flex', justifyContent:'space-between'}}>
            <div onClick={()=>window.__bal_nav&&window.__bal_nav('browse')} style={{width:36, height:36, borderRadius:'50%', background:'rgba(255,255,255,0.12)', display:'flex', alignItems:'center', justifyContent:'center', cursor:'pointer'}}>
              <Icon.Back size={16} c="var(--sage-2)"/>
            </div>
            <div style={{width:36, height:36, borderRadius:'50%', background:'rgba(255,255,255,0.12)', display:'flex', alignItems:'center', justifyContent:'center'}}>
              <Icon.Bookmark size={16} c="var(--sage-2)"/>
            </div>
          </div>
          <div style={{padding:'18px 22px 0', position:'relative'}}>
            <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', color:'var(--moss-2)', fontWeight:600}}>Mineral · sleep · stress</div>
            <div className="serif" style={{fontSize:44, lineHeight:1, marginTop:8}}>Magnesium</div>
            <div style={{fontStyle:'italic', fontSize:15, color:'var(--moss-2)', marginTop:4}} className="serif">The one most adults are low on.</div>

            <div style={{display:'flex', gap:10, marginTop:18}}>
              <div style={{flex:1, background:'rgba(255,255,255,0.08)', padding:'10px 12px', borderRadius:12}}>
                <div style={{fontSize:10, letterSpacing:'0.1em', textTransform:'uppercase', opacity:0.7, fontWeight:600}}>Dose</div>
                <div className="serif" style={{fontSize:18, marginTop:2}}>200–400 mg</div>
              </div>
              <div style={{flex:1, background:'rgba(255,255,255,0.08)', padding:'10px 12px', borderRadius:12}}>
                <div style={{fontSize:10, letterSpacing:'0.1em', textTransform:'uppercase', opacity:0.7, fontWeight:600}}>Timing</div>
                <div className="serif" style={{fontSize:18, marginTop:2}}>45 min pre-bed</div>
              </div>
              <div style={{width:64, background:'var(--sage-2)', color:'var(--forest)', padding:'10px 8px', borderRadius:12, textAlign:'center'}}>
                <div style={{fontSize:10, letterSpacing:'0.1em', textTransform:'uppercase', opacity:0.7, fontWeight:600}}>Grade</div>
                <div className="serif" style={{fontSize:22, fontWeight:700, lineHeight:1.2}}>A</div>
              </div>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div style={{padding:'18px 18px 0', display:'flex', gap:6, overflow:'hidden'}}>
          {['Overview','Dosing','Evidence','Safety'].map((t,i)=>(
            <div key={t} style={{padding:'8px 14px', borderRadius:999, fontSize:13, fontWeight:500, background: i===0?'var(--forest)':'transparent', color: i===0?'var(--sage-2)':'var(--ink-2)', border: i===0?'none':'0.5px solid var(--rule)'}}>{t}</div>
          ))}
        </div>

        {/* Works for */}
        <div style={{padding:'20px 22px 0'}}>
          <div style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--ink-3)', fontWeight:600}}>Best for</div>
          <div style={{display:'flex', gap:8, marginTop:10, flexWrap:'wrap'}}>
            <div className="bal-pill dark"><Icon.Moon size={11} c="var(--sage-2)"/>Sleep · A</div>
            <div className="bal-pill"><Icon.Leaf size={11} c="var(--forest)"/>Stress · B+</div>
            <div className="bal-pill"><Icon.Dumbbell size={11} c="var(--forest)"/>Muscle · B</div>
          </div>
        </div>

        {/* What it does */}
        <div style={{padding:'22px 22px 0'}}>
          <div className="serif" style={{fontSize:22, color:'var(--forest-ink)', marginBottom:8}}>Why it works</div>
          <div style={{fontSize:14, color:'var(--ink-2)', lineHeight:1.55}}>
            Magnesium activates the parasympathetic nervous system and binds to GABA receptors — the same pathway benzodiazepines use, minus the dependence. Most adults run a low-grade deficit because modern soil is depleted and coffee flushes it out.
          </div>
        </div>

        {/* Evidence bars */}
        <div style={{padding:'22px 22px 0'}}>
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline', marginBottom:8}}>
            <div className="serif" style={{fontSize:22, color:'var(--forest-ink)'}}>The evidence</div>
            <div className="bal-pill accent">Grade A</div>
          </div>
          <div className="bal-card" style={{padding:16}}>
            {[
              {label:'Sleep onset', value:88, text:'−17 min avg · 4 RCTs'},
              {label:'Sleep quality', value:72, text:'moderate effect · 3 studies'},
              {label:'Anxiety', value:58, text:'mixed results · 6 studies'},
              {label:'Cramps', value:42, text:'weak evidence · 2 studies'},
            ].map((b,i)=>(
              <div key={i} style={{marginBottom: i<3?14:0}}>
                <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
                  <div style={{fontSize:13, fontWeight:500, color:'var(--forest-ink)'}}>{b.label}</div>
                  <div style={{fontSize:11, color:'var(--ink-3)'}}>{b.text}</div>
                </div>
                <div style={{height:8, background:'var(--sage-2)', borderRadius:4, marginTop:6, overflow:'hidden'}}>
                  <div style={{height:'100%', width:`${b.value}%`, background: b.value>70?'var(--forest)':b.value>50?'var(--moss)':'var(--ochre)', borderRadius:4}}/>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Watch out */}
        <div style={{padding:'22px 22px 0'}}>
          <div className="bal-card" style={{padding:16, background:'var(--clay-soft)', boxShadow:'none'}}>
            <div style={{fontSize:11, letterSpacing:'0.1em', textTransform:'uppercase', color:'var(--clay)', fontWeight:600}}>Watch out for</div>
            <div style={{fontSize:13, color:'var(--ink-2)', marginTop:6, lineHeight:1.5}}>
              <strong>Citrate form</strong> causes GI upset above 300 mg. Stick to <strong>glycinate</strong> — same absorption, no stomach surprise.
            </div>
          </div>
        </div>

        {/* CTA */}
        <div style={{padding:'20px 18px 0'}}>
          <div style={{background:'var(--forest)', color:'var(--sage-2)', padding:'16px 20px', borderRadius:16, display:'flex', alignItems:'center', justifyContent:'space-between'}}>
            <div className="serif" style={{fontSize:20}}>Add to my stack</div>
            <div style={{width:36, height:36, borderRadius:'50%', background:'var(--clay)', display:'flex', alignItems:'center', justifyContent:'center'}}>
              <Icon.Plus size={18} c="white"/>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
window.LearnScreen = LearnScreen;
window.DetailScreen = DetailScreen;


// ===== screen-progress.jsx =====
// Balance — Progress (AI recap) + Onboarding
const ProgressScreen = () => {
  const { Icon, Tabbar } = window;
  return (
    <div className="screen-root">
      <div className="scroll" style={{height:'100%', paddingBottom: 110}}>
        <div style={{height:54}}/>

        <div style={{padding:'8px 22px'}}>
          <div style={{fontSize:11, letterSpacing:'0.12em', textTransform:'uppercase', color:'var(--ink-3)', fontWeight:600}}>Your month</div>
          <div className="serif" style={{fontSize:34, lineHeight:1.05, color:'var(--forest-ink)', marginTop:4}}>
            April, <em>in short</em>.
          </div>
        </div>

        {/* AI recap */}
        <div style={{padding:'18px 18px 0'}}>
          <div className="bal-card" style={{padding:18, position:'relative', overflow:'hidden'}}>
            <div style={{display:'flex', alignItems:'center', gap:8, marginBottom:10, position:'relative'}}>
              <window.BalLogoMark size={28}/>
              <div style={{fontSize:12, fontWeight:600, color:'var(--ink-2)'}}>Balance's read</div>
            </div>
            <div className="serif" style={{fontSize:18, lineHeight:1.4, color:'var(--forest-ink)', maxWidth:'78%', position:'relative'}}>
              Sleep improved <em>~25%</em> since you added magnesium. Energy is flat. Want to try creatine for afternoon dips?
            </div>
            <div style={{display:'flex', gap:8, marginTop:14, position:'relative'}}>
              <div style={{flex:1, padding:'10px 12px', background:'var(--sage-2)', borderRadius:10, textAlign:'center', fontSize:13, fontWeight:500, color:'var(--forest-2)'}}>Keep stack</div>
              <div style={{flex:1, padding:'10px 12px', background:'var(--forest)', borderRadius:10, textAlign:'center', fontSize:13, fontWeight:500, color:'var(--sage-2)'}}>Try creatine →</div>
            </div>
          </div>
        </div>

        {/* Trends */}
        <div style={{padding:'22px 18px 0'}}>
          <div style={{display:'flex', gap:6, marginBottom:14}}>
            {['Sleep','Energy','Focus','Stress'].map((t,i)=>(
              <div key={t} style={{padding:'6px 12px', borderRadius:999, fontSize:12, fontWeight:500, background:i===0?'var(--forest)':'transparent', color:i===0?'var(--sage-2)':'var(--ink-3)', border:i===0?'none':'0.5px solid var(--rule)'}}>{t}</div>
            ))}
          </div>

          <div className="bal-card" style={{padding:18}}>
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'baseline'}}>
              <div className="serif" style={{fontSize:22, color:'var(--forest-ink)'}}>Sleep score</div>
              <div style={{fontSize:11, color:'var(--ink-3)', fontWeight:500}}>Last 8 weeks</div>
            </div>
            <div style={{display:'flex', alignItems:'baseline', gap:6, marginTop:4}}>
              <div className="serif" style={{fontSize:34, color:'var(--forest)', lineHeight:1}}>82</div>
              <div style={{fontSize:13, color:'var(--clay)', fontWeight:600}}>↑ 24</div>
            </div>

            {/* Bars */}
            <div style={{display:'flex', alignItems:'flex-end', gap:4, marginTop:18, height:100}}>
              {[30,36,32,42,48,55,62,68,70,75,80,82].map((h,i)=>{
                const highlight = i>=6;
                return (
                  <div key={i} style={{flex:1, display:'flex', flexDirection:'column', alignItems:'center', gap:4}}>
                    <div style={{width:'100%', height:`${h}%`, background: highlight?'var(--forest)':'var(--sage)', borderRadius:'3px 3px 0 0'}}/>
                  </div>
                );
              })}
            </div>
            <div style={{display:'flex', justifyContent:'space-between', marginTop:6, fontSize:10, color:'var(--ink-4)'}}>
              <span>Feb</span><span>Mar</span><span>Apr</span>
            </div>

            {/* Annotation */}
            <div style={{display:'flex', gap:8, marginTop:16, padding:'10px 12px', background:'var(--surface-2)', borderRadius:10, alignItems:'center'}}>
              <div style={{width:3, height:28, background:'var(--clay)', borderRadius:2}}/>
              <div>
                <div style={{fontSize:12, fontWeight:600, color:'var(--forest-ink)'}}>+ Magnesium · Feb 28</div>
                <div style={{fontSize:11, color:'var(--ink-3)'}}>The inflection point</div>
              </div>
            </div>
          </div>
        </div>

        {/* What worked */}
        <div style={{padding:'22px 18px 0'}}>
          <div className="serif" style={{fontSize:22, color:'var(--forest-ink)', marginBottom:12}}>What worked</div>

          <div className="bal-card" style={{padding:'4px 0'}}>
            {[
              {n:'Magnesium glycinate', note:'Sleep onset −17 min', good:true},
              {n:'Earlier caffeine cutoff', note:'Deep sleep +12%', good:true},
              {n:'Ashwagandha', note:"Didn't move the needle", good:false},
            ].map((r,i,arr)=>(
              <div key={i} style={{padding:'12px 16px', display:'flex', alignItems:'center', gap:12, borderBottom:i<arr.length-1?'0.5px solid var(--rule)':'none'}}>
                <div style={{width:8, height:8, borderRadius:'50%', background:r.good?'var(--forest)':'var(--ink-4)'}}/>
                <div style={{flex:1}}>
                  <div style={{fontSize:14, fontWeight:500, color: r.good?'var(--forest-ink)':'var(--ink-3)'}}>{r.n}</div>
                  <div style={{fontSize:12, color:'var(--ink-3)', marginTop:1}}>{r.note}</div>
                </div>
                {!r.good && <div style={{fontSize:12, color:'var(--clay)', fontWeight:500}}>Drop?</div>}
              </div>
            ))}
          </div>
        </div>
      </div>
      <Tabbar active="me" onNav={window.__bal_nav}/>
    </div>
  );
};

// Onboarding
const OnboardScreen = () => {
  const { Icon } = window;
  return (
    <div className="screen-root" style={{background:'var(--forest)'}}>
      <div style={{position:'absolute', inset:0, overflow:'hidden'}}>
        <div style={{position:'absolute', right:-80, top:-40, width:300, height:300, borderRadius:'50%', background:'rgba(200,220,180,0.06)'}}/>
        <div style={{position:'absolute', left:-60, bottom:120, width:220, height:220, borderRadius:'50%', background:'rgba(199,88,58,0.08)'}}/>
      </div>

      <div style={{position:'relative', height:'100%', padding:'70px 28px 40px', display:'flex', flexDirection:'column', color:'var(--sage-2)'}}>
        {/* Wordmark */}
        <window.BalLogo size={22} variant="mono" color="white"/>

        {/* Hero logo mark */}
        <div style={{display:'flex', justifyContent:'center', marginTop:36, marginBottom:8, position:'relative'}}>
          <div style={{
            width:160, height:160, borderRadius:'50%',
            background:'radial-gradient(circle, rgba(243,169,253,0.5) 0%, rgba(142,119,226,0.2) 50%, transparent 75%)',
            filter:'blur(8px)', position:'absolute',
          }}/>
          <window.BalLogoMark size={140} glow/>
        </div>

        <div style={{flex:1, display:'flex', flexDirection:'column', justifyContent:'flex-end'}}>
          <div style={{fontSize:11, letterSpacing:'0.14em', textTransform:'uppercase', color:'var(--moss-2)', fontWeight:600, marginBottom:14}}>
            Science-backed · 17 guides
          </div>
          <div className="serif" style={{fontSize:38, lineHeight:1.12, color:'white', paddingBottom:6}}>
            What your body needs,<br/><em style={{color:'var(--clay-2)'}}>backed by studies</em>.
          </div>
          <div style={{fontSize:14, color:'var(--moss-2)', marginTop:16, lineHeight:1.5, maxWidth:'90%'}}>
            Ask anything about sleep, stress, energy, or recovery. We search the evidence and return a ranked stack — with dose, timing, and grade.
          </div>

          <div style={{marginTop:24, display:'flex', flexDirection:'column', gap:10}}>
            <div style={{background:'var(--clay)', color:'white', padding:'15px 20px', borderRadius:14, display:'flex', alignItems:'center', justifyContent:'space-between', boxShadow:'0 10px 26px rgba(199,88,58,0.3)'}}>
              <div className="serif" style={{fontSize:20}}>Get started</div>
              <Icon.Chevron size={14} c="white"/>
            </div>
            <div style={{textAlign:'center', padding:'10px', fontSize:14, color:'var(--moss-2)', fontWeight:500}}>I already have an account</div>
          </div>

          <div style={{fontSize:11, color:'var(--moss-2)', opacity:0.7, marginTop:14, lineHeight:1.5, textAlign:'center'}}>
            Not medical advice. For personal health decisions, consult a qualified healthcare professional.
          </div>
        </div>
      </div>
    </div>
  );
};

window.ProgressScreen = ProgressScreen;
window.OnboardScreen = OnboardScreen;
