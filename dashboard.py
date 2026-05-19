#!/usr/bin/env python
"""
SOL Bot dashboard.
Run:  python dashboard.py
Then: http://localhost:8081   (opens automatically)
"""
import json
import sqlite3
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import ccxt

_DB   = Path(__file__).parent / "portfolio.db"
_SYM  = "SOL/USD"
_TF   = "15m"
_LIMS = 200
_PORT = 8081

_ex = ccxt.coinbase({"enableRateLimit": True})


# ── DB helpers ────────────────────────────────────────────────────────────────

def _one(sql, params=()):
    if not _DB.exists():
        return None
    conn = sqlite3.connect(str(_DB), timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        r = conn.execute(sql, params).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def _all(sql, params=()):
    if not _DB.exists():
        return []
    conn = sqlite3.connect(str(_DB), timeout=5)
    conn.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


# ── API functions ─────────────────────────────────────────────────────────────

def get_account():
    row = _one("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1")
    if row is None:
        return {"equity": 10000.0, "cash": 10000.0, "unrealized_pnl": 0.0, "realized_pnl": 0.0}
    positions = json.loads(row["open_positions_json"])
    market_val = sum(p["units"] * p.get("current_price", p["fill_price"]) for p in positions)
    return {
        "equity":         round(row["cash"] + market_val, 2),
        "cash":           round(row["cash"], 2),
        "unrealized_pnl": round(row["unrealized_pnl"], 4),
        "realized_pnl":   round(row["realized_pnl"], 4),
    }


def get_positions():
    row = _one("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1")
    if row is None:
        return []
    out = []
    for p in json.loads(row["open_positions_json"]):
        cost = p["units"] * p["fill_price"]
        mval = p["units"] * p.get("current_price", p["fill_price"])
        out.append({
            "symbol":         p["symbol"],
            "units":          round(p["units"], 4),
            "fill_price":     round(p["fill_price"], 4),
            "current_price":  round(p.get("current_price", p["fill_price"]), 4),
            "stop_loss":      round(p.get("stop_loss", 0), 4),
            "take_profit":    round(p.get("take_profit", 0), 4),
            "unrealized_pnl": round(mval - cost, 4),
            "unrealized_pct": round((mval - cost) / cost * 100, 2) if cost else 0,
        })
    return out


def get_trades():
    return _all("SELECT * FROM trades ORDER BY id DESC LIMIT 500")


def get_equity_history():
    rows = _all(
        "SELECT timestamp, cash, open_positions_json, unrealized_pnl FROM snapshots ORDER BY id"
    )
    if not rows:
        return []
    step = max(1, len(rows) // 500)
    out = []
    for r in rows[::step]:
        positions = json.loads(r["open_positions_json"])
        mval = sum(p["units"] * p.get("current_price", p["fill_price"]) for p in positions)
        out.append({"time": r["timestamp"], "equity": round(r["cash"] + mval, 2)})
    return out


def get_candles():
    try:
        ohlcv = _ex.fetch_ohlcv(_SYM, _TF, limit=_LIMS)
    except Exception as exc:
        return {"error": str(exc), "bars": [], "markers": []}

    bars = [
        {"time": r[0] // 1000, "open": r[1], "high": r[2], "low": r[3], "close": r[4]}
        for r in ohlcv
    ]

    trades = _all(
        "SELECT timestamp, units, fill_price, pnl, status FROM trades ORDER BY id"
    )
    bar_sec = 15 * 60
    markers = []
    for t in trades:
        try:
            ts = t["timestamp"]
            if ts.endswith("Z"):
                ts = ts[:-1] + "+00:00"
            dt = datetime.fromisoformat(ts)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            ts_bar = (int(dt.timestamp()) // bar_sec) * bar_sec
            is_open = t["status"] == "open"
            pnl     = t.get("pnl")
            color   = "#e3b341" if is_open else ("#3fb950" if pnl and pnl >= 0 else "#f85149")
            label   = f"BUY {t['units']:.3f}"
            if not is_open and pnl is not None:
                label += f"  {'+' if pnl >= 0 else ''}{pnl:.2f}"
            markers.append({
                "time": ts_bar, "position": "belowBar",
                "color": color, "shape": "arrowUp", "text": label,
            })
        except Exception:
            pass

    return {"bars": bars, "markers": markers}


# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SOL BOT</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script src="https://unpkg.com/lightweight-charts@4.1.3/dist/lightweight-charts.standalone.production.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#0d1117;color:#e6edf3;font-size:14px}
.hdr{background:#161b22;border-bottom:1px solid #30363d;padding:11px 20px;display:flex;align-items:center;gap:14px;position:sticky;top:0;z-index:100;flex-wrap:wrap}
.logo{font-size:15px;font-weight:700;color:#58a6ff;white-space:nowrap}
.div{width:1px;height:22px;background:#30363d;flex-shrink:0}
.hm{display:flex;flex-direction:column;gap:1px}
.hm-l{font-size:9px;color:#8b949e;text-transform:uppercase;letter-spacing:.6px}
.hm-v{font-size:15px;font-weight:600;font-family:monospace}
.badge{padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;letter-spacing:.5px}
.paper{background:#9e6a0322;color:#e3b341;border:1px solid #9e6a0355}
.ml{margin-left:auto;display:flex;align-items:center;gap:10px}
.upd{font-size:11px;color:#8b949e}
.btn{background:#21262d;border:1px solid #30363d;color:#e6edf3;padding:5px 12px;border-radius:6px;cursor:pointer;font-size:12px}
.btn:hover{background:#30363d}
main{padding:14px;max-width:1600px;margin:0 auto}
.stats{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin-bottom:13px}
@media(max-width:900px){.stats{grid-template-columns:repeat(3,1fr)}}
@media(max-width:600px){.stats{grid-template-columns:repeat(2,1fr)}}
.sc{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px 16px}
.sl{font-size:10px;color:#8b949e;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}
.sv{font-size:21px;font-weight:700;font-family:monospace;line-height:1.1}
.ss{font-size:11px;color:#8b949e;margin-top:3px}
.row2{display:grid;grid-template-columns:3fr 2fr;gap:12px;margin-bottom:13px}
@media(max-width:800px){.row2{grid-template-columns:1fr}}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;overflow:hidden;margin-bottom:13px}
.ch{padding:10px 16px;border-bottom:1px solid #30363d;font-size:10px;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.5px;display:flex;align-items:center;justify-content:space-between;gap:8px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:8px 12px;color:#8b949e;font-size:10px;text-transform:uppercase;letter-spacing:.4px;border-bottom:1px solid #30363d;white-space:nowrap}
td{padding:9px 12px;border-bottom:1px solid #1c2128;white-space:nowrap}
tr:last-child td{border-bottom:none}
tr:hover td{background:#1c2128}
.g{color:#3fb950}.r{color:#f85149}.mu{color:#8b949e}.bl{color:#58a6ff}
.mono{font-family:monospace}
.buy-badge{background:#2ea04320;color:#3fb950;padding:2px 7px;border-radius:4px;font-size:11px;font-weight:600}
.nd{text-align:center;padding:28px;color:#8b949e;font-size:13px}
.cb{padding:12px}
</style>
</head>
<body>

<div class="hdr">
  <span class="logo">◎ SOL BOT</span>
  <span class="badge paper">PAPER</span>
  <div class="div"></div>
  <div class="hm"><span class="hm-l">Equity</span><span class="hm-v" id="heq">—</span></div>
  <div class="hm"><span class="hm-l">Cash</span><span class="hm-v" id="hca">—</span></div>
  <div class="hm"><span class="hm-l">Unrealized P&amp;L</span><span class="hm-v" id="hur">—</span></div>
  <div class="hm"><span class="hm-l">Realized P&amp;L</span><span class="hm-v" id="hre">—</span></div>
  <div class="ml">
    <span class="upd" id="upd">Connecting…</span>
    <button class="btn" onclick="loadAll()">↻ Refresh</button>
  </div>
</div>

<main>
  <div class="stats">
    <div class="sc"><div class="sl">Total P&amp;L</div><div class="sv" id="spnl">—</div><div class="ss" id="spnls">—</div></div>
    <div class="sc"><div class="sl">Win Rate</div><div class="sv" id="swr">—</div><div class="ss" id="swrs">—</div></div>
    <div class="sc"><div class="sl">Total Trades</div><div class="sv" id="sto">—</div><div class="ss" id="stos">—</div></div>
    <div class="sc"><div class="sl">Avg P&amp;L / Trade</div><div class="sv" id="savg">—</div><div class="ss">closed trades</div></div>
    <div class="sc"><div class="sl">Open Positions</div><div class="sv" id="sopen">—</div><div class="ss">of 3 max</div></div>
  </div>

  <div class="row2">
    <div class="card" style="margin-bottom:0">
      <div class="ch">Portfolio Equity Curve</div>
      <div class="cb"><canvas id="eqc" height="185"></canvas></div>
    </div>
    <div class="card" style="margin-bottom:0">
      <div class="ch"><span>Open Positions</span><span class="mu" id="pcnt">0</span></div>
      <div style="overflow-x:auto">
        <table>
          <thead><tr><th>Symbol</th><th>Units</th><th>Entry</th><th>Price</th><th>SL / TP</th><th>Unr. P&amp;L</th></tr></thead>
          <tbody id="ptb"><tr><td colspan="6" class="nd">No open positions</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="ch">
      <span>SOL/USD &middot; 15m</span>
      <span class="mu" id="cprice" style="font-family:monospace;font-size:13px;color:#e6edf3"></span>
    </div>
    <div id="cc" style="height:360px"></div>
  </div>

  <div class="card">
    <div class="ch">Trade History</div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Date / Time</th><th>Dir</th><th>Units</th><th>Entry</th><th>Exit</th><th>P&amp;L</th><th>Signal</th><th>Status</th></tr></thead>
        <tbody id="ttb"><tr><td colspan="8" class="nd">No trades yet</td></tr></tbody>
      </table>
    </div>
  </div>
</main>

<script>
let eqChart = null, cChart = null;

const el  = id => document.getElementById(id);
const fmt = (n, d=2) => n == null ? '—' : n.toLocaleString('en-US', {minimumFractionDigits:d, maximumFractionDigits:d});
const fmtD = n => { if(n == null) return '—'; const s = '$'+fmt(Math.abs(n)); return n >= 0 ? '+'+s : '-'+s; };
const cc  = n => n > 0 ? 'g' : n < 0 ? 'r' : 'mu';
const fmtTs = ts => ts ? new Date(ts).toLocaleString('en-US',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : '—';

async function api(p){ const r = await fetch(p); return r.json(); }

async function loadAccount(){
  const a = await api('/api/account');
  el('heq').textContent = '$'+fmt(a.equity);
  el('hca').textContent = '$'+fmt(a.cash);
  const ur = el('hur'); ur.textContent = fmtD(a.unrealized_pnl); ur.className = 'hm-v '+cc(a.unrealized_pnl);
  const re = el('hre'); re.textContent = fmtD(a.realized_pnl);   re.className = 'hm-v '+cc(a.realized_pnl);
}

async function loadPositions(){
  const ps = await api('/api/positions');
  el('pcnt').textContent  = ps.length;
  el('sopen').textContent = ps.length;
  const tb = el('ptb');
  if(!ps.length){ tb.innerHTML = '<tr><td colspan="6" class="nd">No open positions</td></tr>'; return; }
  tb.innerHTML = ps.map(p => `<tr>
    <td class="bl mono">${p.symbol}</td>
    <td class="mu">${fmt(p.units, 4)}</td>
    <td class="mu">$${fmt(p.fill_price)}</td>
    <td>$${fmt(p.current_price)}</td>
    <td class="mu" style="font-size:11px;line-height:1.6">SL $${fmt(p.stop_loss)}<br>TP $${fmt(p.take_profit)}</td>
    <td class="${cc(p.unrealized_pnl)}">${fmtD(p.unrealized_pnl)}<br><small>${fmt(p.unrealized_pct)}%</small></td>
  </tr>`).join('');
}

async function loadTrades(){
  const ts = await api('/api/trades');
  computeStats(ts);
  renderTrades(ts);
}

function computeStats(trades){
  const closed  = trades.filter(t => t.status !== 'open');
  const wins    = closed.filter(t => t.pnl != null && t.pnl >= 0);
  const totalPnl = closed.reduce((s, t) => s + (t.pnl || 0), 0);
  const openCnt = trades.filter(t => t.status === 'open').length;

  const pnlEl = el('spnl');
  pnlEl.textContent = closed.length ? fmtD(totalPnl) : '$0.00';
  pnlEl.className   = 'sv '+cc(totalPnl);
  el('spnls').textContent = closed.length ? `${closed.length} closed trade${closed.length>1?'s':''}` : 'No closed trades yet';
  el('swr').textContent  = closed.length ? (wins.length/closed.length*100).toFixed(1)+'%' : '—';
  el('swrs').textContent = closed.length ? `${wins.length}W / ${closed.length-wins.length}L` : '—';
  el('sto').textContent  = trades.length;
  el('stos').textContent = `${openCnt} open, ${closed.length} closed`;
  el('savg').textContent = closed.length ? fmtD(totalPnl/closed.length) : '—';
}

function renderTrades(trades){
  const tb = el('ttb');
  if(!trades.length){ tb.innerHTML = '<tr><td colspan="8" class="nd">No trades yet — waiting for a buy signal</td></tr>'; return; }
  tb.innerHTML = trades.map(t => {
    const open = t.status === 'open';
    const pnlCls = open ? 'mu' : (t.pnl >= 0 ? 'g' : 'r');
    return `<tr>
      <td class="mu" style="font-size:12px">${fmtTs(t.timestamp)}</td>
      <td><span class="buy-badge">BUY</span></td>
      <td class="mu">${fmt(t.units, 4)}</td>
      <td class="mu">$${fmt(t.fill_price)}</td>
      <td class="mu">${t.exit_price ? '$'+fmt(t.exit_price) : '—'}</td>
      <td class="${pnlCls}">${t.pnl != null ? fmtD(t.pnl) : '—'}</td>
      <td class="mu" style="font-size:11px;max-width:120px;overflow:hidden;text-overflow:ellipsis">${t.signal||'—'}</td>
      <td class="mu" style="font-size:11px">${t.status}</td>
    </tr>`;
  }).join('');
}

async function loadEqHistory(){
  const h = await api('/api/equity-history');
  if(!Array.isArray(h) || h.length < 2) return;
  const ctx = el('eqc').getContext('2d');
  if(eqChart) eqChart.destroy();
  const g = ctx.createLinearGradient(0, 0, 0, 240);
  g.addColorStop(0, 'rgba(88,166,255,0.22)');
  g.addColorStop(1, 'rgba(88,166,255,0)');
  eqChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: h.map(d => {
        const dt = new Date(d.time);
        return dt.toLocaleDateString('en-US',{month:'short',day:'numeric'})+' '+
               dt.toLocaleTimeString('en-US',{hour:'2-digit',minute:'2-digit'});
      }),
      datasets: [{
        data: h.map(d => d.equity),
        borderColor: '#58a6ff', backgroundColor: g,
        borderWidth: 2, pointRadius: 0, fill: true, tension: 0.3,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: true, animation: false,
      plugins: {legend:{display:false}, tooltip:{callbacks:{label: c => '$'+fmt(c.parsed.y)}}},
      scales: {
        x: {grid:{color:'#21262d'}, ticks:{color:'#8b949e',maxTicksLimit:7,font:{size:10}}},
        y: {grid:{color:'#21262d'}, ticks:{color:'#8b949e',callback:v=>'$'+(v>=1000?(v/1000).toFixed(1)+'k':v),font:{size:10}}},
      },
    },
  });
}

async function loadChart(){
  try {
    const data = await api('/api/candles');
    if(data.error || !data.bars || !data.bars.length) return;

    if(cChart){ cChart.remove(); cChart = null; }
    const wrap = el('cc'); wrap.innerHTML = '';

    cChart = LightweightCharts.createChart(wrap, {
      layout:          {background:{color:'#161b22'}, textColor:'#8b949e'},
      grid:            {vertLines:{color:'#21262d'}, horzLines:{color:'#21262d'}},
      crosshair:       {mode: LightweightCharts.CrosshairMode.Normal},
      rightPriceScale: {borderColor:'#30363d'},
      timeScale:       {borderColor:'#30363d', timeVisible:true, secondsVisible:false},
      width:  wrap.clientWidth,
      height: 360,
    });

    const cs = cChart.addCandlestickSeries({
      upColor:'#3fb950',    downColor:'#f85149',
      borderUpColor:'#3fb950', borderDownColor:'#f85149',
      wickUpColor:'#3fb950',   wickDownColor:'#f85149',
    });
    cs.setData(data.bars);

    if(data.bars.length){
      const last = data.bars[data.bars.length-1];
      el('cprice').textContent = '$'+fmt(last.close);
    }

    if(data.markers && data.markers.length){
      cs.setMarkers(data.markers.slice().sort((a,b) => a.time - b.time));
    }

    cChart.timeScale().fitContent();
    new ResizeObserver(() => { if(cChart) cChart.applyOptions({width:wrap.clientWidth}); }).observe(wrap);
  } catch(e) {
    console.error('Chart error:', e);
  }
}

async function loadAll(){
  el('upd').textContent = 'Loading…';
  try {
    await Promise.all([loadAccount(), loadPositions(), loadTrades(), loadEqHistory(), loadChart()]);
    el('upd').textContent = 'Updated '+new Date().toLocaleTimeString();
  } catch(e) {
    el('upd').textContent = 'Error — see console';
    console.error(e);
  }
}

loadAll();
setInterval(loadAll, 60000);
</script>
</body>
</html>"""


# ── HTTP server ───────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        try:
            if path == "/":
                self._html(HTML)
            elif path == "/api/account":
                self._json(get_account())
            elif path == "/api/positions":
                self._json(get_positions())
            elif path == "/api/trades":
                self._json(get_trades())
            elif path == "/api/equity-history":
                self._json(get_equity_history())
            elif path == "/api/candles":
                self._json(get_candles())
            else:
                self.send_error(404)
        except Exception as exc:
            self._json({"error": str(exc)}, 500)

    def _html(self, body):
        b = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def _json(self, data, code=200):
        b = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def log_message(self, *_):
        pass


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server = HTTPServer(("localhost", _PORT), Handler)
    url    = f"http://localhost:{_PORT}"
    print(f"SOL Bot Dashboard: {url}  (Ctrl+C to stop)")
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("\nStopped.")
