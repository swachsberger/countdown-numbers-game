import streamlit as st
import streamlit.components.v1 as components
import random
import time

DICE_FACES = {
    1: """
┌─────────┐
│         │
│    ●    │
│         │
└─────────┘""",
    2: """
┌─────────┐
│  ●      │
│         │
│      ●  │
└─────────┘""",
    3: """
┌─────────┐
│  ●      │
│    ●    │
│      ●  │
└─────────┘""",
    4: """
┌─────────┐
│  ●   ●  │
│         │
│  ●   ●  │
└─────────┘""",
    5: """
┌─────────┐
│  ●   ●  │
│    ●    │
│  ●   ●  │
└─────────┘""",
    6: """
┌─────────┐
│  ●   ●  │
│  ●   ●  │
│  ●   ●  │
└─────────┘""",
}

st.set_page_config(page_title="Dice Roller", page_icon="🎲", layout="centered")

st.title("🎲 Dice Roller")
st.markdown("---")

if "die1" not in st.session_state:
    st.session_state.die1 = 1
    st.session_state.die2 = 1
    st.session_state.rolled = False

col1, col_mid, col2 = st.columns([2, 1, 2])

with col1:
    st.markdown("### Die 1")
    face1 = st.empty()
    face1.code(DICE_FACES[st.session_state.die1], language=None)

with col_mid:
    st.markdown("<div style='text-align:center; padding-top: 80px; font-size: 2rem;'>+</div>", unsafe_allow_html=True)

with col2:
    st.markdown("### Die 2")
    face2 = st.empty()
    face2.code(DICE_FACES[st.session_state.die2], language=None)

st.markdown("---")

_, btn_col, _ = st.columns([2, 1, 2])
with btn_col:
    roll = st.button("🎲 Roll!", use_container_width=True, type="primary")

score_area = st.empty()

if roll:
    final1 = random.randint(1, 6)
    final2 = random.randint(1, 6)

    # Inject sound: Web Audio API clicks timed to match the animation ease-out
    components.html("""
    <script>
    (function() {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();

        function playClick(offsetSec, volume) {
            const dur = 0.06;
            const bufSize = Math.floor(ctx.sampleRate * dur);
            const buf = ctx.createBuffer(1, bufSize, ctx.sampleRate);
            const data = buf.getChannelData(0);
            for (let i = 0; i < bufSize; i++) {
                data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufSize * 0.15));
            }

            const src = ctx.createBufferSource();
            src.buffer = buf;

            const filter = ctx.createBiquadFilter();
            filter.type = 'bandpass';
            filter.frequency.value = 900;
            filter.Q.value = 1.5;

            const gain = ctx.createGain();
            gain.gain.value = volume;

            src.connect(filter);
            filter.connect(gain);
            gain.connect(ctx.destination);
            src.start(ctx.currentTime + offsetSec);
        }

        // Mirror the Python ease-out schedule: delay = 0.03 + (i/18)^2 * 0.10
        const frames = 18;
        let t = 0;
        for (let i = 0; i < frames; i++) {
            const delay = 0.03 + Math.pow(i / frames, 2) * 0.10;
            t += delay;
            const isLast = i === frames - 1;
            playClick(t, isLast ? 1.8 : 0.7);
        }
    })();
    </script>
    """, height=0)

    # Animate: start fast, slow down toward the end
    frames = 18
    for i in range(frames):
        r1 = random.randint(1, 6) if i < frames - 1 else final1
        r2 = random.randint(1, 6) if i < frames - 1 else final2
        face1.code(DICE_FACES[r1], language=None)
        face2.code(DICE_FACES[r2], language=None)
        # Ease out: delay grows from 30ms to 130ms
        delay = 0.03 + (i / frames) ** 2 * 0.10
        time.sleep(delay)

    st.session_state.die1 = final1
    st.session_state.die2 = final2
    st.session_state.rolled = True

total = st.session_state.die1 + st.session_state.die2

if st.session_state.rolled:
    if total == 2:
        label = "Snake Eyes! 🐍"
    elif total == 12:
        label = "Boxcars! 🎉"
    elif total == 7 or total == 11:
        label = "Lucky roll! ⭐"
    else:
        label = ""

    score_area.markdown(
        f"<h2 style='text-align:center'>Total: {total} {label}</h2>",
        unsafe_allow_html=True,
    )
else:
    score_area.markdown(
        "<h2 style='text-align:center; color: #888;'>Press Roll to start!</h2>",
        unsafe_allow_html=True,
    )
