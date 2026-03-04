"""
Mathful Minds — Test Runner (PSSA Gap Focus)
Run targeted tests on new teaching methods added from PSSA analysis.
Deploy to Streamlit Cloud alongside app.py.
"""

import streamlit as st
import anthropic
import json
import time
import re
from prompt import build_system_prompt, get_level_prompt

st.set_page_config(page_title="Test Runner", page_icon="🧪", layout="wide")
st.title("🧪 Mathful Minds — Test Runner")
st.caption("Automated testing across confidence levels")

# ── API Key ──
api_key = st.secrets.get("ANTHROPIC_API_KEY", "")
if not api_key:
    api_key = st.text_input("Anthropic API Key", type="password")
if not api_key:
    st.warning("Enter your API key to run tests.")
    st.stop()

# ── Test Problems ──
PSSA_GAP_PROBLEMS = [
    {
        "id": "PSSA-1",
        "problem": "Convert 0.363636... (repeating) to a fraction in simplest form.",
        "skill": "Convert repeating decimals to fractions (ID 246)",
        "method": "10x Method",
        "expected_answer": "4/11",
        "category": "Number Sense",
    },
    {
        "id": "PSSA-2",
        "problem": "Which is greater: 5√7 or 7√5? Show your work.",
        "skill": "Estimate irrational numbers / Compare (ID 21)",
        "method": "Estimate and Compare",
        "expected_answer": "7√5",
        "category": "Number Sense",
    },
    {
        "id": "PSSA-3",
        "problem": "A store sells 3 shirts for $24. Another store sells 5 shirts for $40. A student says the second store is a better deal because you save $16 more by buying 5 shirts. Is the student's reasoning correct? Explain why or why not.",
        "skill": "Proportional reasoning: multiplicative vs additive (ID 33)",
        "method": "Proportional vs Additive Reasoning",
        "expected_answer": "Both stores charge $8 per shirt — same rate",
        "category": "Ratios & Proportions",
    },
    {
        "id": "PSSA-4",
        "problem": "A data set contains the values: 12, 15, 13, 14, 85. Should you use the mean or the median to describe the center of this data? Explain your choice.",
        "skill": "Choosing measure of center (ID 225)",
        "method": "The Outlier Check",
        "expected_answer": "Median, because 85 is an outlier",
        "category": "Statistics & Probability",
    },
    {
        "id": "PSSA-5",
        "problem": "Find the mean absolute deviation (MAD) of the data set: 4, 8, 6, 2, 10.",
        "skill": "Mean absolute deviation (ID 227)",
        "method": "4-Step MAD",
        "expected_answer": "2.4",
        "category": "Statistics & Probability",
    },
    {
        "id": "PSSA-6",
        "problem": "A triangle has sides of length 5 cm, 5 cm, and 7 cm. All of its angles are less than 90 degrees. Classify this triangle by its sides AND by its angles.",
        "skill": "Classify triangles by sides and angles (ID 247)",
        "method": "Two-Question Sort",
        "expected_answer": "Isosceles acute triangle",
        "category": "Geometry",
    },
]

ORIGINAL_PROBLEMS = [
    {"id": "OG-1", "problem": "Solve: -5 + 3", "skill": "Add integers", "category": "Number Sense"},
    {"id": "OG-2", "problem": "Solve: 5 - (-7)", "skill": "Subtract integers (KCO)", "category": "Number Sense"},
    {"id": "OG-3", "problem": "Solve: 2/3 ÷ 4/5", "skill": "Divide fractions (KCF)", "category": "Number Sense"},
    {"id": "OG-4", "problem": "Solve: 1/3 + 2/5", "skill": "Add fractions (butterfly)", "category": "Number Sense"},
    {"id": "OG-5", "problem": "What is the square root of 144?", "skill": "Square roots", "category": "Number Sense"},
    {"id": "OG-6", "problem": "Order from least to greatest: -3, 1, -7, 4, 0", "skill": "Compare/order integers", "category": "Number Sense"},
    {"id": "OG-7", "problem": "Simplify: -2 x 3 x (-4)", "skill": "Multiply integers", "category": "Number Sense"},
    {"id": "OG-8", "problem": "If the ratio of dogs to cats is 3:5 and there are 9 dogs, how many cats are there?", "skill": "Ratios (additive trap)", "category": "Ratios & Proportions"},
    {"id": "OG-9", "problem": "Solve for x: 3x + 5 = -16", "skill": "Two-step equations", "category": "Equations"},
    {"id": "OG-10", "problem": "Solve for x: 2(x - 4) = 10", "skill": "Two-step equations (distributive)", "category": "Equations"},
    {"id": "OG-11", "problem": "Solve: 5x - 3 > 12", "skill": "Inequalities", "category": "Equations"},
    {"id": "OG-12", "problem": "A shirt costs $40 and is 25% off. What is the sale price?", "skill": "Percent discount", "category": "Ratios & Proportions"},
    {"id": "OG-13", "problem": "Find the slope of the line passing through (2, 3) and (6, 11).", "skill": "Slope from two points", "category": "Equations"},
    {"id": "OG-14", "problem": "Write the equation of a line with slope 3 and y-intercept -2.", "skill": "Slope-intercept form", "category": "Equations"},
    {"id": "OG-15", "problem": "Find the area of a triangle with base 10 cm and height 6 cm.", "skill": "Area of triangles", "category": "Geometry"},
    {"id": "OG-16", "problem": "Find the volume of a rectangular prism with length 5 in, width 3 in, and height 8 in.", "skill": "Volume of rectangular prism", "category": "Geometry"},
    {"id": "OG-17", "problem": "A circle has a diameter of 10 cm. Find its area. Use pi = 3.14.", "skill": "Area of circles (diameter trap)", "category": "Geometry"},
    {"id": "OG-18", "problem": "A right triangle has legs of length 6 and 8. Find the hypotenuse.", "skill": "Pythagorean theorem (hypotenuse)", "category": "Geometry"},
    {"id": "OG-19", "problem": "A right triangle has a hypotenuse of 13 and one leg of 5. Find the other leg.", "skill": "Pythagorean theorem (leg)", "category": "Geometry"},
    {"id": "OG-20", "problem": "Find the median of: 12, 5, 8, 3, 15, 9, 7", "skill": "Median", "category": "Statistics"},
    {"id": "OG-21", "problem": "A bag has 3 red, 2 blue, and 5 green marbles. What is the probability of drawing a blue marble?", "skill": "Probability", "category": "Statistics"},
    {"id": "OG-22", "problem": "Solve the system: y = 2x + 1 and y = -x + 7", "skill": "Systems by substitution", "category": "Equations"},
]


# ═══════════════════════════════════════
# QUALITY CHECKS
# ═══════════════════════════════════════

def check_json_valid(raw):
    """Try to parse JSON from raw response."""
    try:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return True, data
    except Exception:
        return False, None


def extract_json(raw):
    """Extract JSON from a response that might have extra text."""
    valid, parsed = check_json_valid(raw)
    if valid:
        return parsed
    match = re.search(r'\{.*\}', raw, re.DOTALL)
    if match:
        valid, parsed = check_json_valid(match.group())
        if valid:
            return parsed
    return None


def check_teaching_method(data, problem_info):
    """Check if response uses the expected teaching method."""
    text = json.dumps(data).lower()
    method = problem_info.get("method", "").lower()

    checks = {
        "10x method": any(k in text for k in [
            "10x", "100x", "multiply both sides by 10",
            "multiply both sides by 100", "let x ="
        ]),
        "estimate and compare": any(k in text for k in [
            "estimate", "between", "approximate", "square both",
            "closer to"
        ]),
        "proportional vs additive reasoning": any(k in text for k in [
            "unit rate", "per shirt", "additive", "proportional",
            "$8", "8 per", "multiply"
        ]),
        "the outlier check": any(k in text for k in [
            "outlier", "skew", "median", "resist", "pulls",
            "much larger", "much smaller"
        ]),
        "4-step mad": any(k in text for k in [
            "deviation", "absolute value", "mad",
            "mean absolute", "subtract the mean"
        ]),
        "two-question sort": (
            any(k in text for k in ["isosceles", "scalene", "equilateral"])
            and any(k in text for k in ["acute", "obtuse", "right"])
        ),
    }

    if method in checks:
        return checks[method]
    return True


def check_vertical_alignment(data, level):
    """Check if math fields use multi-line formatting (Level 1 and 5)."""
    if level not in [1, 5]:
        return True
    steps_key = "steps" if level == 1 else "solution_steps"
    steps = data.get(steps_key, [])
    if not steps:
        return True
    multi_line_count = sum(1 for s in steps if "\n" in s.get("math", ""))
    return multi_line_count >= max(1, (len(steps) - 1) // 2)


def check_step0(data, problem_text, level):
    """Check if Step 0 is present for problems that need it."""
    text_lower = problem_text.lower()
    needs_step0 = any(k in text_lower for k in [
        "circle", "diameter", "radius", "hypotenuse", "leg",
        "median", "probability", "classify"
    ])
    if not needs_step0:
        return True

    data_text = json.dumps(data).lower()
    return any(k in data_text for k in [
        "step 0", "radius or diameter", "hypotenuse or leg",
        "order the data", "list all", "by its sides", "by sides"
    ])


def check_correct_answer(data, expected, level):
    """Check if the final answer matches expected (fuzzy)."""
    if not expected:
        return True
    answer_fields = ["final_answer", "correct_answer", "expected_result"]
    for field in answer_fields:
        val = str(data.get(field, "")).lower().strip()
        if expected.lower().strip() in val or val in expected.lower().strip():
            return True
    # Also check full JSON dump
    full_text = json.dumps(data).lower()
    return expected.lower().strip() in full_text


def run_quality_checks(parsed, raw, problem_info, level):
    """Run all quality checks and return results dict."""
    results = {}

    # JSON valid
    results["JSON Valid"] = parsed is not None
    if not parsed:
        return results

    # Teaching method (PSSA problems only)
    if problem_info.get("method"):
        results["Teaching Method Used"] = check_teaching_method(parsed, problem_info)

    # Vertical alignment (L1, L5)
    results["Vertical Alignment"] = check_vertical_alignment(parsed, level)

    # Step 0
    results["Step 0 Present"] = check_step0(parsed, problem_info["problem"], level)

    # Correct answer
    if problem_info.get("expected_answer"):
        results["Correct Answer"] = check_correct_answer(
            parsed, problem_info["expected_answer"], level
        )

    # Level-specific structure
    if level == 1:
        results["Has Steps"] = bool(parsed.get("steps"))
        results["Has Practice Problem"] = bool(parsed.get("practice_problem"))
        results["Step Count"] = len(parsed.get("steps", []))
    elif level in [2, 3]:
        steps = parsed.get("walkthrough_steps", [])
        results["Has Walkthrough Steps"] = bool(steps)
        if steps:
            results["Has Options"] = all("options" in s for s in steps)
            results["Has Option Explanations"] = all(
                "option_explanations" in s for s in steps
            )
            results["Correct Index Valid"] = all(
                0 <= s.get("correct_index", -1) < len(s.get("options", []))
                for s in steps
            )
        if level == 2:
            results["Has Simpler Example"] = bool(parsed.get("simpler_example"))
    elif level == 4:
        results["Has Prompt or Complete"] = bool(
            parsed.get("prompt") or parsed.get("is_complete")
        )
        if parsed.get("mc_fallback"):
            fb = parsed["mc_fallback"]
            opts = fb.get("options", [])
            idx = fb.get("correct_index", -1)
            results["Fallback Index Valid"] = 0 <= idx < len(opts)
    elif level == 5:
        results["Has Acceptable Forms"] = bool(parsed.get("acceptable_forms"))
        forms = parsed.get("acceptable_forms", [])
        results["5+ Acceptable Forms"] = len(forms) >= 5

    return results


# ═══════════════════════════════════════
# SIDEBAR CONFIG
# ═══════════════════════════════════════

st.sidebar.header("Test Configuration")

preset = st.sidebar.selectbox("Problem Set", [
    "PSSA Gap Problems (6 new)",
    "Original 22 Problems",
    "All 28 Problems",
    "Custom Selection",
])

if preset == "PSSA Gap Problems (6 new)":
    selected_problems = PSSA_GAP_PROBLEMS
elif preset == "Original 22 Problems":
    selected_problems = ORIGINAL_PROBLEMS
elif preset == "All 28 Problems":
    selected_problems = PSSA_GAP_PROBLEMS + ORIGINAL_PROBLEMS
else:
    all_problems = PSSA_GAP_PROBLEMS + ORIGINAL_PROBLEMS
    selected_ids = st.sidebar.multiselect(
        "Select problems",
        options=[f"{p['id']}: {p['problem'][:50]}..." for p in all_problems],
        default=[f"{p['id']}: {p['problem'][:50]}..." for p in PSSA_GAP_PROBLEMS],
    )
    selected_problems = [
        p for p in all_problems
        if f"{p['id']}: {p['problem'][:50]}..." in selected_ids
    ]

levels = st.sidebar.multiselect(
    "Confidence Levels",
    options=[1, 2, 3, 4, 5],
    default=[1, 2, 3, 4, 5],
)

st.sidebar.markdown("---")
total_api_calls = len(selected_problems) * len(levels)
st.sidebar.markdown(f"**Total API calls:** {total_api_calls}")
est_minutes = round(total_api_calls * 3 / 60, 1)
st.sidebar.markdown(f"**Est. time:** ~{est_minutes} min")


# ═══════════════════════════════════════
# RUN TESTS
# ═══════════════════════════════════════

if st.button("🚀 Run Tests", type="primary", use_container_width=True):
    if not selected_problems:
        st.error("Select at least one problem.")
        st.stop()

    total_calls = len(selected_problems) * len(levels)
    progress = st.progress(0)
    status = st.empty()
    timer_start = time.time()

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = build_system_prompt()
    results = []
    call_count = 0

    for prob in selected_problems:
        for level in levels:
            call_count += 1
            status.text(
                f"Testing {prob['id']} Level {level}... ({call_count}/{total_calls})"
            )
            progress.progress(call_count / total_calls)

            try:
                level_prompt = get_level_prompt(level, prob["problem"])
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": level_prompt}],
                )
                raw = response.content[0].text
                parsed = extract_json(raw)
                checks = run_quality_checks(parsed, raw, prob, level)

                results.append({
                    "problem_id": prob["id"],
                    "problem": prob["problem"],
                    "skill": prob["skill"],
                    "method": prob.get("method", ""),
                    "category": prob.get("category", ""),
                    "expected_answer": prob.get("expected_answer", ""),
                    "level": level,
                    "raw_response": raw,
                    "parsed": parsed,
                    "checks": checks,
                    "all_passed": all(
                        v is True for v in checks.values()
                        if not isinstance(v, int)
                    ),
                    "error": None,
                })

            except Exception as e:
                results.append({
                    "problem_id": prob["id"],
                    "problem": prob["problem"],
                    "skill": prob["skill"],
                    "method": prob.get("method", ""),
                    "category": prob.get("category", ""),
                    "expected_answer": prob.get("expected_answer", ""),
                    "level": level,
                    "raw_response": None,
                    "parsed": None,
                    "checks": {},
                    "all_passed": False,
                    "error": str(e),
                })

            time.sleep(0.5)

    elapsed = round(time.time() - timer_start, 1)
    progress.progress(1.0)
    status.text(f"✅ Complete! {total_calls} tests in {elapsed}s")
    st.session_state.test_results = results


# ═══════════════════════════════════════
# DISPLAY RESULTS
# ═══════════════════════════════════════

if "test_results" in st.session_state:
    results = st.session_state.test_results

    # ── Summary Metrics ──
    total = len(results)
    passed = sum(1 for r in results if r["all_passed"])
    failed = total - passed
    errors = sum(1 for r in results if r["error"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tests", total)
    col2.metric("Passed ✅", passed)
    col3.metric("Issues ⚠️", failed - errors)
    col4.metric("Errors 🔴", errors)

    # ── Pass rate by check type ──
    st.markdown("---")
    st.markdown("### Check Pass Rates")
    all_check_names = set()
    for r in results:
        for k, v in r["checks"].items():
            if isinstance(v, bool):
                all_check_names.add(k)

    check_cols = st.columns(min(len(all_check_names), 4))
    for i, check_name in enumerate(sorted(all_check_names)):
        applicable = [r for r in results if check_name in r["checks"]]
        passed_check = sum(1 for r in applicable if r["checks"][check_name] is True)
        rate = f"{passed_check}/{len(applicable)}" if applicable else "N/A"
        check_cols[i % len(check_cols)].metric(check_name, rate)

    st.markdown("---")

    # ── PSSA Gap Focus Section ──
    pssa_results = [r for r in results if r["problem_id"].startswith("PSSA")]
    if pssa_results:
        st.markdown("### 🎯 PSSA Gap Teaching Methods")

        for prob_id in sorted(set(r["problem_id"] for r in pssa_results)):
            prob_results = [r for r in pssa_results if r["problem_id"] == prob_id]
            first = prob_results[0]
            all_ok = all(r["all_passed"] for r in prob_results)
            icon = "✅" if all_ok else "⚠️"

            with st.expander(
                f"{icon} {prob_id}: {first['skill']} — Method: {first['method']}"
            ):
                st.markdown(f"**Problem:** {first['problem']}")
                st.markdown(f"**Expected:** {first['expected_answer']}")

                tabs = st.tabs([f"Level {r['level']}" for r in prob_results])
                for tab, r in zip(tabs, prob_results):
                    with tab:
                        if r["error"]:
                            st.error(f"Error: {r['error']}")
                            continue

                        for check_name, check_val in r["checks"].items():
                            if isinstance(check_val, bool):
                                st.markdown(
                                    f"{'✅' if check_val else '❌'} {check_name}"
                                )
                            else:
                                st.markdown(f"📊 {check_name}: {check_val}")

                        if r["parsed"]:
                            st.json(r["parsed"])
                        elif r["raw_response"]:
                            st.code(r["raw_response"][:3000], language="json")

    # ── Original Problems Section ──
    og_results = [r for r in results if r["problem_id"].startswith("OG")]
    if og_results:
        st.markdown("### 📝 Original Test Problems")

        for prob_id in sorted(
            set(r["problem_id"] for r in og_results),
            key=lambda x: int(x.split("-")[1]),
        ):
            prob_results = [r for r in og_results if r["problem_id"] == prob_id]
            first = prob_results[0]
            all_ok = all(r["all_passed"] for r in prob_results)
            icon = "✅" if all_ok else "⚠️"

            with st.expander(f"{icon} {prob_id}: {first['skill']}"):
                st.markdown(f"**Problem:** {first['problem']}")

                tabs = st.tabs([f"Level {r['level']}" for r in prob_results])
                for tab, r in zip(tabs, prob_results):
                    with tab:
                        if r["error"]:
                            st.error(f"Error: {r['error']}")
                            continue

                        for check_name, check_val in r["checks"].items():
                            if isinstance(check_val, bool):
                                st.markdown(
                                    f"{'✅' if check_val else '❌'} {check_name}"
                                )
                            else:
                                st.markdown(f"📊 {check_name}: {check_val}")

                        if r["parsed"]:
                            st.json(r["parsed"])
                        elif r["raw_response"]:
                            st.code(r["raw_response"][:3000], language="json")

    # ── Download Results ──
    st.markdown("---")
    export_data = []
    for r in results:
        export_data.append({
            "problem_id": r["problem_id"],
            "problem": r["problem"],
            "skill": r["skill"],
            "method": r.get("method", ""),
            "expected_answer": r.get("expected_answer", ""),
            "level": r["level"],
            "all_passed": r["all_passed"],
            "checks": r["checks"],
            "error": r["error"],
            "response": r["parsed"] if r["parsed"] else None,
        })

    st.download_button(
        "📥 Download Results (JSON)",
        data=json.dumps(export_data, indent=2),
        file_name="mathful_minds_pssa_test_results.json",
        mime="application/json",
    )
