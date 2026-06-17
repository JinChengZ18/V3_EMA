"""Interactive multi-version timeline viewer (single HTML file).

Takes several regions xlsx reports (+ optionally the live game) as a time series
and builds a viewer with a **version slider**: scrub across patches to watch a
resource grow/shrink, in absolute shading or as a diverging Δ-vs-previous /
Δ-vs-first change map. Reuses the choropleth viewer's client-side LUT recolor.
"""
from __future__ import annotations

import base64
import io
import json
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

from ..analysis.regions import build_region_rows
from ..analysis.regions_diff import read_regions_report
from ..i18n import UI
from ..model import GameData
from ..parser.yml_loc import load_localization
from ..util.logging import get_logger
from . import colormap as cm
from .diff import snapshot_lang, state_metric_values
from .metrics import LEGACY_REMOVED_HEADERS, LEGACY_REMOVED_LOC, Metric, _loc_name, build_metrics
from .render import ProvinceIndex

log = get_logger()


def _snap_res_keys(snap) -> set[str]:
    """Every `res_<...>` column key present across a snapshot's rows."""
    keys: set[str] = set()
    for row in snap.states.values():
        keys.update(k for k in row if k.startswith("res_"))
    return keys


def _removed_kind_values(snap, kind: str) -> dict[str, float]:
    """Per-state values for a removed resource kind (no current building) read
    straight from a snapshot's historical column(s) — see LEGACY_REMOVED_HEADERS."""
    headers = [f"res_{h}" for h, k in LEGACY_REMOVED_HEADERS.items() if k == kind]
    out: dict[str, float] = {}
    for (sid,), row in snap.states.items():
        total = 0.0
        seen = False
        for hk in headers:
            v = row.get(hk)
            if isinstance(v, (int, float)):
                total += v
                seen = True
        if seen and total:
            out[sid] = total
    return out


def _base_image_b64(index: ProvinceIndex) -> str:
    k = index.keys
    rgb = np.dstack([(k >> 16) & 0xFF, (k >> 8) & 0xFF, k & 0xFF]).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _version_label(meta: dict) -> str:
    for k in ("数据版本", "Raw Version", "游戏版本", "Game Version"):
        if k in meta and meta[k]:
            return str(meta[k])
    return "?"


def generate_timeline(
    game: GameData,
    game_root: Path,
    ui: UI,
    report_paths: list[Path],
    out_dir: Path,
    *,
    include_current: bool = True,
    width: int = 2600,
    clip_percentile: float = 99.0,
    gamma: float = 0.7,
) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # Metric definitions + the current game's values come from the live data.
    rows = list(build_region_rows(game, ui))
    cur_metrics = build_metrics(game, ui, rows=rows)            # canonical set
    if not cur_metrics:
        return None

    # Read each report as a version (values resolved in that report's language).
    versions: list[str] = []
    value_sources: list[dict[str, dict[str, float]]] = []      # version -> metric_key -> {sid: val}
    snaps: list = []                                           # parallel to versions; None = live game
    for p in report_paths:
        snap = read_regions_report(p)
        loc = load_localization(game_root, snapshot_lang(snap.meta))
        versions.append(_version_label(snap.meta))
        snaps.append(snap)
        per_metric: dict[str, dict[str, float]] = {}
        for m in cur_metrics:
            per_metric[m.key] = state_metric_values(snap, m.key, header_loc=loc)
        value_sources.append(per_metric)
    if include_current:
        versions.append(f"{game.raw_version or game.version or 'current'} (current)")
        snaps.append(None)
        value_sources.append({m.key: dict(m.values) for m in cur_metrics})

    if len(versions) < 1:
        return None

    # Historical-only resource kinds (removed from the live game, so not in
    # cur_metrics) — add a layer for each that any snapshot still carries, so the
    # timeline shows it fade to zero rather than dropping the kind entirely.
    snap_keys = {id(snap): _snap_res_keys(snap) for snap in snaps if snap is not None}
    present_kinds = {
        k for snap in snaps if snap is not None
        for h, k in LEGACY_REMOVED_HEADERS.items() if f"res_{h}" in snap_keys[id(snap)]
    }
    for kind in sorted(present_kinds):
        key = f"legacy_{kind}"
        label = _loc_name(game, LEGACY_REMOVED_LOC.get(kind, kind))   # English on map outputs
        cur_metrics.append(Metric(key=key, label=label, is_resource=True))
        for vi, snap in enumerate(snaps):
            value_sources[vi][key] = _removed_kind_values(snap, kind) if snap is not None else {}

    index = ProvinceIndex.build(game, game_root, width=width)
    state_ids = [r.state_id for r in rows if r.state_id in index.state_to_colors]
    idx_of = {sid: i for i, sid in enumerate(state_ids)}

    def name(sid):
        return game.loc.get_clean(sid) if game.loc is not None else sid

    bucket_of = {r.state_id: ui[f"rbucket_{r.bucket or 'other'}"] for r in rows}
    states = [{"n": name(sid), "b": bucket_of.get(sid, "")} for sid in state_ids]

    colors, cstate = [], []
    for sid in state_ids:
        for c in index.state_to_colors.get(sid, ()):
            colors.append(int(c))
            cstate.append(idx_of[sid])
    water = [int(c) for c in index.water_colors.tolist()]

    metric_json = []
    for m in cur_metrics:
        vals_per_ver = []
        vmax_per_ver = []
        for vi in range(len(versions)):
            raw = np.zeros(len(state_ids), dtype=np.float64)
            src = value_sources[vi].get(m.key, {})
            for sid, val in src.items():
                if sid in idx_of:
                    raw[idx_of[sid]] = val
            pos = raw[raw > 0]
            vmax = (float(np.percentile(pos, clip_percentile)) if (len(pos) and clip_percentile < 100)
                    else float(pos.max()) if len(pos) else 1.0)
            vmax_per_ver.append(round(vmax if vmax > 0 else 1.0, 2))
            vals_per_ver.append([round(float(x), 2) for x in raw])
        metric_json.append({
            "key": m.key, "label": m.label,
            "table": cm.table_for("auto", m.key, m.is_resource).astype(int).tolist(),
            "vmax": vmax_per_ver, "vals": vals_per_ver,
        })

    cmaps = {n: cm.as_table(n).astype(int).tolist() for n in cm.NAMES if n != "auto"}
    cmaps["diverging"] = cm.as_table("diverging").astype(int).tolist()

    payload = {
        "versions": versions, "states": states, "colors": colors, "cstate": cstate,
        "water": water, "metrics": metric_json, "cmaps": cmaps,
    }
    html = _TEMPLATE.format(
        title=ui["map_timeline_title"],
        generated=datetime.now().isoformat(timespec="minutes"),
        resource_label=ui["map_layer"], cmap_label=ui["map_colormap"],
        mode_label=ui["map_mode"], version_label=ui["map_version"],
        continent_label=ui["map_continent"], search_ph=ui["map_search"],
        labels_label=ui["map_labels"], world_label=ui["map_world"],
        mode_abs=ui["map_mode_abs"], mode_prev=ui["map_mode_prev"], mode_first=ui["map_mode_first"],
        nodata=ui["map_nodata"], water=ui["map_water"], gamma=gamma,
        img_b64=_base_image_b64(index),
        data=json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
    )
    path = out_dir / "resource_timeline.html"
    path.write_text(html, encoding="utf-8")
    log.info("Wrote timeline %s (%d versions, %d layers)", path, len(versions), len(metric_json))
    return path


_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  :root {{ --bg:#efe6d4; --panel:#f7f1e3; --ink:#3a2e22; --muted:#8a7a64; --line:#cdbfa3; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:var(--ink);
          font:14px/1.55 Georgia,"Times New Roman",serif; }}
  header {{ padding:14px 20px; border-bottom:2px solid var(--line); display:flex;
            gap:16px; align-items:center; flex-wrap:wrap; background:linear-gradient(#f7f1e3,#efe6d4); }}
  header h1 {{ font-size:20px; margin:0; font-weight:700; }}
  .controls {{ margin-left:auto; display:flex; gap:14px; align-items:center; flex-wrap:wrap; }}
  label {{ color:var(--muted); font-size:12px; margin-right:5px; }}
  select,input {{ background:#fffdf7; color:var(--ink); border:1px solid var(--line);
                  border-radius:4px; padding:5px 8px; font-size:13px; font-family:inherit; }}
  #slider {{ padding:12px 20px; display:flex; align-items:center; gap:14px;
             border-bottom:1px solid var(--line); }}
  #ver {{ flex:1; }}
  #vlabel {{ font-weight:700; min-width:160px; }}
  #wrap {{ padding:16px 20px; }}
  #viewport {{ position:relative; overflow:hidden; border:1px solid var(--line);
               border-radius:6px; background:#dfe9f2; }}
  #map {{ display:block; width:100%; height:auto; transform-origin:0 0; transition:transform .35s ease; }}
  #sig {{ position:absolute; right:12px; bottom:10px; pointer-events:none; text-align:right;
          font:italic 12px Georgia,serif; color:#5a4a3a; opacity:0.82;
          text-shadow:0 1px 2px #ffffffcc; line-height:1.35; }}
  #legend {{ display:flex; align-items:center; gap:10px; margin-top:12px; color:var(--muted); flex-wrap:wrap; }}
  #bar {{ width:300px; height:14px; border:1px solid var(--line); border-radius:3px; }}
  .sw {{ display:inline-block; width:13px; height:13px; border:1px solid #999; border-radius:2px; vertical-align:-2px; margin:0 4px 0 14px; }}
  #tip {{ position:fixed; pointer-events:none; background:#2b2114ee; color:#f7efe0; padding:6px 10px;
          border-radius:5px; font-size:12.5px; display:none; border:1px solid #7c5a2e; }}
  #tip b {{ color:#f3d79a; }}
  button {{ background:#fffdf7; border:1px solid var(--line); border-radius:4px; padding:5px 10px;
            cursor:pointer; font-family:inherit; }}
</style></head>
<body>
<header>
  <h1>{title}</h1>
  <span style="color:var(--muted);font-size:12px;font-style:italic">{generated}</span>
  <div class="controls">
    <span><label>{resource_label}</label><select id="metric"></select></span>
    <span><label>{mode_label}</label><select id="mode">
      <option value="abs">{mode_abs}</option><option value="prev">{mode_prev}</option>
      <option value="first">{mode_first}</option></select></span>
    <span><label>{cmap_label}</label><select id="cmap"></select></span>
    <span><label>{continent_label}</label><select id="continent"></select></span>
    <span><input id="search" type="text" placeholder="{search_ph}"></span>
    <span><input type="checkbox" id="lbls" checked><label for="lbls">{labels_label}</label></span>
  </div>
</header>
<div id="slider">
  <label>{version_label}</label>
  <input id="ver" type="range" min="0" value="0" step="1">
  <span id="vlabel"></span>
</div>
<div id="wrap">
  <div id="viewport"><canvas id="map"></canvas><div id="sig">Econometrics Automation Tool<br>map by J.C.</div></div>
  <div id="legend">
    <span id="mlabel"></span>
    <span id="lo"></span><canvas id="bar" width="300" height="14"></canvas><span id="hi"></span>
    <span class="sw" style="background:rgb(224,224,224)"></span>{nodata}
    <span class="sw" style="background:rgb(176,206,230)"></span>{water}
  </div>
</div>
<div id="tip"></div>
<script id="data" type="application/json">{data}</script>
<script>
const D=JSON.parse(document.getElementById('data').textContent);
const WATER=[176,206,230],NODATA=[224,224,224],BORDER=[248,248,248];
const img=new Image(); img.onload=init; img.src="data:image/png;base64,{img_b64}";
let W,H,stateIdx,ctx,out,cur,cents,bboxes,spans,areas,bucketBox={{}};
const canvas=document.getElementById('map'),vp=document.getElementById('viewport');

function init(){{
  W=img.width;H=img.height;canvas.width=W;canvas.height=H;
  ctx=canvas.getContext('2d',{{willReadFrequently:true}});ctx.drawImage(img,0,0);
  const px=ctx.getImageData(0,0,W,H).data,c2s=new Map();
  for(let i=0;i<D.colors.length;i++)c2s.set(D.colors[i],D.cstate[i]);
  const waterSet=new Set(D.water),ns=D.states.length,n=W*H;
  stateIdx=new Int32Array(n);
  const scos=new Float64Array(ns),ssin=new Float64Array(ns),sy=new Float64Array(ns);areas=new Int32Array(ns);
  const TWO_PI=6.283185307179586,KX=TWO_PI/W;
  bboxes=Array.from({{length:ns}},()=>[1e9,1e9,-1,-1]);
  for(let p=0,j=0;p<n;p++,j+=4){{const key=(px[j]<<16)|(px[j+1]<<8)|px[j+2];
    let s;if(c2s.has(key))s=c2s.get(key);else if(waterSet.has(key))s=-1;else s=-2;stateIdx[p]=s;
    if(s>=0){{const x=p%W,y=(p/W)|0;scos[s]+=Math.cos(x*KX);ssin[s]+=Math.sin(x*KX);sy[s]+=y;areas[s]++;const b=bboxes[s];
      if(x<b[0])b[0]=x;if(y<b[1])b[1]=y;if(x>b[2])b[2]=x;if(y>b[3])b[3]=y;}}}}
  const ccx=new Float64Array(ns);
  cents=Array.from({{length:ns}},(_,s)=>{{if(!areas[s])return[0,0];let ax=Math.atan2(ssin[s],scos[s]);if(ax<0)ax+=TWO_PI;ccx[s]=ax/TWO_PI*W;return[ccx[s],sy[s]/areas[s]];}});
  spans=new Array(ns);
  {{const bD=new Float64Array(ns).fill(1e18),mX=new Float64Array(ns),mY=new Float64Array(ns);
    const Lx=new Float64Array(ns).fill(1e9),Rx=new Float64Array(ns).fill(-1e9),Ty=new Float64Array(ns).fill(1e9),By=new Float64Array(ns).fill(-1e9);
    for(let p=0;p<n;p++){{const s=stateIdx[p];if(s<0)continue;const x=p%W,y=(p/W)|0;
      let dx=x-ccx[s];if(dx>W/2)dx-=W;else if(dx<-W/2)dx+=W;const dy=y-cents[s][1],dd=dx*dx+dy*dy;if(dd<bD[s]){{bD[s]=dd;mX[s]=x;mY[s]=y;}}
      if(dx<Lx[s])Lx[s]=dx;if(dx>Rx[s])Rx[s]=dx;if(y<Ty[s])Ty[s]=y;if(y>By[s])By[s]=y;}}
    for(let s=0;s<ns;s++){{if(!areas[s]){{spans[s]=null;continue;}}cents[s]=[mX[s],mY[s]];spans[s]=[ccx[s]+Lx[s],Ty[s],ccx[s]+Rx[s],By[s]];}}}}
  {{const acc={{}};
    for(let s=0;s<ns;s++){{if(!areas[s])continue;const b=D.states[s].b||'?';
      (acc[b]||(acc[b]={{c:0,s:0}}));acc[b].c+=Math.cos(ccx[s]*KX);acc[b].s+=Math.sin(ccx[s]*KX);}}
    const cenX={{}};for(const b in acc){{let a=Math.atan2(acc[b].s,acc[b].c);if(a<0)a+=TWO_PI;cenX[b]=a/TWO_PI*W;}}
    for(let s=0;s<ns;s++){{if(!areas[s])continue;const b=D.states[s].b||'?';const sp=spans[s];
      const sh=Math.round((cenX[b]-ccx[s])/W)*W;
      const bb=bucketBox[b]||(bucketBox[b]=[1e9,1e9,-1e9,-1e9]);
      if(sp[0]+sh<bb[0])bb[0]=sp[0]+sh;if(sp[1]<bb[1])bb[1]=sp[1];if(sp[2]+sh>bb[2])bb[2]=sp[2]+sh;if(sp[3]>bb[3])bb[3]=sp[3];}}}}
  out=ctx.createImageData(W,H);
  const ms=document.getElementById('metric');
  D.metrics.forEach((m,i)=>{{const o=document.createElement('option');o.value=i;o.textContent=m.label;ms.appendChild(o);}});
  const cs=document.getElementById('cmap');
  ['auto',...Object.keys(D.cmaps).filter(k=>k!=='diverging')].forEach(k=>{{const o=document.createElement('option');o.value=k;o.textContent=k;cs.appendChild(o);}});
  const ver=document.getElementById('ver');ver.max=D.versions.length-1;ver.value=D.versions.length-1;
  const ct=document.getElementById('continent');const wo=document.createElement('option');
  wo.value='__world';wo.textContent="{world_label}";ct.appendChild(wo);
  Object.keys(bucketBox).sort().forEach(b=>{{const o=document.createElement('option');o.value=b;o.textContent=b;ct.appendChild(o);}});
  ms.onchange=cs.onchange=ver.oninput=document.getElementById('mode').onchange=document.getElementById('lbls').onchange=draw;
  ct.onchange=()=>{{const v=ct.value;v==='__world'?(canvas.style.transform='none'):zoomTo(bucketBox[v]);}};
  document.getElementById('search').addEventListener('input',onSearch);
  new ResizeObserver(()=>vp.style.height=(H*vp.clientWidth/W)+'px').observe(vp);
  draw();
}}
function lerp(cps,t){{t=Math.max(0,Math.min(1,t));const n=cps.length,pos=t*(n-1),lo=Math.floor(pos),hi=Math.min(lo+1,n-1),f=pos-lo,a=cps[lo],b=cps[hi];return [a[0]+(b[0]-a[0])*f,a[1]+(b[1]-a[1])*f,a[2]+(b[2]-a[2])*f];}}
function draw(){{
  const mi=+document.getElementById('metric').value||0,v=+document.getElementById('ver').value||0,
    mode=document.getElementById('mode').value,cmName=document.getElementById('cmap').value;
  cur=D.metrics[mi];document.getElementById('vlabel').textContent=D.versions[v];
  const ns=D.states.length,raw=cur.vals[v],sc=new Uint8Array(ns*3),txt=new Array(ns);
  let lo='0',hi=''+cur.vmax[v];
  if(mode==='abs'){{
    const cps=cmName==='auto'?cur.table:D.cmaps[cmName],vmax=cur.vmax[v];
    for(let s=0;s<ns;s++){{const r=raw[s];const col=r>0?lerp(cps,Math.pow(r/vmax,{gamma})):NODATA;
      sc[s*3]=col[0];sc[s*3+1]=col[1];sc[s*3+2]=col[2];txt[s]=r>0?(''+r):null;}}
    drawBar(cps,false);document.getElementById('lo').textContent='0';document.getElementById('hi').textContent=vmax;
  }} else {{
    const ref=mode==='first'?cur.vals[0]:(v>0?cur.vals[v-1]:cur.vals[0]);
    let maxabs=1;for(let s=0;s<ns;s++){{const d=raw[s]-ref[s];if(Math.abs(d)>maxabs)maxabs=Math.abs(d);}}
    const cps=D.cmaps.diverging;
    for(let s=0;s<ns;s++){{const d=raw[s]-ref[s];
      if(Math.abs(d)<1e-9){{sc[s*3]=NODATA[0];sc[s*3+1]=NODATA[1];sc[s*3+2]=NODATA[2];txt[s]=null;}}
      else{{const col=lerp(cps,(Math.max(-1,Math.min(1,d/maxabs))+1)/2);
        sc[s*3]=col[0];sc[s*3+1]=col[1];sc[s*3+2]=col[2];txt[s]=(d>0?'+':'−')+Math.abs(Math.round(d));}}}}
    drawBar(cps,false);document.getElementById('lo').textContent='-'+Math.round(maxabs);
    document.getElementById('hi').textContent='+'+Math.round(maxabs);
  }}
  const o=out.data,n=W*H;
  for(let p=0,j=0;p<n;p++,j+=4){{const s=stateIdx[p];let r,g,b;
    if(s>=0){{r=sc[s*3];g=sc[s*3+1];b=sc[s*3+2];}}else if(s===-1){{r=WATER[0];g=WATER[1];b=WATER[2];}}else{{r=BORDER[0];g=BORDER[1];b=BORDER[2];}}
    o[j]=r;o[j+1]=g;o[j+2]=b;o[j+3]=255;}}
  ctx.putImageData(out,0,0);
  if(document.getElementById('lbls').checked)drawLabels(sc,txt);
  document.getElementById('mlabel').textContent=cur.label;
  curTxt=txt;
}}
let curTxt=[];
function drawBar(cps){{const bar=document.getElementById('bar'),bx=bar.getContext('2d');
  for(let x=0;x<bar.width;x++){{const c=lerp(cps,x/(bar.width-1));bx.fillStyle=`rgb(${{c[0]|0}},${{c[1]|0}},${{c[2]|0}})`;bx.fillRect(x,0,1,bar.height);}}}}
function drawLabels(sc,txt){{ctx.textAlign='center';ctx.textBaseline='middle';ctx.lineJoin='round';
  for(let s=0;s<D.states.length;s++){{const t=txt[s];if(t===null)continue;const a=areas[s];if(a<70)continue;
    const sz=Math.max(9,Math.min(24,Math.sqrt(a)*0.5));ctx.font='700 '+sz+'px Georgia,serif';
    const lum=0.299*sc[s*3]+0.587*sc[s*3+1]+0.114*sc[s*3+2],fg=lum>140?'#231a10':'#fdf6ea',halo=lum>140?'#fdf6ea':'#241a10';
    const [cx,cy]=cents[s];ctx.lineWidth=Math.max(2,sz/5);ctx.strokeStyle=halo;ctx.strokeText(t,cx,cy);ctx.fillStyle=fg;ctx.fillText(t,cx,cy);}}}}
function zoomTo(b){{if(!b||b[2]<=b[0])return;const pad=Math.max(8,W*0.012),ds=vp.clientWidth/W;
  const x0=b[0]-pad,y0=Math.max(0,b[1]-pad),x1=b[2]+pad,y1=Math.min(H,b[3]+pad);
  const cw=vp.clientWidth,ch=vp.clientHeight;
  const z=Math.max(1,Math.min(cw/((x1-x0)*ds),ch/((y1-y0)*ds),8));
  canvas.style.transform=`translate(${{cw/2-((x0+x1)/2)*ds*z}}px,${{ch/2-((y0+y1)/2)*ds*z}}px) scale(${{z}})`;}}
function onSearch(e){{const q=e.target.value.trim().toLowerCase();if(!q)return;
  for(let s=0;s<D.states.length;s++)if(D.states[s].n.toLowerCase().includes(q)){{
    if(spans[s])zoomTo(spans[s]);break;}}}}
const tip=document.getElementById('tip');
canvas.addEventListener('mousemove',e=>{{const r=canvas.getBoundingClientRect();
  const x=Math.floor((e.clientX-r.left)/r.width*W),y=Math.floor((e.clientY-r.top)/r.height*H);
  if(x<0||y<0||x>=W||y>=H){{tip.style.display='none';return;}}
  const s=stateIdx[y*W+x];if(s<0){{tip.style.display='none';return;}}
  const v=+document.getElementById('ver').value||0;
  tip.innerHTML=`<b>${{D.states[s].n}}</b><br>${{cur.label}}: ${{cur.vals[v][s]}}`+(curTxt[s]?`<br>Δ ${{curTxt[s]}}`:'');
  tip.style.display='block';tip.style.left=(e.clientX+14)+'px';tip.style.top=(e.clientY+14)+'px';}});
canvas.addEventListener('mouseleave',()=>tip.style.display='none');
</script></body></html>
"""
