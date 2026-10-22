/* ta-v3d 런타임: TA3D_Q에 쌓인 장면 정의를 찾아 붙인다. 장면 정의 형식은 skills/viz/SKILL.md "# 3D" 참고 */
(function(){
const T=window.T3,root=document.documentElement;
const css=n=>getComputedStyle(root).getPropertyValue(n).trim();
const isDark=()=>{const t=root.dataset.theme;return t?t==='dark':matchMedia('(prefers-color-scheme: dark)').matches;};
const ease=t=>t<.5?2*t*t:1-Math.pow(-2*t+2,2)/2;
const clamp=t=>Math.min(1,Math.max(0,t));
const reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
const TXT=(root.lang||'').startsWith('en')
  ?{replay:'↻ Replay',hint:'Press the buttons in order · drag the scene to rotate it'}
  :{replay:'↻ 다시 재생',hint:'버튼을 차례로 누르면 단계가 넘어가요 · 장면을 드래그하면 돌려 볼 수 있어요'};
// ?ta3d=<id>:<단계> — 애니메이션 없이 그 단계로 바로 간다(ta.py shot --step이 씀)
const forced=(()=>{const m=/[?&]ta3d=([^&]+)/.exec(location.search);if(!m)return null;const a=decodeURIComponent(m[1]).split(':');return {id:a[0],step:+a[1]||0};})();

function mount(spec){
  const el=document.getElementById(spec.id);
  if(!el||el._ta3d)return;
  el._ta3d=true;
  const box=el.querySelector('.v3d'),fb=el.querySelector('.v3d-fb');
  const fail=e=>{if(e)console.error(e);if(box)box.hidden=true;if(fb)fb.hidden=false;};
  if(!T||!box)return fail();
  const mk=(tag,cls,parent)=>{const d=document.createElement(tag);if(cls)d.className=cls;parent.appendChild(d);return d;};
  const stage=mk('div','v3d-stage',box),cv=mk('canvas','',stage),lbBox=mk('div','v3d-labels',stage);
  const bar=mk('div','v3d-bar',box),say=mk('p','v3d-say',box);
  mk('p','v3d-hint',box).textContent=spec.hint||TXT.hint;
  say.setAttribute('aria-live','polite');
  stage.setAttribute('role','img');
  if(box.dataset.label)stage.setAttribute('aria-label',box.dataset.label);

  let renderer;
  try{renderer=new T.WebGLRenderer({canvas:cv,antialias:true,alpha:true});}catch(e){return fail(e);}
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.shadowMap.enabled=true;
  const scene=new T.Scene(),cam=new T.PerspectiveCamera(35,16/10,0.1,500);
  const ctr=new T.OrbitControls(cam,cv);
  ctr.enableDamping=true;ctr.enableZoom=false;ctr.enablePan=false;ctr.maxPolarAngle=Math.PI*0.47;
  scene.add(new T.HemisphereLight(0xffffff,0x8a8a8a,1.7));
  const sun=new T.DirectionalLight(0xffffff,2.2),sr=spec.shadow||10;
  sun.position.set(6,12,8);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);
  Object.assign(sun.shadow.camera,{left:-sr,right:sr,top:sr,bottom:-sr});
  scene.add(sun);
  const ground=new T.Mesh(new T.PlaneGeometry(200,200),new T.ShadowMaterial({opacity:.18}));
  ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;ground.visible=spec.ground!==false;
  scene.add(ground);

  // color(재질, '--t1'): 재질 색을 CSS 변수에 묶어 라이트/다크 전환 때 다시 칠한다
  const themed=[];
  const ctx={T,scene,cam,css,isDark,ease,clamp,color:(m,v)=>{themed.push([m,v]);m.color.set(css(v));return m;}};
  let update;
  try{update=spec.build(ctx)||(()=>{});}catch(e){return fail(e);}
  const recolor=()=>{for(const [m,v] of themed)m.color.set(css(v));ground.material.opacity=isDark()?.45:.18;};
  recolor();
  new MutationObserver(recolor).observe(root,{attributes:true,attributeFilter:['data-theme']});
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change',recolor);

  const steps=spec.steps,keys=Object.keys(spec.vars||{});
  const LB=(spec.labels||[]).map(o=>{const d=mk('span','lb '+(o.c||''),lbBox);d.textContent=o.t;return {...o,el:d};});
  const btns=steps.map((s,i)=>{const b=mk('button','',bar);b.type='button';b.textContent=s.label;b.onclick=()=>go(i,i===0&&step===0);return b;});
  const rb=mk('button','v3d-re',bar);
  rb.type='button';rb.textContent=TXT.replay;rb.onclick=()=>go(step,true);

  let step=0,v={...spec.vars},from={...v},goal={...v},tw=1,cf=null,ct=null,camT=1;
  const DUR=reduce?1e-3:(spec.dur||1.6),CDUR=reduce?1e-3:1.2;
  const V=a=>new T.Vector3(...a);
  // 단계 i의 goal은 모든 변수의 목표값을 담는다. replay면 변수를 처음 값으로 되돌린 뒤 움직인다
  function go(i,replay,instant){
    step=i;
    if(replay)v={...spec.vars};
    from={...v};goal={...v,...steps[i].goal};tw=0;
    cf={p:cam.position.clone(),t:ctr.target.clone()};ct={p:V(steps[i].cam.p),t:V(steps[i].cam.t)};camT=0;
    if(instant){v={...goal};tw=1;cam.position.copy(ct.p);ctr.target.copy(ct.t);camT=1;}
    say.textContent=steps[i].say||'';
    btns.forEach((b,k)=>b.setAttribute('aria-pressed',String(k===i)));
  }
  ctr.addEventListener('start',()=>{camT=1;});

  const timer=new T.Timer(),pv=new T.Vector3();
  timer.connect(document);
  function frame(){
    timer.update();
    const dt=Math.min(timer.getDelta(),0.1);
    if(tw<1){tw=Math.min(1,tw+dt/DUR);const k=ease(tw);for(const n of keys)v[n]=from[n]+(goal[n]-from[n])*k;}
    if(camT<1){camT=Math.min(1,camT+dt/CDUR);const k=ease(camT);cam.position.lerpVectors(cf.p,ct.p,k);ctr.target.lerpVectors(cf.t,ct.t,k);}
    update(v,dt,step);
    ctr.update();
    renderer.render(scene,cam);
    const w=stage.clientWidth,h=stage.clientHeight;
    for(const o of LB){
      const on=!!o.on(v,step);
      o.el.classList.toggle('on',on);
      if(!on)continue;
      pv.set(...o.at(v,step)).project(cam);
      o.el.style.left=((pv.x*.5+.5)*w)+'px';o.el.style.top=((-pv.y*.5+.5)*h)+'px';
    }
  }
  function resize(){
    const w=stage.clientWidth,h=stage.clientHeight;
    if(!w||!h)return;
    renderer.setSize(w,h,false);cam.aspect=w/h;cam.fov=w<520?48:35;cam.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(stage);
  resize();
  cam.position.set(...steps[0].cam.p);ctr.target.set(...steps[0].cam.t);
  const f=forced&&forced.id===spec.id?forced.step:null;
  f!=null?go(f,false,true):go(0,true);
  // 화면에 보일 때만 그리고, 처음 보일 때 1단계 애니메이션을 시작한다
  let started=f!=null;
  new IntersectionObserver(es=>{
    const on=es[0].isIntersecting;
    if(on&&!started){started=true;go(0,true);}
    renderer.setAnimationLoop(on?frame:null);
  },{threshold:.25}).observe(stage);
}

const q=window.TA3D_Q=window.TA3D_Q||[];
q.forEach(mount);
q.push=s=>{mount(s);return 0;};
window.TA3D={mount};
})();
