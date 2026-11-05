"use strict";
const $=(s,r=document)=>r.querySelector(s);
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function h(tag,attrs,...kids){const e=document.createElement(tag);for(const k in(attrs||{})){const v=attrs[k];if(v==null||v===false)continue;if(k==="class")e.className=v;else if(k==="html")e.innerHTML=v;else if(k.startsWith("on"))e.addEventListener(k.slice(2),v);else e.setAttribute(k,v===true?"":v)}for(const c of kids.flat())if(c!=null&&c!==false)e.append(c.nodeType?c:document.createTextNode(c));return e}
const TONE={Critical:"#cd2b31",High:"#cd2b31",Fail:"#cd2b31",rejected:"#cd2b31","On Hold":"#cd2b31",overdue:"#cd2b31",Warning:"#ab6400",Medium:"#ab6400","Pending Approval":"#ab6400",proposed:"#793aaf",Info:"#3451b2",open:"#3451b2",Low:"#0b7a6c",Pass:"#0b7a6c",Approved:"#0b7a6c",approved:"#0b7a6c",resolved:"#0b7a6c","auto-closed":"#6b7080",live:"#0b7a6c",Healthy:"#0b7a6c",Watch:"#ab6400",Rejected:"#6b7080"};
const tone=v=>TONE[v]||(/crit|high|fail|bad|reject|hold/i.test(v)?"#cd2b31":/warn|med|pend/i.test(v)?"#ab6400":/ok|pass|low|good|appr|done|clear|live/i.test(v)?"#0b7a6c":"#6b7080");
const ICON={bot:"M12 8V4H8M4 12a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2zM2 14h2M20 14h2M9 15v1M15 15v1",users:"M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M22 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8",store:"M3 9l1-5h16l1 5M3 9v11h18V9M3 9a3 3 0 0 0 6 0 3 3 0 0 0 6 0 3 3 0 0 0 6 0M9 20v-6h6v6",boxes:"M21 8l-9-5-9 5 9 5zM3 8v8l9 5 9-5V8M12 13v8",megaphone:"M3 11v2a1 1 0 0 0 1 1h3l8 5V5L7 10H4a1 1 0 0 0-1 1zM19 8a5 5 0 0 1 0 8",messages:"M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z",clipboard:"M9 4h6v3H9zM8 5H6a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 13l2 2 4-4",bell:"M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0",network:"M12 2v6M12 16v6M5 6l5 4M19 6l-5 4M5 18l5-4M19 18l-5-4M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8",flask:"M10 2v7L4 20a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1l-6-11V2M8 2h8M7 15h10",upload:"M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12",shield:"M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10",radar:"M12 12l7-7M12 2a10 10 0 1 0 10 10M12 6a6 6 0 1 0 6 6M12 10a2 2 0 1 0 2 2",route:"M6 19a3 3 0 1 0 0-6 3 3 0 0 0 0 6M18 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6M9 16h6a3 3 0 0 0 0-6H9a3 3 0 0 1 0-6h3",dollar:"M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6",truck:"M1 3h15v13H1zM16 8h4l3 3v5h-7M5.5 21a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5M18.5 21a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5",cloud:"M17.5 19a4.5 4.5 0 1 0-1.4-8.8A6 6 0 1 0 5 15a4 4 0 0 0 1 4z",trend:"M3 17l6-6 4 4 8-8M15 7h6v6",chart:"M3 3v18h18M7 15l4-4 3 3 5-6",check:"M22 11.1V12a10 10 0 1 1-5.9-9.1M22 4L12 14l-3-3",user:"M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8",file:"M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8zM14 2v6h6M9 13h6M9 17h6"};
const icon=n=>{const s=document.createElementNS("http://www.w3.org/2000/svg","svg");s.setAttribute("viewBox","0 0 24 24");const p=document.createElementNS("http://www.w3.org/2000/svg","path");p.setAttribute("d",ICON[n]||ICON.file);s.append(p);return s};
const S={me:null,page:null,tab:null,params:{},lang:localStorage.getItem("lang")||"English",theme:localStorage.getItem("theme")==="dark"?"dark":"light",pulse:null,tree:null,timer:null,seq:0,boot:null,authScreen:"login",recoveryEmail:"",recoveryOtp:"",otpResendUntil:0,otpCountdown:null,apiNotice:""};
function applyTheme(){document.documentElement.dataset.theme=S.theme;document.querySelectorAll("[data-theme-toggle]").forEach(button=>{const next=S.theme==="dark"?"light":"dark";button.textContent=next==="dark"?"Dark mode":"Light mode";button.setAttribute("aria-label","Switch to "+next+" mode");button.setAttribute("aria-pressed",String(S.theme==="dark"));button.title="Switch to "+next+" mode"})}
function toggleTheme(){S.theme=S.theme==="dark"?"light":"dark";localStorage.setItem("theme",S.theme);applyTheme()}
function themeToggle(className){const next=S.theme==="dark"?"light":"dark";return h("button",{class:className||"btn sm theme-toggle",type:"button","data-theme-toggle":"",onclick:toggleTheme,"aria-label":"Switch to "+next+" mode","aria-pressed":String(S.theme==="dark"),title:"Switch to "+next+" mode"},next==="dark"?"Dark mode":"Light mode")}
applyTheme();
const LANGS_CODE={};
function pageIsAllowed(id){return !!(S.me&&Array.isArray(S.me.menu)&&S.me.menu.some(item=>item&&item.id===id))}
function firstAllowedPage(){const menu=S.me&&Array.isArray(S.me.menu)?S.me.menu:[];const first=menu.find(item=>item&&typeof item.id==="string"&&item.id);return first?first.id:null}
function authToken(){try{return sessionStorage.getItem("fo_token")||localStorage.getItem("fo_token")||""}catch(e){return""}}
function setToken(tok,remember){try{sessionStorage.removeItem("fo_token");localStorage.removeItem("fo_token");if(tok)(remember?localStorage:sessionStorage).setItem("fo_token",tok)}catch(e){}}
async function api(path,opt={}){const o={credentials:"same-origin",...opt};o.headers={...(opt.headers||{})};if(opt.json!==undefined){o.method=o.method||"POST";o.headers["Content-Type"]="application/json";o.body=JSON.stringify(opt.json)}const tk=authToken();if(tk)o.headers.Authorization="Bearer "+tk;
 let r;try{r=await fetch(path,o)}catch{return{ok:false,error:true,networkError:true,msg:"Unable to reach the FranchiseOps AI backend. Check that the application server is running."}}
 let d=null;try{d=await r.json()}catch(e){}
 if(r.status===401&&S.me&&!path.includes("login")){setToken("");S.me=null;S.authScreen="login";S.loginNotice=(d&&(d.detail||d.msg))||"Your session ended. Sign in again.";render();return{ok:false,msg:"Session ended"}}
 if(!d)d={ok:false,msg:r.ok?"The server returned an unreadable response.":"Error "+r.status};
 if(!r.ok){d.ok=false;d.error=true;d.status=r.status;if(!d.msg)d.msg=d.detail||("Error "+r.status)}
 return d}
function toast(msg,bad){const t=h("div",{class:bad?"bad":""},msg);$("#toast").append(t);setTimeout(()=>t.remove(),bad?7000:4500)}
const fmt={num:v=>v==null?"–":(typeof v==="number"?(Math.abs(v)>=1000?v.toLocaleString(undefined,{maximumFractionDigits:1}):+v.toFixed(2)):v),int:v=>v==null?"–":Math.round(v).toLocaleString(),money:v=>v==null?"–":"$"+Math.round(v).toLocaleString()};
function md(t){let s=esc(t||"");s=s.replace(/```([\s\S]*?)```/g,(_,c)=>"<pre>"+c.trim()+"</pre>").replace(/`([^`]+)`/g,"<code>$1</code>").replace(/\*\*([^*]+)\*\*/g,"<b>$1</b>");const L=s.split("\n");let o="",inl=false,tb=null;const row=l=>l.trim().replace(/^\||\|$/g,"").split("|").map(x=>x.trim());const endT=()=>{if(tb){o+='<div class="tbl" style="margin:8px 0"><table><thead><tr>'+row(tb[0]).map(x=>"<th>"+x+"</th>").join("")+"</tr></thead><tbody>"+tb.slice(2).map(r=>"<tr>"+row(r).map(x=>"<td>"+x+"</td>").join("")+"</tr>").join("")+"</tbody></table></div>";tb=null}};for(let i=0;i<L.length;i++){const l=L[i];if(/^\s*\|.*\|\s*$/.test(l)){if(inl){o+="</ul>";inl=false}(tb=tb||[]).push(l);continue}endT();const m=l.match(/^\s*[-*•]\s+(.*)/);if(m){if(!inl){o+="<ul>";inl=true}o+="<li>"+m[1]+"</li>"}else{if(inl){o+="</ul>";inl=false}const hd=l.match(/^(#{1,3})\s+(.*)/);o+=hd?`<h${hd[1].length}>${hd[2]}</h${hd[1].length}>`:(l.trim()?l+"<br>":"")}}endT();if(inl)o+="</ul>";return o}

// ---------------------------------------------------------------- block renderers (each returns {el, update(b)})
function mount(b,key){const f=R[b.t];if(!f){return{el:h("div",{class:"card"},"Unsupported block: "+b.t),update(){}}}const m=f(b,key);m.t=b.t;m.k=b.key||b.id||"";return m}
function mountList(parent,blocks,key){const hs=blocks.map((b,i)=>mount(b,key+"/"+i));hs.forEach(x=>parent.append(x.el));return hs}
function updList(parent,hs,blocks,key){if(hs.length!==blocks.length||hs.some((x,i)=>x.t!==blocks[i].t||x.k!==(blocks[i].key||blocks[i].id||""))){parent.replaceChildren();return mountList(parent,blocks,key)}hs.forEach((x,i)=>x.update(blocks[i]));return hs}
const R={};
R.kpis=b=>{const el=h("div",{class:"kpis"});const up=b=>{el.replaceChildren(...b.items.map(i=>h("div",{class:"kpi "+(i.tone||"")},h("div",{class:"l"},i.label),h("div",{class:"v"},typeof i.value==="number"?fmt.num(i.value):i.value),i.sub?h("div",{class:"s"},i.sub):null)))};up(b);return{el,update:up}};
R.callout=b=>{const el=h("div");const up=b=>{el.className="callout "+(b.tone||"info");el.replaceChildren(h("div",null,b.title?h("b",null,b.title+" "):null,h("span",{html:md(b.text)})))};up(b);return{el,update:up}};
R.md=b=>{const el=h("div",{class:"md"});const up=b=>el.innerHTML=md(b.text);up(b);return{el,update:up}};
R.row=(b,k)=>{const el=h("div",{class:"row"});const sty=r=>el.style.gridTemplateColumns=(r||b.cols.map(()=>1)).map(x=>x+"fr").join(" ");sty(b.ratio);let hs=[];const wrap=[];const up=nb=>{sty(nb.ratio);if(hs.length!==nb.cols.length||hs.some((x,i)=>x.t!==nb.cols[i].t)){el.replaceChildren();hs=nb.cols.map((c,i)=>{const m=mount(c,k+"/"+i);el.append(m.el);return m})}else hs.forEach((x,i)=>x.update(nb.cols[i]))};up(b);return{el,update:up}};
R.col=(b,k)=>{const el=h("div",{class:"col"});let hs=mountList(el,b.blocks,k);return{el,update:nb=>{hs=updList(el,hs,nb.blocks,k)}}};
R.card=(b,k)=>{const el=h("div",{class:"card"});const hd=h("h3"),sub=h("div",{class:"sub"}),body=h("div");el.append(hd,sub,body);let hs=[];const up=(nb,first)=>{hd.textContent=nb.title||"";hd.style.display=nb.title?"":"none";sub.textContent=nb.sub||"";sub.style.display=nb.sub?"":"none";hs=first?mountList(body,nb.blocks,k):updList(body,hs,nb.blocks,k)};up(b,true);return{el,update:nb=>up(nb)}};
R.hero=b=>{const el=h("div",{class:"hero"});const up=b=>{const c=b.risk?tone(b.risk):"#8b8d98";el.replaceChildren(h("div",{class:"sc",style:"color:"+c},b.score==null?"–":Math.round(b.score)),h("div",{style:"flex:1"},h("h2",null,b.title," ",b.risk?h("span",{class:"pill",style:`color:${c};border-color:${c}`},b.risk):null),h("p",null,b.blurb),h("p",{style:"color:#454a58"},b.summary||"No run yet."),h("p",null,b.ts?`last run ${b.ts.slice(11,19)} · ${b.ms} ms`:"")),b.can_run?h("button",{class:"btn primary",onclick:async e=>{e.target.disabled=true;const r=await api("/api/run_agent",{json:{agent:b.agent}});toast(r.msg,!r.ok);e.target.disabled=false;reloadPage()}},"Run now"):null)};up(b);return{el,update:up}};
R.brief=b=>{const el=h("div",{class:"card"});const out=h("div",{class:"md"});const up=b=>{out.dataset.def=b.text;if(!out.dataset.ai)out.innerHTML=md(b.text)};el.append(h("h3",null,"Executive briefing"),out,b.can_brief?h("button",{class:"btn sm",style:"margin-top:8px",onclick:async e=>{e.target.disabled=true;out.dataset.ai="1";out.textContent="";let acc="";await sse("/api/brief",{lang:S.lang},ev=>{if(ev.ev==="tok"){acc+=ev.text;out.innerHTML=md(acc)}if(ev.ev==="final")out.innerHTML=md(ev.text)});e.target.disabled=false}},"Write with the GPU model"):null);up(b);return{el,update:up}};
R.button=b=>{const el=h("button",{class:"btn "+(b.tone||"primary"),onclick:async()=>{if(b.payload&&b.payload.download){window.open(b.url,"_blank");return}if(b.confirm&&!confirm(b.confirm))return;el.disabled=true;const r=await api(b.url,{json:b.payload||{}});toast(r.msg||"Done",!r.ok);el.disabled=false;if(r.refresh)reloadPage()}},b.label);return{el,update(){}}};
R.table=b=>{const el=h("div"),title=h("h3",{style:"margin:0 0 6px;font-size:13.5px"}),sub=h("div",{class:"sub"}),srch=h("input",{class:"srch",placeholder:"Search…",oninput:()=>{st.q=srch.value.toLowerCase();draw()}}),box=h("div",{class:"tbl"}),st={sort:null,dir:1,q:""};let cur=b;el.append(title,sub,srch,box);
 const draw=()=>{const b=cur;title.textContent=b.title||"";title.style.display=b.title?"":"none";sub.textContent=b.sub||"";sub.style.display=b.sub?"":"none";srch.style.display=b.search?"":"none";if(b.h)box.style.maxHeight=b.h+"px";
  let rows=b.rows;if(st.q)rows=rows.filter(r=>Object.values(r).some(v=>String(v).toLowerCase().includes(st.q)));if(st.sort)rows=[...rows].sort((x,y)=>{const a=x[st.sort],c=y[st.sort];return(a==null)-(c==null)||(a>c?1:a<c?-1:0)*st.dir});
  const mx={};b.cols.forEach(c=>{if(c.type==="pct"){mx[c.k]=Math.max(...b.rows.map(r=>Math.abs(r[c.k]||0)))<=1.0001?100:1}});
  const th=h("tr",null,...b.cols.map(c=>h("th",{onclick:()=>{st.dir=st.sort===c.k?-st.dir:1;st.sort=c.k;draw()}},c.label+(st.sort===c.k?(st.dir>0?" ▲":" ▼"):""))));
  const tb=rows.slice(0,400).map(r=>{const tr=h("tr",{class:b.open?"cl":""},...b.cols.map(c=>{const v=r[c.k];const t=c.type||"text";let n;
    if(t==="pill"&&v!=null&&v!=="")n=h("span",{class:"pill",style:`color:${tone(v)};border-color:${tone(v)}55;background:${tone(v)}18`},v);
    else if(t==="bar"){const m=c.max||100,p=Math.max(0,Math.min(100,(v||0)/m*100)),col=c.k.match(/risk|prob|congest|ci|index/i)?(p>66?"#e5484d":p>40?"#f5a524":"#12a594"):(p<60?"#e5484d":p<80?"#f5a524":"#12a594");n=h("div",{class:"bar"},h("span",null,v==null?"–":fmt.num(v)),h("i",null,h("b",{style:`width:${p}%;background:${col}`})))}
    else if(t==="pct")n=document.createTextNode(v==null?"–":(+(v*mx[c.k]).toFixed(1))+"%");else if(t==="money")n=document.createTextNode(fmt.money(v));else if(t==="int")n=document.createTextNode(fmt.int(v));else if(t==="num")n=document.createTextNode(fmt.num(v));else n=document.createTextNode(v==null?"":v);
    return h("td",{title:typeof v==="string"&&v.length>40?v:null},n)}));if(b.open)tr.onclick=()=>UI.openEntity(r[b.open.col]);return tr});
  const sc=box.scrollTop;box.replaceChildren(h("table",null,h("thead",null,th),h("tbody",null,...tb)));box.scrollTop=sc;if(!rows.length)box.append(h("div",{class:"sub",style:"padding:12px"},"No rows."))};
 draw();return{el,update:nb=>{cur=nb;draw()}}};
R.tickets=b=>{const el=h("div"),st={f:"all",open:new Set()};let cur=b;const body=h("div"),fl=h("div",{class:"filters"});el.append(h("h3",{style:"margin:0 0 6px;font-size:13.5px"},b.title||"Tickets"),h("div",{class:"sub"},b.sub||""),fl,body);
 const act=async(id,a,json)=>{const r=await api(`/api/ticket/${id}/${a}`,{json:json||{}});toast(r.msg,!r.ok);if(document.activeElement)document.activeElement.blur();st.sig=null;reloadPage(true)};
 const draw=()=>{const items=cur.items;st.sig=JSON.stringify(items)+st.f+[...st.open];const cnt=k=>k==="all"?items.length:k==="proposed"?items.filter(i=>i.status==="proposed").length:k==="overdue"?items.filter(i=>i.overdue).length:items.filter(i=>i.sev===k).length;
  fl.replaceChildren(...["all","proposed","Critical","Warning","Info","overdue"].map(k=>h("span",{class:"chip"+(st.f===k?" on":""),onclick:()=>{st.f=k;draw()}},(k==="proposed"?"awaiting approval":k)+" · "+cnt(k))));
  const list=items.filter(i=>st.f==="all"||(st.f==="proposed"?i.status==="proposed":st.f==="overdue"?i.overdue:i.sev===st.f));
  body.replaceChildren(...list.slice(0,80).map(i=>{const c=tone(i.sev);const t=h("div",{class:"tk "+i.sev+" "+i.status},
   h("div",{class:"h"},h("b",null,"#"+i.id+" "+i.type.replace(/_/g," ")),h("span",{class:"pill",style:`color:${c};border-color:${c}66`},i.sev),i.status==="proposed"?h("span",{class:"pill",style:"color:#8e4ec6;border-color:#8e4ec666"},"awaiting approval"):null,i.overdue?h("span",{class:"pill",style:"color:#e5484d;border-color:#e5484d66"},"overdue"):null,h("a",{href:"#",onclick:e=>{e.preventDefault();UI.openEntity(i.target)}},i.target)),
   h("div",{class:"d"},i.detail),h("div",{class:"m"},h("span",null,"agent: "+i.agent),h("span",null,"owner: "+(i.owner||"–")),h("span",null,"assignee: "+(i.assignee||"unassigned")),h("span",null,"due "+(i.due||"–")),h("span",null,i.ts)),
   i.chain&&i.chain.length?h("div",{class:"m"},h("span",null,"approval chain: "),...i.chain.map(s=>h("span",{class:"pill",style:`color:${s.status==="approved"?"#1a9e6e":s.status==="rejected"?"#e5484d":"#8e4ec6"};border-color:currentColor`},"L"+s.step+" "+s.role+(s.status==="approved"?" ✓ "+s.by:s.status==="rejected"?" ✗":" …")))):null,
   i.status==="proposed"&&i.turn&&!i.can_approve?h("div",{class:"m"},"Waiting for a "+i.turn+" to decide"):null,
   i.note?h("div",{class:"m"},"note: "+i.note):null,
   h("div",{class:"a"},i.status==="proposed"&&i.can_approve?[h("button",{class:"btn ok sm",onclick:()=>act(i.id,"approve")},"Approve & execute"),h("button",{class:"btn danger sm",onclick:()=>act(i.id,"reject")},"Reject")]:null,
    i.quote&&i.can_approve&&i.status!=="proposed"?[h("button",{class:"btn ok sm",onclick:()=>act(i.id,"approve")},"Approve quote"),h("button",{class:"btn danger sm",onclick:()=>act(i.id,"reject")},"Reject")]:null,
    i.can_resolve?[h("button",{class:"btn sm",onclick:()=>act(i.id,"resolve")},"Resolve"),(()=>{const a=h("input",{class:"in",style:"width:170px",placeholder:"assign to email",value:i.assignee||""});return h("span",{style:"display:flex;gap:4px"},a,h("button",{class:"btn sm",onclick:()=>a.value&&act(i.id,"assign",{assignee:a.value})},"Assign"))})()]:null,
    h("button",{class:"btn sm",onclick:()=>{st.open.has(i.id)?st.open.delete(i.id):st.open.add(i.id);draw()}},"Comments ("+i.comments.length+")")),
   st.open.has(i.id)?h("div",{class:"cm"},...i.comments.map(c=>h("div",null,h("b",null,c.by),` ${c.ts}: ${c.body}`)),(()=>{const t=h("input",{class:"in",placeholder:"Write a comment and press Enter",onkeydown:e=>{if(e.key==="Enter"&&t.value.trim())act(i.id,"comment",{body:t.value})}});return t})()):null);return t}));if(!list.length)body.append(h("div",{class:"sub"},"Nothing here."))};
 draw();return{el,update:nb=>{if(el.contains(document.activeElement)&&document.activeElement.tagName==="INPUT"){cur=nb;return}if(JSON.stringify(nb.items)+st.f+[...st.open]===st.sig)return;cur=nb;draw()}}};
// ---- charts
const FN={size3:v=>Math.max(8,Math.min(34,Math.sqrt(Math.abs(v[3]||10))*1.6)),scatterTip:p=>`<b>${esc(p.value[2]||"")}</b><br>${esc(p.seriesName||"")}<br>${p.value[0]}, ${p.value[1]}`,nodeTip:p=>p.dataType==="node"?`<b>${esc(p.name)}</b><br>${esc(p.data.tip||"")}`:"",nodeLabel:p=>p.data.showLabel?p.name:""};
function revive(o){if(Array.isArray(o))return o.map(revive);if(o&&typeof o==="object"){if(o.__fn)return FN[o.__fn];const r={};for(const k in o)r[k]=revive(o[k]);return r}return o}
echarts.registerTheme("lt",{color:["#0f766e","#2563eb","#f59e0b","#7c3aed","#e5484d","#16a34a","#db2777","#0891b2","#64748b"],backgroundColor:"transparent",textStyle:{fontFamily:"Inter, system-ui, sans-serif",color:"#454a58"},legend:{textStyle:{color:"#454a58"}},categoryAxis:{axisLine:{lineStyle:{color:"#d9dce8"}},axisTick:{show:false},axisLabel:{color:"#6b7080"},splitLine:{lineStyle:{color:"#eceef6"}}},valueAxis:{axisLine:{show:false},axisTick:{show:false},axisLabel:{color:"#6b7080"},splitLine:{lineStyle:{color:"#eceef6"}}},tooltip:{backgroundColor:"#fff",borderColor:"#e6e8f0",textStyle:{color:"#1c2024"},extraCssText:"box-shadow:0 8px 24px rgba(20,24,40,.12);border-radius:10px"}});
const CH=[];function lazy(box,fn){let d=0;const t=()=>{if(d)return;if(box.isConnected&&box.clientWidth>0){d=1;fn()}else setTimeout(t,60)};t()}
R.chart=b=>{const el=h("div"),box=h("div",{style:`height:${b.h||290}px`});el.append(h("h3",{style:"margin:0 0 4px;font-size:13.5px;display:"+(b.title?"block":"none")},b.title||""),box);let ch=null,cur=b;
 const init=()=>{ch=echarts.init(box,"lt",{renderer:"canvas"});CH.push(ch);ch.setOption(revive(cur.opt),true);
  ch.on("click",p=>{const o=cur.open;if(!o)return;let id=null;if(o.bar)id=p.name;else if(o.scatter)id=p.value&&p.value[2];else if(o.graph)id=p.data&&p.data.open;else if(p.data&&p.data.open)id=p.data.open;if(id)UI.openEntity(id)});
  if(cur.open)box.style.cursor="pointer"};
 lazy(box,init);
 return{el,update:nb=>{cur=nb;if(ch){const r=JSON.stringify(nb.opt);if(box._h!==r){box._h=r;ch.setOption(revive(nb.opt),{replaceMerge:["series","xAxis","yAxis"]})}}},};};
window.addEventListener("resize",()=>CH.forEach(c=>{try{c.resize()}catch(e){}}));
// ---- map
function shiftGeo(g,sh){const mv=c=>typeof c[0]==="number"?[c[0]+sh,c[1]]:c.map(mv);return{type:"FeatureCollection",features:g.features.map(f=>({type:"Feature",properties:f.properties,geometry:{type:f.geometry.type,coordinates:mv(f.geometry.coordinates)}}))}}
let WORLD=null;async function world(){if(WORLD)return WORLD;try{const t=await(await fetch("/static/vendor/world.topo.json")).json();WORLD=topojson.feature(t,t.objects.countries)}catch(e){WORLD={type:"FeatureCollection",features:[]}}return WORLD}
R.map=b=>{const el=h("div"),box=h("div",{class:"map",style:`height:${b.h||470}px`}),lg=h("div",{class:"lg"});el.append(box,lg);let M=null,grp=null,cur=b;
 const draw=()=>{grp.clearLayers();const SH=[-360,0,360];cur.layers.forEach(L=>{if(L.type==="lines")L.lines.forEach(l=>{if(l.pts.length<2)return;SH.forEach(sh=>{const p=L2.polyline(l.pts.map(q=>[q[0],q[1]+sh]),{color:l.color||"#0f766e",weight:l.w||2,dashArray:l.dash||null,opacity:.9,lineJoin:"round",renderer:M._r});if(l.tip)p.bindTooltip(l.tip,{sticky:true});grp.addLayer(p)})});
   else if(L.type==="circles")L.items.forEach(c=>SH.forEach(sh=>{const k=L2.circle([c.lat,c.lon+sh],{radius:c.r_m,color:c.color||"#e5484d",weight:1,fillOpacity:.18,renderer:M._r});if(c.tip)k.bindTooltip(c.tip);grp.addLayer(k)}));
   else if(L.type==="points")[...L.pts].sort((a,c)=>(a.z||0)-(c.z||0)).forEach(p=>SH.forEach(sh=>{const m=L2.circleMarker([p.lat,p.lon+sh],{radius:p.r||5,color:"#ffffff",weight:1.2,fillColor:p.color||"#0f766e",fillOpacity:.95,renderer:M._r});if(p.tip)m.bindTooltip(p.tip,{sticky:true});const o=p.open||(cur.open?p.id:null)||p.id;if(o)m.on("click",()=>UI.openEntity(o));grp.addLayer(m)}))});
  lg.replaceChildren(...(cur.legend||[]).map(([t,c])=>h("span",null,h("i",{style:"background:"+c}),t)))};
 const L2=L;const go=async()=>{M=L2.map(box,{zoomControl:true,worldCopyJump:true,attributionControl:false,minZoom:1,preferCanvas:true});M._r=L2.canvas({padding:.5});const w=await world();[-360,0,360].forEach(sh=>L2.geoJSON(sh?shiftGeo(w,sh):w,{renderer:M._r,style:{color:"#b9b2a0",weight:.8,fillColor:"#f3efe6",fillOpacity:1},interactive:false}).addTo(M));grp=L2.layerGroup().addTo(M);
  const v=cur.view||{};if(v.bounds)M.fitBounds(v.bounds);else M.setView(v.center||[20,0],v.zoom||2);draw();setTimeout(()=>M.invalidateSize(),50)};
 lazy(box,go);
 return{el,update:nb=>{cur=nb;if(M&&grp)draw()}}};
// ---- forms
R.form=b=>{const el=h("div",{class:b.title||b.inline?"":""});const res=h("div",{class:"res"});const f=h("form",{class:"f"+(b.inline?" inline":"")});let ins={};
 b.fields.forEach(fl=>{const w=h("div",{class:"fld"+(fl.type==="textarea"||fl.type==="checks"||fl.type==="multi"?" wide":"")});if(fl.type!=="hidden")w.append(h("label",null,fl.label||fl.name));let i;
  if(fl.type==="select")i=h("select",{name:fl.name},...fl.options.map(o=>h("option",{value:o,selected:String(o)===String(fl.value)},o)));
  else if(fl.type==="multi"){i=h("select",{name:fl.name,multiple:true,size:5},...fl.options.map(o=>h("option",{value:o,selected:(fl.value||[]).includes(o)},o)))}
  else if(fl.type==="checks"){i=h("div",{class:"chk"},...fl.options.map(o=>h("label",null,h("input",{type:"checkbox",value:o,checked:(fl.value||[]).includes(o)}),o)));i.get=()=>[...i.querySelectorAll("input:checked")].map(x=>x.value)}
  else if(fl.type==="textarea")i=h("textarea",{name:fl.name,placeholder:fl.placeholder||""},fl.value||"");
  else if(fl.type==="range"){const v=h("span",{style:"color:#12a594"},fl.value);i=h("input",{type:"range",name:fl.name,min:fl.min,max:fl.max,step:fl.step||1,value:fl.value,oninput:e=>v.textContent=e.target.value});w.firstChild.append(" ",v)}
  else if(fl.type==="file")i=h("input",{type:"file",name:fl.name,accept:fl.accept||null});
  else if(fl.type==="hidden"){i=h("input",{type:"hidden",name:fl.name,value:fl.value});w.style.display="none"}
  else i=h("input",{type:fl.type==="number"?"number":fl.type==="date"?"date":fl.type==="password"?"password":"text",name:fl.name,value:fl.value==null?"":fl.value,min:fl.min,max:fl.max,step:fl.step||(fl.type==="number"?"any":null),placeholder:fl.placeholder||""});
  i.fl=fl;ins[fl.name]=i;w.append(i);f.append(w)});
 const btn=h("button",{class:"btn "+(b.tone||"primary"),type:"submit"},b.submit||"Submit");f.append(h("div",{class:"fld"},btn));
 f.addEventListener("submit",async e=>{e.preventDefault();const v={};let fd=null;for(const n in ins){const i=ins[n],fl=i.fl;if(fl.type==="file"){if(i.files[0]){fd=fd||new FormData();fd.append(n,i.files[0])}}else if(fl.type==="checks")v[n]=i.get();else if(fl.type==="multi")v[n]=[...i.selectedOptions].map(o=>o.value);else if(fl.type==="number"||fl.type==="range")v[n]=i.value===""?null:+i.value;else v[n]=i.value}
  if(b.url.startsWith("get:")){const q=new URLSearchParams();for(const n in v)if(v[n]!==""&&v[n]!=null)q.set(n,v[n]);window.open(b.url.slice(4)+"?"+q,"_blank");return}
  if(b.url.startsWith("page:")){const[,id,tab]=b.url.split(":");UI.go(id,tab||S.tab,v);return}
  btn.disabled=true;const t0=btn.textContent;btn.textContent="Working…";let r;
  if(fd){for(const n in v)fd.append(n,Array.isArray(v[n])?v[n].join(","):v[n]);r=await api(b.url,{method:"POST",body:fd})}else r=await api(b.url,{json:v});
  btn.disabled=false;btn.textContent=t0;toast(r.msg||(r.ok?"Done":"Failed"),!r.ok);res.replaceChildren();if(r.blocks){const hs=mountList(res,r.blocks,"res");}if(r.refresh)reloadPage(true)});
 if(b.title||b.sub){const c=h("div",{class:"card"},b.title?h("h3",null,b.title):null,b.sub?h("div",{class:"sub"},b.sub):null,f,res);el.append(c)}else el.append(f,res);return{el,update(){}}};
// ---- chat
function setChatState(chat,state,message){
 if(!chat||!chat.isConnected)return;
 let status=chat.querySelector(".chat-status");
 if(!status){status=h("div",{class:"chat-status",role:"status","aria-live":"polite"});chat.querySelector(".cin")?.before(status)}
 chat.dataset.state=state;chat.setAttribute("aria-busy",String(state==="loading"));
 status.className="chat-status"+(state==="error"?" is-error":state==="complete"?" is-complete":"");
 status.textContent=message;
 chat.querySelectorAll(".cin input,.cin button").forEach(control=>{
  if(state==="loading"){if(control.dataset.wasDisabled===undefined)control.dataset.wasDisabled=String(control.disabled);control.disabled=true}
  else if(control.dataset.wasDisabled!==undefined){control.disabled=control.dataset.wasDisabled==="true";delete control.dataset.wasDisabled}
 });
}
function showChatError(chat,message){
 if(!chat||!chat.isConnected)return;
 const bubble=chat.querySelector(".msgs .m.a:last-child");
 if(bubble)bubble.append(h("p",{class:"chat-error",role:"alert"},message));
 setChatState(chat,"error",message);
}
async function sse(url,json,on){
 const chat=url==="/api/copilot"?document.querySelector(".chat"):null;
 if(chat)setChatState(chat,"loading","Connecting to Copilot…");
 let completed=false;
 try{
  const r=await fetch(url,{method:"POST",credentials:"same-origin",headers:{"Content-Type":"application/json",...(authToken()?{Authorization:"Bearer "+authToken()}:{})},body:JSON.stringify(json)});
  if(!r.ok){
   const message=`Copilot could not complete the request (HTTP ${r.status}). Please try again.`;
   if(chat){showChatError(chat,message);return}
   on({ev:"final",text:"Error "+r.status});return;
  }
  if(chat)setChatState(chat,"loading","Copilot is responding…");
  const rd=r.body.getReader(),dec=new TextDecoder();let buf="";
  for(;;){
   const{value,done}=await rd.read();if(done)break;
   buf+=dec.decode(value,{stream:true});let i;
   while((i=buf.indexOf("\n\n"))>=0){
    const m=buf.slice(0,i);buf=buf.slice(i+2);
    if(m.startsWith("data: ")){
     const ev=JSON.parse(m.slice(6));if(ev.ev==="final")completed=true;on(ev);
     if(chat&&ev.ev==="tok")setChatState(chat,"loading","Generating a response…");
    }
   }
  }
  if(chat){
   if(completed)setChatState(chat,"complete","Response complete.");
   else showChatError(chat,"The response stream ended before completion. Please try again.");
  }
 }catch(error){
  if(chat){showChatError(chat,"Connection to Copilot failed. Check your connection and try again.");return}
  throw error;
 }
}
R.chat=b=>{let cid=null,hist=[];const el=h("div",{class:"card chat"}),msgs=h("div",{class:"msgs"}),inp=h("input",{placeholder:"Ask about outlets, staff, inventory, campaigns, reviews or audits",onkeydown:e=>{if(e.key==="Enter")send(inp.value)}});
 const lang=h("select",{class:"in",style:"width:auto",onchange:()=>{S.lang=lang.value;localStorage.setItem("lang",S.lang)}},...b.langs.map(l=>h("option",{value:l,selected:l===S.lang},l)));
 const hsel=h("select",{class:"in",style:"width:auto;max-width:260px",onchange:()=>{if(hsel.value)openChat(hsel.value)}},h("option",{value:""},"Previous chats…"));
 const listChats=async()=>{const r=await api("/api/chats");if(!r.chats)return;hsel.replaceChildren(h("option",{value:""},r.chats.length?`Previous chats (${r.chats.length})`:"No saved chats yet"),...r.chats.map(c=>h("option",{value:c.id,selected:c.id===cid},c.title+" · "+(c.ts||"").replace("T"," ").slice(5,16))));return r.chats};
 const showMsg=m=>{if(m.role==="user")msgs.append(h("div",{class:"m u"},m.text));else{const o=h("div",{class:"md"});o.innerHTML=md(m.text);const a=h("div",{class:"m a"},o);if(m.en){const tg=h("a",{class:"lnk",style:"cursor:pointer;font-size:12px",onclick:()=>{const on=tg._e=!tg._e;o.innerHTML=md(on?m.en:m.text);tg.textContent=on?"Show "+(m.lang||"translation"):"Show English original"}},"Show English original");a.append(h("div",{class:"st"},"Translated with NLLB-200 ",tg))}if(m.sql)a.append(h("details",{class:"cites"},h("summary",null,"Show the exact query"),h("pre",{style:"white-space:pre-wrap;font-size:11px"},m.sql)));msgs.append(a)}};
 const openChat=async id=>{const r=await api("/api/chats/"+encodeURIComponent(id));if(!r.msgs)return;cid=id;hist=r.msgs;msgs.replaceChildren();hist.forEach(showMsg);msgs.lastChild&&msgs.lastChild.scrollIntoView({block:"nearest"});listChats()};
 const newChat=()=>{cid=null;hist=[];msgs.replaceChildren();hsel.value="";inp.focus()};
 const delChat=async()=>{if(!cid||!confirm("Delete this chat?"))return;await api("/api/chats/"+encodeURIComponent(cid),{method:"DELETE"});newChat();listChats()};
 const saveChat=async()=>{const r=await api("/api/chats/save",{json:{id:cid,msgs:hist}});if(r.id){cid=r.id;listChats()}};
 listChats().then(cs=>{if(cs&&cs.length&&!hist.length)openChat(cs[0].id)});
 const send=async q=>{q=q.trim();if(!q)return;inp.value="";hist.push({role:"user",text:q});msgs.append(h("div",{class:"m u"},q));const a=h("div",{class:"m a"}),stg=h("div"),tr=h("div"),out=h("div",{class:"md"});a.append(stg,tr,out);msgs.append(a);let acc="";const sc=()=>{msgs.lastChild.scrollIntoView({block:"nearest"})};
  await sse("/api/copilot",{q,lang:S.lang},ev=>{if(ev.ev==="stage"){stg.append(h("div",{class:"st"},ev.text))}else if(ev.ev==="cites"){const d=h("details",{class:"cites"},h("summary",null,`Sources (${ev.rows.length})`),...ev.rows.map(r=>h("div",{class:"st",title:r.text},h("b",null,`[${r.n}] `),`${r.title} · ${r.source} · ${r.why||r.score}`)));stg.append(d)}else if(ev.ev==="trace"){tr.replaceChildren(h("div",{class:"tbl",style:"margin:6px 0"},h("table",null,h("tbody",null,...ev.rows.map(r=>h("tr",null,h("td",null,r.agent),h("td",null,h("span",{class:"pill",style:`color:${tone(r.risk)};border-color:${tone(r.risk)}55`},r.risk)),h("td",{style:"white-space:normal"},r.finding)))))))}else if(ev.ev==="tok"){acc+=ev.text;out.innerHTML=md(acc)}else if(ev.ev==="final"){out.innerHTML=md(ev.text);hist.push({role:"assistant",text:ev.text,en:ev.en,lang:ev.lang,sql:ev.sql});saveChat();if(ev.en){const tg=h("a",{class:"lnk",style:"cursor:pointer;font-size:12px;margin-left:8px",onclick:()=>{const on=tg._e=!tg._e;out.innerHTML=md(on?ev.en:ev.text);tg.textContent=on?"Show "+(ev.lang||"translation"):"Show English original"}},"Show English original");stg.append(h("div",{class:"st"},"Translated with NLLB-200 ",tg))}if(ev.sql)stg.append(h("details",{class:"cites"},h("summary",null,"Show the exact query"),h("pre",{style:"white-space:pre-wrap;font-size:11px"},ev.sql)));stg.append(h("div",{class:"st"},`done in ${(ev.ms/1000).toFixed(1)}s`+(ev.tok_s?` · ${ev.tok_s} tok/s`:"")))}sc()})};
 el.append(h("div",{style:"display:flex;gap:8px;align-items:center;flex-wrap:wrap"},h("button",{class:"btn sm",onclick:newChat},"+ New chat"),hsel,h("button",{class:"btn sm ghost",onclick:delChat,title:"Delete this chat"},"Delete"),h("b",{style:"margin-left:8px"},"Answer language"),lang,null),msgs,h("div",{class:"filters"},...b.examples.map(e=>h("span",{class:"chip",onclick:()=>send(e)},e))),h("div",{class:"cin"},inp,(()=>{const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR)return null;const VL={Hindi:"hi-IN",Tamil:"ta-IN",Telugu:"te-IN",Kannada:"kn-IN",Malayalam:"ml-IN",Bengali:"bn-IN",Gujarati:"gu-IN",Marathi:"mr-IN",Punjabi:"pa-IN",Urdu:"ur-IN",Arabic:"ar-SA",French:"fr-FR",German:"de-DE",Spanish:"es-ES",Portuguese:"pt-PT",Chinese:"zh-CN",Japanese:"ja-JP",Korean:"ko-KR",Russian:"ru-RU",Indonesian:"id-ID",Turkish:"tr-TR",Italian:"it-IT",Dutch:"nl-NL",Thai:"th-TH",Vietnamese:"vi-VN"};let rec=null;const mic=h("button",{class:"btn",title:"Speak your question (browser speech recognition)",onclick:()=>{if(rec){rec.stop();return}rec=new SR();const k=Object.keys(VL).find(x=>S.lang.startsWith(x));rec.lang=k?VL[k]:"en-IN";rec.interimResults=true;rec.onresult=e=>{inp.value=[...e.results].map(r=>r[0].transcript).join(" ")};rec.onend=()=>{rec=null;mic.textContent="🎤";if(inp.value.trim())send(inp.value)};mic.textContent="⏺";try{rec.start()}catch(e){rec=null;mic.textContent="🎤"}}},"🎤");return mic})(),h("button",{class:"btn primary",onclick:()=>send(inp.value)},"Ask")));return{el,update(){}}};

// ---------------------------------------------------------------- shell
const UI={};
UI.openEntity=async id=>{if(!id)return;$("#dt").textContent=id;$("#db").replaceChildren(h("div",{class:"boot"},h("div",{class:"spin"}),"Loading…"));$("#drawer").classList.add("on");const d=await api("/api/detail/"+encodeURIComponent(id));if(d.title===undefined){$("#db").replaceChildren(h("div",{class:"callout warn"},d.msg||"Not available"));return}$("#dt").textContent=d.title||id;$("#db").replaceChildren();mountList($("#db"),d.blocks||[],"d");translateUI($("#db"))};
UI.closeDrawer=()=>$("#drawer").classList.remove("on");
UI.go=(id,tab,params)=>{
 const allowed=pageIsAllowed(id),target=allowed?id:firstAllowedPage();
 if(!target){toast("Access unavailable: no pages are available for this account.",true);return}
 S.page=target;S.tab=allowed?(tab||null):null;S.params=allowed?(params||{}):{};
 history.replaceState(null,"","#"+target+(S.tab?":"+S.tab:""));loadPage(false);renderNav();
 if(!allowed){const page=S.me.menu.find(item=>item&&item.id===target);toast(`Access unavailable: ${id||"that page"} is not in your available pages. Redirected to ${page?page.label:target}.`,true)}
};
function fmtTime(t){if(!t)return"Never";const d=new Date(t);return isNaN(d)?String(t):d.toLocaleString("en-IN",{timeZone:"Asia/Kolkata",day:"2-digit",month:"short",year:"numeric",hour:"2-digit",minute:"2-digit",hour12:true})+" IST"}
function fmtShort(t){if(!t)return"Never";const d=new Date(t);return isNaN(d)?String(t):d.toLocaleString("en-IN",{timeZone:"Asia/Kolkata",day:"2-digit",month:"short",hour:"2-digit",minute:"2-digit",hour12:true})+" IST"}
function avatarEl(src,name,size){const s=size||32;if(src)return h("img",{class:"av",src:src,alt:"",style:`width:${s}px;height:${s}px`});const ini=String(name||"?").split(/[\s@._-]+/).filter(Boolean).slice(0,2).map(x=>x[0].toUpperCase()).join("")||"?";return h("span",{class:"av",style:`width:${s}px;height:${s}px;font-size:${Math.round(s*.4)}px`,"aria-hidden":"true"},ini)}
function renderProfilePage(){
 const root=h("div",{class:"profile-page"});
 const status=h("p",{class:"profile-feedback","role":"status","aria-live":"polite"});
 const say=(el,msg,kind)=>{el.className="profile-feedback"+(kind?" is-"+kind:"");el.textContent=msg||""};
 const head=h("section",{class:"profile-header card"}),details=h("div",{class:"profile-details"});
 const username=h("input",{id:"profile-username",name:"username",type:"text",autocomplete:"username",minlength:"3",required:true});
 const editStatus=h("p",{class:"profile-feedback","role":"status","aria-live":"polite"});
 const edit=h("form",{class:"profile-form",hidden:true});
 const editCancel=h("button",{class:"btn",type:"button"},"Cancel"),editSave=h("button",{class:"btn primary",type:"submit"},"Save username");
 edit.append(h("div",{class:"profile-edit-grid"},h("div",{class:"fld"},h("label",{for:"profile-username"},"Username"),username)),h("div",{class:"profile-form-actions"},editCancel,editSave),editStatus);
 const editButton=h("button",{class:"btn sm",type:"button","aria-expanded":"false"},"Change username");
 const currentPassword=h("input",{id:"profile-current-password",name:"current-password",type:"password",autocomplete:"current-password",required:true});
 const newPassword=h("input",{id:"profile-new-password",name:"new-password",type:"password",autocomplete:"new-password",minlength:"8",required:true});
 const confirmPassword=h("input",{id:"profile-confirm-password",name:"confirm-password",type:"password",autocomplete:"new-password",minlength:"8",required:true});
 const passwordStatus=h("p",{class:"profile-feedback","role":"status","aria-live":"polite"});
 const passwordForm=h("form",{class:"profile-form",hidden:true});
 const passwordCancel=h("button",{class:"btn",type:"button"},"Cancel"),passwordSave=h("button",{class:"btn primary",type:"submit"},"Save password");
 passwordForm.append(h("div",{class:"profile-edit-grid"},
  h("div",{class:"fld"},h("label",{for:"profile-current-password"},"Current password"),h("div",{class:"password-field"},currentPassword,passwordToggle(currentPassword))),
  h("div",{class:"fld"},h("label",{for:"profile-new-password"},"New password"),h("div",{class:"password-field"},newPassword,passwordToggle(newPassword))),
  h("div",{class:"fld"},h("label",{for:"profile-confirm-password"},"Confirm new password"),h("div",{class:"password-field"},confirmPassword,passwordToggle(confirmPassword))),
  h("p",{class:"password-guidance profile-password-guidance"},"Use at least 8 characters with uppercase and lowercase letters, a number, and a symbol.")),
  h("div",{class:"profile-form-actions"},passwordCancel,passwordSave),passwordStatus);
 const passwordButton=h("button",{class:"btn sm",type:"button","aria-expanded":"false"},"Change password");
 const criteria=passwordCriteriaForProfile(newPassword);
 let p=null;
 const row=(label,text)=>h("div",{class:"profile-row"},h("div",{class:"profile-label"},label),h("div",{class:"profile-value"},text));
 const draw=()=>{
  const initials=(p.username||p.email||"?").split(/[\s@._-]+/).filter(Boolean).slice(0,2).map(x=>x[0].toUpperCase()).join("")||"?";
  head.replaceChildren(h("div",{class:"profile-avatar","aria-label":"Profile photo"},p.picture?h("img",{src:p.picture,alt:"Your profile photo"}):initials),h("div",{class:"profile-header-copy"},h("span",{class:"auth-kicker"},"FRANCHISEOPS AI ACCOUNT"),h("h2",null,p.username),h("p",null,p.email)),h("span",{class:"profile-role"},p.role));
  details.replaceChildren(row("Username",p.username),row("Email address",p.email),row("Role",p.role),row("Outlet",p.outlet||"All outlets"),row("Joined",fmtTime(p.created_at)),row("Last login",fmtTime(p.last_login)));
  username.value=p.username;sqDraw();welcomeDraw();
 };
 editButton.onclick=()=>{const open=edit.hidden;edit.hidden=!open;editButton.setAttribute("aria-expanded",String(open));say(editStatus,"");if(open)username.focus()};
 editCancel.onclick=()=>{username.value=p.username;say(editStatus,"");edit.hidden=true;editButton.setAttribute("aria-expanded","false")};
 username.addEventListener("input",()=>username.setCustomValidity(""));
 edit.addEventListener("submit",async event=>{event.preventDefault();say(editStatus,"");
  username.setCustomValidity(/^[A-Za-z0-9_]{3,}$/.test(username.value.trim())?"":"Use at least 3 letters, numbers, or underscores.");
  if(!edit.reportValidity()){say(editStatus,"Check the highlighted field.","error");return}
  editSave.disabled=true;const r=await api("/api/profile/username",{json:{username:username.value.trim()}});editSave.disabled=false;
  if(!r.ok){say(editStatus,r.msg||"Could not update the username.","error");return}
  p.username=r.username;S.me.user.username=r.username;draw();say(editStatus,"Username updated.","notice");toast("Username updated.");
 });
 passwordButton.onclick=()=>{const open=passwordForm.hidden;passwordForm.hidden=!open;passwordButton.setAttribute("aria-expanded",String(open));say(passwordStatus,"");if(open)currentPassword.focus()};
 passwordCancel.onclick=()=>{passwordForm.reset();say(passwordStatus,"");passwordForm.hidden=true;passwordButton.setAttribute("aria-expanded","false")};
 for(const f of [currentPassword,newPassword,confirmPassword])f.addEventListener("input",()=>f.setCustomValidity(""));
 passwordForm.addEventListener("submit",async event=>{event.preventDefault();say(passwordStatus,"");
  if(!passwordForm.reportValidity()){say(passwordStatus,"Check the highlighted fields.","error");return}
  if(criteria.some(test=>!test())){say(passwordStatus,"Choose a password that meets the listed requirements.","error");newPassword.focus();return}
  if(newPassword.value!==confirmPassword.value){confirmPassword.setCustomValidity("Passwords do not match.");confirmPassword.reportValidity();say(passwordStatus,"The new passwords do not match.","error");return}
  passwordSave.disabled=true;const r=await api("/api/profile/password",{json:{current_password:currentPassword.value,new_password:newPassword.value,confirm_password:confirmPassword.value}});passwordSave.disabled=false;
  if(!r.ok){say(passwordStatus,r.msg||"Could not change the password.","error");return}
  setToken(r.token,!!localStorage.getItem("fo_token"));passwordForm.reset();passwordForm.hidden=true;passwordButton.setAttribute("aria-expanded","false");say(status,"Password changed. Other sessions were signed out.","notice");toast("Password changed.");
 });
 const welcome=h("section",{class:"card profile-welcome"});
 const sessionEnds=()=>{try{const b=authToken().split(".")[1].replace(/-/g,"+").replace(/_/g,"/");const x=JSON.parse(atob(b));return x.exp?fmtTime(new Date(x.exp*1000).toISOString()):"unknown"}catch(e){return"unknown"}};
 const welcomeDraw=()=>welcome.replaceChildren(h("div",null,h("h2",null,"Welcome back, "+p.username+"!"),h("p",null,"You are signed in as "+p.role+(p.outlet?" at "+p.outlet:" (all outlets)")+". Member since "+fmtTime(p.created_at)+".")),h("div",{class:"session-pill"},h("span",{class:"dot g"}),"Session active · expires "+sessionEnds()));
 const photoInput=h("input",{type:"file",accept:"image/png,image/jpeg,image/webp",hidden:true,id:"profile-photo-file"});
 const photoStatus=h("p",{class:"profile-feedback","role":"status","aria-live":"polite"});
 const setPhoto=async body=>{const r=await api("/api/profile/picture",{json:body});if(!r.ok){say(photoStatus,r.msg||"Could not save the photo.","error");return}
  p.picture=r.picture;S.me.user.picture=r.picture;draw();const slot=$(".av-slot");if(slot)slot.replaceChildren(avatarEl(r.picture,p.username,34));say(photoStatus,r.picture?"Photo saved.":"Photo removed.","notice");toast(r.picture?"Photo saved.":"Photo removed.")};
 photoInput.addEventListener("change",()=>{const f=photoInput.files[0];photoInput.value="";if(!f)return;
  if(!/^image\/(png|jpeg|webp)$/.test(f.type)){say(photoStatus,"Choose a PNG, JPEG or WebP image.","error");return}
  if(f.size>8*1024*1024){say(photoStatus,"That image is larger than 8 MB.","error");return}
  const img=new Image(),url=URL.createObjectURL(f);
  img.onload=()=>{const n=192,cv=document.createElement("canvas");cv.width=cv.height=n;const cx=cv.getContext("2d");cx.fillStyle="#fff";cx.fillRect(0,0,n,n);const s=Math.min(img.width,img.height);cx.drawImage(img,(img.width-s)/2,(img.height-s)/2,s,s,0,0,n,n);URL.revokeObjectURL(url);setPhoto({image:cv.toDataURL("image/jpeg",0.85)})};
  img.onerror=()=>{URL.revokeObjectURL(url);say(photoStatus,"That image could not be read.","error")};img.src=url});
 const photoCard=h("section",{class:"card profile-card profile-photo","aria-labelledby":"profile-photo-title"},h("div",{class:"profile-section-heading"},h("div",null,h("h2",{id:"profile-photo-title"},"Profile photo"),h("p",null,"Shown in the sidebar and to your Admin. It is cropped to a small square before it is saved."))),
  h("div",{class:"photo-actions"},h("button",{class:"btn sm",type:"button",onclick:()=>photoInput.click()},"Upload photo"),h("button",{class:"btn sm ghost",type:"button",onclick:()=>setPhoto({remove:true})},"Remove photo"),photoInput),photoStatus);
 const sqCurrent=h("p",{class:"profile-feedback"}),sqStatus=h("p",{class:"profile-feedback","role":"status","aria-live":"polite"});
 const sqSelect=h("select",{id:"profile-sq",name:"security_question",required:true},h("option",{value:""},"Loading questions…"));
 const sqAnswer=h("input",{id:"profile-sq-answer",name:"security_answer",type:"text",autocomplete:"off",spellcheck:"false",required:true,minlength:"2",maxlength:"100"});
 const sqPassword=h("input",{id:"profile-sq-password",name:"current-password",type:"password",autocomplete:"current-password",required:true});
 const sqSave=h("button",{class:"btn primary",type:"submit"},"Save security question");
 const sqForm=h("form",{class:"profile-form"});
 sqForm.append(h("div",{class:"profile-edit-grid"},h("div",{class:"fld"},h("label",{for:"profile-sq"},"Security question"),sqSelect),h("div",{class:"fld"},h("label",{for:"profile-sq-answer"},"Your answer"),sqAnswer),
  h("div",{class:"fld"},h("label",{for:"profile-sq-password"},"Current password"),h("div",{class:"password-field"},sqPassword,passwordToggle(sqPassword)))),h("div",{class:"profile-form-actions"},sqSave),sqStatus);
 api("/api/auth/options").then(o=>{if(o.questions)sqSelect.replaceChildren(h("option",{value:""},"Choose a security question"),...o.questions.map(x=>h("option",{value:x},x)))});
 const sqDraw=()=>{sqCurrent.textContent=p&&p.security_question?"Current question: "+p.security_question:"No security question yet. Set one so you can recover your password without e-mail."};
 sqForm.addEventListener("submit",async event=>{event.preventDefault();say(sqStatus,"");
  if(!sqForm.reportValidity()){say(sqStatus,"Check the highlighted fields.","error");return}
  sqSave.disabled=true;const r=await api("/api/profile/security",{json:{current_password:sqPassword.value,security_question:sqSelect.value,security_answer:sqAnswer.value}});sqSave.disabled=false;
  if(!r.ok){say(sqStatus,r.msg||"Could not save the security question.","error");return}
  p.security_question=r.security_question;sqDraw();sqForm.reset();say(sqStatus,"Security question saved.","notice");toast("Security question saved.");
 });
 const questionCard=h("section",{class:"card profile-card","aria-labelledby":"profile-sq-title"},h("div",{class:"profile-section-heading"},h("div",null,h("h2",{id:"profile-sq-title"},"Security question"),h("p",null,"Used by Forgot password. Your answer is stored scrambled and never shown."))),sqCurrent,sqForm);
 const account=h("section",{class:"card profile-card","aria-labelledby":"profile-account-title"},h("div",{class:"profile-section-heading"},h("div",null,h("h2",{id:"profile-account-title"},"Account information"),h("p",null,"Your details. Your password hash is never shown."))),details);
 const editCard=h("section",{class:"card profile-card","aria-labelledby":"profile-edit-title"},h("div",{class:"profile-section-heading"},h("div",null,h("h2",{id:"profile-edit-title"},"Username"),h("p",null,"Pick the name shown in the workspace.")),editButton),edit);
 const securityCard=h("section",{class:"card profile-card","aria-labelledby":"profile-security-title"},h("div",{class:"profile-section-heading"},h("div",null,h("h2",{id:"profile-security-title"},"Security"),h("p",null,"Enter your current password to set a new one.")),passwordButton),passwordForm,status);
 root.append(welcome,head,photoCard,account,editCard,securityCard,questionCard);
 head.replaceChildren(h("div",{class:"boot"},h("div",{class:"spin"}),"Loading your profile…"));
 api("/api/profile").then(r=>{if(!r.profile){head.replaceChildren(h("div",{class:"callout error"},r.msg||"Could not load your profile."));return}p=r.profile;draw()});
 return root;
}
function passwordCriteriaForProfile(input){
 return[()=>input.value.length>=8,()=>/[A-Z]/.test(input.value),()=>/[a-z]/.test(input.value),()=>/[0-9]/.test(input.value),()=>/[!@#$%^&*(),.?":{}|<>~`_+=/\\[\];'-]/.test(input.value)];
}
function pickOutlet(username,role,outlets,def){
 return new Promise(resolve=>{
  const sel=h("select",{class:"in","aria-label":"Outlet"},...outlets.map(x=>h("option",{value:x},x)));if(def)sel.value=def;
  const done=v=>{ov.remove();document.removeEventListener("keydown",kd,true);resolve(v)};
  const kd=e=>{if(e.key==="Escape")done(null)};
  const ov=h("div",{class:"kpal",role:"dialog","aria-modal":"true","aria-label":"Choose an outlet",onclick:e=>{if(e.target===ov)done(null)}},
   h("div",{class:"card",style:"padding:20px;display:grid;gap:12px;max-width:420px"},h("h3",{style:"margin:0"},"Choose the outlet"),
    h("p",{class:"sub",style:"margin:0"},username+" becomes a "+role+", who works at one outlet. Which outlet?"),sel,
    h("div",{class:"profile-form-actions"},h("button",{class:"btn",type:"button",onclick:()=>done(null)},"Cancel"),h("button",{class:"btn primary",type:"button",onclick:()=>done(sel.value)},"Apply"))));
  document.addEventListener("keydown",kd,true);document.body.append(ov);sel.focus();
 });
}
function renderAdminDashboard(){
 const root=h("div",{class:"admin-dashboard"});
 let data=null,query="",pendingDelete=null;
 const kpis=h("section",{class:"admin-kpis","aria-label":"Administration overview"});
 const roleCard=h("section",{class:"card admin-card","aria-labelledby":"admin-roles-title"});
 const userSection=h("section",{class:"card admin-card","aria-labelledby":"admin-users-title"});
 const activitySection=h("section",{class:"card admin-card","aria-labelledby":"admin-activity-title"});
 const matrixSection=h("section",{class:"card admin-card","aria-labelledby":"admin-matrix-title"});
 const formStatus=h("p",{class:"profile-feedback","role":"status","aria-live":"polite"});
 const say=(msg,kind)=>{formStatus.className="profile-feedback"+(kind?" is-"+kind:"");formStatus.textContent=msg||""};
 const act=async(path,body)=>{const r=await api(path,{json:body||{}});if(r.ok){toast(r.msg);await load()}else toast(r.msg||"That action failed.",true);return r};
 const kpi=(label,value,sub,tone)=>h("article",{class:"kpi "+(tone||"")},h("div",{class:"l"},label),h("div",{class:"v"},String(value)),h("div",{class:"s"},sub));
 const table=(heads,rows,empty)=>h("div",{class:"tbl admin-table"},h("table",null,h("thead",null,h("tr",null,...heads.map(x=>h("th",null,x)))),h("tbody",null,...(rows.length?rows:[h("tr",null,h("td",{colspan:String(heads.length)},h("div",{class:"admin-empty",role:"status"},empty)))]))));
 // ---- add user form
 const email=h("input",{id:"admin-user-email",name:"email",type:"email",autocomplete:"off",required:true});
 const username=h("input",{id:"admin-user-username",name:"username",type:"text",autocomplete:"off",minlength:"3",required:true});
 const pass=h("input",{id:"admin-user-password",name:"password",type:"password",autocomplete:"new-password",minlength:"8",required:true});
 const role=h("select",{id:"admin-user-role",name:"role",required:true});
 const outlet=h("select",{id:"admin-user-outlet",name:"outlet"});
 const outletField=h("div",{class:"fld",hidden:true},h("label",{for:"admin-user-outlet"},"Outlet"),outlet);
 const addForm=h("form",{class:"admin-add-form",hidden:true,novalidate:true,"aria-labelledby":"admin-add-title"});
 const syncOutlet=()=>{const need=data&&data.scoped_roles.includes(role.value);outletField.hidden=!need;outlet.required=!!need;if(!need)outlet.value=""};
 role.addEventListener("change",syncOutlet);
 addForm.append(h("div",{class:"admin-editor-heading"},h("div",null,h("h3",{id:"admin-add-title"},"Add user"),h("p",null,"The user signs in with the temporary password and should change it in their profile."))),
  h("div",{class:"admin-form-grid"},h("div",{class:"fld"},h("label",{for:"admin-user-email"},"Email address"),email),h("div",{class:"fld"},h("label",{for:"admin-user-username"},"Username"),username),
   h("div",{class:"fld"},h("label",{for:"admin-user-password"},"Temporary password"),h("div",{class:"password-field"},pass,passwordToggle(pass))),h("div",{class:"fld"},h("label",{for:"admin-user-role"},"Role"),role),outletField),
  formStatus,h("div",{class:"admin-form-footer"},h("span",{class:"sub"},"The same email and password rules as signup apply."),h("div",{class:"profile-form-actions"},
   h("button",{class:"btn",type:"button",onclick:()=>{addForm.reset();say("");addForm.hidden=true;syncOutlet()}},"Close"),h("button",{class:"btn primary",type:"submit"},"Create user"))));
 addForm.addEventListener("submit",async event=>{event.preventDefault();say("");
  if(!addForm.reportValidity()){say("Check the highlighted fields.","error");return}
  const r=await api("/api/admin/users",{json:{email:email.value.trim(),username:username.value.trim(),password:pass.value,role:role.value,outlet:outlet.value}});
  if(!r.ok){say(r.msg||"Could not create the user.","error");return}
  toast(r.msg);addForm.reset();addForm.hidden=true;syncOutlet();await load();
 });
 const addButton=h("button",{class:"btn primary",type:"button",onclick:()=>{addForm.hidden=false;email.focus()}},"Add user");
 const search=h("input",{class:"admin-search",type:"search",placeholder:"Search users by email, username, role or outlet","aria-label":"Search users",oninput:()=>{query=search.value.trim().toLowerCase();drawUsers()}});
 // ---- users table
 const roleCell=u=>{
  const me=data.me===u.id;const sel=h("select",{class:"in admin-role-select","aria-label":"Role of "+u.username,disabled:me,title:me?"You cannot change your own role.":""},...data.roles.map(r=>h("option",{value:r,selected:r===u.role},r)));
  sel.addEventListener("change",async()=>{
   let o="";if(data.scoped_roles.includes(sel.value)){o=await pickOutlet(u.username,sel.value,data.outlets,u.outlet||u.saved_outlet||"");if(!o){sel.value=u.role;return}}
   const r=await act("/api/admin/users/"+u.id+"/role",{role:sel.value,outlet:o});if(!r.ok)sel.value=u.role;
  });return sel};
 const outletCell=u=>{
  if(!data.scoped_roles.includes(u.role))return h("span",{class:"sub",style:"margin:0"},"All outlets");
  const sel=h("select",{class:"in admin-role-select","aria-label":"Outlet of "+u.username},...data.outlets.map(x=>h("option",{value:x,selected:x===u.outlet},x)));
  sel.addEventListener("change",async()=>{const r=await act("/api/admin/users/"+u.id+"/role",{role:u.role,outlet:sel.value});if(!r.ok)sel.value=u.outlet});return sel};
 const actionsCell=u=>{
  const me=data.me===u.id;
  if(pendingDelete===u.id)return h("div",{class:"admin-row-actions"},h("span",{class:"sub",style:"margin:0 6px 0 0"},"Delete "+u.username+"?"),h("button",{class:"btn sm danger",type:"button",onclick:async()=>{pendingDelete=null;await act("/api/admin/users/"+u.id+"/delete",{confirm:true})}},"Confirm delete"),h("button",{class:"btn sm",type:"button",onclick:()=>{pendingDelete=null;drawUsers()}},"Cancel"));
  return h("div",{class:"admin-row-actions"},
   h("button",{class:"btn sm",type:"button",disabled:me&&!u.locked,title:me?"You cannot lock your own account.":"",onclick:()=>act("/api/admin/users/"+u.id+(u.locked?"/unlock":"/lock"))},u.locked?"Unlock":"Lock"),
   h("button",{class:"btn sm danger",type:"button",disabled:me,title:me?"You cannot delete your own account.":"",onclick:()=>{pendingDelete=u.id;drawUsers()}},"Delete"));
 };
 const drawUsers=()=>{
  if(!data)return;const rows=data.users.filter(u=>!query||[u.email,u.username,u.role,u.outlet||""].join(" ").toLowerCase().includes(query)).map(u=>
   h("tr",null,h("td",null,u.email),h("td",null,h("span",{class:"who-cell"},avatarEl(u.picture,u.username,26),u.username+(data.me===u.id?" (you)":""))),h("td",null,roleCell(u)),h("td",null,outletCell(u)),
    h("td",null,h("span",{class:"pill",style:"color:"+(u.locked?"#cd2b31":"#0b7a6c")+";border-color:currentColor"},u.locked?"Locked":"Active")),h("td",null,fmtShort(u.created_at)),h("td",null,fmtShort(u.last_login)),h("td",null,actionsCell(u))));
  userTable.replaceChildren(table(["Email","Username","Role","Outlet","Status","Created","Last login","Actions"],rows,query?"No users match your search.":"No users yet."));
 };
 const userTable=h("div",null);
 userSection.append(h("div",{class:"admin-section-heading"},h("div",null,h("h2",{id:"admin-users-title"},"User management"),h("p",null,"Promote or demote with the role drop-down. A locked user is signed out at once.")),addButton),h("div",{class:"admin-user-toolbar"},search),addForm,userTable);
 const draw=()=>{
  const k=data.kpis;
  kpis.replaceChildren(kpi("Total users",k.total,"registered accounts"),kpi("Active users",k.active,"can sign in"),kpi("Locked users",k.locked,"blocked from signing in",k.locked?"Warning":""),kpi("Roles in use",Object.values(k.per_role).filter(n=>n>0).length,"of "+data.roles.length+" roles"));
  roleCard.replaceChildren(h("div",{class:"admin-section-heading"},h("div",null,h("h2",{id:"admin-roles-title"},"Users per role"),h("p",null,"How many accounts hold each role."))),
   h("div",{class:"admin-row-actions"},...data.roles.map(r=>h("span",{class:"chip"},r+": ",h("b",null,String(k.per_role[r]||0))))));
  role.replaceChildren(h("option",{value:""},"Choose a role"),...data.roles.map(r=>h("option",{value:r},r)));
  outlet.replaceChildren(h("option",{value:""},"Choose an outlet"),...data.outlets.map(x=>h("option",{value:x},x)));syncOutlet();
  drawUsers();
  activitySection.replaceChildren(h("div",{class:"admin-section-heading"},h("div",null,h("h2",{id:"admin-activity-title"},"Activity log"),h("p",null,"Latest "+data.activity.length+" actions: who, what and when."))),
   table(["Time","Who","Action","Target","Detail"],data.activity.map(a=>h("tr",null,h("td",null,fmtTime(a.ts)),h("td",null,a.actor),h("td",null,h("span",{class:"pill",style:"color:#3451b2;border-color:currentColor"},String(a.event).replace(/_/g," "))),h("td",null,a.target),h("td",null,a.detail))),"No activity recorded yet."));
  const cols=Object.keys(data.matrix[0]);
  matrixSection.replaceChildren(h("div",{class:"admin-section-heading"},h("div",null,h("h2",{id:"admin-matrix-title"},"Roles and privileges"),h("p",null,"What each role can open and do. Enforced on the server, not only in the menu."))),
   table(cols,data.matrix.map(r=>h("tr",null,...cols.map(c=>h("td",{style:c==="Role"?"font-weight:600":"text-align:center;color:"+(r[c]==="✓"?"#0b7a6c":"#cd2b31")},r[c])))),"No roles."));
 };
 const load=async()=>{
  const d=await api("/api/admin/overview");
  if(!d.users){root.replaceChildren(h("div",{class:"callout error"},d.msg||"Could not load the admin dashboard."));return}
  data=d;data.me=S.me&&S.me.user&&S.me.user.id;draw();
 };
 root.append(kpis,roleCard,userSection,activitySection,matrixSection);
 kpis.replaceChildren(h("div",{class:"boot"},h("div",{class:"spin"}),"Loading the dashboard…"));load();
 return root;
}
async function loadPage(silent){const seq=++S.seq;clearTimeout(S.timer);if(S.page==="profile"||S.page==="admin"){S.tab=null;S.params={};S.live=0;const profile=S.page==="profile";$("#ttl").textContent=profile?"My Profile":"Admin Dashboard";$("#sub").textContent=profile?"Account details and security":"Users, access, and recent activity";document.title=(profile?"My Profile":"Admin Dashboard")+" · "+S.me.name;$("#tabs").replaceChildren();$("#tabs").style.display="none";$("#acts").replaceChildren();$("#blocks").replaceChildren(profile?renderProfilePage():renderAdminDashboard());return}const q=new URLSearchParams();if(S.tab)q.set("tab",S.tab);if(Object.keys(S.params).length)q.set("p",JSON.stringify(S.params));
 if(!silent){S.tree=null;$("#blocks").replaceChildren(h("div",{class:"boot"},h("div",{class:"spin"}),"Loading…"))}
 const t=performance.now();const d=await api(`/api/page/${S.page}?`+q);if(seq!==S.seq)return;
 if(d.blocks===undefined){$("#blocks").replaceChildren(h("div",{class:"callout error",role:"alert"},h("span",null,h("b",null,d.status===403?"Access denied (403). ":d.status===404?"Not found. ":"Could not load this page. "),d.msg||"")));return}
 S.ms=Math.round(performance.now()-t);$("#ttl").textContent=d.title;$("#sub").textContent=d.sub||"";document.title=d.title+" · "+S.me.name;
 const tabs=$("#tabs");tabs.replaceChildren(...(d.tabs||[]).map(x=>h("b",{class:(S.tab||d.tabs[0].id)===x.id?"on":"",onclick:()=>{S.params={};UI.go(S.page,x.id)}},x.label)));tabs.style.display=d.tabs?"":"none";
 $("#acts").replaceChildren(...(d.actions||[]).map(a=>h("button",{class:"btn "+(a.tone||"primary"),onclick:async e=>{e.target.disabled=true;const r=await api(a.url,{json:{}});toast(r.msg,!r.ok);e.target.disabled=false;reloadPage(true)}},a.label)));
 const box=$("#blocks");const focus=document.activeElement&&box.contains(document.activeElement)&&["INPUT","TEXTAREA","SELECT"].includes(document.activeElement.tagName);
 if(!S.tree||silent===false||!S.tree.ok){box.replaceChildren();S.tree={hs:mountList(box,d.blocks,"p"),ok:1,id:S.page,tab:S.tab};translateUI(box)}else S.tree.hs=updList(box,S.tree.hs,d.blocks,"p");
 S.live=d.live||0;sched()}
function sched(){clearTimeout(S.timer);if(S.live&&S.lang==="English"||S.live&&true)S.timer=setTimeout(()=>{if(!document.hidden)loadPage(true);else sched()},S.live*1000)}
function reloadPage(soft){loadPage(!!soft)}
async function translateUI(root){if(S.lang==="English")return;const nodes=[];const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);let n;while((n=w.nextNode())){const t=n.nodeValue.trim();if(t.length>2&&/[A-Za-z]{3}/.test(t)&&!n.parentElement.closest("script,style,pre,code,.m.u,.mono,.noTr,input,select,option")&&!n._tr&&!(n.parentElement.closest("td")&&t.split(/\s+/).length<4)&&!/^[A-Z]{2,6}-?[A-Z]?\d+$/.test(t))nodes.push(n)}
 const list=nodes.slice(0,300);if(!list.length)return;const r=await api("/api/translate_batch",{json:{texts:list.map(n=>n.nodeValue.trim()),lang:S.lang}});if(r.out)list.forEach((n,i)=>{if(r.out[i]){n.nodeValue=r.out[i];n._tr=1}})}
const GROUPS=[["Assistant",["copilot","approvals"]],["Agents",["workforce","outlets","inventory","marketing","sentiment","audit","route","quotes","carriers","weather","margin","customs"]],["Insights",["twin","reports","notifications"]],["Platform",["feeds","admin","profile"]]];
function renderNav(){const nav=$("#nav");if(!nav)return;const menu=S.me&&Array.isArray(S.me.menu)?S.me.menu.filter(m=>m&&pageIsAllowed(m.id)):[];const items=[];const used=new Set();const mk=m=>h("div",{class:"nav"+(m.id===S.page?" on":"")+(m.id==="command"?" cmd":""),"data-id":m.id,onclick:()=>UI.go(m.id)},icon(m.icon),h("span",null,m.label.replace(/^Agent \d+ · /,"")),h("em",{class:"bd",style:"display:none"}));
 GROUPS.forEach(([g,ids])=>{const ms=menu.filter(m=>ids.includes(m.id));if(!ms.length)return;items.push(h("div",{class:"ngrp"},g));ms.forEach(m=>{used.add(m.id);items.push(mk(m))})});
 menu.filter(m=>!used.has(m.id)&&m.id!=="command").forEach(m=>items.push(mk(m)));const c=menu.find(m=>m.id==="command");if(c)items.push(mk(c));
 nav.replaceChildren(...items);updBadges()}
// ---- command palette (Ctrl/Cmd+K): pages, entities, ask the copilot
UI.palette=()=>{if($(".kpal"))return;let sel=0,rows=[];const inp=h("input",{placeholder:"Jump to a page, open an entity (e.g. OUT-007, QTE-0012, SHP-…), or ask the Copilot…"}),lst=h("div",{class:"lst"}),ov=h("div",{class:"kpal",onclick:e=>{if(e.target===ov)close()}},h("div",null,inp,lst));
 const close=()=>{ov.remove();document.removeEventListener("keydown",kd,true)};
 const build=()=>{const q=inp.value.trim(),ql=q.toLowerCase();rows=[];S.me.menu.filter(m=>pageIsAllowed(m.id)&&(!ql||m.label.toLowerCase().includes(ql)||m.id.includes(ql))).forEach(m=>rows.push({g:"Pages",t:m.label.replace(/^Agent \d+ · /,""),s:"go to",f:()=>UI.go(m.id)}));
  if(/^[A-Za-z]{2,5}-?[A-Za-z]?\d+$/.test(q))rows.unshift({g:"Open",t:q.toUpperCase(),s:"entity",f:()=>UI.openEntity(q.toUpperCase())});
  if(q.length>2)rows.push({g:"Ask",t:"Ask the Copilot: "+q,s:"agents + RAG",f:()=>{UI.go("copilot");setTimeout(()=>{const i=document.querySelector(".cin input");if(i){i.value=q;i.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter"}))}},700)}});
  if(sel>=rows.length)sel=rows.length-1;
  let last="";lst.replaceChildren(...rows.flatMap((r,i)=>{const e=[];if(r.g!==last){last=r.g;e.push(h("div",{class:"gl"},r.g))}e.push(h("div",{class:"it"+(i===sel?" on":""),onclick:()=>{close();r.f()}},r.t,h("small",null,r.s)));return e}))};
 const kd=e=>{if(e.key==="Escape"){close()}else if(e.key==="ArrowDown"){sel=Math.min(rows.length-1,sel+1);build();e.preventDefault()}else if(e.key==="ArrowUp"){sel=Math.max(0,sel-1);build();e.preventDefault()}else if(e.key==="Enter"&&document.activeElement===inp){const r=rows[sel];if(r){close();r.f()}}};
 document.addEventListener("keydown",kd,true);inp.addEventListener("input",()=>{sel=0;build()});document.body.append(ov);build();inp.focus()};
document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"&&S.me){e.preventDefault();UI.palette()}});
function updBadges(){const p=S.pulse;if(!p)return;const cc=$('.nav[data-id="command"] .bd');if(cc){const n=p.critical;cc.style.display=n?"":"none";cc.textContent=n;cc.className="bd"}const ap=$('.nav[data-id="approvals"] .bd');if(ap){const n=p.proposed;ap.style.display=n?"":"none";ap.textContent=n;ap.className="bd a"}
 const g=p.gpu||{};$("#gpu").style.display="none";
 $("#hl").innerHTML=`<span class="dot g live"></span>live · health ${p.health==null?"–":Math.round(p.health)} · open ${p.open} · crit ${p.critical} · cycle ${p.cycles}`;$("#warn").style.display="none";if(!p.worker_alive)$("#hl").innerHTML+=' · <b style="color:#e5484d">worker down</b>'}
function openStream(){if(S.es)S.es.close();const es=new EventSource("/api/stream");S.es=es;es.onmessage=e=>{const p=JSON.parse(e.data);if(p.error)return;const old=S.pulse;S.pulse=p;updBadges();if(old&&p.dec!==old.dec&&S.live)loadPage(true)};es.onerror=()=>{}}
// ---------------------------------------------------------------- auth screens
function passwordToggle(input){
 const button=h("button",{class:"password-toggle",type:"button","aria-label":"Show password","aria-pressed":"false",onclick:()=>{const show=input.type==="password";input.type=show?"text":"password";button.textContent=show?"Hide":"Show";button.setAttribute("aria-label",show?"Hide password":"Show password");button.setAttribute("aria-pressed",String(show));input.focus()}},"Show");
 return button;
}
function authSubmitButton(label,busyLabel){
 const spinner=h("span",{class:"login-spinner","aria-hidden":"true",hidden:true}),text=h("span",null,label);
 const button=h("button",{class:"btn primary login-submit",type:"submit","aria-busy":"false"},spinner,text);
 return{button,setLoading(loading){button.disabled=loading;button.setAttribute("aria-busy",String(loading));spinner.hidden=!loading;text.textContent=loading?busyLabel:label}};
}
function passwordCriteria(input){
 return[()=>input.value.length>=8,()=>/[A-Z]/.test(input.value),()=>/[a-z]/.test(input.value),()=>/[0-9]/.test(input.value),()=>/[!@#$%^&*(),.?":{}|<>~`_+=/\\[\];'-]/.test(input.value)];
}
function updatePasswordStrength(input,meter,fill,label,criteria){
 const score=criteria.filter(test=>test()).length;
 const strength=input.value?["","Very weak","Weak","Fair","Good","Strong"][score]:"Enter a password";
 label.textContent=strength;fill.style.width=(score*20)+"%";
 fill.dataset.level=score===0?"empty":score<3?"weak":score<5?"medium":"strong";
 meter.setAttribute("aria-valuenow",String(score));meter.setAttribute("aria-valuetext",strength);
}
function authShell(form,label){
 return h("section",{class:"login","aria-label":label},
  h("aside",{class:"lp","aria-label":"FranchiseOps AI overview"},
   h("div",{class:"login-brand"},h("span",{class:"login-mark","aria-hidden":"true"},icon("radar")),h("span",null,"FranchiseOps",h("b",null," AI"))),
   h("div",{class:"login-message"},h("span",{class:"login-eyebrow"},"FRANCHISE MANAGEMENT PLATFORM"),h("h2",null,"Run every location with greater clarity."),h("p",null,"Bring franchise operations, performance insights, and AI-powered assistance into one workspace.")),
   h("ul",{class:"login-benefits"},h("li",null,h("span",{class:"benefit-icon","aria-hidden":"true"},"01"),h("span",null,h("b",null,"See the bigger picture"),h("small",null,"A clearer view across your franchise network."))),h("li",null,h("span",{class:"benefit-icon","aria-hidden":"true"},"02"),h("span",null,h("b",null,"Turn signals into action"),h("small",null,"Insights from six focused operations agents."))),h("li",null,h("span",{class:"benefit-icon","aria-hidden":"true"},"03"),h("span",null,h("b",null,"Ask your operations Copilot"),h("small",null,"Explore live operational data in plain language.")))),
   h("div",{class:"login-footnote"},"A unified workspace for franchise teams.")),
  h("main",{class:"auth-panel"},themeToggle("btn sm theme-toggle auth-theme-toggle"),form));
}
function renderLogin(){
 clearInterval(S.otpCountdown);S.otpCountdown=null;
 const app=$("#app");app.classList.add("auth-shell");S.authScreen="login";
 const status=h("p",{class:"login-status",role:"status","aria-live":"polite"},S.apiNotice);
 if(S.apiNotice)status.classList.add("is-error");
 if(S.loginNotice){status.textContent=S.loginNotice;status.className="login-status is-notice";S.loginNotice=""}
 const email=h("input",{id:"login-identity",name:"identity",type:"text",autocomplete:"username",autocapitalize:"none",spellcheck:"false",required:true});
 const password=h("input",{id:"login-password",name:"password",type:"password",autocomplete:"current-password",required:true});
 const toggle=passwordToggle(password);
 const submitLabel=h("span",null,"Sign in"),spinner=h("span",{class:"login-spinner","aria-hidden":"true",hidden:true});
 const submit=h("button",{id:"login-submit",class:"btn primary login-submit",type:"submit","aria-busy":"false"},spinner,submitLabel);
 UI.setLoginLoading=loading=>{submit.disabled=loading;submit.setAttribute("aria-busy",String(loading));spinner.hidden=!loading;submitLabel.textContent=loading?"Signing in...":"Sign in"};
 email.addEventListener("input",()=>email.setCustomValidity(""));
 password.addEventListener("input",()=>password.setCustomValidity(""));
 const unavailable=async event=>{
  event.preventDefault();status.className="login-status";status.textContent="";
  email.setCustomValidity(email.value.trim()?"":"Enter your email or username.");
  password.setCustomValidity(password.value?"":"Enter your password.");
  if(!event.currentTarget.reportValidity()){status.className="login-status is-error";status.textContent="Enter your email or username and password.";return}
  UI.setLoginLoading(true);
  const r=await api("/api/auth/login",{json:{identity:email.value.trim(),password:password.value}});
  UI.setLoginLoading(false);
  if(r.ok&&r.token){setToken(r.token,$("#remember-me").checked);S.me=null;S.apiNotice="";render();return}
  status.className="login-status is-error";status.textContent=r.msg||"Could not sign in.";password.value="";password.focus();
 };
 const showSignup=event=>{event.preventDefault();S.authScreen="signup";renderSignup()};
 const showForgot=event=>{event.preventDefault();S.authScreen="forgot";renderForgotPassword()};
 const form=h("form",{class:"auth auth-form",novalidate:true,onsubmit:unavailable},
  h("div",{class:"auth-heading"},h("span",{class:"auth-kicker"},"FRANCHISE OPERATIONS INTELLIGENCE"),h("h1",null,"Welcome back"),h("p",null,"Sign in to continue to your operations workspace.")),
  h("div",{class:"fld"},h("label",{for:"login-identity"},"Email or username"),email),
  h("div",{class:"fld"},h("label",{for:"login-password"},"Password"),h("div",{class:"password-field"},password,toggle)),
  h("div",{class:"login-options"},h("label",{class:"remember",for:"remember-me"},h("input",{id:"remember-me",name:"remember",type:"checkbox"}),h("span",null,"Remember me")),h("a",{href:"#forgot-password",onclick:showForgot},"Forgot password?")),
  submit,status,
  h("p",{class:"signup-prompt"},"New to FranchiseOps AI? ",h("a",{href:"#signup",onclick:showSignup},"Create an account")));
 app.replaceChildren(authShell(form,"FranchiseOps AI sign in"));
}
function renderSignup(){
 clearInterval(S.otpCountdown);S.otpCountdown=null;
 const app=$("#app");app.classList.add("auth-shell");S.authScreen="signup";
 const status=h("p",{class:"signup-status","role":"status","aria-live":"polite"});
 const email=h("input",{id:"signup-email",name:"email",type:"email",autocomplete:"email",autocapitalize:"none",spellcheck:"false",required:true});
 const username=h("input",{id:"signup-username",name:"username",type:"text",autocomplete:"username",autocapitalize:"none",spellcheck:"false",minlength:"3",required:true});
 const role=h("select",{id:"signup-role",name:"role",required:true,"aria-describedby":"signup-access-guidance"},h("option",{value:""},"Loading roles…"));
 const outlet=h("select",{id:"signup-outlet",name:"outlet","aria-describedby":"signup-access-guidance"},h("option",{value:""},"Loading outlets…"));
 const outletField=h("div",{class:"fld",hidden:true},h("label",{for:"signup-outlet"},"Your outlet"),outlet);
 let scoped=[];
 const syncOutlet=()=>{const need=scoped.includes(role.value);outletField.hidden=!need;outlet.required=need;if(!need)outlet.value=""};
 role.addEventListener("change",syncOutlet);
 api("/api/auth/options").then(o=>{
  if(!o.roles){status.className="signup-status is-error";status.textContent=o.msg||"Could not load the role list. Refresh the page.";return}
  scoped=o.scoped_roles||[];
  question.replaceChildren(h("option",{value:""},"Choose a security question"),...(o.questions||[]).map(x=>h("option",{value:x},x)));
  role.replaceChildren(h("option",{value:""},"Choose your role"),...o.roles.map(r=>h("option",{value:r},r)));
  outlet.replaceChildren(h("option",{value:""},"Choose your outlet"),...o.outlets.map(x=>h("option",{value:x},x)));syncOutlet();
 });
 const question=h("select",{id:"signup-question",name:"security_question",required:true},h("option",{value:""},"Loading questions…"));
 const sqAnswer=h("input",{id:"signup-answer",name:"security_answer",type:"text",autocomplete:"off",autocapitalize:"none",spellcheck:"false",required:true,minlength:"2",maxlength:"100"});
 const password=h("input",{id:"signup-password",name:"password",type:"password",autocomplete:"new-password",minlength:"8",required:true,"aria-describedby":"signup-strength signup-guidance"});
 const confirm=h("input",{id:"signup-confirm",name:"confirm-password",type:"password",autocomplete:"new-password",minlength:"8",required:true});
 const strengthText=h("span",{class:"strength-label","aria-hidden":"true"},"Enter a password");
 const strengthFill=h("span",{class:"strength-fill"});
 const criteria=passwordCriteria(password),meter=h("div",{id:"signup-strength",class:"strength-meter","role":"progressbar","aria-label":"Password strength estimate","aria-valuemin":"0","aria-valuemax":"5","aria-valuenow":"0","aria-valuetext":"Enter a password"},h("span",{class:"strength-track"},strengthFill),strengthText);
 const updateStrength=()=>updatePasswordStrength(password,meter,strengthFill,strengthText,criteria);
 password.addEventListener("input",()=>{password.setCustomValidity("");updateStrength()});
 username.addEventListener("input",()=>username.setCustomValidity(""));
 confirm.addEventListener("input",()=>confirm.setCustomValidity(""));
 const togglePassword=passwordToggle(password),toggleConfirm=passwordToggle(confirm);
 const submit=authSubmitButton("Create account","Creating account...");
 const validationMessage=message=>{status.className="signup-status is-error";status.textContent=message};
 const onSubmit=async event=>{
  event.preventDefault();status.className="signup-status";status.textContent="";
  username.setCustomValidity(/^[A-Za-z0-9_]{3,}$/.test(username.value.trim())?"":"Use at least 3 letters, numbers, or underscores for your username.");
  if(!event.currentTarget.reportValidity()){validationMessage("Please check the highlighted fields.");return}
  if(!role.value){validationMessage("Choose your role.");role.focus();return}
  if(criteria.map(test=>test()).some(ok=>!ok)){validationMessage("Use at least 8 characters with uppercase and lowercase letters, a number, and a symbol.");password.focus();return}
  if(password.value!==confirm.value){confirm.setCustomValidity("Passwords do not match.");confirm.reportValidity();validationMessage("The passwords do not match.");confirm.focus();return}
  if(!question.value){validationMessage("Choose a security question.");question.focus();return}
  if(sqAnswer.value.trim().length<2){validationMessage("Enter a security answer of at least 2 characters.");sqAnswer.focus();return}
  submit.setLoading(true);
  const r=await api("/api/auth/signup",{json:{email:email.value.trim(),username:username.value.trim(),password:password.value,confirm_password:confirm.value,role:role.value,outlet:outlet.value,security_question:question.value,security_answer:sqAnswer.value}});
  submit.setLoading(false);
  if(r.ok){S.loginNotice="Account created. Sign in with your new account.";S.authScreen="login";renderLogin();return}
  validationMessage(r.msg||"Could not create the account.");
 };
 const backToLogin=event=>{event.preventDefault();S.authScreen="login";renderLogin()};
 const form=h("form",{class:"auth auth-form signup-form",novalidate:true,onsubmit:onSubmit},
  h("div",{class:"auth-heading"},h("span",{class:"auth-kicker"},"FRANCHISE MANAGEMENT PLATFORM"),h("h1",null,"Create your account"),h("p",null,"Set up your access to the FranchiseOps AI workspace.")),
  h("p",{id:"signup-access-guidance",class:"auth-info"},"Choose the role you work in; it decides which pages you can open. Store Managers and Staff are limited to their own outlet. An administrator can change your role later, and Admin accounts are created by an administrator only."),
  h("div",{class:"fld"},h("label",{for:"signup-email"},"Email address"),email),
  h("div",{class:"fld"},h("label",{for:"signup-username"},"Username"),username),
  h("div",{class:"fld"},h("label",{for:"signup-role"},"Your role"),role),
  outletField,
  h("div",{class:"fld"},h("label",{for:"signup-password"},"Password"),h("div",{class:"password-field"},password,togglePassword),
   meter,
   h("p",{id:"signup-guidance",class:"password-guidance"},"Aim for 8+ characters with uppercase and lowercase letters, a number, and a symbol.")),
  h("div",{class:"fld"},h("label",{for:"signup-confirm"},"Confirm password"),h("div",{class:"password-field"},confirm,toggleConfirm)),
  h("div",{class:"fld"},h("label",{for:"signup-question"},"Security question"),question),
  h("div",{class:"fld"},h("label",{for:"signup-answer"},"Your answer"),sqAnswer,h("p",{class:"password-guidance"},"Used to recover your password if you forget it. Capital letters do not matter.")),
  submit.button,
  status,
  h("p",{class:"signup-prompt"},"Already have an account? ",h("a",{href:"#login",onclick:backToLogin},"Return to login")));
 app.replaceChildren(authShell(form,"Create a FranchiseOps AI account"));
}
function renderForgotPassword(){
 clearInterval(S.otpCountdown);S.otpCountdown=null;
 const app=$("#app");app.classList.add("auth-shell");S.authScreen="forgot";
 const status=h("p",{class:"auth-feedback","role":"status","aria-live":"polite"});
 const email=h("input",{id:"recovery-email",name:"email",type:"text",autocomplete:"username",autocapitalize:"none",spellcheck:"false",required:true,value:S.recoveryEmail});
 const submit=authSubmitButton("Send me a code by e-mail","Sending...");
 const onSubmit=async event=>{
  event.preventDefault();status.className="auth-feedback";status.textContent="";
  email.setCustomValidity(email.value.trim()?"":"Enter your email or username.");
  if(!event.currentTarget.reportValidity()){status.classList.add("is-error");status.textContent="Enter your email or username.";return}
  S.recoveryEmail=email.value.trim();submit.setLoading(true);
  const r=await api("/api/auth/forgot",{json:{email:S.recoveryEmail}});submit.setLoading(false);
  if(!r.ok){status.classList.add("is-error");status.textContent=r.msg||"Could not send the code.";return}
  S.recoveryOtp="";S.otpResendUntil=Date.now()+60000;S.otpNotice=r.msg;S.authScreen="otp";renderOtpVerification();
 };
 const back=event=>{event.preventDefault();S.authScreen="login";renderLogin()};
 const viaQuestion=h("button",{class:"btn login-submit",type:"button",onclick:async()=>{
  status.className="auth-feedback";status.textContent="";
  email.setCustomValidity(email.value.trim()?"":"Enter your email or username.");
  if(!email.reportValidity()){status.classList.add("is-error");status.textContent="Enter your email or username.";return}
  S.recoveryEmail=email.value.trim();viaQuestion.disabled=true;const r=await api("/api/auth/security-question",{json:{email:S.recoveryEmail}});viaQuestion.disabled=false;
  if(!r.ok){status.classList.add("is-error");status.textContent=r.msg||"Could not load the question.";return}
  S.recoveryQuestion=r.question;S.authScreen="answer";renderSecurityAnswer();
 }},"Answer my security question");
 email.addEventListener("input",()=>{email.setCustomValidity("");S.recoveryEmail=email.value});
 const form=h("form",{class:"auth auth-form recovery-form",novalidate:true,onsubmit:onSubmit},
  h("div",{class:"auth-heading"},h("span",{class:"auth-kicker"},"ACCOUNT RECOVERY"),h("h1",null,"Forgot your password?"),h("p",null,"Enter your email or username, then choose how to prove it is you: a 6-digit code by e-mail, or your security question.")),
  h("div",{class:"fld"},h("label",{for:"recovery-email"},"Email or username"),email),
  submit.button,viaQuestion,status,
  h("p",{class:"signup-prompt"},h("a",{href:"#login",onclick:back},"Back to login")));
 app.replaceChildren(authShell(form,"Recover your FranchiseOps AI account"));
}
function renderOtpVerification(){
 clearInterval(S.otpCountdown);S.otpCountdown=null;
 const app=$("#app");app.classList.add("auth-shell");S.authScreen="otp";
 if(!S.otpResendUntil)S.otpResendUntil=Date.now()+60000;
 const status=h("p",{class:"auth-feedback","role":"status","aria-live":"polite"});
 if(S.otpNotice){status.classList.add("is-notice");status.textContent=S.otpNotice;S.otpNotice=""}
 const emailText=h("b",null,S.recoveryEmail||"your email");
 const code=h("input",{id:"recovery-otp",class:"otp-code",name:"otp",type:"text",inputmode:"numeric",pattern:"[0-9]{6}",minlength:"6",maxlength:"6",autocomplete:"one-time-code",autocapitalize:"off",spellcheck:"false",required:true,value:S.recoveryOtp,"aria-describedby":"otp-guidance"});
 const resend=h("button",{class:"btn otp-resend",type:"button",disabled:true,onclick:async()=>{
  resend.disabled=true;const r=await api("/api/auth/forgot",{json:{email:S.recoveryEmail}});
  status.className="auth-feedback "+(r.ok?"is-notice":"is-error");status.textContent=r.msg||"Could not resend the code.";
  S.otpResendUntil=Date.now()+60000;if(!S.otpCountdown)S.otpCountdown=setInterval(updateCountdown,1000);updateCountdown();
 }},"Resend code");
 const countdown=h("span",{id:"otp-countdown",class:"otp-countdown","aria-live":"off"});
 const submit=authSubmitButton("Verify code","Verifying...");
 const updateCountdown=()=>{
  const remaining=Math.max(0,Math.ceil((S.otpResendUntil-Date.now())/1000));
  resend.disabled=remaining>0;
  resend.textContent=remaining>0?"Resend code ("+String(Math.floor(remaining/60)).padStart(2,"0")+":"+String(remaining%60).padStart(2,"0")+")":"Resend code";
  countdown.textContent=remaining>0?"You can ask for a new code in "+remaining+" seconds.":"You can ask for a new code now.";
  if(!remaining){clearInterval(S.otpCountdown);S.otpCountdown=null}
 };
 updateCountdown();
 if(S.otpResendUntil>Date.now())S.otpCountdown=setInterval(updateCountdown,1000);
 const onSubmit=async event=>{
  event.preventDefault();status.className="auth-feedback";status.textContent="";
  const value=code.value.trim();
  code.setCustomValidity(!value?"Enter the six-digit code.":/^\d{6}$/.test(value)?"":"Enter exactly six digits.");
  if(!event.currentTarget.reportValidity()){
   code.setAttribute("aria-invalid","true");status.classList.add("is-error");status.textContent=!value?"Enter the six-digit code.":"Enter exactly six digits.";return;
  }
  submit.setLoading(true);const r=await api("/api/auth/verify",{json:{email:S.recoveryEmail,otp:value}});submit.setLoading(false);
  if(!r.ok){code.setAttribute("aria-invalid","true");status.classList.add("is-error");status.textContent=r.msg||"That code is wrong or has expired.";return}
  S.recoveryOtp=value;code.removeAttribute("aria-invalid");S.authScreen="reset";renderResetPassword();
 };
 code.addEventListener("input",()=>{S.recoveryOtp=code.value;code.setCustomValidity("");code.removeAttribute("aria-invalid")});
 const back=event=>{event.preventDefault();S.recoveryOtp=code.value;S.authScreen="forgot";renderForgotPassword()};
 const form=h("form",{class:"auth auth-form recovery-form otp-form",novalidate:true,onsubmit:onSubmit},
  h("div",{class:"auth-heading"},h("span",{class:"auth-kicker"},"ACCOUNT RECOVERY"),h("h1",null,"Verify your email"),h("p",null,"Enter the six-digit verification code sent to ",emailText,".")),
  h("div",{class:"fld"},h("label",{for:"recovery-otp"},"Six-digit verification code"),code,h("p",{id:"otp-guidance",class:"password-guidance"},"The code is valid for 5 minutes and works once. Three wrong codes pause recovery for 15 minutes.")),
  h("div",{class:"otp-resend-row"},resend,countdown),
  submit.button,status,
  h("p",{class:"signup-prompt"},h("a",{href:"#forgot-password",onclick:back},"Back to email")));
 app.replaceChildren(authShell(form,"Verify your FranchiseOps AI recovery code"));
}
function renderResetPassword(){
 clearInterval(S.otpCountdown);S.otpCountdown=null;
 const app=$("#app");app.classList.add("auth-shell");S.authScreen="reset";
 const status=h("p",{class:"auth-feedback","role":"status","aria-live":"polite"});
 const password=h("input",{id:"reset-password",name:"password",type:"password",autocomplete:"new-password",minlength:"8",required:true,"aria-describedby":"reset-strength reset-guidance"});
 const confirm=h("input",{id:"reset-confirm",name:"confirm-password",type:"password",autocomplete:"new-password",minlength:"8",required:true});
 const strengthText=h("span",{class:"strength-label","aria-hidden":"true"},"Enter a password"),strengthFill=h("span",{class:"strength-fill"});
 const meter=h("div",{id:"reset-strength",class:"strength-meter","role":"progressbar","aria-label":"New password strength estimate","aria-valuemin":"0","aria-valuemax":"5","aria-valuenow":"0","aria-valuetext":"Enter a password"},h("span",{class:"strength-track"},strengthFill),strengthText);
 const criteria=passwordCriteria(password),submit=authSubmitButton("Reset password","Resetting...");
 const updateStrength=()=>updatePasswordStrength(password,meter,strengthFill,strengthText,criteria);
 password.addEventListener("input",()=>{password.setCustomValidity("");updateStrength()});
 confirm.addEventListener("input",()=>confirm.setCustomValidity(""));
 const onSubmit=async event=>{
  event.preventDefault();status.className="auth-feedback";status.textContent="";
  if(!event.currentTarget.reportValidity()){status.classList.add("is-error");status.textContent="Please check the highlighted fields.";return}
  if(criteria.some(test=>!test())){password.setCustomValidity("Use at least 8 characters with uppercase and lowercase letters, a number, and a symbol.");password.reportValidity();status.classList.add("is-error");status.textContent="Choose a password with at least 8 characters, uppercase and lowercase letters, a number, and a symbol.";password.focus();return}
  if(password.value!==confirm.value){confirm.setCustomValidity("Passwords do not match.");confirm.reportValidity();status.classList.add("is-error");status.textContent="The passwords do not match.";confirm.focus();return}
  submit.setLoading(true);const r=await api("/api/auth/reset",{json:{email:S.recoveryEmail,otp:S.recoveryOtp,password:password.value,confirm_password:confirm.value}});submit.setLoading(false);
  if(!r.ok){status.classList.add("is-error");status.textContent=r.msg||"Could not reset the password.";return}
  S.recoveryEmail="";S.recoveryOtp="";S.otpResendUntil=0;S.loginNotice=r.msg;S.authScreen="login";renderLogin();
 };
 const back=event=>{event.preventDefault();S.authScreen="login";renderLogin()};
 const backToOtp=event=>{event.preventDefault();S.authScreen="otp";renderOtpVerification()};
 const form=h("form",{class:"auth auth-form recovery-form",novalidate:true,onsubmit:onSubmit},
  h("div",{class:"auth-heading"},h("span",{class:"auth-kicker"},"ACCOUNT RECOVERY"),h("h1",null,"Choose a new password"),h("p",null,"Enter and confirm your new password.")),
  h("div",{class:"fld"},h("label",{for:"reset-password"},"New password"),h("div",{class:"password-field"},password,passwordToggle(password)),
   meter,h("p",{id:"reset-guidance",class:"password-guidance"},"Use at least 8 characters with uppercase and lowercase letters, a number, and a symbol.")),
  h("div",{class:"fld"},h("label",{for:"reset-confirm"},"Confirm new password"),h("div",{class:"password-field"},confirm,passwordToggle(confirm))),
  submit.button,status,
  S.recoveryEmail?h("p",{class:"auth-secondary-link"},h("a",{href:"#otp-verification",onclick:backToOtp},"Back to code verification")):null,
  h("p",{class:"signup-prompt"},h("a",{href:"#login",onclick:back},"Back to login")));
 app.replaceChildren(authShell(form,"Reset your FranchiseOps AI password"));
}
function renderSecurityAnswer(){
 clearInterval(S.otpCountdown);S.otpCountdown=null;
 const app=$("#app");app.classList.add("auth-shell");S.authScreen="answer";
 const status=h("p",{class:"auth-feedback","role":"status","aria-live":"polite"});
 const answer=h("input",{id:"recovery-answer",name:"answer",type:"text",autocomplete:"off",autocapitalize:"none",spellcheck:"false",required:true,maxlength:"100"});
 const password=h("input",{id:"reset-password",name:"password",type:"password",autocomplete:"new-password",minlength:"8",required:true,"aria-describedby":"reset-strength reset-guidance"});
 const confirm=h("input",{id:"reset-confirm",name:"confirm-password",type:"password",autocomplete:"new-password",minlength:"8",required:true});
 const strengthText=h("span",{class:"strength-label","aria-hidden":"true"},"Enter a password"),strengthFill=h("span",{class:"strength-fill"});
 const meter=h("div",{id:"reset-strength",class:"strength-meter","role":"progressbar","aria-label":"New password strength estimate","aria-valuemin":"0","aria-valuemax":"5","aria-valuenow":"0","aria-valuetext":"Enter a password"},h("span",{class:"strength-track"},strengthFill),strengthText);
 const criteria=passwordCriteria(password),submit=authSubmitButton("Reset password","Resetting...");
 const updateStrength=()=>updatePasswordStrength(password,meter,strengthFill,strengthText,criteria);
 password.addEventListener("input",()=>{password.setCustomValidity("");updateStrength()});
 confirm.addEventListener("input",()=>confirm.setCustomValidity(""));
 const onSubmit=async event=>{
  event.preventDefault();status.className="auth-feedback";status.textContent="";
  if(!event.currentTarget.reportValidity()){status.classList.add("is-error");status.textContent="Please check the highlighted fields.";return}
  if(criteria.some(test=>!test())){status.classList.add("is-error");status.textContent="Choose a password with at least 8 characters, uppercase and lowercase letters, a number, and a symbol.";password.focus();return}
  if(password.value!==confirm.value){confirm.setCustomValidity("Passwords do not match.");confirm.reportValidity();status.classList.add("is-error");status.textContent="The passwords do not match.";confirm.focus();return}
  submit.setLoading(true);const r=await api("/api/auth/reset-with-answer",{json:{email:S.recoveryEmail,answer:answer.value,password:password.value,confirm_password:confirm.value}});submit.setLoading(false);
  if(!r.ok){status.classList.add("is-error");status.textContent=r.msg||"Could not reset the password.";answer.focus();return}
  S.recoveryEmail="";S.recoveryQuestion="";S.loginNotice=r.msg;S.authScreen="login";renderLogin();
 };
 const back=event=>{event.preventDefault();S.authScreen="forgot";renderForgotPassword()};
 const useCode=async event=>{event.preventDefault();const r=await api("/api/auth/forgot",{json:{email:S.recoveryEmail}});if(!r.ok){status.classList.add("is-error");status.textContent=r.msg||"Could not send the code.";return}S.recoveryOtp="";S.otpResendUntil=Date.now()+60000;S.otpNotice=r.msg;S.authScreen="otp";renderOtpVerification()};
 const form=h("form",{class:"auth auth-form recovery-form",novalidate:true,onsubmit:onSubmit},
  h("div",{class:"auth-heading"},h("span",{class:"auth-kicker"},"ACCOUNT RECOVERY"),h("h1",null,"Answer your security question"),h("p",null,"Answer it, then choose a new password for ",h("b",null,S.recoveryEmail||"your account"),".")),
  h("div",{class:"auth-info",role:"note"},h("b",null,S.recoveryQuestion||"Your security question")),
  h("div",{class:"fld"},h("label",{for:"recovery-answer"},"Your answer"),answer,h("p",{class:"password-guidance"},"Capital letters and extra spaces do not matter. Three wrong answers pause this option for 15 minutes.")),
  h("div",{class:"fld"},h("label",{for:"reset-password"},"New password"),h("div",{class:"password-field"},password,passwordToggle(password)),
   meter,h("p",{id:"reset-guidance",class:"password-guidance"},"Use at least 8 characters with uppercase and lowercase letters, a number, and a symbol.")),
  h("div",{class:"fld"},h("label",{for:"reset-confirm"},"Confirm new password"),h("div",{class:"password-field"},confirm,passwordToggle(confirm))),
  submit.button,status,
  h("p",{class:"auth-secondary-link"},"No question set up, or forgot the answer? ",h("a",{href:"#otp",onclick:useCode},"Send me a code by e-mail instead")),
  h("p",{class:"signup-prompt"},h("a",{href:"#forgot-password",onclick:back},"Back"),"  ·  ",h("a",{href:"#login",onclick:event=>{event.preventDefault();S.authScreen="login";renderLogin()}},"Back to login")));
 app.replaceChildren(authShell(form,"Answer your security question"));
}
async function render(){const app=$("#app");if(S.es){S.es.close();S.es=null}
 if(!S.me)app.replaceChildren(h("div",{class:"boot",role:"status"},h("div",{class:"spin","aria-hidden":"true"}),"Connecting to FranchiseOps AI…"));
 const pub=await api("/api/public");S.pub=pub;S.apiNotice=pub.error&&pub.status!==401?pub.msg:"";
 if(!S.me&&authToken()){const m=await api("/api/me");if(m.user){S.me=m;S.apiNotice=""}else if(m.error&&m.status!==401&&!S.apiNotice)S.apiNotice=m.msg}
 if(!S.me){if(S.authScreen==="signup")renderSignup();else if(S.authScreen==="forgot")renderForgotPassword();else if(S.authScreen==="otp")renderOtpVerification();else if(S.authScreen==="answer")renderSecurityAnswer();else if(S.authScreen==="reset")renderResetPassword();else renderLogin();return}
 if(Array.isArray(S.me.menu)&&!S.me.menu.some(m=>m.id==="profile"))S.me.menu=[...S.me.menu,{id:"profile",label:"My Profile",icon:"user"}];
 if(Array.isArray(S.me.menu)&&!S.me.menu.some(m=>m.id==="admin")&&String(S.me.user.role||"").toLowerCase()==="admin")S.me.menu=[...S.me.menu,{id:"admin",label:"Admin Dashboard",icon:"shield"}];
 app.classList.remove("auth-shell");
 app.replaceChildren(h("div",{class:"side"},h("div",{class:"brand"},h("i",null,icon("radar")),h("div",null,S.me.name,h("small",null,S.me.user.role+" · "+S.me.user.email))),h("div",{class:"ksearch",onclick:()=>UI.palette()},"Search or ask…",h("kbd",null,"Ctrl K")),h("div",{id:"nav"}),h("div",{class:"sp"}),h("div",{class:"sidefoot"},h("span",{class:"av-slot"},avatarEl(S.me.user.picture,S.me.user.username||S.me.user.email,34)),h("div",{class:"who"},h("b",null,S.me.user.username||S.me.user.email),h("small",null,S.me.user.role+(S.me.scope?" · "+S.me.scope:""))),h("button",{class:"btn sm signout",type:"button",onclick:()=>UI.signOut()},"Sign out"))),
  h("div",{class:"main"},h("div",{id:"warn",class:"warnbar",style:"display:none"},"No CUDA GPU detected: models run on CPU and will be slow. In Colab choose Runtime → Change runtime type → T4 GPU, then restart."),
   h("div",{class:"top"},h("div",null,h("h1",{id:"ttl"}),h("div",{class:"sub",id:"sub"})),h("div",{class:"sp"}),h("div",{id:"acts",style:"display:flex;gap:8px"}),themeToggle(),h("span",{class:"chip",id:"hl"},"connecting…"),h("span",{class:"chip",id:"gpu"})),
   h("div",{class:"content"},h("div",{class:"tabs",id:"tabs"}),h("div",{id:"pg"},h("div",{class:"blocks",id:"blocks"})))));

 renderNav();const hs=(location.hash||"").slice(1).split(":");UI.go(hs[0]||firstAllowedPage(),hs[1]);openStream();api("/api/pulse").then(p=>{if(!p.error){S.pulse=p;updBadges()}})}
window.addEventListener("hashchange",()=>{if(!S.me)return;const hs=(location.hash||"").slice(1).split(":");UI.go(hs[0]||firstAllowedPage(),hs[1])});
UI.signOut=async()=>{await api("/api/auth/logout",{json:{}});setToken("");if(S.es){S.es.close();S.es=null}clearTimeout(S.timer);S.me=null;S.tree=null;S.authScreen="login";S.loginNotice="You have been signed out.";render()};
window.UI=UI;render();
