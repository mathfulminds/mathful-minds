"""
Mathful Minds — AI Math Tutor
Streamlit Application v2 — Complete 5-Level Confidence System
"""

import streamlit as st
import anthropic
import json
from tutor import (
    generate_worked_example,
    generate_mc_walkthrough,
    generate_open_ended_step,
    evaluate_student_answer,
    generate_full_solution,
    generate_simpler_problem,
    ask_followup_question,
    call_claude,
    parse_json_response,
)
from prompt import build_system_prompt, get_level_prompt

# ─── Page Config ───
st.set_page_config(
    page_title="Mathful Minds",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── CSS ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

    .stApp { font-family: 'DM Sans', sans-serif; }
    [data-testid="collapsedControl"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    .block-container { padding-top: 1.2rem; max-width: 760px; }

    /* Header */
    .mm-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 14px;
        margin-bottom: 1.2rem;
        color: white;
    }
    .mm-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; }
    .mm-header p { margin: 0.15rem 0 0 0; opacity: 0.7; font-size: 0.85rem; }

    /* Confidence cards */
    .conf-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 8px;
        margin: 1rem 0;
    }
    .conf-card {
        background: #f7f8fa;
        border: 2px solid #e0e3e8;
        border-radius: 12px;
        padding: 12px 8px;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
    }
    .conf-card:hover { border-color: #3498db; background: #ebf5fb; }
    .conf-card .emoji { font-size: 1.8rem; display: block; margin-bottom: 4px; }
    .conf-card .label { font-size: 0.7rem; color: #555; line-height: 1.2; }

    /* Two-column solution */
    .solution-step {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        padding: 10px 0;
        border-bottom: 1px solid #f0f0f0;
    }
    .solution-step:last-child { border-bottom: none; }
    .step-math {
        font-family: 'DM Sans', sans-serif;
        font-size: 1.05rem;
        font-weight: 600;
        color: #1a1a2e;
        padding: 6px 10px;
        background: #f8f9fa;
        border-radius: 6px;
    }
    .step-explain {
        font-size: 0.9rem;
        color: #555;
        padding: 6px 0;
        display: flex;
        align-items: center;
    }

    /* MC option buttons */
    .mc-option {
        display: block;
        width: 100%;
        padding: 12px 16px;
        margin: 6px 0;
        background: #f7f8fa;
        border: 2px solid #e0e3e8;
        border-radius: 10px;
        text-align: left;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all 0.15s;
    }
    .mc-option:hover { border-color: #3498db; background: #ebf5fb; }
    .mc-correct { border-color: #27ae60 !important; background: #eafaf1 !important; }
    .mc-wrong { border-color: #e74c3c !important; background: #fdedec !important; }

    /* Progress bar */
    .step-progress {
        display: flex;
        gap: 4px;
        margin: 0.5rem 0 1rem 0;
    }
    .step-dot {
        flex: 1;
        height: 6px;
        border-radius: 3px;
        background: #e0e3e8;
    }
    .step-dot.done { background: #27ae60; }
    .step-dot.current { background: #3498db; }

    /* Help button */
    .help-btn {
        background: #fff3e0;
        border: 1px solid #ffcc02;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 0.85rem;
        color: #e67e22;
        cursor: pointer;
        margin-top: 8px;
    }

    /* Problem display */
    .problem-box {
        background: #f0f4ff;
        border: 1px solid #c5d5f0;
        border-radius: 10px;
        padding: 1rem;
        margin: 0.75rem 0;
        font-size: 1.05rem;
        font-weight: 500;
    }

    /* Final answer highlight */
    .final-answer {
        background: #eafaf1;
        border: 2px solid #27ae60;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        font-size: 1.2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# ─── Session State Defaults ───
DEFAULTS = {
    "phase": "input",          # input → confidence → working → solution
    "problem": "",
    "confidence_level": 0,
    "level_data": None,        # Structured data from Claude
    "current_step": 0,
    "step_answers": [],        # Track student's MC/open answers
    "step_history": [],        # For Level 4 step tracking
    "full_solution": None,
    "conversation": [],        # For ask-a-question feature
    "show_simpler": False,
    "simpler_data": None,
    "dropped_level": False,
}
for key, val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = val

# API key from secrets
if "api_key" not in st.session_state:
    try:
        st.session_state.api_key = st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.session_state.api_key = ""


def reset_problem():
    """Reset everything for a new problem."""
    for key, val in DEFAULTS.items():
        st.session_state[key] = val


def get_client():
    """Get the Anthropic client."""
    return anthropic.Anthropic(api_key=st.session_state.api_key)


def render_two_column_solution(steps, title=None):
    """Render steps in the two-column layout (math left, explanation right)."""
    if title:
        st.markdown(f"**{title}**")

    for i, step in enumerate(steps):
        math_text = step.get("math", "")
        explanation = step.get("explanation", "")
        st.markdown(f"""
        <div class="solution-step">
            <div class="step-math">{math_text}</div>
            <div class="step-explain">{explanation}</div>
        </div>
        """, unsafe_allow_html=True)


def render_step_progress(total, current):
    """Render a visual progress bar showing which step the student is on."""
    dots = ""
    for i in range(total):
        if i < current:
            dots += '<div class="step-dot done"></div>'
        elif i == current:
            dots += '<div class="step-dot current"></div>'
        else:
            dots += '<div class="step-dot"></div>'
    st.markdown(f'<div class="step-progress">{dots}</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════
# HEADER
# ═══════════════════════════════════════
st.markdown("""
<div class="mm-header">
    <h1>🧠 Mathful Minds</h1>
    <p>Your AI math tutor — let's work through it together.</p>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════
# API KEY CHECK
# ═══════════════════════════════════════
if not st.session_state.api_key:
    st.text_input(
        "🔑 Enter your API key to get started",
        type="password",
        placeholder="sk-ant-api03-...",
        key="api_input",
    )
    if st.session_state.get("api_input"):
        st.session_state.api_key = st.session_state.api_input
        st.rerun()
    st.caption("Get a key at [console.anthropic.com](https://console.anthropic.com) → Add it to Streamlit Secrets for permanent access.")
    st.stop()


# ═══════════════════════════════════════
# PHASE 1: PROBLEM INPUT
# ═══════════════════════════════════════
if st.session_state.phase == "input":
    st.markdown("### Enter your math problem")

    # Text input
    problem_text = st.text_area(
        "Type or paste your problem here:",
        placeholder="Example: Solve 3x + 5 = -16",
        height=80,
        label_visibility="collapsed",
    )

    # Photo upload
    uploaded_file = st.file_uploader(
        "Or upload a photo of your problem",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("**Let's Go →**", use_container_width=True, type="primary"):
            if problem_text.strip():
                st.session_state.problem = problem_text.strip()
                st.session_state.phase = "confidence"
                st.rerun()
            elif uploaded_file:
                # For now, ask student to also type the problem
                # Photo OCR can be added in v1.1
                st.warning("Please also type the problem in the text box so I can read it clearly.")
            else:
                st.warning("Enter a math problem to get started.")

    with col2:
        if st.button("I need a practice problem", use_container_width=True):
            st.session_state.problem = "__GENERATE__"
            st.session_state.phase = "confidence"
            st.rerun()


# ═══════════════════════════════════════
# PHASE 2: CONFIDENCE SELECTION
# ═══════════════════════════════════════
elif st.session_state.phase == "confidence":
    # Show the problem
    st.markdown(f'<div class="problem-box">📝 {st.session_state.problem}</div>', unsafe_allow_html=True)

    st.markdown("### How confident are you in solving this?")

    # Five confidence cards as columns
    cols = st.columns(5)

    levels = [
        {"emoji": "😧", "label": "I am so lost.", "level": 1},
        {"emoji": "😬", "label": "I don't really get it.", "level": 2},
        {"emoji": "🙂", "label": "I'm starting to get it.", "level": 3},
        {"emoji": "😎", "label": "I got this!", "level": 4},
        {"emoji": "🤩", "label": "I could teach it!", "level": 5},
    ]

    for i, lvl in enumerate(levels):
        with cols[i]:
            if st.button(
                f"{lvl['emoji']}\n\n{lvl['label']}",
                key=f"conf_{lvl['level']}",
                use_container_width=True,
            ):
                st.session_state.confidence_level = lvl["level"]
                st.session_state.phase = "loading"
                st.rerun()

    # Back button
    if st.button("← Change problem"):
        reset_problem()
        st.rerun()


# ═══════════════════════════════════════
# PHASE 2.5: LOADING (API CALL)
# ═══════════════════════════════════════
elif st.session_state.phase == "loading":
    level = st.session_state.confidence_level
    problem = st.session_state.problem

    level_names = {1: "I am so lost", 2: "I don't really get it", 3: "I'm starting to get it", 4: "I got this!", 5: "I could teach it!"}

    st.markdown(f'<div class="problem-box">📝 {problem}</div>', unsafe_allow_html=True)

    with st.spinner(f"Setting up your Level {level} experience..."):
        try:
            client = get_client()
            system = build_system_prompt()

            if level == 1:
                prompt = get_level_prompt(1, problem)
                raw = call_claude(client, system, prompt)
                data = parse_json_response(raw)
                st.session_state.level_data = data
                st.session_state.phase = "level_1"

            elif level == 2:
                prompt = get_level_prompt(2, problem, num_options=3)
                raw = call_claude(client, system, prompt)
                data = parse_json_response(raw)
                st.session_state.level_data = data
                st.session_state.current_step = 0
                st.session_state.phase = "level_2_example"

            elif level == 3:
                prompt = get_level_prompt(3, problem, num_options=4)
                raw = call_claude(client, system, prompt)
                data = parse_json_response(raw)
                st.session_state.level_data = data
                st.session_state.current_step = 0
                st.session_state.phase = "level_3_mc"

            elif level == 4:
                prompt = get_level_prompt(4, problem, step_history=[])
                raw = call_claude(client, system, prompt)
                data = parse_json_response(raw)
                st.session_state.level_data = data
                st.session_state.phase = "level_4_open"

            elif level == 5:
                prompt = get_level_prompt(5, problem)
                raw = call_claude(client, system, prompt)
                data = parse_json_response(raw)
                st.session_state.level_data = data
                st.session_state.phase = "level_5_answer"

            st.rerun()

        except json.JSONDecodeError:
            st.error("I had trouble setting up this problem. Let me try again.")
            if st.button("Try Again"):
                st.rerun()
        except anthropic.AuthenticationError:
            st.error("Invalid API key. Please check your key.")
            st.session_state.api_key = ""
            st.rerun()
        except Exception as e:
            st.error(f"Something went wrong: {str(e)}")
            if st.button("Try Again"):
                st.rerun()


# ═══════════════════════════════════════
# LEVEL 1: FULL WORKED EXAMPLE
# ═══════════════════════════════════════
elif st.session_state.phase == "level_1":
    data = st.session_state.level_data
    problem = st.session_state.problem

    st.markdown(f'<div class="problem-box">📝 {data.get("problem_restated", problem)}</div>', unsafe_allow_html=True)
    st.markdown("#### Here's how to solve this step by step:")

    # Two-column solution
    render_two_column_solution(data.get("steps", []))

    # Final answer
    final = data.get("final_answer", "")
    if final:
        st.markdown(f'<div class="final-answer">✅ {final}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if data.get("practice_problem"):
            if st.button("Try a practice problem →", use_container_width=True, type="primary"):
                st.session_state.problem = data["practice_problem"]
                st.session_state.phase = "confidence"
                st.session_state.level_data = None
                st.rerun()

    with col2:
        if st.button("Show me a simpler problem", use_container_width=True):
            st.session_state.show_simpler = True
            st.rerun()

    with col3:
        if st.button("New problem", use_container_width=True):
            reset_problem()
            st.rerun()

    # Simpler problem (if requested)
    if st.session_state.show_simpler:
        if st.session_state.simpler_data is None:
            with st.spinner("Creating a simpler example..."):
                try:
                    client = get_client()
                    st.session_state.simpler_data = generate_simpler_problem(client, st.session_state.api_key, problem)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            sdata = st.session_state.simpler_data
            st.markdown("---")
            st.markdown(f"#### Let's start simpler: {sdata.get('simpler_problem', '')}")
            if sdata.get("why_simpler"):
                st.caption(sdata["why_simpler"])
            render_two_column_solution(sdata.get("steps", []))
            if sdata.get("final_answer"):
                st.markdown(f'<div class="final-answer">✅ {sdata["final_answer"]}</div>', unsafe_allow_html=True)
            if sdata.get("bridge"):
                st.info(sdata["bridge"])

    # Ask a question
    st.markdown("---")
    question = st.text_input("💬 Have a question about this?", placeholder="Ask anything about this problem...")
    if question:
        with st.spinner("Thinking..."):
            try:
                client = get_client()
                answer = ask_followup_question(client, st.session_state.api_key, problem, st.session_state.conversation, question)
                st.session_state.conversation.append({"role": "user", "content": question})
                st.session_state.conversation.append({"role": "assistant", "content": answer})
                st.markdown(f"**Mathful:** {answer}")
            except Exception as e:
                st.error(f"Error: {e}")


# ═══════════════════════════════════════
# LEVEL 2: SIMPLER EXAMPLE → MC (2-3 options)
# ═══════════════════════════════════════
elif st.session_state.phase == "level_2_example":
    data = st.session_state.level_data
    problem = st.session_state.problem

    st.markdown(f'<div class="problem-box">📝 {data.get("problem_restated", problem)}</div>', unsafe_allow_html=True)

    # Show simpler example first
    simpler = data.get("simpler_example", {})
    if simpler:
        st.markdown(f"#### First, let's look at a simpler problem:")
        st.markdown(f'<div class="problem-box" style="background:#fff8e1; border-color:#ffe082;">💡 {simpler.get("problem", "")}</div>', unsafe_allow_html=True)

        render_two_column_solution(simpler.get("steps", []))

        if simpler.get("final_answer"):
            st.success(f"**Answer:** {simpler['final_answer']}")
        if simpler.get("bridge"):
            st.info(f"💡 {simpler['bridge']}")

    st.markdown("---")

    if st.button("**Got it! Let's try the original problem →**", type="primary", use_container_width=True):
        st.session_state.phase = "level_2_mc"
        st.session_state.current_step = 0
        st.rerun()

    # Drop to Level 1
    if st.button("I need more help — show me the full solution", use_container_width=True):
        st.session_state.confidence_level = 1
        st.session_state.phase = "loading"
        st.session_state.dropped_level = True
        st.rerun()


# ═══════════════════════════════════════
# LEVELS 2 & 3: MULTIPLE CHOICE WALKTHROUGH
# ═══════════════════════════════════════
elif st.session_state.phase in ("level_2_mc", "level_3_mc"):
    data = st.session_state.level_data
    problem = st.session_state.problem
    steps = data.get("walkthrough_steps", [])
    current = st.session_state.current_step
    is_level_2 = st.session_state.phase == "level_2_mc"

    st.markdown(f'<div class="problem-box">📝 {data.get("problem_restated", problem)}</div>', unsafe_allow_html=True)

    # Progress bar
    if steps:
        render_step_progress(len(steps), current)

    # Check if we've completed all steps
    if current >= len(steps):
        st.session_state.phase = "solution"
        st.rerun()

    # Current step
    if current < len(steps):
        step = steps[current]

        # Show current equation state
        if step.get("current_state"):
            st.markdown(f"**Current:** `{step['current_state']}`")

        # Question
        st.markdown(f"### Step {step.get('step_number', current + 1)}: {step.get('question', 'What would you do next?')}")

        # Check if student already answered this step
        answer_key = f"mc_answer_{current}"

        if answer_key not in st.session_state:
            # Show options as buttons
            options = step.get("options", [])
            option_labels = ["A", "B", "C", "D", "E"]

            for i, option in enumerate(options):
                label = option_labels[i] if i < len(option_labels) else str(i + 1)
                if st.button(f"**{label}.** {option}", key=f"opt_{current}_{i}", use_container_width=True):
                    correct_idx = step.get("correct_index", 0)
                    is_correct = (i == correct_idx)
                    st.session_state[answer_key] = {
                        "selected": i,
                        "correct": correct_idx,
                        "is_correct": is_correct,
                    }
                    st.rerun()

            # "I need more help" button
            st.markdown("---")
            drop_level = 1 if is_level_2 else 2
            drop_label = "I need more help" if is_level_2 else "I need more help"
            if st.button(f"🤔 {drop_label}", use_container_width=True):
                st.session_state.confidence_level = drop_level
                st.session_state.phase = "loading"
                st.session_state.dropped_level = True
                st.rerun()

        else:
            # Show result
            result = st.session_state[answer_key]
            options = step.get("options", [])
            correct_idx = result["correct"]

            if result["is_correct"]:
                st.success(f"✅ **{options[result['selected']]}**")
                if step.get("explanation"):
                    st.caption(step["explanation"])
            else:
                st.error(f"❌ Not quite. You chose: **{options[result['selected']]}**")
                st.success(f"✅ The correct step: **{options[correct_idx]}**")
                if step.get("explanation"):
                    st.info(step["explanation"])

            if step.get("result"):
                st.markdown(f"**After this step:** `{step['result']}`")

            # Next step button
            if st.button("**Next Step →**", type="primary", use_container_width=True):
                st.session_state.current_step += 1
                st.rerun()


# ═══════════════════════════════════════
# LEVEL 4: OPEN-ENDED PROMPTS
# ═══════════════════════════════════════
elif st.session_state.phase == "level_4_open":
    data = st.session_state.level_data
    problem = st.session_state.problem

    st.markdown(f'<div class="problem-box">📝 {problem}</div>', unsafe_allow_html=True)

    if data.get("is_complete"):
        st.session_state.phase = "solution"
        st.rerun()

    # Show current state
    if data.get("current_state"):
        st.markdown(f"**Current:** `{data['current_state']}`")

    # Open-ended prompt
    prompt_text = data.get("prompt", "What would you do next?")
    st.markdown(f"### {prompt_text}")

    # Student input
    answer_key = f"l4_answer_{data.get('step_number', 0)}"

    if answer_key not in st.session_state:
        student_input = st.text_input("Your answer:", key=f"l4_input_{data.get('step_number', 0)}", placeholder="Type what you'd do next...")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("**Check →**", type="primary", use_container_width=True) and student_input:
                # Check against expected keywords
                expected = data.get("expected_keywords", [])
                input_lower = student_input.lower()
                matches = sum(1 for kw in expected if kw.lower() in input_lower)
                is_correct = matches >= len(expected) / 2 if expected else True

                if not is_correct:
                    # Also check with Claude for more nuanced evaluation
                    try:
                        client = get_client()
                        eval_result = evaluate_student_answer(
                            client, st.session_state.api_key, problem, student_input,
                            context=f"Current state: {data.get('current_state', '')}. Expected: {data.get('expected_result', '')}"
                        )
                        is_correct = eval_result.get("is_correct", False)
                    except Exception:
                        pass

                st.session_state[answer_key] = {
                    "input": student_input,
                    "is_correct": is_correct,
                }
                st.rerun()

        with col2:
            if st.button("🤔 I'm not sure", use_container_width=True):
                # Show MC fallback
                st.session_state[answer_key] = {"input": "", "is_correct": False, "show_mc": True}
                st.rerun()

    else:
        result = st.session_state[answer_key]

        if result.get("show_mc"):
            # Show MC fallback options
            st.info("No worries! Let me give you some options.")
            fallback = data.get("mc_fallback", {})
            options = fallback.get("options", [])
            correct_idx = fallback.get("correct_index", 0)

            mc_key = f"l4_mc_{data.get('step_number', 0)}"
            if mc_key not in st.session_state:
                for i, opt in enumerate(options):
                    label = ["A", "B", "C", "D"][i] if i < 4 else str(i + 1)
                    if st.button(f"**{label}.** {opt}", key=f"l4mc_{data.get('step_number', 0)}_{i}", use_container_width=True):
                        st.session_state[mc_key] = i
                        st.rerun()
            else:
                selected = st.session_state[mc_key]
                if selected == correct_idx:
                    st.success(f"✅ {options[selected]}")
                else:
                    st.error(f"❌ Not quite.")
                    st.success(f"✅ {options[correct_idx]}")

                if st.button("**Next Step →**", type="primary", use_container_width=True):
                    # Move to next step
                    st.session_state.step_history.append({
                        "step": data.get("step_number", 1),
                        "action": options[correct_idx]
                    })
                    # Get next step from Claude
                    with st.spinner("..."):
                        try:
                            client = get_client()
                            system = build_system_prompt()
                            prompt = get_level_prompt(4, problem, step_history=st.session_state.step_history)
                            raw = call_claude(client, system, prompt)
                            new_data = parse_json_response(raw)
                            st.session_state.level_data = new_data
                            st.rerun()
                        except Exception as e:
                            st.session_state.phase = "solution"
                            st.rerun()

        elif result["is_correct"]:
            st.success(f"✅ Good. {result['input']}")
            if st.button("**Next Step →**", type="primary", use_container_width=True):
                st.session_state.step_history.append({
                    "step": data.get("step_number", 1),
                    "action": result["input"]
                })
                with st.spinner("..."):
                    try:
                        client = get_client()
                        system = build_system_prompt()
                        prompt = get_level_prompt(4, problem, step_history=st.session_state.step_history)
                        raw = call_claude(client, system, prompt)
                        new_data = parse_json_response(raw)
                        st.session_state.level_data = new_data
                        st.rerun()
                    except Exception as e:
                        st.session_state.phase = "solution"
                        st.rerun()
        else:
            st.error(f"Not quite. Let me give you some options instead.")
            st.session_state[answer_key] = {"input": result["input"], "is_correct": False, "show_mc": True}
            st.rerun()


# ═══════════════════════════════════════
# LEVEL 5: ANSWER CHECK
# ═══════════════════════════════════════
elif st.session_state.phase == "level_5_answer":
    data = st.session_state.level_data
    problem = st.session_state.problem

    st.markdown(f'<div class="problem-box">📝 {data.get("problem_restated", problem)}</div>', unsafe_allow_html=True)

    st.markdown("### 🤩 I like the confidence! What do you think the answer is?")

    if "l5_result" not in st.session_state:
        answer = st.text_input("Your answer:", placeholder="Type your final answer...", key="l5_input")

        if st.button("**Check My Answer →**", type="primary", use_container_width=True) and answer:
            # Check against acceptable forms
            acceptable = data.get("acceptable_forms", [])
            correct = data.get("correct_answer", "")
            answer_clean = answer.strip().lower().replace(" ", "")

            is_correct = False
            for form in acceptable:
                if answer_clean == form.lower().replace(" ", ""):
                    is_correct = True
                    break

            # Also check direct match
            if answer_clean == correct.lower().replace(" ", ""):
                is_correct = True

            st.session_state.l5_result = {
                "answer": answer,
                "is_correct": is_correct,
            }
            st.rerun()
    else:
        result = st.session_state.l5_result

        if result["is_correct"]:
            st.markdown(f'<div class="final-answer">🎉 Correct! {data.get("correct_answer", "")}</div>', unsafe_allow_html=True)
            st.markdown("Here's the full solution for reference:")
            render_two_column_solution(data.get("solution_steps", []))
        else:
            st.error(f"Not quite. Your answer: **{result['answer']}**")
            st.info("No worries — let's work through it step by step.")

            if st.button("**Drop to Level 4 — work through it →**", type="primary", use_container_width=True):
                st.session_state.confidence_level = 4
                st.session_state.phase = "loading"
                st.session_state.dropped_level = True
                st.rerun()

            if st.button("Just show me the solution", use_container_width=True):
                st.session_state.phase = "solution"
                st.rerun()

    # New problem
    st.markdown("---")
    if st.button("New problem", use_container_width=True):
        reset_problem()
        st.rerun()


# ═══════════════════════════════════════
# FINAL SOLUTION (shown at end of all levels)
# ═══════════════════════════════════════
elif st.session_state.phase == "solution":
    problem = st.session_state.problem

    st.markdown(f'<div class="problem-box">📝 {problem}</div>', unsafe_allow_html=True)

    # Generate full solution if we don't have one
    if st.session_state.full_solution is None:
        with st.spinner("Generating the complete solution..."):
            try:
                client = get_client()
                st.session_state.full_solution = generate_full_solution(client, st.session_state.api_key, problem)
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

    sol = st.session_state.full_solution

    st.markdown("### Complete Solution")
    render_two_column_solution(sol.get("steps", []))

    if sol.get("final_answer"):
        st.markdown(f'<div class="final-answer">✅ {sol["final_answer"]}</div>', unsafe_allow_html=True)

    st.markdown("---")

    # Post-solution actions
    col1, col2 = st.columns(2)
    with col1:
        if st.button("**New Problem →**", type="primary", use_container_width=True):
            reset_problem()
            st.rerun()
    with col2:
        if st.button("Try a similar problem", use_container_width=True):
            # Generate a practice problem
            st.session_state.problem = f"Give me a problem similar to: {problem}"
            st.session_state.phase = "confidence"
            st.session_state.level_data = None
            st.session_state.full_solution = None
            st.rerun()

    # Ask a question
    st.markdown("---")
    question = st.text_input("💬 Have a question about this solution?", placeholder="Ask anything...", key="sol_question")
    if question:
        with st.spinner("Thinking..."):
            try:
                client = get_client()
                answer = ask_followup_question(client, st.session_state.api_key, problem, st.session_state.conversation, question)
                st.session_state.conversation.append({"role": "user", "content": question})
                st.session_state.conversation.append({"role": "assistant", "content": answer})
                st.markdown(f"**Mathful:** {answer}")
            except Exception as e:
                st.error(f"Error: {e}")
