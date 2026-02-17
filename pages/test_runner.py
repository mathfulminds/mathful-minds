"""
Mathful Minds — Test Runner
Drop this file into a "pages" folder next to your app.py.
It will appear as a page in the Streamlit sidebar.

Folder structure:
    app.py
    tutor.py
    prompt.py
    pages/
        test_runner.py   ← this file
"""

import streamlit as st
import json
import time
import sys
import os

# Make sure we can import from the parent directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import anthropic
from prompt import build_system_prompt, get_level_prompt
from tutor import call_claude, parse_json_response

# ─── Page Config ───
st.set_page_config(page_title="Mathful Minds — Test Runner", page_icon="🧪", layout="wide")

# ─── Styling ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    .stApp { font-family: 'DM Sans', sans-serif; }
    .block-container { max-width: 1100px; }

    .test-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.2rem 1.5rem; border-radius: 14px; margin-bottom: 1.2rem; color: white;
    }
    .test-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; }
    .test-header p { margin: 0.15rem 0 0 0; opacity: 0.7; font-size: 0.85rem; }

    .stat-row { display: flex; gap: 12px; margin: 1rem 0; }
    .stat-box {
        flex: 1; background: white; border: 1px solid #e0e3e8; border-radius: 12px;
        padding: 1rem; text-align: center;
    }
    .stat-box .num { font-size: 1.8rem; font-weight: 700; }
    .stat-box .lbl { font-size: 0.8rem; color: #888; }
    .green { color: #27ae60; }
    .red { color: #e74c3c; }
    .blue { color: #3498db; }
    .orange { color: #e67e22; }

    .problem-box {
        background: #f0f4ff; border: 1px solid #c5d5f0; border-radius: 8px;
        padding: 0.6rem 1rem; font-weight: 500; margin-bottom: 0.5rem;
    }
    .badge {
        display: inline-block; background: #fff3e0; color: #e67e22;
        border: 1px solid #ffcc02; border-radius: 12px;
        padding: 1px 8px; font-size: 0.72rem; font-weight: 600; margin-right: 4px;
    }
    .json-box {
        background: #1a1a2e; color: #a8d8a8; padding: 0.8rem; border-radius: 8px;
        font-family: 'Courier New', monospace; font-size: 0.75rem;
        white-space: pre-wrap; word-wrap: break-word; max-height: 350px; overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# TEST PROBLEMS (22 total)
# ═══════════════════════════════════════
TEST_PROBLEMS = [
    {"num": 1,  "problem": "-8 + 3",
     "cat": "Number Sense", "skill": "Adding integers (different signs)", "badges": []},
    {"num": 2,  "problem": "5 - (-7)",
     "cat": "Number Sense", "skill": "KCO — subtracting negatives", "badges": ["KCO"]},
    {"num": 3,  "problem": "1/2 ÷ 2/3",
     "cat": "Number Sense", "skill": "KCF — fraction division", "badges": ["KCF"]},
    {"num": 4,  "problem": "3/4 + 2/5",
     "cat": "Number Sense", "skill": "Butterfly method — adding unlike fractions", "badges": ["Butterfly"]},
    {"num": 5,  "problem": "-3 × -4 × -2",
     "cat": "Number Sense", "skill": "Multiplying integers — odd negatives", "badges": []},
    {"num": 6,  "problem": "What is the square root of 81?",
     "cat": "Number Sense", "skill": "Roots", "badges": []},
    {"num": 7,  "problem": "Estimate the square root of 45",
     "cat": "Number Sense", "skill": "Estimating irrationals", "badges": []},
    {"num": 8,  "problem": "The ratio of cats to dogs is 3:5. If there are 12 cats, how many dogs?",
     "cat": "Ratios & Proportions", "skill": "Scaling — watch for additive trap", "badges": ["Additive Trap"]},
    {"num": 9,  "problem": "A recipe calls for 2 cups of flour for every 3 cups of sugar. How much flour for 12 cups of sugar?",
     "cat": "Ratios & Proportions", "skill": "Proportional reasoning", "badges": []},
    {"num": 10, "problem": "Solve the proportion: 4/x = 8/14",
     "cat": "Ratios & Proportions", "skill": "Solving proportions", "badges": []},
    {"num": 11, "problem": "Solve: 3x + 5 = -16",
     "cat": "Expressions & Equations", "skill": "Two-step equation", "badges": []},
    {"num": 12, "problem": "Simplify: 4(2x - 3) + 5x",
     "cat": "Expressions & Equations", "skill": "Distributive property + combining like terms", "badges": []},
    {"num": 13, "problem": "Solve: 2x - 7 > 15",
     "cat": "Expressions & Equations", "skill": "Inequality", "badges": []},
    {"num": 14, "problem": "Solve: x/4 + 3 = 10",
     "cat": "Expressions & Equations", "skill": "Equation with fraction", "badges": []},
    {"num": 15, "problem": "Find the area of a triangle with base 10 cm and height 6 cm",
     "cat": "Geometry", "skill": "Area of triangle", "badges": []},
    {"num": 16, "problem": "Find the volume of a cylinder with radius 5 cm and height 12 cm",
     "cat": "Geometry", "skill": "Volume of cylinder (Step 0)", "badges": []},
    {"num": 17, "problem": "Find the area of a circle with diameter 14 inches",
     "cat": "Geometry", "skill": "Area of circle (diameter trap)", "badges": ["Diameter Trap"]},
    {"num": 18, "problem": "A right triangle has legs of 6 and 8. Find the hypotenuse.",
     "cat": "Geometry", "skill": "Pythagorean theorem — hypotenuse", "badges": []},
    {"num": 19, "problem": "A right triangle has a hypotenuse of 13 and a leg of 5. Find the other leg.",
     "cat": "Geometry", "skill": "Pythagorean theorem — leg", "badges": ["Always-Add Error"]},
    {"num": 20, "problem": "Find the mean, median, and mode: 3, 7, 7, 2, 9, 4, 7",
     "cat": "Statistics & Probability", "skill": "Measures of center", "badges": []},
    {"num": 21, "problem": "What is the probability of rolling a 4 on a standard die?",
     "cat": "Statistics & Probability", "skill": "Probability (value-as-probability error)", "badges": ["Value-as-Prob"]},
    {"num": 22, "problem": "You flip a coin and roll a die. What is the probability of getting heads and a 3?",
     "cat": "Statistics & Probability", "skill": "Compound independent probability", "badges": []},
]

LEVEL_INFO = {
    1: {"emoji": "😧", "name": "I am so lost", "type": "Full worked example"},
    2: {"emoji": "😬", "name": "I don't really get it", "type": "Simpler example + MC"},
    3: {"emoji": "🙂", "name": "I'm starting to get it", "type": "MC walkthrough (4 options)"},
    4: {"emoji": "😎", "name": "I got this!", "type": "Open-ended prompt"},
    5: {"emoji": "🤩", "name": "I could teach it!", "type": "Answer check data"},
}


# ═══════════════════════════════════════
# QUALITY CHECKS
# ═══════════════════════════════════════
def run_checks(data, raw_text, level, skill):
    """Return list of (name, passed, detail) tuples."""
    checks = []
    if data is None:
        checks.append(("Valid JSON", False, "Could not parse response"))
        return checks
    checks.append(("Valid JSON", True, ""))

    if level == 1:
        steps = data.get("steps", [])
        checks.append(("Has steps", len(steps) > 0, f"{len(steps)} steps"))
        checks.append(("Step count 3-7", 2 <= len(steps) <= 8, f"{len(steps)}"))
        checks.append(("Has final answer", bool(data.get("final_answer")), str(data.get("final_answer", ""))[:60]))
        checks.append(("Has practice problem", bool(data.get("practice_problem")), str(data.get("practice_problem", ""))[:60]))
        for i, s in enumerate(steps):
            checks.append((f"Step {i+1} has math", bool(s.get("math", "").strip()), ""))
            checks.append((f"Step {i+1} has explanation", bool(s.get("explanation", "").strip()), ""))
        any_vert = any("\n" in s.get("math", "") or "\\n" in s.get("math", "") for s in steps)
        checks.append(("Vertical alignment", any_vert, "Math uses multi-line layout"))

    elif level == 2:
        sim = data.get("simpler_example", {})
        checks.append(("Has simpler example", bool(sim), ""))
        if sim:
            checks.append(("Simpler has steps", len(sim.get("steps", [])) > 0, ""))
            checks.append(("Has bridge sentence", bool(sim.get("bridge")), str(sim.get("bridge", ""))[:60]))
        wt = data.get("walkthrough_steps", [])
        checks.append(("Has walkthrough steps", len(wt) > 0, f"{len(wt)} steps"))
        for i, ws in enumerate(wt):
            n = len(ws.get("options", []))
            checks.append((f"WS {i+1}: 2-3 options", 2 <= n <= 3, f"{n} options"))
            ci = ws.get("correct_index", -1)
            checks.append((f"WS {i+1}: valid correct_index", 0 <= ci < n, f"idx={ci}, n={n}"))
            exps = ws.get("option_explanations", [])
            checks.append((f"WS {i+1}: has explanations", len(exps) == n, f"{len(exps)} exps for {n} opts"))

    elif level == 3:
        wt = data.get("walkthrough_steps", [])
        checks.append(("Has walkthrough steps", len(wt) > 0, f"{len(wt)} steps"))
        for i, ws in enumerate(wt):
            n = len(ws.get("options", []))
            checks.append((f"WS {i+1}: exactly 4 options", n == 4, f"{n} options"))
            ci = ws.get("correct_index", -1)
            checks.append((f"WS {i+1}: valid correct_index", 0 <= ci < n, f"idx={ci}, n={n}"))
            exps = ws.get("option_explanations", [])
            checks.append((f"WS {i+1}: has explanations", len(exps) == n, f"{len(exps)} exps for {n} opts"))

    elif level == 4:
        checks.append(("Has prompt", bool(data.get("prompt")), str(data.get("prompt", ""))[:60]))
        checks.append(("Has expected_keywords", bool(data.get("expected_keywords")), str(data.get("expected_keywords", ""))))
        checks.append(("Has MC fallback", bool(data.get("mc_fallback")), ""))

    elif level == 5:
        checks.append(("Has correct_answer", bool(data.get("correct_answer")), str(data.get("correct_answer", ""))))
        checks.append(("Has acceptable_forms", len(data.get("acceptable_forms", [])) > 0, str(data.get("acceptable_forms", []))))
        checks.append(("Has solution_steps", len(data.get("solution_steps", [])) > 0, ""))

    # Teaching method checks
    raw_lower = (raw_text or json.dumps(data or {})).lower()
    skill_lower = skill.lower()

    if "kco" in skill_lower:
        checks.append(("Uses KCO method", "kco" in raw_lower or ("keep" in raw_lower and "change" in raw_lower), ""))
    if "kcf" in skill_lower:
        checks.append(("Uses KCF method", "kcf" in raw_lower or ("keep" in raw_lower and "flip" in raw_lower), ""))
    if "butterfly" in skill_lower:
        checks.append(("Uses butterfly method", "butterfly" in raw_lower, ""))
    if "additive trap" in skill_lower:
        checks.append(("Emphasizes multiply/scale", "multiply" in raw_lower or "scale" in raw_lower, ""))
    if "diameter" in skill_lower:
        checks.append(("Step 0: radius vs diameter", "radius" in raw_lower and "diameter" in raw_lower, ""))
    if "leg" in skill_lower and "pythagorean" in skill_lower:
        checks.append(("Uses subtraction for leg", "subtract" in raw_lower, ""))
    if "value-as-prob" in skill_lower:
        checks.append(("Lists all outcomes", "outcome" in raw_lower or "list" in raw_lower, ""))

    return checks


# ═══════════════════════════════════════
# HEADER
# ═══════════════════════════════════════
st.markdown("""
<div class="test-header">
    <h1>🧪 Mathful Minds — Test Runner</h1>
    <p>Run your 22 test problems through all 5 levels and see exactly what Claude returns.</p>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# API KEY
# ═══════════════════════════════════════
api_key = ""
try:
    api_key = st.secrets["ANTHROPIC_API_KEY"]
except (KeyError, FileNotFoundError):
    pass

if not api_key:
    api_key = st.text_input("🔑 API Key:", type="password")

if not api_key:
    st.warning("Add your API key to Streamlit Secrets or enter it above.")
    st.stop()


# ═══════════════════════════════════════
# TEST CONFIGURATION
# ═══════════════════════════════════════
st.markdown("### Configure Your Test Run")

col_left, col_right = st.columns(2)

with col_left:
    selected_levels = st.multiselect(
        "Which levels to test:",
        options=[1, 2, 3, 4, 5],
        default=[1, 2, 3, 4, 5],
        format_func=lambda x: f"Level {x} {LEVEL_INFO[x]['emoji']} — {LEVEL_INFO[x]['name']}",
    )

with col_right:
    # Quick-select options
    preset = st.radio(
        "Problem selection:",
        ["All 22 problems", "Misconception traps only (#8, #17, #19, #21)", "Custom"],
        horizontal=True,
    )

if preset == "All 22 problems":
    selected_nums = [p["num"] for p in TEST_PROBLEMS]
elif preset == "Misconception traps only (#8, #17, #19, #21)":
    selected_nums = [8, 17, 19, 21]
else:
    selected_nums = st.multiselect(
        "Pick problems:",
        options=[p["num"] for p in TEST_PROBLEMS],
        default=[1, 8, 11, 17, 19, 21],
        format_func=lambda n: f"#{n} — {next(p['problem'] for p in TEST_PROBLEMS if p['num']==n)[:50]}",
    )

total_calls = len(selected_nums) * len(selected_levels)
st.info(f"**{len(selected_nums)} problems × {len(selected_levels)} levels = {total_calls} API calls** — estimated time: ~{total_calls * 3}–{total_calls * 5} seconds")


# ═══════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════
if "test_results" not in st.session_state:
    st.session_state.test_results = None

if st.button("🚀 **Run Tests**", type="primary", use_container_width=True, disabled=(total_calls == 0)):

    client = anthropic.Anthropic(api_key=api_key)
    system = build_system_prompt()
    selected_problems = [p for p in TEST_PROBLEMS if p["num"] in selected_nums]

    results = []
    progress_bar = st.progress(0, text="Starting tests...")
    status_area = st.empty()
    count = 0

    for prob in selected_problems:
        for level in selected_levels:
            count += 1
            progress_bar.progress(
                count / total_calls,
                text=f"[{count}/{total_calls}] Problem #{prob['num']} @ Level {level}..."
            )

            # Build prompt
            try:
                if level == 1:
                    prompt = get_level_prompt(1, prob["problem"])
                elif level == 2:
                    prompt = get_level_prompt(2, prob["problem"], num_options=3)
                elif level == 3:
                    prompt = get_level_prompt(3, prob["problem"], num_options=4)
                elif level == 4:
                    prompt = get_level_prompt(4, prob["problem"], step_history=[])
                elif level == 5:
                    prompt = get_level_prompt(5, prob["problem"])

                start = time.time()
                raw = call_claude(client, system, prompt)
                elapsed = round(time.time() - start, 2)

                data = parse_json_response(raw)
                error = None
            except json.JSONDecodeError as e:
                data = None
                error = f"JSON parse error: {e}"
                elapsed = round(time.time() - start, 2)
            except Exception as e:
                data = None
                raw = ""
                error = str(e)
                elapsed = 0

            results.append({
                "num": prob["num"],
                "problem": prob["problem"],
                "cat": prob["cat"],
                "skill": prob["skill"],
                "badges": prob["badges"],
                "level": level,
                "data": data,
                "raw": raw if 'raw' in dir() else "",
                "error": error,
                "elapsed": elapsed,
            })

            # Small delay to be nice to the API
            time.sleep(0.5)

    progress_bar.progress(1.0, text="✅ Done!")
    st.session_state.test_results = results
    st.rerun()


# ═══════════════════════════════════════
# DISPLAY RESULTS
# ═══════════════════════════════════════
if st.session_state.test_results:
    results = st.session_state.test_results

    # Summary stats
    total = len(results)
    passed_json = sum(1 for r in results if r["data"] is not None)
    failed_json = total - passed_json
    all_checks_flat = []
    for r in results:
        checks = run_checks(r["data"], r.get("raw", ""), r["level"], r["skill"])
        all_checks_flat.extend(checks)
    total_checks = len(all_checks_flat)
    passed_checks = sum(1 for _, ok, _ in all_checks_flat if ok)
    avg_time = round(sum(r["elapsed"] for r in results) / max(total, 1), 1)

    st.markdown("---")
    st.markdown("### Results Summary")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Tests", total)
    c2.metric("✅ Valid JSON", passed_json)
    c3.metric("❌ Failed", failed_json)
    c4.metric("Quality Checks", f"{passed_checks}/{total_checks}")

    st.markdown("---")

    # Clear button
    if st.button("🗑️ Clear results and run again"):
        st.session_state.test_results = None
        st.rerun()

    # Group by problem
    st.markdown("### Detailed Results")

    current_cat = None
    for prob in TEST_PROBLEMS:
        prob_results = [r for r in results if r["num"] == prob["num"]]
        if not prob_results:
            continue

        # Category header
        if prob["cat"] != current_cat:
            current_cat = prob["cat"]
            st.markdown(f"#### {current_cat}")

        # Badge HTML
        badge_html = " ".join(f'<span class="badge">{b}</span>' for b in prob.get("badges", []))

        with st.expander(f"**#{prob['num']}** — {prob['problem'][:60]}{'...' if len(prob['problem'])>60 else ''}"):
            st.markdown(f'<div class="problem-box">📝 {prob["problem"]}</div>', unsafe_allow_html=True)
            st.markdown(f"**Skill:** {prob['skill']} {badge_html}", unsafe_allow_html=True)

            # Tab per level
            level_tabs = st.tabs([
                f"L{r['level']} {LEVEL_INFO[r['level']]['emoji']}"
                for r in prob_results
            ])

            for tab, r in zip(level_tabs, prob_results):
                with tab:
                    li = LEVEL_INFO[r["level"]]

                    # Status
                    if r["data"] is not None:
                        st.success(f"✅ Valid response — {r['elapsed']}s")
                    else:
                        st.error(f"❌ Failed — {r.get('error', 'Unknown error')}")

                    st.caption(f"{li['emoji']} Level {r['level']}: {li['name']} — {li['type']}")

                    # Quality checks
                    checks = run_checks(r["data"], r.get("raw", ""), r["level"], r["skill"])

                    st.markdown("**Quality Checks:**")
                    for check_name, ok, detail in checks:
                        icon = "✅" if ok else "❌"
                        detail_str = f" — {detail}" if detail else ""
                        st.markdown(f"&nbsp;&nbsp;{icon} {check_name}{detail_str}")

                    # JSON response
                    if r["data"]:
                        with st.expander("📄 View JSON response"):
                            st.json(r["data"])
                    elif r.get("raw"):
                        with st.expander("📄 View raw response (failed to parse)"):
                            st.code(r["raw"], language="text")

    # ─── Download raw JSON ───
    st.markdown("---")
    st.markdown("### Export")
    download_data = json.dumps(
        [{k: v for k, v in r.items() if k != "raw"} for r in results],
        indent=2, ensure_ascii=False, default=str,
    )
    st.download_button(
        "⬇️ Download full results as JSON",
        data=download_data,
        file_name="mathful_minds_test_results.json",
        mime="application/json",
    )

else:
    st.markdown("---")
    st.markdown("*Configure your options above and hit **Run Tests** to get started.*")

    # Show the 22 problems for reference
    with st.expander("📋 View all 22 test problems"):
        for p in TEST_PROBLEMS:
            badges = " ".join(f'`{b}`' for b in p.get("badges", []))
            st.markdown(f"**#{p['num']}** — {p['problem']}  \n*{p['skill']}* {badges}")
