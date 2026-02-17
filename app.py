"""
Mathful Minds — AI Math Tutor
Main Streamlit Application
"""

import streamlit as st
import anthropic
from skills import DOMAINS, get_skill_by_id, get_all_skills
from prompt import build_system_prompt

# ─── Page Config ───
st.set_page_config(
    page_title="Mathful Minds",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global */
    .stApp {
        font-family: 'DM Sans', sans-serif;
    }

    /* Header */
    .mathful-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .mathful-header h1 {
        margin: 0;
        font-size: 1.8rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }
    .mathful-header p {
        margin: 0.25rem 0 0 0;
        opacity: 0.8;
        font-size: 0.95rem;
    }

    /* Skill badge */
    .skill-badge {
        background: #e8f4f8;
        border: 1px solid #b8dde6;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        color: #1a5276;
    }
    .skill-badge strong {
        color: #0f3460;
    }

    /* Confidence indicator */
    .confidence-bar {
        display: flex;
        gap: 4px;
        margin-top: 0.5rem;
    }
    .conf-dot {
        width: 24px;
        height: 8px;
        border-radius: 4px;
        background: #ddd;
    }
    .conf-dot.active {
        background: #2ecc71;
    }

    /* Chat messages */
    .stChatMessage {
        font-family: 'DM Sans', sans-serif !important;
    }

    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background: #f8f9fa;
    }
    section[data-testid="stSidebar"] h2 {
        font-size: 1.1rem;
        color: #1a1a2e;
        margin-top: 1rem;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Math display */
    .katex { font-size: 1.1em !important; }
</style>
""", unsafe_allow_html=True)


# ─── Session State Initialization ───
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_skill" not in st.session_state:
    st.session_state.selected_skill = None
if "confidence_level" not in st.session_state:
    st.session_state.confidence_level = 3
if "attempt_count" not in st.session_state:
    st.session_state.attempt_count = 0
if "api_key" not in st.session_state:
    # Try to load from Streamlit secrets first
    try:
        st.session_state.api_key = st.secrets["ANTHROPIC_API_KEY"]
    except (KeyError, FileNotFoundError):
        st.session_state.api_key = ""


# ─── Sidebar ───
with st.sidebar:
    st.markdown("## 🧠 Mathful Minds")
    st.markdown("---")

    # API Key input
    if st.session_state.api_key and st.session_state.api_key.startswith("sk-ant"):
        st.success("API key loaded", icon="✅")
    else:
        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=st.session_state.api_key,
            help="Get yours at console.anthropic.com",
            placeholder="sk-ant-...",
        )
        if api_key:
            st.session_state.api_key = api_key

    st.markdown("---")

    # Domain and Skill Selection
    st.markdown("## 📚 Choose Your Skill")

    # Domain selector
    domain_names = list(DOMAINS.keys())
    selected_domain = st.selectbox(
        "Domain",
        [""] + domain_names,
        format_func=lambda d: "Select a domain..." if d == "" else f"{DOMAINS[d]['icon']} {d}",
    )

    if selected_domain:
        domain_data = DOMAINS[selected_domain]
        subcat_names = list(domain_data["subcategories"].keys())

        selected_subcat = st.selectbox(
            "Topic",
            [""] + subcat_names,
            format_func=lambda s: "Select a topic..." if s == "" else s,
        )

        if selected_subcat:
            skills_in_subcat = domain_data["subcategories"][selected_subcat]
            skill_options = {f"#{s['id']}: {s['name']}": s for s in skills_in_subcat}

            selected_skill_label = st.selectbox(
                "Skill",
                [""] + list(skill_options.keys()),
                format_func=lambda s: "Select a skill..." if s == "" else s,
            )

            if selected_skill_label and selected_skill_label != "":
                skill = skill_options[selected_skill_label]
                # Check if skill changed
                if (
                    st.session_state.selected_skill is None
                    or st.session_state.selected_skill["id"] != skill["id"]
                ):
                    st.session_state.selected_skill = skill
                    st.session_state.messages = []
                    st.session_state.attempt_count = 0

    st.markdown("---")

    # Confidence Level
    st.markdown("## 💪 Confidence Level")
    confidence_labels = {
        1: "1 — Just Starting",
        2: "2 — Building",
        3: "3 — Developing",
        4: "4 — Confident",
        5: "5 — Independent",
    }
    st.session_state.confidence_level = st.select_slider(
        "How confident are you with this skill?",
        options=[1, 2, 3, 4, 5],
        value=st.session_state.confidence_level,
        format_func=lambda x: confidence_labels[x],
    )

    st.markdown("---")

    # New Problem Button
    if st.button("🔄 New Problem", use_container_width=True):
        st.session_state.messages = []
        st.session_state.attempt_count = 0
        st.rerun()

    # Info
    st.markdown("---")
    st.caption("Built by Mathful Minds")
    st.caption("Powered by Claude")


# ─── Main Content ───

# Header
st.markdown("""
<div class="mathful-header">
    <h1>🧠 Mathful Minds</h1>
    <p>Your AI math tutor — let's work through it together.</p>
</div>
""", unsafe_allow_html=True)

# Skill badge
if st.session_state.selected_skill:
    skill = st.session_state.selected_skill
    conf = st.session_state.confidence_level
    conf_dots = "".join(
        f'<div class="conf-dot {"active" if i < conf else ""}"></div>'
        for i in range(5)
    )

    st.markdown(f"""
    <div class="skill-badge">
        <strong>Skill #{skill['id']}:</strong> {skill['name']}
        <div style="margin-top: 0.4rem; font-size: 0.85rem; color: #666;">
            Confidence: {confidence_labels[conf]}
        </div>
        <div class="confidence-bar">{conf_dots}</div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.info("👈 Select a skill from the sidebar to get started!")
    st.stop()

# Check for API key
if not st.session_state.api_key:
    st.warning("No API key found. Enter it in the sidebar or add it to your app's Secrets.")
    st.markdown("""
    **Option 1 — Paste in sidebar** (temporary, resets on refresh)

    **Option 2 — Add to Streamlit Secrets** (permanent):
    1. Go to your app settings → **Secrets**
    2. Add: `ANTHROPIC_API_KEY = "sk-ant-api03-your-key-here"`
    3. Save and reboot the app
    """)
    st.stop()


# ─── Chat Display ───
for msg in st.session_state.messages:
    role = msg["role"]
    with st.chat_message(role, avatar="🧠" if role == "assistant" else "🧑‍🎓"):
        st.markdown(msg["content"])

# ─── Chat Input ───
if prompt := st.chat_input("Type your math problem or answer here..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(prompt)

    # Build system prompt
    skill = st.session_state.selected_skill
    system = build_system_prompt(
        skill_id=skill["id"],
        skill_name=skill["name"],
        confidence_level=st.session_state.confidence_level,
    )

    # Call Claude API
    try:
        client = anthropic.Anthropic(api_key=st.session_state.api_key)

        # Build message history for API
        api_messages = []
        for msg in st.session_state.messages:
            api_messages.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        with st.chat_message("assistant", avatar="🧠"):
            with st.spinner("Thinking..."):
                response = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1024,
                    system=system,
                    messages=api_messages,
                )
                assistant_msg = response.content[0].text

            st.markdown(assistant_msg)

        # Save assistant message
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_msg,
        })

    except anthropic.AuthenticationError:
        st.error("Invalid API key. Please check your key in the sidebar.")
    except anthropic.RateLimitError:
        st.error("Rate limit reached. Please wait a moment and try again.")
    except Exception as e:
        st.error(f"Something went wrong: {str(e)}")
