import os
import time
from fasthtml.common import *

# NOTE: This app uses in-memory state.
# For Cloud Run, deploy with --max-instances=1 to ensure state consistency.
# For multi-instance setups, replace GameState with Firestore or Redis.

# ── State ─────────────────────────────────────────────────────────────────────

class GameState:
    def __init__(self):
        self.users: list[str] = []
        self.buzzes: list[tuple[str, float]] = []  # (name, timestamp)
        self.game_active: bool = False
        self.points: dict[str, int] = {}

    def setup(self, names: list[str]):
        new_users = [n.strip() for n in names if n.strip()][:5]
        # Preserve points for players whose names are kept
        self.points = {name: self.points.get(name, 0) for name in new_users}
        self.users = new_users
        self.buzzes = []
        self.game_active = False

    def start(self):
        self.buzzes = []
        self.game_active = True

    def reset(self):
        self.buzzes = []
        self.game_active = False

    def buzz(self, name: str) -> bool:
        if not self.game_active or name not in self.users:
            return False
        if any(b[0] == name for b in self.buzzes):
            return False
        self.buzzes.append((name, time.time()))
        return True

    def adjust_points(self, name: str, delta: int):
        if name in self.users:
            self.points[name] = max(0, self.points.get(name, 0) + delta)


state = GameState()

# ── App ───────────────────────────────────────────────────────────────────────

app, rt = fast_app(live=False)

# ── CSS ───────────────────────────────────────────────────────────────────────

ADMIN_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
:root {
    --bg:      #0f0f1a;
    --surface: #1a1a2e;
    --border:  #2a2a4a;
    --text:    #e0e0f0;
    --muted:   #8888aa;
    --red:     #e04444;
    --green:   #00c878;
    --gold:    #ffd700;
    --silver:  #b0b0b0;
    --bronze:  #cd7f32;
}
body {
    background: var(--bg);
    color: var(--text);
    font-family: system-ui, -apple-system, sans-serif;
    min-height: 100vh;
    padding: 2rem 1rem;
}
main { max-width: 640px; margin: 0 auto; }
h1 {
    font-size: 1.8rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 1.75rem;
}
h2 {
    font-size: 0.75rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 1rem;
}
.card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
}
.setup-form {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}
label {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.label-txt {
    width: 72px;
    font-size: 0.8rem;
    color: var(--muted);
    flex-shrink: 0;
}
input[type="text"] {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    color: var(--text);
    padding: 0.45rem 0.75rem;
    font-size: 0.95rem;
    outline: none;
    transition: border-color 0.15s;
}
input[type="text"]:focus { border-color: var(--red); }
.btn {
    cursor: pointer;
    border: none;
    border-radius: 6px;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    padding: 0.55rem 1.1rem;
    text-transform: uppercase;
    transition: opacity 0.15s, transform 0.1s;
    margin-top: 0.75rem;
}
.btn:active { transform: scale(0.97); }
.btn-red   { background: var(--red);   color: #fff; }
.btn-green { background: var(--green); color: #000; margin-top: 0; }
.btn-grey  { background: var(--border); color: var(--text); margin-top: 0; }
.btn:hover { opacity: 0.85; }
.controls { display: flex; gap: 0.75rem; margin-bottom: 1rem; }
.controls .btn { flex: 1; }
.player-links { list-style: none; display: flex; flex-direction: column; gap: 0.45rem; }
.player-links li { display: flex; align-items: baseline; gap: 0.6rem; font-size: 0.9rem; }
.player-name { font-weight: 600; min-width: 80px; }
.player-links a { color: #6ab0ff; text-decoration: none; font-size: 0.82rem; word-break: break-all; }
.player-links a:hover { text-decoration: underline; }
.badge {
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
}
.badge-green { background: rgba(0,200,120,0.15); color: var(--green); border: 1px solid var(--green); }
.badge-grey  { background: rgba(136,136,170,0.1); color: var(--muted); border: 1px solid var(--border); }
.lb-table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.lb-table th {
    text-align: left;
    color: var(--muted);
    font-size: 0.7rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    padding: 0.2rem 0.5rem 0.5rem;
    border-bottom: 1px solid var(--border);
}
.lb-table td { padding: 0.45rem 0.5rem; }
.lb-table td:last-child { text-align: right; color: var(--muted); font-size: 0.85rem; font-variant-numeric: tabular-nums; }
.rank-1 td { color: var(--gold);   font-weight: 700; }
.rank-2 td { color: var(--silver); }
.rank-3 td { color: var(--bronze); }
.pending td { color: #33334a; }
.muted { color: var(--muted); font-size: 0.9rem; }
.td-pts { text-align: right; font-variant-numeric: tabular-nums; font-weight: 600; }
/* Points section */
.pts-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.65rem 0;
    border-bottom: 1px solid var(--border);
}
.pts-row:last-child { border-bottom: none; }
.pts-name { font-weight: 600; font-size: 0.95rem; flex: 1; }
.pts-controls { display: flex; align-items: center; gap: 0.5rem; }
.pts-value { font-size: 1.5rem; font-weight: 700; min-width: 2.2rem; text-align: right; font-variant-numeric: tabular-nums; }
.pts-label { font-size: 0.7rem; color: var(--muted); margin-right: 0.4rem; align-self: flex-end; padding-bottom: 0.2rem; }
.btn-pts {
    width: 44px;
    height: 44px;
    border-radius: 8px;
    border: none;
    font-size: 1.4rem;
    font-weight: 700;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    line-height: 1;
    transition: opacity 0.15s, transform 0.1s;
}
.btn-pts:active { transform: scale(0.93); }
.btn-inc { background: var(--green); color: #000; }
.btn-dec { background: var(--border); color: var(--text); }
.btn-pts:hover { opacity: 0.85; }
"""

USER_CSS = """
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body {
    background: #1a1a2e;
    color: #e0e0f0;
    font-family: system-ui, -apple-system, sans-serif;
    min-height: 100vh;
    display: flex;
    justify-content: center;
    align-items: center;
}
main {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.5rem;
    padding: 2rem;
    text-align: center;
}
h1 {
    font-size: 2rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}
#buzzer-ui {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1.25rem;
}
.buzzer-btn {
    width: 200px;
    height: 200px;
    border-radius: 50%;
    border: none;
    font-size: 1.2rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    outline: none;
    transition: transform 0.1s, box-shadow 0.1s;
}
.buzzer-btn.active {
    background: radial-gradient(circle at 35% 35%, #ff4444, #cc0000);
    box-shadow: 0 8px 0 #660000, 0 12px 24px rgba(0,0,0,0.5);
    color: #fff;
    cursor: pointer;
}
.buzzer-btn.active:hover {
    background: radial-gradient(circle at 35% 35%, #ff6666, #ee1111);
}
.buzzer-btn.active:active {
    transform: translateY(6px);
    box-shadow: 0 2px 0 #660000, 0 4px 10px rgba(0,0,0,0.4);
}
.buzzer-btn.waiting {
    background: radial-gradient(circle at 35% 35%, #555566, #333344);
    box-shadow: 0 8px 0 #111122, 0 12px 20px rgba(0,0,0,0.4);
    color: #55556a;
    cursor: not-allowed;
}
.buzzer-btn.buzzed-first {
    background: radial-gradient(circle at 35% 35%, #ffe040, #cc9900);
    box-shadow: 0 8px 0 #886600, 0 12px 24px rgba(0,0,0,0.5);
    color: #fff;
    cursor: default;
}
.buzzer-btn.buzzed-late {
    background: radial-gradient(circle at 35% 35%, #00e090, #00aa66);
    box-shadow: 0 8px 0 #005533, 0 12px 24px rgba(0,0,0,0.5);
    color: #fff;
    cursor: default;
}
.buzz-msg { font-size: 0.95rem; color: #8888aa; }
.buzz-msg.live { color: #00e090; font-weight: 700; letter-spacing: 0.05em; }
.buzz-msg.gold { color: #ffd700; font-size: 1.1rem; font-weight: 700; }
.error { color: #e04444; }
"""

# ── Sound JS ──────────────────────────────────────────────────────────────────

BUZZ_SOUND_JS = """
// Default buzzer
function playBuzz() {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    var ctx = new AC();
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(120, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(60, ctx.currentTime + 0.3);
    gain.gain.setValueAtTime(0.7, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.4);
}

// Duck quack: sawtooth through a bandpass filter that sweeps high→low ("wah")
function playDuck() {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    var ctx = new AC();
    var t = ctx.currentTime;
    var osc = ctx.createOscillator();
    var filter = ctx.createBiquadFilter();
    var gain = ctx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(370, t);
    osc.frequency.linearRampToValueAtTime(330, t + 0.20);
    filter.type = 'bandpass';
    filter.Q.value = 5;
    filter.frequency.setValueAtTime(1900, t);
    filter.frequency.exponentialRampToValueAtTime(580, t + 0.13);
    filter.frequency.exponentialRampToValueAtTime(850, t + 0.22);
    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.55, t + 0.015);
    gain.gain.setValueAtTime(0.55, t + 0.16);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.24);
    osc.connect(filter);
    filter.connect(gain);
    gain.connect(ctx.destination);
    osc.start(t);
    osc.stop(t + 0.27);
}

// Frog ribbit: two short square-wave chirps ("rib" + "bit"), each falling in pitch
function playFrog() {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    var ctx = new AC();
    var t = ctx.currentTime;
    function chirp(st, freq, dur, amp) {
        var osc = ctx.createOscillator();
        var gain = ctx.createGain();
        osc.type = 'square';
        osc.frequency.setValueAtTime(freq, st);
        osc.frequency.exponentialRampToValueAtTime(freq * 0.82, st + dur);
        gain.gain.setValueAtTime(0, st);
        gain.gain.linearRampToValueAtTime(amp, st + 0.01);
        gain.gain.setValueAtTime(amp, st + dur * 0.7);
        gain.gain.exponentialRampToValueAtTime(0.001, st + dur + 0.03);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(st);
        osc.stop(st + dur + 0.05);
    }
    chirp(t + 0.00, 900, 0.08, 0.30);  // "rib"
    chirp(t + 0.13, 680, 0.13, 0.35);  // "bit"
}

// Cow moo: low sawtooth ~150 Hz with slow pitch arc and vibrato
function playCow() {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    var ctx = new AC();
    var t = ctx.currentTime;
    var osc = ctx.createOscillator();
    var vibrato = ctx.createOscillator();
    var vibratoGain = ctx.createGain();
    var gain = ctx.createGain();
    osc.type = 'sawtooth';
    osc.frequency.setValueAtTime(145, t);
    osc.frequency.linearRampToValueAtTime(165, t + 0.12);
    osc.frequency.setValueAtTime(165, t + 0.35);
    osc.frequency.linearRampToValueAtTime(135, t + 0.80);
    vibrato.type = 'sine';
    vibrato.frequency.value = 5;
    vibratoGain.gain.value = 7;
    vibrato.connect(vibratoGain);
    vibratoGain.connect(osc.frequency);
    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.40, t + 0.09);
    gain.gain.setValueAtTime(0.40, t + 0.60);
    gain.gain.exponentialRampToValueAtTime(0.001, t + 0.88);
    osc.connect(gain);
    gain.connect(ctx.destination);
    vibrato.start(t); osc.start(t);
    vibrato.stop(t + 0.92); osc.stop(t + 0.92);
}

// Horn: two sawtooth oscillators (classic klaxon chord)
function playHorn() {
    var AC = window.AudioContext || window.webkitAudioContext;
    if (!AC) return;
    var ctx = new AC();
    var master = ctx.createGain();
    master.connect(ctx.destination);
    master.gain.setValueAtTime(0, ctx.currentTime);
    master.gain.linearRampToValueAtTime(0.35, ctx.currentTime + 0.02);
    master.gain.setValueAtTime(0.35, ctx.currentTime + 0.45);
    master.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
    [466, 349].forEach(function(freq) {   // Bb4 + F4
        var osc = ctx.createOscillator();
        osc.type = 'sawtooth';
        osc.frequency.value = freq;
        osc.connect(master);
        osc.start(ctx.currentTime);
        osc.stop(ctx.currentTime + 0.65);
    });
}
"""

# Maps user position → sound function name
_SOUND_FNS = ["playCow", "playHorn", "playDuck", "playFrog", "playBuzz"]

def get_sound_fn(name: str) -> str:
    if name not in state.users:
        return "playBuzz"
    return _SOUND_FNS[min(state.users.index(name), len(_SOUND_FNS) - 1)]

# ── Admin components ──────────────────────────────────────────────────────────

def leaderboard_div():
    if not state.users:
        inner = P("No players configured yet.", cls="muted")
    else:
        status_cls = "badge-green" if state.game_active else "badge-grey"
        status_txt = "Round Active" if state.game_active else "Waiting"

        rows = []
        for i, (name, ts) in enumerate(state.buzzes):
            medals = ("🥇", "🥈", "🥉")
            medal = medals[i] if i < 3 else f"#{i + 1}"
            delay = "WINNER" if i == 0 else f"+{ts - state.buzzes[0][1]:.3f}s"
            pts = state.points.get(name, 0)
            rows.append(Tr(Td(medal), Td(name), Td(str(pts), cls="td-pts"), Td(delay), cls=f"rank-{i + 1}"))

        pending = [u for u in state.users if not any(b[0] == u for b in state.buzzes)]
        for name in pending:
            pts = state.points.get(name, 0)
            rows.append(Tr(Td("—"), Td(name), Td(str(pts), cls="td-pts"), Td("—"), cls="pending"))

        inner = Div(
            Span(status_txt, cls=f"badge {status_cls}"),
            Table(
                Thead(Tr(Th(""), Th("Player"), Th("Pts"), Th("Time"))),
                Tbody(*rows),
                cls="lb-table",
            ),
        )

    return Div(
        H2("Leaderboard"),
        inner,
        id="leaderboard",
        hx_get="/admin/leaderboard",
        hx_trigger="every 1s",
        hx_swap="outerHTML",
        cls="card",
    )


def points_div():
    if not state.users:
        return Div(id="points-section")

    rows = [
        Div(
            Span(name, cls="pts-name"),
            Div(
                Span(str(state.points.get(name, 0)), cls="pts-value"),
                Span("pts", cls="pts-label"),
                Button("−",
                       hx_post=f"/admin/points/{name}/dec",
                       hx_target="#points-section",
                       hx_swap="outerHTML",
                       cls="btn-pts btn-dec"),
                Button("+",
                       hx_post=f"/admin/points/{name}/inc",
                       hx_target="#points-section",
                       hx_swap="outerHTML",
                       cls="btn-pts btn-inc"),
                cls="pts-controls",
            ),
            cls="pts-row",
        )
        for name in state.users
    ]

    return Div(
        H2("Points"),
        *rows,
        id="points-section",
        cls="card",
    )


def game_section(base_url: str = ""):
    if not state.users:
        return Div(id="game-section")

    links = [
        Li(
            Span(name, cls="player-name"),
            A(f"{base_url}/user/{name}", href=f"/user/{name}", target="_blank"),
        )
        for name in state.users
    ]

    return Div(
        Div(H2("Player Links"), Ul(*links, cls="player-links"), cls="card"),
        Div(
            Button("▶ Start Round",
                   hx_post="/admin/start",
                   hx_target="#leaderboard",
                   hx_swap="outerHTML",
                   cls="btn btn-green"),
            Button("↺ Reset",
                   hx_post="/admin/reset",
                   hx_target="#leaderboard",
                   hx_swap="outerHTML",
                   cls="btn btn-grey"),
            cls="controls",
        ),
        leaderboard_div(),
        points_div(),
        id="game-section",
    )


# ── User components ───────────────────────────────────────────────────────────

def buzzer_ui(name: str):
    if name not in state.users:
        return Div(P("Unknown player. Check your link.", cls="error"), id="buzzer-ui")

    already_buzzed = any(b[0] == name for b in state.buzzes)

    if already_buzzed:
        rank = next(i + 1 for i, b in enumerate(state.buzzes) if b[0] == name)
        if rank == 1:
            btn_cls, msg, msg_cls = "buzzer-btn buzzed-first", "You were FIRST! 🏆", "buzz-msg gold"
        else:
            delay = state.buzzes[rank - 1][1] - state.buzzes[0][1]
            btn_cls = "buzzer-btn buzzed-late"
            msg = f"#{rank} place — {delay:.3f}s after the winner"
            msg_cls = "buzz-msg"
        return Div(
            Button("BUZZED!", disabled=True, cls=btn_cls),
            P(msg, cls=msg_cls),
            id="buzzer-ui",
            hx_get=f"/user/{name}/status",
            hx_trigger="every 2s",
            hx_swap="outerHTML",
        )

    if state.game_active:
        return Div(
            Button("BUZZ",
                   cls="buzzer-btn active",
                   hx_post=f"/buzz/{name}",
                   hx_target="#buzzer-ui",
                   hx_swap="outerHTML",
                   onclick=f"{get_sound_fn(name)}()"),
            P("Round is LIVE — HIT IT!", cls="buzz-msg live"),
            id="buzzer-ui",
            hx_get=f"/user/{name}/status",
            hx_trigger="every 1s",
            hx_swap="outerHTML",
        )

    return Div(
        Button("BUZZ", disabled=True, cls="buzzer-btn waiting"),
        P("Waiting for round to start…", cls="buzz-msg"),
        id="buzzer-ui",
        hx_get=f"/user/{name}/status",
        hx_trigger="every 1s",
        hx_swap="outerHTML",
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_base_url(req) -> str:
    # Handles Cloud Run's reverse proxy headers
    host = req.headers.get("x-forwarded-host") or req.headers.get("host") or req.url.netloc
    scheme = req.headers.get("x-forwarded-proto") or req.url.scheme
    return f"{scheme}://{host}"


# ── Routes ────────────────────────────────────────────────────────────────────

@rt("/")
def get():
    return RedirectResponse("/admin")


@rt("/admin")
def get(req):
    base_url = get_base_url(req)
    cur = state.users
    inputs = [
        Label(
            Span(f"Player {i + 1}", cls="label-txt"),
            Input(
                type="text", name="names",
                placeholder=f"Player {i + 1}",
                value=cur[i] if i < len(cur) else "",
                maxlength=30,
            ),
        )
        for i in range(5)
    ]
    return Html(
        Head(
            Title("Buzzer – Admin"),
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            htmxsrc, fhjsscr,
            Style(ADMIN_CSS),
        ),
        Body(
            Main(
                H1("Admin Panel"),
                Div(
                    H2("Setup Players"),
                    Form(
                        *inputs,
                        Button("Save Players", type="submit", cls="btn btn-red"),
                        hx_post="/admin/setup",
                        hx_target="#game-section",
                        hx_swap="outerHTML",
                        cls="setup-form",
                    ),
                    cls="card",
                ),
                game_section(base_url),
            )
        ),
    )


@rt("/admin/setup")
async def post(req):
    form = await req.form()
    names = list(form.getlist("names"))
    state.setup(names)
    return game_section(get_base_url(req))


@rt("/admin/start")
def post():
    if state.users:
        state.start()
    return leaderboard_div()


@rt("/admin/reset")
def post():
    state.reset()
    return leaderboard_div()


@rt("/admin/leaderboard")
def get():
    return leaderboard_div()


@rt("/user/{name}")
def get(name: str):
    return Html(
        Head(
            Title(f"Buzzer – {name}"),
            Meta(charset="utf-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1"),
            htmxsrc, fhjsscr,
            Style(USER_CSS),
            Script(BUZZ_SOUND_JS),
        ),
        Body(
            Main(
                H1(name),
                buzzer_ui(name),
            )
        ),
    )


@rt("/user/{name}/status")
def get(name: str):
    return buzzer_ui(name)


@rt("/buzz/{name}")
def post(name: str):
    state.buzz(name)
    return buzzer_ui(name)


@rt("/admin/points/{name}/inc")
def post(name: str):
    state.adjust_points(name, 1)
    return points_div()


@rt("/admin/points/{name}/dec")
def post(name: str):
    state.adjust_points(name, -1)
    return points_div()


# ── Entry point ───────────────────────────────────────────────────────────────

port = int(os.environ.get("PORT", 8080))
serve(host="0.0.0.0", port=port, reload=False)
