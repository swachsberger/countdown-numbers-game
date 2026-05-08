import streamlit as st
import random
import ast
import re

# ─── constants ───────────────────────────────────────────────────────────────
LARGE_POOL = [25, 50, 75, 100]
SMALL_POOL = [1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6, 7, 7, 8, 8, 9, 9, 10, 10]

# ─── game setup ──────────────────────────────────────────────────────────────
def draw_numbers(n_large: int) -> list:
    large_pool = list(LARGE_POOL)
    random.shuffle(large_pool)
    large = large_pool[:n_large]

    small_pool = list(SMALL_POOL)
    random.shuffle(small_pool)
    small = small_pool[: 6 - n_large]

    return sorted(large + small, reverse=True)


def generate_target() -> int:
    return random.randint(100, 999)


def score_for_diff(diff: int) -> int:
    if diff == 0:
        return 10
    if diff <= 5:
        return 7
    if diff <= 10:
        return 5
    return 0


# ─── expression evaluator ────────────────────────────────────────────────────
def _eval_node(node, steps: list) -> int:
    if isinstance(node, ast.Constant):
        v = node.value
        if not isinstance(v, int) or v <= 0:
            raise ValueError(f"'{v}' is not a valid positive-integer tile")
        return v

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, steps)
        right = _eval_node(node.right, steps)

        if isinstance(node.op, ast.Add):
            result, sym = left + right, "+"
        elif isinstance(node.op, ast.Sub):
            result, sym = left - right, "−"
            if result <= 0:
                raise ValueError(
                    f"{left} − {right} = {result}  →  intermediate results must be positive integers"
                )
        elif isinstance(node.op, ast.Mult):
            result, sym = left * right, "×"
        elif isinstance(node.op, ast.Div):
            if right == 0:
                raise ValueError("Division by zero")
            if left % right != 0:
                raise ValueError(
                    f"{left} ÷ {right} = {left/right:.4g}  →  fractions are not allowed"
                )
            result, sym = left // right, "÷"
            if result <= 0:
                raise ValueError(
                    f"{left} ÷ {right} = {result}  →  intermediate results must be positive integers"
                )
        else:
            raise ValueError(
                f"Operator '{type(node.op).__name__}' not allowed — use only +  −  ×  ÷"
            )

        steps.append(f"{left} {sym} {right} = {result}")
        return result

    if isinstance(node, ast.UnaryOp):
        raise ValueError("Unary operators (e.g. −x) are not allowed")

    raise ValueError(f"Unexpected element in expression: {type(node).__name__}")


def validate_and_evaluate(raw: str, available: list):
    """Returns (result, error_msg, steps).  result is None on error."""
    expr = (
        raw.strip()
        .replace("×", "*")
        .replace("÷", "/")
        .replace("x", "*")
        .replace("X", "*")
    )

    if not re.fullmatch(r"[\d\s\+\-\*\/\(\)]+", expr):
        return None, "Only digits, spaces, and +  −  ×  ÷  ( ) are allowed", []

    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        return None, f"Syntax error: {exc.msg}", []

    # Collect all integer literals
    nums_used = []
    for node in ast.walk(tree.body):
        if isinstance(node, ast.Constant):
            if not isinstance(node.value, int):
                return None, f"'{node.value}' is not a whole number", []
            nums_used.append(node.value)

    # Check each literal is in the tile pool (respecting duplicates)
    pool = list(available)
    for n in nums_used:
        if n in pool:
            pool.remove(n)
        else:
            return (
                None,
                f"{n} is not available — either not in your tiles or used more than once",
                [],
            )

    steps: list = []
    try:
        result = _eval_node(tree.body, steps)
    except ValueError as exc:
        return None, str(exc), []

    return result, None, steps


# ─── solver ──────────────────────────────────────────────────────────────────
def solve_countdown(numbers: list, target: int) -> dict:
    best: dict = {"diff": float("inf"), "value": None, "steps": []}

    def recurse(nums: list, steps: list) -> bool:
        for v in nums:
            diff = abs(v - target)
            if diff < best["diff"]:
                best["diff"] = diff
                best["value"] = v
                best["steps"] = list(steps)
                if diff == 0:
                    return True

        if len(nums) < 2:
            return False

        for i in range(len(nums)):
            for j in range(i + 1, len(nums)):
                a, b = nums[i], nums[j]
                rest = [nums[k] for k in range(len(nums)) if k not in (i, j)]

                candidates = [(a + b, f"{a} + {b} = {a + b}")]
                if a > 1 and b > 1:
                    candidates.append((a * b, f"{a} × {b} = {a * b}"))
                if a > b:
                    candidates.append((a - b, f"{a} − {b} = {a - b}"))
                elif b > a:
                    candidates.append((b - a, f"{b} − {a} = {b - a}"))
                if b > 1 and a % b == 0:
                    candidates.append((a // b, f"{a} ÷ {b} = {a // b}"))
                if a > 1 and b % a == 0:
                    candidates.append((b // a, f"{b} ÷ {a} = {b // a}"))

                for res, step in candidates:
                    if res > 0:
                        if recurse(rest + [res], steps + [step]):
                            return True
        return False

    recurse(list(numbers), [])
    return best


# ─── session state init ───────────────────────────────────────────────────────
def _init():
    defaults = {
        "total_score": 0,
        "round_num": 0,
        "numbers": None,
        "target": None,
        "phase": "setup",   # setup | play | result
        "round_result": None,
        "best_solution": None,
        "history": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _start_round(n_large: int):
    st.session_state.numbers = draw_numbers(n_large)
    st.session_state.target = generate_target()
    st.session_state.phase = "play"
    st.session_state.round_result = None
    st.session_state.best_solution = None
    st.session_state.round_num += 1


def _submit(expr: str):
    result, error, steps = validate_and_evaluate(expr, st.session_state.numbers)
    if error:
        st.session_state.round_result = {"error": error}
        return
    diff = abs(result - st.session_state.target)
    pts = score_for_diff(diff)
    st.session_state.total_score += pts
    st.session_state.round_result = {
        "expr": expr, "value": result, "diff": diff,
        "score": pts, "steps": steps, "auto": False,
    }
    st.session_state.history.append(
        {"round": st.session_state.round_num, "target": st.session_state.target,
         "result": result, "diff": diff, "score": pts}
    )
    st.session_state.phase = "result"


def _auto_solve():
    sol = solve_countdown(st.session_state.numbers, st.session_state.target)
    st.session_state.best_solution = sol
    st.session_state.round_result = {
        "value": sol["value"], "diff": sol["diff"],
        "score": 0, "steps": sol["steps"], "auto": True,
    }
    st.session_state.history.append(
        {"round": st.session_state.round_num, "target": st.session_state.target,
         "result": sol["value"], "diff": sol["diff"], "score": 0}
    )
    st.session_state.phase = "result"


# ─── UI components ────────────────────────────────────────────────────────────
TILE_CSS = (
    "display:inline-block;background:{bg};color:{fg};"
    "padding:8px 18px;margin:4px;border-radius:10px;"
    "font-size:26px;font-weight:700;box-shadow:0 3px 6px rgba(0,0,0,.25);"
)

LARGE_COLOR = "#c0392b"
SMALL_COLOR = "#1a5276"


def _tile_html(n: int) -> str:
    bg = LARGE_COLOR if n in LARGE_POOL else SMALL_COLOR
    return f"<span style='{TILE_CSS.format(bg=bg, fg='white')}'>{n}</span>"


def _render_tiles(numbers: list):
    html = " ".join(_tile_html(n) for n in numbers)
    st.markdown(
        f"<div style='text-align:center;margin:10px 0'>{html}</div>",
        unsafe_allow_html=True,
    )


def _render_target(target: int):
    st.markdown(
        f"<div style='text-align:center'>"
        f"<span style='font-size:80px;font-weight:900;color:#c0392b;"
        f"letter-spacing:6px;line-height:1'>{target}</span><br>"
        f"<span style='color:#888;font-size:14px;letter-spacing:3px'>TARGET</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


def _show_working(steps: list, final_value: int = None):
    if not steps:
        if final_value is not None:
            st.info(f"**{final_value}** is one of your tiles — no calculation needed!")
        return
    lines = "\n".join(steps)
    st.code(lines, language=None)


def _show_best_solution(sol: dict, target: int):
    val, diff = sol["value"], sol["diff"]
    if diff == 0:
        st.success(f"✅  Best solution: **{val}** — exact!")
    else:
        st.warning(f"Closest achievable: **{val}** (off by {diff} from {target})")
    _show_working(sol["steps"], val)


# ─── pages ────────────────────────────────────────────────────────────────────
def _page_setup():
    st.markdown("### 🎲 New Round")
    st.markdown(
        "**Large numbers:** 25 · 50 · 75 · 100 &nbsp;|&nbsp; "
        "**Small numbers:** two each of 1–10"
    )
    n_large = st.select_slider(
        "How many large numbers?",
        options=[0, 1, 2, 3, 4],
        value=1,
        format_func=lambda x: f"{x} large / {6-x} small",
    )
    st.caption("You need 6 numbers total.")
    st.write("")
    if st.button("🎲  Draw Numbers!", type="primary", use_container_width=True):
        _start_round(n_large)
        st.rerun()


def _page_play():
    numbers = st.session_state.numbers
    target = st.session_state.target

    _render_target(target)
    st.write("")
    _render_tiles(numbers)
    st.write("")

    st.markdown(
        "Enter your solution using **+  −  ×  ÷** and **(  )**. "
        "Each tile can be used **at most once**. "
        "All intermediate results must be **positive whole numbers**."
    )

    expr = st.text_input(
        "Your expression:",
        placeholder=f"e.g.  75 * 4 + 25 − 3",
        key="play_expr",
    )

    # Show validation error from previous attempt without leaving the play page
    if isinstance(st.session_state.round_result, dict) and st.session_state.round_result.get("error"):
        st.error(f"❌  {st.session_state.round_result['error']}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("✅  Submit Answer", type="primary", use_container_width=True):
            if expr.strip():
                _submit(expr.strip())
                st.rerun()
            else:
                st.warning("Please enter an expression first.")
    with c2:
        if st.button("🤖  Solve It For Me", use_container_width=True):
            with st.spinner("Computing best solution…"):
                _auto_solve()
            st.rerun()

    st.write("")
    if st.button("⏭  Skip this round (0 pts)", use_container_width=True):
        st.session_state.history.append(
            {"round": st.session_state.round_num,
             "target": target, "result": None, "diff": None, "score": 0}
        )
        st.session_state.round_result = {"skipped": True, "score": 0}
        st.session_state.phase = "result"
        st.rerun()


def _page_result():
    numbers = st.session_state.numbers
    target = st.session_state.target
    res = st.session_state.round_result

    _render_target(target)
    st.write("")
    _render_tiles(numbers)
    st.divider()

    if res.get("skipped"):
        st.info("Round skipped — **0 points** awarded.")

    elif res.get("auto"):
        st.info("🤖  Computer solved it — **0 points** (try it yourself next time!)")
        _show_best_solution({"value": res["value"], "diff": res["diff"], "steps": res["steps"]}, target)

    else:
        diff = res["diff"]
        score = res["score"]
        val = res["value"]
        expr_display = res["expr"]

        if diff == 0:
            st.success(f"🎉  **Exact match!**  `{expr_display}` = **{val}**")
            st.balloons()
        elif diff <= 5:
            st.warning(f"⭐  **Very close!**  `{expr_display}` = **{val}**  (off by {diff})")
        elif diff <= 10:
            st.warning(f"🔶  **Not bad!**  `{expr_display}` = **{val}**  (off by {diff})")
        else:
            st.error(f"❌  **Too far.**  `{expr_display}` = **{val}**  (off by {diff})")

        c1, c2 = st.columns(2)
        c1.metric("Points this round", f"+{score}")
        c2.metric("Running total", st.session_state.total_score)

        if res["steps"]:
            with st.expander("📋  See your working"):
                _show_working(res["steps"])

        # Offer best solution when player didn't get it exact
        if diff != 0:
            st.write("")
            if st.button("💡  Show best possible solution"):
                with st.spinner("Searching…"):
                    sol = solve_countdown(numbers, target)
                    st.session_state.best_solution = sol

            if st.session_state.best_solution:
                _show_best_solution(st.session_state.best_solution, target)

    st.divider()

    # History table
    if st.session_state.history:
        with st.expander("📊  Round history"):
            rows = []
            for h in st.session_state.history:
                diff_str = str(h["diff"]) if h["diff"] is not None else "—"
                result_str = str(h["result"]) if h["result"] is not None else "skipped"
                rows.append(
                    f"| {h['round']} | {h['target']} | {result_str} | {diff_str} | {h['score']} |"
                )
            header = "| Round | Target | Your answer | Off by | Pts |\n|---|---|---|---|---|"
            st.markdown(header + "\n" + "\n".join(rows))

    st.write("")
    if st.button("▶  Next Round", type="primary", use_container_width=True):
        st.session_state.phase = "setup"
        st.session_state.round_result = None
        st.session_state.best_solution = None
        st.rerun()


# ─── main ─────────────────────────────────────────────────────────────────────
def main():
    st.set_page_config(page_title="Countdown Numbers", page_icon="🔢", layout="centered")

    st.markdown(
        """
        <style>
        [data-testid="stAppViewContainer"] { background: #0e1117; }
        h1 { letter-spacing: 2px; }
        .stMetric label { font-size: 13px !important; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _init()

    # ── header ──
    st.title("🔢  Countdown Numbers")

    col1, col2, col3 = st.columns(3)
    col1.metric("Round", st.session_state.round_num or "—")
    col2.metric("Total Score", st.session_state.total_score)
    max_pts = st.session_state.round_num * 10
    pct = f"{100 * st.session_state.total_score // max_pts}%" if max_pts else "—"
    col3.metric("Best possible %", pct)

    st.divider()

    # ── route to phase ──
    phase = st.session_state.phase
    if phase == "setup":
        _page_setup()
    elif phase == "play":
        _page_play()
    elif phase == "result":
        _page_result()


if __name__ == "__main__":
    main()
