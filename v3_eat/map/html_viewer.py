"""Self-contained interactive choropleth viewer (single HTML file).

Embeds a downscaled province base image (each province keeps its unique color)
plus a compact JSON of {color -> state} and per-metric values + colormaps. The
browser does the LUT recolor on a <canvas>, draws value labels, supports
continent zoom + state search, and hover tooltips — no server, no deps. Per-state
bounding boxes / centroids are computed client-side during the single pixel pass
that builds the color→state map, so they cost nothing in the payload.
"""
from __future__ import annotations

import base64
import io
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from ..analysis.regions import RegionRow
from ..i18n import UI
from ..model import GameData
from ..util.logging import get_logger
from . import colormap as cm
from .metrics import Metric
from .render import ProvinceIndex

log = get_logger()


def _payload(
    game: GameData,
    ui: UI,
    rows: list[RegionRow],
    metrics: list[Metric],
    index: ProvinceIndex,
    *,
    cmap: str,
    clip_percentile: float,
    log_scale: bool,
    gamma: float = 0.7,
) -> dict:
    # Stable order: only land states that exist in the bitmap index.
    state_ids = [r.state_id for r in rows if r.state_id in index.state_to_colors]
    idx_of = {sid: i for i, sid in enumerate(state_ids)}
    bucket_label = {r.state_id: ui[f"rbucket_{r.bucket or 'other'}"] for r in rows}

    def name(sid: str) -> str:
        return game.loc.get_clean(sid) if game.loc is not None else sid

    states = [{"n": name(sid), "b": bucket_label.get(sid, "")} for sid in state_ids]

    colors: list[int] = []
    cstate: list[int] = []
    for sid in state_ids:
        for c in index.state_to_colors.get(sid, ()):
            colors.append(int(c))
            cstate.append(idx_of[sid])
    water = [int(c) for c in index.water_colors.tolist()]

    metric_json = []
    for m in metrics:
        raw = np.zeros(len(state_ids), dtype=np.float64)
        for sid, val in m.values.items():
            if sid in idx_of:
                raw[idx_of[sid]] = val
        pos = raw[raw > 0]
        if len(pos) == 0:
            continue
        scale = np.log1p(raw) if log_scale else raw
        spos = np.log1p(pos) if log_scale else pos
        vmax = float(np.percentile(spos, clip_percentile)) if clip_percentile < 100 else float(spos.max())
        if vmax <= 0:
            vmax = float(spos.max()) or 1.0
        norm = np.clip(scale / vmax, 0.0, 1.0) ** gamma   # match PNG depth contrast
        norm[raw <= 0] = -1.0
        table = cm.table_for(cmap, m.key, m.is_resource, m.is_crop).astype(int).tolist()
        metric_json.append({
            "key": m.key, "label": m.label, "vmax": round(float(pos.max()), 2),
            "norm": [round(float(x), 4) for x in norm],
            "raw": [round(float(x), 2) for x in raw],
            "table": table,
        })

    cmaps = {n: cm.as_table(n).astype(int).tolist() for n in cm.NAMES if n != "auto"}
    return {
        "states": states, "colors": colors, "cstate": cstate, "water": water,
        "metrics": metric_json, "cmaps": cmaps,
    }


def _base_image_from_index(index: ProvinceIndex) -> str:
    """Reconstruct the downscaled province base image from the packed keys."""
    k = index.keys
    rgb = np.dstack([(k >> 16) & 0xFF, (k >> 8) & 0xFF, k & 0xFF]).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


_TEMPLATE = """<!DOCTYPE html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --bg:#efe6d4; --panel:#f7f1e3; --ink:#3a2e22; --muted:#8a7a64;
           --line:#cdbfa3; --accent:#7c5a2e; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
          font:14px/1.55 Georgia,"Times New Roman","Noto Serif SC","Songti SC",SimSun,serif; }}
  header {{ padding:14px 20px; border-bottom:2px solid var(--line); display:flex;
            gap:18px; align-items:center; flex-wrap:wrap;
            background:linear-gradient(#f7f1e3,#efe6d4); }}
  header h1 {{ font-size:20px; margin:0; font-weight:700; letter-spacing:.5px; }}
  header .meta {{ color:var(--muted); font-size:12px; font-style:italic; }}
  .controls {{ margin-left:auto; display:flex; gap:14px; align-items:center; flex-wrap:wrap; }}
  label {{ color:var(--muted); font-size:12px; margin-right:5px; }}
  select,input {{ background:#fffdf7; color:var(--ink); border:1px solid var(--line);
                  border-radius:4px; padding:5px 8px; font-size:13px; font-family:inherit; }}
  input#search {{ width:150px; }}
  .chk {{ display:flex; align-items:center; gap:5px; }}
  #wrap {{ padding:16px 20px; }}
  #viewport {{ position:relative; overflow:hidden; border:1px solid var(--line);
               border-radius:6px; background:#dfe9f2; box-shadow:0 1px 4px #0002; }}
  #map {{ display:block; cursor:grab; touch-action:none; }}
  #map.drag {{ cursor:grabbing; }}
  #sig {{ position:absolute; right:12px; bottom:10px; pointer-events:none; text-align:right;
          font:italic 12px Georgia,"Times New Roman",serif; color:#5a4a3a;
          opacity:0.82; text-shadow:0 1px 2px #ffffffcc, 0 0 2px #ffffffcc; line-height:1.35; }}
  #legend {{ display:flex; align-items:center; gap:10px; margin-top:12px;
             color:var(--muted); flex-wrap:wrap; }}
  #bar {{ width:280px; height:14px; border:1px solid var(--line); border-radius:3px; }}
  .sw {{ display:inline-block; width:13px; height:13px; border:1px solid #999;
         border-radius:2px; vertical-align:-2px; margin:0 4px 0 14px; }}
  #mlabel {{ font-weight:700; color:var(--ink); font-size:15px; }}
  #tip {{ position:fixed; pointer-events:none; background:#2b2114ee; color:#f7efe0;
          padding:6px 10px; border-radius:5px; font-size:12.5px; display:none;
          border:1px solid #7c5a2e; max-width:240px; box-shadow:0 2px 8px #0005; }}
  #tip b {{ color:#f3d79a; }}
  button {{ background:#fffdf7; border:1px solid var(--line); border-radius:4px;
            padding:5px 10px; cursor:pointer; font-family:inherit; color:var(--ink); }}
  button:hover {{ background:#f0e7d2; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <span class="meta">{version} · {generated}</span>
  <div class="controls">
    <span><label>{resource_label}</label><select id="metric"></select></span>
    <span><label>{cmap_label}</label><select id="cmap"></select></span>
    <span><label>{continent_label}</label><select id="continent"></select></span>
    <span><input id="search" type="text" placeholder="{search_ph}"></span>
    <span class="chk"><input type="checkbox" id="lbls" checked><label for="lbls">{labels_label}</label></span>
    <button id="reset">{reset_label}</button>
  </div>
</header>
<div id="wrap">
  <div id="viewport"><canvas id="map"></canvas><div id="sig">Econometrics Automation Tool<br>map by J.C.</div></div>
  <div id="legend">
    <span id="mlabel"></span>
    <span>0</span><canvas id="bar" width="280" height="14"></canvas><span id="vmax"></span>
    <span class="sw" style="background:rgb(224,224,224)"></span>{nodata}
    <span class="sw" style="background:rgb(176,206,230)"></span>{water}
  </div>
</div>
<div id="tip"></div>
<script id="data" type="application/json">{data}</script>
<script>
const D = JSON.parse(document.getElementById('data').textContent);
const WATER=[176,206,230], NODATA=[224,224,224], BORDER=[248,248,248];
const img = new Image(); img.onload = init; img.src = "data:image/png;base64,{img_b64}";
let W,H, stateIdx, baseData, off, offctx, vctx, out, cur, cents, bboxes, spans, areas, bucketBox={{}};
let cam={{x:0,y:0,z:1}};   // camera: source-pixel at viewport centre + view-px per source-px
const canvas=document.getElementById('map'), vp=document.getElementById('viewport');

function init(){{
  W=img.width; H=img.height;
  const tmp=document.createElement('canvas'); tmp.width=W; tmp.height=H;
  const tctx=tmp.getContext('2d',{{willReadFrequently:true}}); tctx.drawImage(img,0,0);
  baseData=tctx.getImageData(0,0,W,H);
  off=document.createElement('canvas'); off.width=W; off.height=H;
  offctx=off.getContext('2d'); vctx=canvas.getContext('2d');
  const px=baseData.data, c2s=new Map();
  for(let i=0;i<D.colors.length;i++) c2s.set(D.colors[i], D.cstate[i]);
  const waterSet=new Set(D.water), ns=D.states.length, n=W*H;
  stateIdx=new Int32Array(n);
  const scos=new Float64Array(ns), ssin=new Float64Array(ns), sy=new Float64Array(ns); areas=new Int32Array(ns);
  const TWO_PI=6.283185307179586, KX=TWO_PI/W;
  bboxes=Array.from({{length:ns}},()=>[1e9,1e9,-1,-1]);
  for(let p=0,j=0;p<n;p++,j+=4){{
    const key=(px[j]<<16)|(px[j+1]<<8)|px[j+2];
    let s; if(c2s.has(key)){{s=c2s.get(key);}} else if(waterSet.has(key)){{s=-1;}} else {{s=-2;}}
    stateIdx[p]=s;
    if(s>=0){{ const x=p%W, y=(p/W)|0; scos[s]+=Math.cos(x*KX); ssin[s]+=Math.sin(x*KX); sy[s]+=y; areas[s]++;
      const b=bboxes[s]; if(x<b[0])b[0]=x; if(y<b[1])b[1]=y; if(x>b[2])b[2]=x; if(y>b[3])b[3]=y; }}
  }}
  // circular mean for x so wrap_x seam-crossing states (e.g. Chukotka) aren't mid-ocean
  const ccx=new Float64Array(ns);
  cents=Array.from({{length:ns}},(_,s)=>{{ if(!areas[s])return[0,0]; let ax=Math.atan2(ssin[s],scos[s]); if(ax<0)ax+=TWO_PI; ccx[s]=ax/TWO_PI*W; return [ccx[s], sy[s]/areas[s]]; }});
  // 2nd pass: medoid (in-state label anchor) + wrap-aware CONTIGUOUS extent per state
  spans=new Array(ns);
  {{ const bD=new Float64Array(ns).fill(1e18), mX=new Float64Array(ns), mY=new Float64Array(ns);
     const Lx=new Float64Array(ns).fill(1e9), Rx=new Float64Array(ns).fill(-1e9), Ty=new Float64Array(ns).fill(1e9), By=new Float64Array(ns).fill(-1e9);
     for(let p=0;p<n;p++){{ const s=stateIdx[p]; if(s<0) continue; const x=p%W,y=(p/W)|0;
       let dx=x-ccx[s]; if(dx>W/2)dx-=W; else if(dx<-W/2)dx+=W; const dy=y-cents[s][1], dd=dx*dx+dy*dy;
       if(dd<bD[s]){{ bD[s]=dd; mX[s]=x; mY[s]=y; }}
       if(dx<Lx[s])Lx[s]=dx; if(dx>Rx[s])Rx[s]=dx; if(y<Ty[s])Ty[s]=y; if(y>By[s])By[s]=y; }}
     for(let s=0;s<ns;s++){{ if(!areas[s]){{spans[s]=null;continue;}} cents[s]=[mX[s],mY[s]];
       spans[s]=[ccx[s]+Lx[s], Ty[s], ccx[s]+Rx[s], By[s]]; }} }}
  // wrap-aware bucket bbox: union of member states' contiguous spans, shifted to the bucket's mean longitude
  {{ const acc={{}};
     for(let s=0;s<ns;s++){{ if(!areas[s])continue; const b=D.states[s].b||'?';
       (acc[b]||(acc[b]={{c:0,s:0}})); acc[b].c+=Math.cos(ccx[s]*KX); acc[b].s+=Math.sin(ccx[s]*KX); }}
     const cenX={{}}; for(const b in acc){{ let a=Math.atan2(acc[b].s,acc[b].c); if(a<0)a+=TWO_PI; cenX[b]=a/TWO_PI*W; }}
     for(let s=0;s<ns;s++){{ if(!areas[s])continue; const b=D.states[s].b||'?'; const sp=spans[s];
       const sh=Math.round((cenX[b]-ccx[s])/W)*W;
       const bb=bucketBox[b]||(bucketBox[b]=[1e9,1e9,-1e9,-1e9]);
       if(sp[0]+sh<bb[0])bb[0]=sp[0]+sh; if(sp[1]<bb[1])bb[1]=sp[1]; if(sp[2]+sh>bb[2])bb[2]=sp[2]+sh; if(sp[3]>bb[3])bb[3]=sp[3]; }}
  }}
  out=offctx.createImageData(W,H);
  const ms=document.getElementById('metric');
  D.metrics.forEach((m,i)=>{{const o=document.createElement('option');o.value=i;o.textContent=m.label;ms.appendChild(o);}});
  const cs=document.getElementById('cmap');
  ['auto',...Object.keys(D.cmaps)].forEach(k=>{{const o=document.createElement('option');o.value=k;o.textContent=k;cs.appendChild(o);}});
  cs.value="{cmap}";
  const ct=document.getElementById('continent'); const buckets=Object.keys(bucketBox).sort();
  const wo=document.createElement('option'); wo.value='__world'; wo.textContent="{world_label}"; ct.appendChild(wo);
  buckets.forEach(b=>{{const o=document.createElement('option');o.value=b;o.textContent=b;ct.appendChild(o);}});
  ms.onchange=cs.onchange=draw;
  document.getElementById('lbls').onchange=draw;
  ct.onchange=()=>{{ const v=ct.value; v==='__world'?resetZoom():zoomTo(bucketBox[v]); }};
  document.getElementById('reset').onclick=()=>{{ct.value='__world';resetZoom();}};
  document.getElementById('search').addEventListener('input',onSearch);
  sizeView(); resetZoom(); attachPanZoom(); draw();
}}

function lerp(cps,t){{ t=Math.max(0,Math.min(1,t)); const n=cps.length,pos=t*(n-1),
  lo=Math.floor(pos),hi=Math.min(lo+1,n-1),f=pos-lo,a=cps[lo],b=cps[hi];
  return [a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f,a[2]+(b[2]-a[2])*f]; }}

function curTable(){{ const c=document.getElementById('cmap').value;
  return c==='auto'?cur.table:D.cmaps[c]; }}

function draw(){{
  const mi=+document.getElementById('metric').value||0; cur=D.metrics[mi];
  const cps=curTable(), ns=D.states.length, sc=new Uint8Array(ns*3);
  for(let s=0;s<ns;s++){{ const nv=cur.norm[s]; const col=nv<0?NODATA:lerp(cps,nv);
    sc[s*3]=col[0]; sc[s*3+1]=col[1]; sc[s*3+2]=col[2]; }}
  const o=out.data,n=W*H;
  for(let p=0,j=0;p<n;p++,j+=4){{ const s=stateIdx[p]; let r,g,b;
    if(s>=0){{r=sc[s*3];g=sc[s*3+1];b=sc[s*3+2];}}
    else if(s===-1){{r=WATER[0];g=WATER[1];b=WATER[2];}} else {{r=BORDER[0];g=BORDER[1];b=BORDER[2];}}
    o[j]=r;o[j+1]=g;o[j+2]=b;o[j+3]=255; }}
  offctx.putImageData(out,0,0);
  if(document.getElementById('lbls').checked) drawLabels(sc);
  document.getElementById('mlabel').textContent=cur.label;
  document.getElementById('vmax').textContent=cur.vmax;
  const bar=document.getElementById('bar'),bx=bar.getContext('2d');
  for(let x=0;x<bar.width;x++){{const c=lerp(cps,x/(bar.width-1));
    bx.fillStyle=`rgb(${{c[0]|0}},${{c[1]|0}},${{c[2]|0}})`;bx.fillRect(x,0,1,bar.height);}}
  drawView();
}}

function drawLabels(sc){{
  offctx.textAlign='center'; offctx.textBaseline='middle'; offctx.lineJoin='round';
  const ns=D.states.length;
  for(let s=0;s<ns;s++){{
    const v=cur.raw[s]; if(v<=0) continue; const a=areas[s]; if(a<70) continue;
    const sz=Math.max(9,Math.min(26,Math.sqrt(a)*0.5)); offctx.font='700 '+sz+'px Georgia,serif';
    const lum=0.299*sc[s*3]+0.587*sc[s*3+1]+0.114*sc[s*3+2];
    const fg=lum>140?'#231a10':'#fdf6ea', halo=lum>140?'#fdf6ea':'#241a10';
    const [cx,cy]=cents[s]; const t=(v===Math.round(v))?(''+v):v.toFixed(1);
    offctx.lineWidth=Math.max(2,sz/5); offctx.strokeStyle=halo; offctx.strokeText(t,cx,cy);
    offctx.fillStyle=fg; offctx.fillText(t,cx,cy);
  }}
}}

// ---- camera + infinite horizontal wrap (pan/zoom like the in-game map) ----
function sizeView(){{
  const vw=Math.max(40,Math.round(vp.clientWidth));
  const vh=Math.round(vw*H/W);                 // full-map aspect
  vp.style.height=vh+'px'; canvas.width=vw; canvas.height=vh;
}}
function clampCam(){{
  const fit=canvas.width/W; cam.z=Math.max(fit, Math.min(cam.z, fit*40));
  cam.x=((cam.x%W)+W)%W;                        // wrap horizontally
  cam.y=Math.max(0,Math.min(H,cam.y));
}}
function drawView(){{
  const vw=canvas.width, vh=canvas.height, z=cam.z;
  vctx.fillStyle='#dfe9f2'; vctx.fillRect(0,0,vw,vh);
  vctx.imageSmoothingEnabled=true;
  const tileW=W*z, sx0=vw/2-cam.x*z, sy=vh/2-cam.y*z;
  let i0=Math.floor((0-sx0)/tileW)-1, i1=Math.ceil((vw-sx0)/tileW)+1;
  for(let i=i0;i<=i1;i++) vctx.drawImage(off,0,0,W,H, sx0+i*tileW, sy, tileW, H*z);
}}
function resetZoom(){{ cam.z=canvas.width/W; cam.x=W/2; cam.y=H/2; clampCam(); drawView(); }}
function zoomTo(b){{ if(!b) return; const pad=Math.max(8,W*0.015);
  const bw=(b[2]-b[0])+2*pad, bh=(b[3]-b[1])+2*pad, fit=canvas.width/W;
  cam.z=Math.max(fit, Math.min(canvas.width/bw, canvas.height/bh, fit*40));
  cam.x=(b[0]+b[2])/2; cam.y=(b[1]+b[3])/2; clampCam(); drawView(); }}
function attachPanZoom(){{
  let drag=null;
  canvas.addEventListener('pointerdown',e=>{{ drag={{x:e.clientX,y:e.clientY}}; canvas.classList.add('drag'); canvas.setPointerCapture(e.pointerId); }});
  canvas.addEventListener('pointerup',e=>{{ drag=null; canvas.classList.remove('drag'); }});
  canvas.addEventListener('pointermove',e=>{{
    if(drag){{ cam.x-=(e.clientX-drag.x)/cam.z; cam.y-=(e.clientY-drag.y)/cam.z; drag={{x:e.clientX,y:e.clientY}}; clampCam(); drawView(); }}
    hover(e);
  }});
  canvas.addEventListener('wheel',e=>{{ e.preventDefault();
    const r=canvas.getBoundingClientRect(), mx=e.clientX-r.left, my=e.clientY-r.top;
    const sx=cam.x+(mx-canvas.width/2)/cam.z, sy=cam.y+(my-canvas.height/2)/cam.z;
    cam.z*=(e.deltaY<0?1.18:1/1.18); clampCam();
    cam.x=sx-(mx-canvas.width/2)/cam.z; cam.y=sy-(my-canvas.height/2)/cam.z; clampCam(); drawView();
  }},{{passive:false}});
  canvas.addEventListener('mouseleave',()=>tip.style.display='none');
  window.addEventListener('resize',()=>{{ const fx=cam.x,fy=cam.y,fz=cam.z/(canvas.width/W); sizeView(); cam.z=fz*(canvas.width/W); cam.x=fx; cam.y=fy; clampCam(); drawView(); }});
}}

function onSearch(e){{ const q=e.target.value.trim().toLowerCase(); if(!q) return;
  let best=-1; for(let s=0;s<D.states.length;s++){{ if(D.states[s].n.toLowerCase().includes(q)){{best=s;break;}} }}
  if(best>=0 && spans[best]){{ zoomTo(spans[best]); }} }}

const tip=document.getElementById('tip');
function hover(e){{ const r=canvas.getBoundingClientRect();
  let sx=Math.floor(cam.x+(e.clientX-r.left-canvas.width/2)/cam.z);
  const sy=Math.floor(cam.y+(e.clientY-r.top-canvas.height/2)/cam.z);
  sx=((sx%W)+W)%W;
  if(sy<0||sy>=H){{tip.style.display='none';return;}}
  const s=stateIdx[sy*W+sx]; if(s<0){{tip.style.display='none';return;}}
  tip.innerHTML=`<b>${{D.states[s].n}}</b><br>${{cur.label}}: ${{cur.raw[s]}}`;
  tip.style.display='block'; tip.style.left=(e.clientX+14)+'px'; tip.style.top=(e.clientY+14)+'px'; }}
</script>
</body>
</html>
"""


def write_html_viewer(
    path: Path,
    game: GameData,
    game_root: Path,
    ui: UI,
    rows: list[RegionRow],
    metrics: list[Metric],
    *,
    cmap: str = cm.DEFAULT,
    clip_percentile: float = 99.0,
    log_scale: bool = False,
    gamma: float = 0.7,
    version_label: str = "",
    html_width: int = 4096,
) -> Path:
    index = ProvinceIndex.build(game, game_root, width=html_width)
    img_b64 = _base_image_from_index(index)
    data = _payload(game, ui, rows, metrics, index,
                    cmap=cmap, clip_percentile=clip_percentile, log_scale=log_scale, gamma=gamma)
    html = _TEMPLATE.format(
        lang=("zh" if ui.lang == "zh" else "en"),
        title=ui["map_title"],
        version=version_label or ui["meta_unknown"],
        generated=datetime.now().isoformat(timespec="minutes"),
        resource_label=ui["map_layer"],
        cmap_label=ui["map_colormap"],
        continent_label=ui["map_continent"],
        search_ph=ui["map_search"],
        labels_label=ui["map_labels"],
        reset_label=ui["map_reset"],
        world_label=ui["map_world"],
        nodata=ui["map_nodata"],
        water=ui["map_water"],
        cmap=cmap,
        data=json.dumps(data, ensure_ascii=False, separators=(",", ":")),
        img_b64=img_b64,
    )
    path.write_text(html, encoding="utf-8")
    return path
