# 🧠 Mathful Minds — AI Math Tutor

An AI-powered math tutor for middle school students (grades 6-8) with confidence-based scaffolding, misconception detection, and 245 skills across 5 domains.

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Get Your API Key
- Go to [console.anthropic.com](https://console.anthropic.com)
- Create an account (or log in)
- Navigate to **API Keys** → **Create Key**
- Copy the key (starts with `sk-ant-...`)

### 3. Run the App
```bash
streamlit run app.py
```

### 4. Start Tutoring
1. Paste your API key in the sidebar
2. Select a **Domain** → **Topic** → **Skill**
3. Set your **Confidence Level** (1-5)
4. Type a math problem and start learning!

## Architecture

```
mathful_minds/
├── app.py              # Streamlit interface
├── prompt.py           # System prompt (core pedagogical IP)
├── skills.py           # 245-skill catalog organized by domain
├── requirements.txt    # Python dependencies
├── README.md           # This file
└── .streamlit/
    └── config.toml     # App theme
```

## How It Works

### The System Prompt (`prompt.py`)
This is the product. It encodes:
- **3-Attempt Socratic Escalation**: Question → Hint → Full Explanation
- **5-Level Confidence Scaffolding**: From "I'll walk you through it" to "You do it, I'll check"
- **Skill-Specific Teaching Methods**: KCO for subtraction, KCF for division, Butterfly method for fractions, formula framework for geometry, and more
- **Misconception Detection**: Catches 25+ common middle school math errors in real time
- **Two-Column Layout**: Math on the left, explanation on the right

### The Skills Catalog (`skills.py`)
245 skills across 5 domains:
- 🔢 Number Sense (Skills 1-22)
- ⚖️ Ratios & Proportions (Skills 23-51)
- 📐 Expressions & Equations (Skills 52-143)
- 📏 Geometry (Skills 144-222)
- 📊 Statistics & Probability (Skills 223-245)

### The App (`app.py`)
Clean Streamlit interface with:
- Skill selector (domain → topic → skill)
- Confidence level slider
- Chat interface with math rendering
- Session management (new problem resets attempt counter)

## API Costs
Uses Claude Sonnet (`claude-sonnet-4-20250514`) which costs ~$3 per million input tokens and ~$15 per million output tokens. A typical tutoring session (10-20 messages) costs approximately $0.01-0.05. Your $5 in credits will support hundreds of sessions.

## Deployment Options

### Option A: Run Locally (Free)
```bash
streamlit run app.py
```

### Option B: Streamlit Cloud (Free)
1. Push code to a GitHub repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo and deploy
4. Students enter their own API key or you set it as a secret

### Option C: Custom Domain
1. Deploy to Streamlit Cloud
2. Use a custom domain (requires Streamlit Teams, or use a reverse proxy)

## Next Steps for Development

### Phase 1 (Current): Core Tutor
✅ System prompt with all pedagogical methods
✅ 245-skill catalog
✅ Streamlit chat interface
✅ Confidence-based scaffolding

### Phase 2: Enhanced Experience
- [ ] Student accounts (save progress)
- [ ] Skill mastery tracking
- [ ] Adaptive difficulty
- [ ] Practice problem generation
- [ ] Photo upload for handwritten problems

### Phase 3: Analytics
- [ ] Teacher dashboard
- [ ] Misconception frequency tracking
- [ ] Student progress reports
- [ ] Class-wide analytics

## Environment Variables (Optional)
Instead of entering the API key in the sidebar, you can set it as an environment variable:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```
Then modify `app.py` to read from `os.environ` as a fallback.

---

**Built by Mathful Minds** | Powered by Claude
