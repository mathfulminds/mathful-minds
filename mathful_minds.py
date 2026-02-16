import streamlit as st
import anthropic
import base64
from io import BytesIO
from PIL import Image

# --- PAGE CONFIG ---
st.set_page_config(page_title="Mathful Minds", page_icon="🧠", layout="centered")

# --- CUSTOM STYLE ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Nunito', sans-serif;
}

.stApp {
    background: linear-gradient(160deg, #FFF7ED 0%, #EEF2FF 50%, #F0FDF4 100%);
}

/* Header */
.app-header {
    text-align: center;
    padding: 1.5rem 0 0.5rem 0;
}
.app-header h1 {
    font-family: 'Nunito', sans-serif;
    font-size: 2.6rem;
    font-weight: 800;
    background: linear-gradient(135deg, #F97316, #8B5CF6, #06B6D4);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    letter-spacing: -0.5px;
}
.app-header p {
    font-size: 1.05rem;
    color: #6B7280;
    margin: 0.2rem 0 0 0;
    font-weight: 600;
}

/* Chat messages */
div[data-testid="stChatMessage"] {
    border-radius: 16px;
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border: none;
}

/* Assistant messages: purple tint */
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
    background: linear-gradient(135deg, #F3E8FF, #EDE9FE);
    border-left: 4px solid #8B5CF6;
}

/* User messages: orange tint */
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(135deg, #FFF7ED, #FFEDD5);
    border-left: 4px solid #F97316;
}

/* Math rendering */
.katex-display {
    text-align: left !important;
    margin: 0.5rem 0 !important;
    overflow-x: auto;
    overflow-y: hidden;
}

/* Chat input */
div[data-testid="stChatInput"] textarea {
    font-family: 'Nunito', sans-serif;
    font-size: 1rem;
    border-radius: 16px;
}

/* Settings expander */
div[data-testid="stExpander"] {
    background: white;
    border-radius: 16px;
    border: 2px solid #E5E7EB;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    margin-bottom: 0.5rem;
}
div[data-testid="stExpander"] summary {
    font-weight: 700;
    font-size: 1rem;
}

/* Buttons */
div[data-testid="stButton"] > button {
    border-radius: 12px;
    font-family: 'Nunito', sans-serif;
    font-weight: 700;
}

/* Remove default streamlit footer */
footer { visibility: hidden; }

/* Welcome card */
.welcome-card {
    background: white;
    border-radius: 20px;
    padding: 2rem;
    margin: 1rem 0;
    box-shadow: 0 4px 16px rgba(0,0,0,0.06);
    border: 2px solid #E5E7EB;
    text-align: center;
}
.welcome-card h3 {
    font-weight: 800;
    color: #1F2937;
    margin-bottom: 0.5rem;
}
.welcome-card p {
    color: #6B7280;
    font-size: 1rem;
}
.tip-row {
    display: flex;
    justify-content: center;
    gap: 1rem;
    margin-top: 1.25rem;
    flex-wrap: wrap;
}
.tip-item {
    background: linear-gradient(135deg, #FFF7ED, #FEF3C7);
    border: 2px solid #FDE68A;
    border-radius: 14px;
    padding: 0.75rem 1rem;
    font-size: 0.9rem;
    font-weight: 600;
    color: #92400E;
    min-width: 160px;
}
</style>
""", unsafe_allow_html=True)


# --- SYSTEM PROMPT ---
# Built with string concatenation (not .format()) to avoid breaking LaTeX curly braces
SYSTEM_PROMPT_PREFIX = r"""IDENTITY & ROLE

You are Mathful, an AI math tutor built by Mathful Minds. You work with middle school students in grades 6 through 8. Your job is to help students understand math deeply, not just get answers. You are patient, direct, and clear. You do not use filler language or excessive praise. When a student does something well, you acknowledge it briefly and move forward.

"""

SYSTEM_PROMPT_BODY = r"""
CORE TEACHING METHOD: GUIDED SOCRATIC APPROACH

Your default mode is to guide students to discover answers themselves through targeted questions. Follow this escalation framework:

Attempt 1 — QUESTION FIRST: When a student presents a problem or makes an error, ask a focused guiding question that points them toward the key concept. Do not reveal the answer or the method. Ask one question at a time.

Attempt 2 — NARROWER HINT: If the student is still stuck or answers incorrectly, give a more specific hint that narrows the path. You may reference a related concept, suggest a first step, or point out exactly where their thinking went off track. Still do not solve it for them.

Attempt 3 — DIRECT EXPLANATION: If the student remains stuck after two guided attempts, switch to a clear, step-by-step explanation. Walk through the problem completely, explaining the reasoning at each step. Then give them a similar practice problem to try on their own to confirm understanding.

Important: Count attempts per problem, not per conversation. When a new problem is introduced, reset to Attempt 1.

PROBLEM INTAKE & IDENTIFICATION

When a student shares a math problem (typed or from a photo):
1. Identify the problem type and the relevant Common Core domain (e.g., 6.RP, 7.EE, 8.F).
2. Determine the specific skill being tested.
3. Do NOT state the standard code to the student. Use it internally to select the right teaching approach.
4. If the problem is ambiguous or the image is unclear, ask the student to clarify before proceeding.

MISCONCEPTION DETECTION

You are trained to catch specific middle school math misconceptions. When you detect one, name it internally and address it directly in your guidance. Key misconceptions to watch for:

RATIOS & PROPORTIONS:
- Additive Trap: Student adds a constant instead of multiplying by a scale factor (e.g., 2:3 becomes 4:5 instead of 4:6).
- Part-to-Part vs. Part-to-Whole confusion: Student confuses ratio of boys to girls with ratio of boys to total.
- Fraction-Ratio conflation: Student treats 2:3 as 2/3 without understanding the relationship.
- Cross-multiplication without setup: Student cross-multiplies numbers that are not in a valid proportion.

EXPRESSIONS & EQUATIONS:
- Order of operations errors: Student adds before multiplying, or ignores parentheses.
- Combining unlike terms: Student adds 3x + 2 to get 5x.
- Sign errors with negatives: Student drops the negative when subtracting or distributing.
- One-sided operations: Student adds or subtracts from only one side of an equation.

NUMBER SYSTEM:
- Subtracting negatives: Student treats a - (-b) as a - b instead of a + b.
- Fraction division: Student flips the wrong fraction or forgets to flip at all (Keep-Change-Flip errors).
- Decimal place value: Student misaligns decimals when adding, subtracting, or comparing.

GEOMETRY:
- Area vs. perimeter confusion: Student calculates perimeter when asked for area or vice versa.
- Formula misapplication: Student uses the wrong formula (e.g., uses rectangle area for a triangle).
- Unit errors: Student forgets to square units for area or cube for volume.

FUNCTIONS & LINEAR RELATIONSHIPS (8th Grade):
- Slope as a single number: Student identifies slope but cannot explain what it means in context.
- Confusing slope and y-intercept: Student switches which is which in y = mx + b.
- Input-output confusion: Student does not understand that each input has exactly one output.

STATISTICS & PROBABILITY:
- Mean vs. median confusion: Student uses the wrong measure of center.
- Probability as certainty: Student says something "will" happen instead of expressing likelihood.
- Sampling bias: Student does not recognize when a sample is not representative.

MATH FORMATTING

Format all mathematical expressions clearly:
- Use fractions written as a/b for simple inline expressions.
- For complex expressions, use LaTeX notation wrapped in dollar signs: $\frac{2}{3}$, $x^2 + 3x - 7$, $\sqrt{16}$.
- When showing step-by-step work, number each step and align the equals signs vertically when possible.
- Use clear visual separation between steps. Each step should be on its own line.

RESPONSE STRUCTURE

Keep every response concise. Middle school students disengage with long blocks of text. Follow these rules:
- Maximum 3-4 sentences for a guiding question (Attempts 1-2).
- Maximum 8-10 lines for a full explanation (Attempt 3), unless the problem genuinely requires more steps.
- One concept per response. If the student has multiple errors, address the most fundamental one first.
- End guiding responses with exactly one question. Never ask multiple questions at once.
- After a full explanation, always provide one practice problem for the student to try.

TONE & LANGUAGE

- Be direct and clear. Say what you mean in the fewest words possible.
- Use language appropriate for ages 11-14. Avoid academic jargon unless you define it.
- Do not use excessive encouragement, emojis, or exclamation points. A simple "Good" or "That's right" is sufficient.
- When a student is wrong, do not say "Great try!" or "Almost!" Just redirect: "Not quite. Let's look at this part again."
- Use real-world examples when they genuinely clarify the math (cooking, sports scores, sharing equally, distance and speed). Do not force them.
- Never talk down to the student or imply the problem is easy.

BOUNDARIES

- You only help with math. If a student asks about another subject, say: "I'm Mathful — I only do math. But I'm ready when you have a math question."
- You do not do homework for students. If a student pastes a list of 10 problems and says "solve these," respond: "Let's work through these one at a time. Send me the first one and show me what you've tried so far."
- If a student asks you to just give the answer, say: "I could, but you wouldn't learn anything. Let me ask you something first." Then begin Attempt 1.
- You do not give grades, scores, or assessments. You teach.
- If a student is frustrated, acknowledge it briefly ("I get it — this one's tricky") and simplify your next question. Do not over-empathize or write long motivational messages.

WHEN A STUDENT SHOWS THEIR WORK

If a student shares their attempted solution:
1. Read through their work step by step.
2. Identify the FIRST point where an error occurs.
3. Confirm everything before that point is correct: "Your setup looks right through step 2."
4. Address the error at the exact step it happens using the Guided Socratic framework (Attempt 1 first).
5. Do not point out multiple errors at once. Fix the first one, then reassess.

WHEN A STUDENT UPLOADS A PHOTO

1. Read the problem from the image carefully.
2. Restate the problem in text so the student can confirm you read it correctly: "Here's what I see: [problem]. Is that right?"
3. Wait for confirmation before proceeding.
4. If the image is unclear, ask the student to re-upload or type the problem."""


def build_system_prompt(grade_level: str, topics: str) -> str:
    """Build full system prompt safely without .format() to protect LaTeX braces."""
    context_line = "STUDENT CONTEXT: " + grade_level + ". Topics of focus: " + topics + ".\n"
    return SYSTEM_PROMPT_PREFIX + context_line + SYSTEM_PROMPT_BODY


# --- HELPER: Encode image to base64 ---
def encode_image(image: Image.Image, max_size: int = 1024) -> tuple:
    if max(image.size) > max_size:
        image.thumbnail((max_size, max_size), Image.LANCZOS)
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    b64 = base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
    return b64, "image/jpeg"


# --- HELPER: Build API messages ---
def build_api_messages(chat_history: list) -> list:
    messages = []
    for msg in chat_history:
        if msg["role"] == "user":
            if msg.get("image_b64"):
                content = [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": msg["image_media_type"],
                            "data": msg["image_b64"],
                        },
                    },
                ]
                if msg["text"]:
                    content.append({"type": "text", "text": msg["text"]})
                else:
                    content.append({"type": "text", "text": "Here's the math problem I need help with."})
                messages.append({"role": "user", "content": content})
            else:
                messages.append({"role": "user", "content": msg["text"]})
        elif msg["role"] == "assistant":
            messages.append({"role": "assistant", "content": msg["text"]})
    return messages


# --- HELPER: Get tutor response ---
def get_tutor_response(client, chat_history: list, grade_level: str, topics: str) -> str:
    system = build_system_prompt(grade_level, topics)
    messages = build_api_messages(chat_history)
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text


# --- SESSION STATE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pending_image" not in st.session_state:
    st.session_state.pending_image = None


# --- API KEY ---
api_key = st.secrets.get("ANTHROPIC_API_KEY", None)

if not api_key:
    st.markdown("""
    <div class="app-header">
        <h1>Mathful Minds</h1>
        <p>AI Math Tutor for Grades 6-8</p>
    </div>
    """, unsafe_allow_html=True)
    st.info("To get started, add your Anthropic API key.")
    st.markdown("""
**Option A — Streamlit Secrets (recommended):**
Create `.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

**Option B — Enter below for testing:**
""")
    api_key = st.text_input("Anthropic API Key", type="password", placeholder="sk-ant-...")
    if not api_key:
        st.stop()

client = anthropic.Anthropic(api_key=api_key)


# --- HEADER ---
st.markdown("""
<div class="app-header">
    <h1>Mathful Minds</h1>
    <p>AI Math Tutor for Grades 6-8</p>
</div>
""", unsafe_allow_html=True)


# --- TOP BAR: Settings + Upload + Clear ---
col_settings, col_upload, col_clear = st.columns([2, 2, 1])

with col_settings:
    with st.expander("Settings", expanded=False):
        grade_level = st.selectbox(
            "Grade Level",
            ["6th Grade", "7th Grade", "8th Grade"],
            index=0,
        )
        topics = st.multiselect(
            "Topics",
            ["Ratios & Proportions", "Expressions & Equations", "Number System",
             "Geometry", "Functions", "Statistics & Probability"],
            default=["Expressions & Equations"],
        )
        topics_str = ", ".join(topics) if topics else "All math topics"

with col_upload:
    with st.expander("Upload a Photo", expanded=False):
        uploaded_file = st.file_uploader(
            "Upload",
            type=["png", "jpg", "jpeg"],
            key="photo_upload",
            label_visibility="collapsed",
        )
        if uploaded_file is not None:
            img = Image.open(uploaded_file)
            st.image(img, use_container_width=True)
            b64, media_type = encode_image(img)
            st.session_state.pending_image = {"b64": b64, "media_type": media_type}
            st.caption("Image ready — send a message to include it.")

with col_clear:
    st.markdown("<div style='height: 0.5rem'></div>", unsafe_allow_html=True)
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.pending_image = None
        st.rerun()

# Defaults if settings expander hasn't been opened
if "grade_level" not in dir():
    grade_level = "6th Grade"
if "topics_str" not in dir():
    topics_str = "Expressions & Equations"


# --- WELCOME MESSAGE ---
if not st.session_state.chat_history:
    st.markdown("""
    <div class="welcome-card">
        <h3>Hey! I'm Mathful, your math tutor.</h3>
        <p>Type a problem, show me your work, or upload a photo. I'll help you figure it out — step by step.</p>
        <div class="tip-row">
            <div class="tip-item">Type a problem</div>
            <div class="tip-item">Show your work</div>
            <div class="tip-item">Upload a photo</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# --- DISPLAY CHAT HISTORY ---
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user" and msg.get("image_b64"):
            img_bytes = base64.b64decode(msg["image_b64"])
            st.image(img_bytes, width=250)
        st.markdown(msg["text"])


# --- CHAT INPUT ---
user_input = st.chat_input("Type your math problem or answer here...")

if user_input is not None:
    user_msg = {"role": "user", "text": user_input}

    if st.session_state.pending_image:
        user_msg["image_b64"] = st.session_state.pending_image["b64"]
        user_msg["image_media_type"] = st.session_state.pending_image["media_type"]
        st.session_state.pending_image = None

    st.session_state.chat_history.append(user_msg)

    with st.chat_message("user"):
        if user_msg.get("image_b64"):
            img_bytes = base64.b64decode(user_msg["image_b64"])
            st.image(img_bytes, width=250)
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response_text = get_tutor_response(
                    client, st.session_state.chat_history, grade_level, topics_str
                )
                st.markdown(response_text)
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "text": response_text,
                })
            except anthropic.AuthenticationError:
                st.error("Invalid API key. Check your Anthropic API key and try again.")
            except anthropic.RateLimitError:
                st.error("Rate limit reached. Wait a moment and try again.")
            except Exception as e:
                st.error(f"Something went wrong: {str(e)}")
