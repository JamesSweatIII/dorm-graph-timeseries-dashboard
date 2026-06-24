import os
import json
import streamlit as st

_ANIMATE_JS_CACHE = None


def _get_animate_js():
    global _ANIMATE_JS_CACHE
    if _ANIMATE_JS_CACHE is None:
        path = os.path.join(os.path.dirname(__file__), "..", "lib", "animate.js")
        with open(path) as f:
            _ANIMATE_JS_CACHE = f.read()
    return _ANIMATE_JS_CACHE


def animated_metrics(metrics, key="metrics"):
    items_html = ""
    for i, m in enumerate(metrics):
        color = m.get("color", "f59e6f")
        icon = m.get("icon", "")
        items_html += f"""
        <div class="mc" style="--accent:#{color}">
            <div class="mi">{icon}</div>
            <div class="ml">{m['label']}</div>
            <div class="mv" id="{key}-v{i}">0</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html><head><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:transparent; font-family:system-ui,-apple-system,sans-serif; }}
.mg {{ display:grid; grid-template-columns:repeat({len(metrics)},1fr); gap:10px; }}
.mc {{
    background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.08);
    border-radius:14px; padding:16px 12px; text-align:center; position:relative; overflow:hidden;
    backdrop-filter:blur(12px);
}}
.mc::after {{
    content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background:var(--accent); transform:scaleX(0);
    animation:sl 0.6s cubic-bezier(0.34,1.56,0.64,1) 0.15s forwards;
    box-shadow: 0 0 8px var(--accent);
}}
@keyframes sl {{ to {{ transform:scaleX(1); }} }}
.mi {{ font-size:22px; margin-bottom:2px; }}
.ml {{ font-size:11px; text-transform:uppercase; letter-spacing:0.8px; color:rgba(255,255,255,0.45); margin-bottom:6px; }}
.mv {{ font-size:34px; font-weight:700; color:#fff; font-variant-numeric:tabular-nums; }}
</style></head><body>
<div class="mg">{items_html}</div>
<script>
{_get_animate_js()}
(function(){{
    var m = {json.dumps([{'t': m['value']} for m in metrics])};
    m.forEach(function(x,i){{ var e=document.getElementById('{key}-v'+i); if(e) anim8.countUp(e,x.t,900,''); }});
}})();
</script></body></html>"""
    st.components.v1.html(html, height=125)


def animated_chart(data, title="", key="chart"):
    labels = data.get("columns", [])
    if "time" in labels or "timestamp" in labels:
        time_col = "time" if "time" in labels else "timestamp"
        value_cols = [c for c in labels if c not in (time_col,)]
    else:
        value_cols = labels[:]
    chart_labels = [row.get("time", row.get("timestamp", "")) for row in data["data"]]
    datasets = [{"label": col, "data": [row.get(col, 0) for row in data["data"]]} for col in value_cols]
    chart_data = {"labels": chart_labels, "datasets": datasets}
    cw, ch = 680, 250

    html = f"""<!DOCTYPE html>
<html><head><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:transparent; font-family:system-ui,-apple-system,sans-serif; }}
.cc {{ padding:6px; }}
.ct {{ color:#94a3b8; font-size:12px; font-weight:500; margin-bottom:4px; padding-left:4px; letter-spacing:0.3px; }}
canvas {{ display:block; width:{cw}px; height:{ch}px; border-radius:10px; }}
</style></head><body>
<div class="cc">
    <div class="ct">{title}</div>
    <canvas id="{key}" width="{cw}" height="{ch}"></canvas>
</div>
<script>
{_get_animate_js()}
(function(){{
    var d = {json.dumps(chart_data)};
    var c = document.getElementById('{key}');
    if(c) anim8.LineChart(c, d, {{padding:{{top:30,right:20,bottom:38,left:55}},duration:700,backgroundColor:'rgba(30,41,59,0.5)',paddingRatio:0.15}});
}})();
</script></body></html>"""
    st.components.v1.html(html, height=ch + 55)


def page_header(title, subtitle=""):
    html = f"""<!DOCTYPE html>
<html><head><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:transparent; font-family:system-ui,-apple-system,sans-serif; }}
.hd {{
    opacity:0; transform:translateY(-10px) scale(0.98);
    animation:hIn 0.6s cubic-bezier(0.34,1.56,0.64,1) 0.05s forwards;
    text-align:center; padding:8px 0 4px;
}}
@keyframes hIn {{ to {{ opacity:1; transform:translateY(0) scale(1); }} }}
.hd .emoji {{ font-size:36px; display:block; margin-bottom:4px; }}
.hd h1 {{ font-size:26px; font-weight:700; margin:0 0 2px; }}
.hd h1 .w {{ color:#f59e6f; }}
.hd h1 .t {{ color:#f1f5f9; }}
.hd .sb {{ font-size:13px; color:rgba(255,255,255,0.4); letter-spacing:0.3px; }}
</style></head><body>
<div class="hd">
    <span class="emoji">🏠</span>
    <h1><span class="w">Welcome to</span> <span class="t">{title}</span></h1>
    {f'<div class="sb">{subtitle}</div>' if subtitle else ''}
</div>
<script>{_get_animate_js()}</script></body></html>"""
    st.components.v1.html(html, height=105)


def info_banner(text):
    html = f"""<!DOCTYPE html>
<html><head><style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:transparent; font-family:system-ui,-apple-system,sans-serif; }}
.bn {{
    background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.06); border-radius:12px;
    padding:10px 14px; color:#cbd5e1; font-size:13px; opacity:0; text-align:center;
    animation:bIn 0.5s cubic-bezier(0.22,1,0.36,1) 0.2s forwards;
}}
@keyframes bIn {{ to {{ opacity:1; }} }}
.bn strong {{ color:#f59e6f; }}
</style></head><body>
<div class="bn">{text}</div>
<script>{_get_animate_js()}</script></body></html>"""
    st.components.v1.html(html, height=52)
