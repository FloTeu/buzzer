from fasthtml.common import *

app, rt = fast_app(live=True)

buzzer_sound_js = """
function playBuzzerSound() {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioContext();

    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);

    oscillator.type = 'sawtooth';
    oscillator.frequency.setValueAtTime(120, ctx.currentTime);
    oscillator.frequency.exponentialRampToValueAtTime(60, ctx.currentTime + 0.3);

    gainNode.gain.setValueAtTime(0.8, ctx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);

    oscillator.start(ctx.currentTime);
    oscillator.stop(ctx.currentTime + 0.4);

    const btn = document.getElementById('buzzer-btn');
    btn.classList.add('pressed');
    setTimeout(() => btn.classList.remove('pressed'), 300);
}
"""

buzzer_css = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    background: #1a1a2e;
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    font-family: sans-serif;
}

.buzzer-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2rem;
}

h1 {
    color: #e0e0e0;
    font-size: 2rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
}

#buzzer-btn {
    width: 200px;
    height: 200px;
    border-radius: 50%;
    background: radial-gradient(circle at 35% 35%, #ff4444, #cc0000);
    border: 8px solid #880000;
    box-shadow: 0 8px 0 #660000, 0 12px 20px rgba(0,0,0,0.5);
    cursor: pointer;
    transition: transform 0.1s, box-shadow 0.1s;
    outline: none;
    color: white;
    font-size: 1.1rem;
    font-weight: bold;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}

#buzzer-btn:hover {
    background: radial-gradient(circle at 35% 35%, #ff6666, #ee1111);
}

#buzzer-btn.pressed {
    transform: translateY(6px);
    box-shadow: 0 2px 0 #660000, 0 4px 10px rgba(0,0,0,0.5);
}

#buzzer-btn:active {
    transform: translateY(6px);
    box-shadow: 0 2px 0 #660000, 0 4px 10px rgba(0,0,0,0.5);
}
"""


@rt("/")
def get():
    return Html(
        Head(
            Title("Buzzer"),
            Style(buzzer_css),
        ),
        Body(
            Div(
                H1("Buzzer"),
                Button(
                    "BUZZ",
                    id="buzzer-btn",
                    onclick="playBuzzerSound()",
                ),
                cls="buzzer-container",
            ),
            Script(buzzer_sound_js),
        ),
    )


serve()
