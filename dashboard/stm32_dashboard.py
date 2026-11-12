"""
STM32F446RE — Temperature Regulation Dashboard  (Pro Light Edition)
Run:
    pip install -r requirements.txt
    python stm32_dashboard.py
Open: http://127.0.0.1:8050
"""

import threading
import serial
from dash import Dash, dcc, html, Input, Output, State
import plotly.graph_objects as go

# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════
SERIAL_PORT = "COM8"
BAUD_RATE   = 9600
PWM_MAX     = 16000
KP          = 800
TCMIN, TCMAX = 50, 70
MAX_HIST    = 80

live = {"connected": False, "tm_c": 0.0, "tc_c": 60.0, "pwm": 0, "port_name": ""}

def serial_reader():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
        live["connected"] = True
        live["port_name"] = SERIAL_PORT
        while True:
            line = ser.readline().decode("utf-8", errors="ignore").strip()
            if line.startswith("DATA:"):
                parts = line[5:].split(",")
                if len(parts) == 3:
                    try:
                        live["tm_c"] = float(parts[0])
                        live["tc_c"] = float(parts[1])
                        live["pwm"]  = int(parts[2])
                    except ValueError:
                        pass
    except Exception as e:
        live["connected"] = False
        print(f"[Serial] {SERIAL_PORT} not found — simulation mode. ({e})")

threading.Thread(target=serial_reader, daemon=True).start()

def adc_to_tm(adc):  return ((int(adc) * 3300) >> 12) / 10.0
def adc_to_tc(pot):  return TCMIN + (int(pot) * (TCMAX - TCMIN) / 4096)
def pid_p(tm, tc):   return int(min(KP * max(0.0, tm - tc), PWM_MAX))
def to_f(c):         return round(c * 9 / 5 + 32, 1)

# ══════════════════════════════════════════════════════════════
#  LIGHT PROFESSIONAL THEME
# ══════════════════════════════════════════════════════════════
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&family=Architects+Daughter&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --bg:           #fdf6ff;
    --surface:      #ffffff;
    --surface2:     #faf4ff;
    --border:       #ecdff7;
    --peach:        #ffb3a7;
    --peach-bg:     #fff0ee;
    --peach-text:   #c0513e;
    --mint:         #a8e6cf;
    --mint-bg:      #edfaf4;
    --mint-text:    #2d8a65;
    --lavender:     #c9b8f7;
    --lavender-bg:  #f2eeff;
    --lavender-text:#6a4bc4;
    --sky:          #a3d4f7;
    --sky-bg:       #eaf5ff;
    --sky-text:     #2470b0;
    --butter:       #ffe9a0;
    --butter-bg:    #fffbec;
    --butter-text:  #a07c10;
    --text:         #3d2c4e;
    --text-soft:    #8a7aa0;
    --text-muted:   #b5a8c8;
    --radius:       20px;
    --shadow:       0 4px 18px rgba(160,100,220,0.12);
    --shadow-card:  0 2px 12px rgba(160,100,220,0.07);
}

body {
    font-family: 'Nunito', sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
}

::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--lavender); border-radius: 10px; }

/* ── Outer layout ── */
.dash-outer { display: flex; min-height: 100vh; }

/* ── Sidebar ── */
.sidebar {
    width: 290px; flex-shrink: 0;
    background: var(--surface);
    border-right: 2px dashed var(--border);
    padding: 26px 20px 30px;
    display: flex; flex-direction: column; gap: 22px;
    min-height: 100vh;
}

.sidebar-logo {
    display: flex; align-items: center; gap: 12px;
    padding-bottom: 18px;
    border-bottom: 2px dashed var(--border);
}
.sidebar-logo-icon {
    width: 44px; height: 44px;
    background: var(--lavender-bg);
    border: 2px solid var(--lavender);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
}
.sidebar-logo-text h2 {
    font-family: 'Architects Daughter', cursive;
    font-size: 15px; color: var(--lavender-text); line-height: 1.2;
}
.sidebar-logo-text span { font-size: 11px; color: var(--text-muted); font-weight: 700; }

.sidebar-section-label {
    font-family: 'Architects Daughter', cursive;
    font-size: 12px; color: var(--text-muted);
    margin-bottom: 10px;
    display: flex; align-items: center; gap: 8px;
}
.sidebar-section-label::after {
    content: ''; flex: 1; height: 2px; border-radius: 2px; background: var(--border);
}

.control-block {
    background: var(--surface2);
    border: 1.5px solid var(--border);
    border-radius: 14px; padding: 14px 15px; margin-bottom: 10px;
}
.control-block:last-child { margin-bottom: 0; }
.control-title {
    font-size: 12px; font-weight: 800; color: var(--text-soft);
    margin-bottom: 8px;
    display: flex; justify-content: space-between; align-items: center;
}
.val-tag {
    font-size: 11px; font-weight: 700;
    background: var(--lavender-bg); color: var(--lavender-text);
    padding: 2px 9px; border-radius: 20px; border: 1px solid var(--lavender);
}

.unit-row {
    background: var(--butter-bg); border: 1.5px solid var(--butter); border-radius: 14px; padding: 13px 15px;
}
.unit-label { font-size: 12px; font-weight: 800; color: var(--butter-text); margin-bottom: 9px; }

/* System info */
.sys-info-row { display: flex; flex-direction: column; gap: 7px; }
.sys-info-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 7px 11px; background: var(--surface2);
    border-radius: 10px; border: 1.5px solid var(--border);
}
.sys-info-key { font-size: 11px; color: var(--text-muted); font-weight: 700; }
.sys-info-val { font-size: 11px; font-weight: 900; color: var(--lavender-text); }

.conn-badge-wrap { margin-top: auto; }
.conn-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 12px;
    font-weight: 600;
}
.conn-badge.live { background: rgba(34,197,94,0.1); color: #16a34a; border: 1px solid rgba(34,197,94,0.2); }
.conn-badge.sim  { background: var(--amber-soft); color: var(--amber); border: 1px solid rgba(245,158,11,0.2); }
.conn-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: currentColor;
    animation: pulse 2s infinite;
}
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.35;} }

/* ── Main content ── */
.main-content {
    flex: 1; padding: 26px 26px 40px;
    display: flex; flex-direction: column; gap: 18px; overflow: hidden;
}

/* ── Top bar ── */
.top-bar { display: flex; align-items: center; justify-content: space-between; }
.top-bar h1 {
    font-family: 'Architects Daughter', cursive;
    font-size: 22px; color: var(--lavender-text); letter-spacing: 0.3px;
}
.top-bar .subtitle { font-size: 12px; color: var(--text-muted); font-weight: 700; margin-top: 4px; }
.tick-pill {
    background: var(--lavender-bg); border: 1.5px solid var(--lavender);
    border-radius: 20px; padding: 6px 16px;
    font-size: 13px; font-weight: 800; color: var(--lavender-text);
}

/* ── Metric cards ── */
.metrics-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.metric-card {
    border-radius: var(--radius); padding: 20px 20px 16px; border: 2px solid;
    box-shadow: var(--shadow-card); position: relative; overflow: hidden;
    transition: transform 0.18s, box-shadow 0.18s;
}
.metric-card:hover { transform: translateY(-3px) rotate(-0.5deg); box-shadow: var(--shadow); }
.metric-card.hot  { background: var(--peach-bg);    border-color: var(--peach); }
.metric-card.cold { background: var(--sky-bg);      border-color: var(--sky); }
.metric-card.err  { background: var(--lavender-bg); border-color: var(--lavender); }
.metric-card.pwm  { background: var(--mint-bg);     border-color: var(--mint); }
.metric-label {
    font-size: 11px; font-weight: 800; text-transform: uppercase;
    letter-spacing: 0.08em; margin-bottom: 10px;
}
.metric-card.hot  .metric-label { color: var(--peach-text); }
.metric-card.cold .metric-label { color: var(--sky-text); }
.metric-card.err  .metric-label { color: var(--lavender-text); }
.metric-card.pwm  .metric-label { color: var(--mint-text); }
.metric-value {
    font-family: 'Architects Daughter', cursive;
    font-size: 32px; line-height: 1; margin-bottom: 7px;
}
.metric-card.hot  .metric-value { color: var(--peach-text); }
.metric-card.cold .metric-value { color: var(--sky-text); }
.metric-card.err  .metric-value { color: var(--lavender-text); }
.metric-card.pwm  .metric-value { color: var(--mint-text); }
.metric-sub { font-size: 10px; font-weight: 700; color: var(--text-muted); }
.metric-icon { position: absolute; right: 14px; top: 14px; font-size: 28px; opacity: 0.18; }
.metric-chip {
    display: inline-block; font-size: 10px; font-weight: 800;
    padding: 3px 9px; border-radius: 20px; margin-top: 8px; border: 1.5px solid;
}
.chip-hot  { background: var(--peach-bg);    color: var(--peach-text);    border-color: var(--peach); }
.chip-cold { background: var(--sky-bg);      color: var(--sky-text);      border-color: var(--sky); }
.chip-err  { background: var(--lavender-bg); color: var(--lavender-text); border-color: var(--lavender); }
.chip-pwm  { background: var(--mint-bg);     color: var(--mint-text);     border-color: var(--mint); }

/* ── Charts row ── */
.charts-row { display: grid; grid-template-columns: 1fr 300px; gap: 14px; flex: 1; }
.chart-card {
    background: var(--surface); border: 2px solid var(--border);
    border-radius: var(--radius); padding: 18px 20px 10px; box-shadow: var(--shadow-card);
}
.chart-card-label {
    font-family: 'Architects Daughter', cursive;
    font-size: 11px; color: var(--text-muted); margin-bottom: 2px;
}
.chart-card-title {
    font-family: 'Architects Daughter', cursive;
    font-size: 16px; color: var(--lavender-text); margin-bottom: 12px;
}

/* ── Status bar ── */
.status-bar { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.status-card {
    background: var(--surface); border: 2px solid var(--border);
    border-radius: 16px; padding: 15px 18px;
    display: flex; align-items: center; gap: 12px; box-shadow: var(--shadow-card);
}
.status-icon {
    width: 38px; height: 38px; border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 17px; flex-shrink: 0;
}
.status-icon.green  { background: var(--mint-bg);     border: 1.5px solid var(--mint); }
.status-icon.blue   { background: var(--sky-bg);      border: 1.5px solid var(--sky); }
.status-icon.purple { background: var(--lavender-bg); border: 1.5px solid var(--lavender); }
.status-text-label { font-size: 10px; font-weight: 800; text-transform: uppercase;
                     letter-spacing: 0.07em; color: var(--text-muted); margin-bottom: 3px; }
.status-text-value { font-size: 13px; font-weight: 800; color: var(--text); }

/* ── conn badge ── */
.conn-badge-wrap { margin-top: auto; }
.conn-badge { display: flex; align-items: center; gap: 8px; padding: 10px 14px;
              border-radius: 14px; font-size: 13px; font-weight: 800; }
.conn-badge.live { background: var(--mint-bg); color: var(--mint-text); border: 2px solid var(--mint); }
.conn-badge.sim  { background: var(--butter-bg); color: var(--butter-text); border: 2px solid var(--butter); }
.conn-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor;
            animation: pulse 2s infinite; }
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }

/* ── Plotly overrides ── */
.js-plotly-plot .plotly .modebar { display: none !important; }
"""

# ══════════════════════════════════════════════════════════════
#  APP
# ══════════════════════════════════════════════════════════════
app = Dash(__name__, title="STM32 Dashboard ✨")
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>{%title%}</title>
    {%favicon%}
    {%css%}
    <style>''' + CSS + '''</style>
</head>
<body>
{%app_entry%}
<footer>{%config%}{%scripts%}{%renderer%}</footer>
</body>
</html>
'''

app.layout = html.Div(className="dash-outer", children=[

    # ══════════════════════════════════════════════════════════
    #  SIDEBAR — Simulation Controls + System Info
    # ══════════════════════════════════════════════════════════
    html.Div(className="sidebar", children=[

        # Logo / title
        html.Div(className="sidebar-logo", children=[
            html.Div("🌡", className="sidebar-logo-icon"),
            html.Div(className="sidebar-logo-text", children=[
                html.H2("STM32F446RE"),
                html.Span("Temp. Regulation System"),
            ]),
        ]),

        # Simulation controls
        html.Div([
            html.Div("Simulation controls", className="section-label"),

            html.Div(className="control-block", children=[
                html.Div(["LM35 — Measured Temp",
                          html.Span(id="lm35-val-label", className="val-tag")],
                         className="control-title"),
                dcc.Slider(id="lm35-slider", min=0, max=4095, step=1, value=1600,
                           marks={0:"0", 1024:"1k", 2048:"2k", 3072:"3k", 4095:"4k"},
                           tooltip={"always_visible": False}),
            ]),

            html.Div(className="control-block", children=[
                html.Div(["Potentiometer — Setpoint",
                          html.Span(id="pot-val-label", className="val-tag")],
                         className="control-title"),
                dcc.Slider(id="pot-slider", min=0, max=4095, step=1, value=2048,
                           marks={0:"0", 1024:"1k", 2048:"2k", 3072:"3k", 4095:"4k"},
                           tooltip={"always_visible": False}),
            ]),

            html.Div(className="unit-row", children=[
                html.Div("Display unit", className="unit-label"),
                dcc.RadioItems(id="unit-toggle",
                               options=[{"label": " °C  ", "value": "C"},
                                        {"label": " °F", "value": "F"}],
                               value="C", inline=True,
                               style={"fontSize":"13px", "fontWeight":"800", "color":"#a07c10"}),
            ]),
        ]),

        # System info
        html.Div([
            html.Div("System info", className="section-label"),
            html.Div(className="sys-info-row", children=[
                html.Div(className="sys-info-item", children=[
                    html.Span("Clock", className="sys-info-key"),
                    html.Span("168 MHz", className="sys-info-val"),
                ]),
                html.Div(className="sys-info-item", children=[
                    html.Span("Timer", className="sys-info-key"),
                    html.Span("TIM7 @ 1 Hz", className="sys-info-val"),
                ]),
                html.Div(className="sys-info-item", children=[
                    html.Span("UART", className="sys-info-key"),
                    html.Span("9600 baud", className="sys-info-val"),
                ]),
                html.Div(className="sys-info-item", children=[
                    html.Span("PWM Pin", className="sys-info-key"),
                    html.Span("TIM4/PB6", className="sys-info-val"),
                ]),
                html.Div(className="sys-info-item", children=[
                    html.Span("Kp", className="sys-info-key"),
                    html.Span(str(KP), className="sys-info-val"),
                ]),
                html.Div(className="sys-info-item", children=[
                    html.Span("Setpoint Range", className="sys-info-key"),
                    html.Span(f"{TCMIN}–{TCMAX} °C", className="sys-info-val"),
                ]),
            ]),
        ]),

        # Connection badge (pushed to bottom)
        html.Div(className="conn-badge-wrap", children=[
            html.Div(id="conn-badge"),
        ]),
    ]),

    # ══════════════════════════════════════════════════════════
    #  MAIN CONTENT
    # ══════════════════════════════════════════════════════════
    html.Div(className="main-content", children=[

        # Top bar
        html.Div(className="top-bar", children=[
            html.Div([
        html.H1("Temperature Regulation Dashboard ✨"),
                html.Div("STM32F446RE · HSE+PLL · Real-time P-Controller", className="subtitle"),
            ]),
            html.Div(id="tick-label", className="tick-pill"),
        ]),

        # 4 Metric cards
        html.Div(className="metrics-grid", children=[
            html.Div(className="metric-card hot", children=[
                html.Div("🌡", className="metric-icon"),
                html.Div("Tm — Measured", className="metric-label"),
                html.Div(id="tm-display", className="metric-value"),
                html.Div(id="tm-sub", className="metric-sub"),
                html.Div("LM35 · ADC CH8", className="metric-chip chip-hot"),
            ]),
            html.Div(className="metric-card cold", children=[
                html.Div("🎯", className="metric-icon"),
                html.Div("Tc — Setpoint", className="metric-label"),
                html.Div(id="tc-display", className="metric-value"),
                html.Div(id="tc-sub", className="metric-sub"),
                html.Div("Pot · ADC CH9", className="metric-chip chip-cold"),
            ]),
            html.Div(className="metric-card err", children=[
                html.Div("⚡", className="metric-icon"),
                html.Div("Error Tm − Tc", className="metric-label"),
                html.Div(id="err-display", className="metric-value"),
                html.Div(id="err-sub", className="metric-sub"),
                html.Div("P-Controller Input", className="metric-chip chip-err"),
            ]),
            html.Div(className="metric-card pwm", children=[
                html.Div("🔧", className="metric-icon"),
                html.Div("PWM Duty — TIM4/PB6", className="metric-label"),
                html.Div(id="pwm-display", className="metric-value"),
                html.Div(id="pwm-sub", className="metric-sub"),
                html.Div("Actuator Output", className="metric-chip chip-pwm"),
            ]),
        ]),

        # Charts row
        html.Div(className="charts-row", children=[
            html.Div(className="chart-card", children=[
                html.Div("Live Readings", className="chart-card-label"),
                html.Div("Temperature Over Time", className="chart-card-title"),
                dcc.Graph(id="temp-chart", style={"height":"260px"},
                          config={"displayModeBar": False}),
            ]),
            html.Div(className="chart-card", children=[
                html.Div("Actuator Output", className="chart-card-label"),
                html.Div("PWM Duty Cycle", className="chart-card-title"),
                dcc.Graph(id="pwm-gauge", style={"height":"260px"},
                          config={"displayModeBar": False}),
            ]),
        ]),

        # Status bar
        html.Div(className="status-bar", children=[
            html.Div(className="status-card", children=[
                html.Div("🔗", className="status-icon green"),
                html.Div([
                    html.Div("Serial Port", className="status-text-label"),
                    html.Div(id="status-port", className="status-text-value"),
                ]),
            ]),
            html.Div(className="status-card", children=[
                html.Div("⚙️", className="status-icon blue"),
                html.Div([
                    html.Div("P-Controller", className="status-text-label"),
                    html.Div(id="status-pid", className="status-text-value"),
                ]),
            ]),
            html.Div(className="status-card", children=[
                html.Div("📡", className="status-icon purple"),
                html.Div([
                    html.Div("Actuator State", className="status-text-label"),
                    html.Div(id="status-actuator", className="status-text-value"),
                ]),
            ]),
        ]),

        # Hidden stores
        dcc.Store(id="history-store", data={"tm":[], "tc":[], "t":[]}),
        dcc.Interval(id="ticker", interval=1200, n_intervals=0),
    ]),
])

# ══════════════════════════════════════════════════════════════
#  CALLBACK
# ══════════════════════════════════════════════════════════════
@app.callback(
    Output("conn-badge",      "children"),
    Output("tick-label",      "children"),
    Output("lm35-val-label",  "children"),
    Output("pot-val-label",   "children"),
    Output("tm-display",      "children"),
    Output("tc-display",      "children"),
    Output("err-display",     "children"),
    Output("pwm-display",     "children"),
    Output("tm-sub",          "children"),
    Output("tc-sub",          "children"),
    Output("err-sub",         "children"),
    Output("pwm-sub",         "children"),
    Output("temp-chart",      "figure"),
    Output("pwm-gauge",       "figure"),
    Output("status-port",     "children"),
    Output("status-pid",      "children"),
    Output("status-actuator", "children"),
    Output("history-store",   "data"),
    Input("ticker",           "n_intervals"),
    Input("lm35-slider",      "value"),
    Input("pot-slider",       "value"),
    Input("unit-toggle",      "value"),
    State("history-store",    "data"),
)
def update(n, lm35_raw, pot_raw, unit, history):
    lm35_raw = lm35_raw or 0
    pot_raw  = pot_raw  or 0

    if live["connected"]:
        Tm_c, Tc_c, pwm = live["tm_c"], live["tc_c"], live["pwm"]
        badge = html.Div(className="conn-badge live", children=[
            html.Div(className="conn-dot"), "Live Board"])
        port_txt = live["port_name"]
    else:
        Tm_c = adc_to_tm(lm35_raw)
        Tc_c = adc_to_tc(pot_raw)
        pwm  = pid_p(Tm_c, Tc_c)
        badge = html.Div(className="conn-badge sim", children=[
            html.Div(className="conn-dot"), "Simulation mode ✨"])
        port_txt = f"{SERIAL_PORT} — not found"

    err_c   = Tm_c - Tc_c
    pwm_pct = round(pwm / PWM_MAX * 100)
    sym     = "°F" if unit == "F" else "°C"

    Tm  = to_f(Tm_c)  if unit == "F" else round(Tm_c, 1)
    Tc  = to_f(Tc_c)  if unit == "F" else round(Tc_c, 1)
    err = round(to_f(Tm_c) - to_f(Tc_c), 1) if unit == "F" else round(err_c, 1)

    pid_txt = f"Kp={KP}  CCR={pwm}"
    act_txt = "ON — cooling 🌬️" if pwm_pct > 0 else "OFF — at target 🎯"

    # History
    history["tm"].append(round(Tm_c, 1))
    history["tc"].append(round(Tc_c, 1))
    history["t"].append(n)
    if len(history["tm"]) > MAX_HIST:
        for k in ("tm", "tc", "t"):
            history[k] = history[k][-MAX_HIST:]

    plot_tm = [to_f(v) for v in history["tm"]] if unit == "F" else history["tm"]
    plot_tc = [to_f(v) for v in history["tc"]] if unit == "F" else history["tc"]
    y_lo = min(min(plot_tm), min(plot_tc)) - 5
    y_hi = max(max(plot_tm), max(plot_tc)) + 5

    # ── Temperature chart ──────────────────────────────────────
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=history["t"], y=plot_tc,
        fill=None, mode="lines",
        line=dict(color="rgba(163,212,247,0)", width=0),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_trace(go.Scatter(
        x=history["t"], y=plot_tm,
        fill="tonexty",
        fillcolor="rgba(255,179,167,0.18)",
        mode="lines",
        line=dict(color="#e0836e", width=2.5),
        name="Tm (measured)",
    ))
    fig.add_trace(go.Scatter(
        x=history["t"], y=plot_tc,
        mode="lines",
        line=dict(color="#6aaee0", width=2, dash="dash"),
        name="Tc (setpoint)",
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=48, r=16, t=8, b=32),
        legend=dict(x=0, y=1.12, orientation="h",
                    font=dict(size=12, color="#8a7aa0", family="Nunito"),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(
            showgrid=True, gridcolor="rgba(201,184,247,0.2)",
            zeroline=False, tickfont=dict(size=11, color="#b5a8c8", family="Nunito"),
            title=dict(text="tick", font=dict(size=11, color="#b5a8c8", family="Nunito")),
            linecolor="#ecdff7",
        ),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(201,184,247,0.2)",
            zeroline=False, tickfont=dict(size=11, color="#b5a8c8", family="Nunito"),
            ticksuffix=sym, range=[y_lo, y_hi],
            linecolor="#ecdff7",
        ),
        font=dict(family="Nunito, sans-serif"),
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#ffffff", font_size=12,
                        font_family="Nunito, sans-serif",
                        bordercolor="#ecdff7"),
    )

    # ── PWM gauge ─────────────────────────────────────────────
    gauge_color = ("#e0836e" if pwm_pct > 80
                   else "#c9a050" if pwm_pct > 40
                   else "#4dab8a")

    fig_g = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=pwm_pct,
        delta={"reference": 50, "valueformat": ".0f",
               "increasing": {"color": "#e0836e"},
               "decreasing": {"color": "#4dab8a"}},
        number={"suffix": "%", "font": {"size": 40, "family": "Nunito",
                                         "color": gauge_color}},
        gauge={
            "axis": {"range": [0, 100],
                     "tickwidth": 1,
                     "tickfont": {"size": 10, "color": "#b5a8c8", "family": "Nunito"},
                     "tickcolor": "#ecdff7"},
            "bar":  {"color": gauge_color, "thickness": 0.25},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0,  40], "color": "rgba(168,230,207,0.15)"},
                {"range": [40, 80], "color": "rgba(255,233,160,0.15)"},
                {"range": [80,100], "color": "rgba(255,179,167,0.15)"},
            ],
            "threshold": {
                "line": {"color": "#e0836e", "width": 2},
                "thickness": 0.75, "value": 80,
            },
        },
    ))
    fig_g.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=40, b=0),
        font=dict(family="Nunito, sans-serif"),
        height=240,
    )

    return (
        badge,
        f"Tick {n:04d} ✦",
        f"{lm35_raw}",
        f"{pot_raw}",
        f"{Tm} {sym}",
        f"{Tc} {sym}",
        f"{'+' if err >= 0 else ''}{err} {sym}",
        f"{pwm_pct}%",
        f"ADC CH8 · raw {lm35_raw}",
        f"ADC CH9 · raw {pot_raw}",
        "Above setpoint — actuator ON" if err_c > 0 else "Below setpoint — OFF",
        f"CCR {pwm} / {PWM_MAX}",
        fig, fig_g,
        port_txt,
        pid_txt,
        act_txt,
        history,
    )


if __name__ == "__main__":
    print("\n  STM32 Temperature Dashboard  ✨")
    print("  ─────────────────────────────────────────────────────")
    print(f"  Port   : {SERIAL_PORT} @ {BAUD_RATE} baud")
    print("  Browser: http://127.0.0.1:8050\n")
    app.run(debug=False, port=8050)
