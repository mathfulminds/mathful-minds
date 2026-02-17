"""
Mathful Minds — Tutoring Engine
Handles all 5 confidence levels by generating structured content via Claude API.
The app controls the FLOW, Claude provides the CONTENT.
"""

import json
import base64
import anthropic
from prompt import build_system_prompt, get_level_prompt


def read_problem_from_image(client, image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """
    Read a math problem from an uploaded image using Claude's vision.
    Returns the extracted problem text for student confirmation.
    """
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": b64,
                    },
                },
                {
                    "type": "text",
                    "text": """Read the math problem from this image. Respond with ONLY a JSON object:

{"problem_text": "the math problem written clearly in text form", "is_clear": true, "notes": "any notes about unclear parts, empty string if clear"}

Rules:
- Write the problem exactly as shown, using standard math notation
- Use / for fractions, ^ for exponents, sqrt() for square roots
- If the image is unclear or you can't read parts of it, set is_clear to false and explain in notes
- If there are multiple problems, extract only the first one""",
                },
            ],
        }],
    )

    raw = response.content[0].text
    try:
        return parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        return {
            "problem_text": raw.strip(),
            "is_clear": True,
            "notes": "",
        }


def call_claude(client, system: str, user_message: str, max_tokens: int = 2048) -> str:
    """Make a single Claude API call and return the text response."""
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


def parse_json_response(text: str) -> dict:
    """Extract and parse JSON from Claude's response, handling markdown fences."""
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Try to find JSON object in the text
    start = cleaned.find("{")
    end = cleaned.rfind("}") + 1
    if start != -1 and end > start:
        cleaned = cleaned[start:end]

    return json.loads(cleaned)


def generate_worked_example(client, api_key: str, problem: str) -> dict:
    """
    Level 1: Generate a full worked example with two-column layout data.
    Returns structured steps + a practice problem.
    """
    system = build_system_prompt()
    prompt = get_level_prompt(1, problem)

    raw = call_claude(client, system, prompt)

    try:
        data = parse_json_response(raw)
        # Validate expected structure
        if "steps" not in data:
            raise ValueError("Missing 'steps' key")
        return data
    except (json.JSONDecodeError, ValueError):
        # Fallback: return the raw text as a single step
        return {
            "problem_restated": problem,
            "steps": [{"math": "", "explanation": raw}],
            "practice_problem": None,
            "simpler_example": None,
        }


def generate_mc_walkthrough(client, api_key: str, problem: str, num_options: int = 4) -> dict:
    """
    Levels 2-3: Generate a multi-step MC walkthrough.
    Level 2 = 2-3 options per step, Level 3 = 4 options per step.
    Returns all steps at once so the app can display them one at a time.
    """
    system = build_system_prompt()
    level = 2 if num_options <= 3 else 3
    prompt = get_level_prompt(level, problem, num_options=num_options)

    raw = call_claude(client, system, prompt)

    try:
        data = parse_json_response(raw)
        if "steps" not in data:
            raise ValueError("Missing 'steps' key")
        return data
    except (json.JSONDecodeError, ValueError):
        return {
            "problem_restated": problem,
            "steps": [],
            "error": "Could not generate walkthrough. Try again.",
            "raw": raw,
        }


def generate_open_ended_step(client, api_key: str, problem: str, step_history: list) -> dict:
    """
    Level 4: Generate the next open-ended prompt based on where the student is.
    Called step by step (one API call per step).
    """
    system = build_system_prompt()
    prompt = get_level_prompt(4, problem, step_history=step_history)

    raw = call_claude(client, system, prompt)

    try:
        data = parse_json_response(raw)
        return data
    except (json.JSONDecodeError, ValueError):
        return {
            "prompt": raw,
            "step_number": len(step_history) + 1,
            "is_final": False,
            "error": True,
        }


def evaluate_student_answer(client, api_key: str, problem: str, student_answer: str, context: str = "") -> dict:
    """
    Level 4-5: Evaluate a student's typed answer.
    Returns whether it's correct and provides feedback.
    """
    system = build_system_prompt()
    prompt = f"""The student is working on this problem: {problem}

{f"Context of where they are in the problem: {context}" if context else ""}

The student's answer is: {student_answer}

Evaluate their answer. Respond with ONLY a JSON object:
{{
    "is_correct": true or false,
    "feedback": "Brief, direct feedback (1-2 sentences max). If wrong, identify the specific error without giving the answer.",
    "correct_answer": "The correct answer or next step (only include if is_correct is true)"
}}"""

    raw = call_claude(client, system, prompt)

    try:
        return parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        return {
            "is_correct": False,
            "feedback": "Let me take another look at that. Can you try again?",
            "raw": raw,
        }


def generate_full_solution(client, api_key: str, problem: str) -> dict:
    """
    Generate the final full solution shown at the end (all levels).
    Two-column format: math left, explanation right.
    """
    system = build_system_prompt()
    prompt = f"""Generate a complete step-by-step solution for this problem: {problem}

Respond with ONLY a JSON object in this exact format:
{{
    "problem_restated": "The problem written clearly",
    "steps": [
        {{"math": "the mathematical expression or equation for this step", "explanation": "One clear sentence explaining what was done and why"}},
        {{"math": "next expression", "explanation": "Next explanation"}}
    ],
    "final_answer": "The final answer clearly stated"
}}

Rules for generating steps:
- Each step should have EXACTLY one mathematical operation
- Explanations must be ONE sentence — clear, direct, no jargon
- Use the specific teaching methods from your instructions (KCO for subtraction, KCF for division, butterfly method for fractions, formula framework for geometry, etc.)
- Vertically align the math — each step builds on the previous one
- Include units where appropriate
- For the first step, identify the variables or values given in the problem"""

    raw = call_claude(client, system, prompt)

    try:
        return parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        return {
            "problem_restated": problem,
            "steps": [{"math": "", "explanation": raw}],
            "final_answer": "",
        }


def generate_simpler_problem(client, api_key: str, original_problem: str) -> dict:
    """
    Level 1 'Show me a simpler problem' — generates a stripped-down version
    of the same concept with a full worked example.
    """
    system = build_system_prompt()
    prompt = f"""The student is struggling with this problem: {original_problem}

They've asked for a simpler version of the same concept. Generate:
1. A simpler problem that uses the same skill but with easier numbers or fewer steps
2. A full worked example of that simpler problem

Respond with ONLY a JSON object:
{{
    "simpler_problem": "The simpler version of the problem",
    "why_simpler": "One sentence explaining why this is a good starting point",
    "steps": [
        {{"math": "expression", "explanation": "One sentence explanation"}},
        {{"math": "expression", "explanation": "One sentence explanation"}}
    ],
    "final_answer": "The answer",
    "bridge": "One sentence connecting this back to the original problem"
}}"""

    raw = call_claude(client, system, prompt)

    try:
        return parse_json_response(raw)
    except (json.JSONDecodeError, ValueError):
        return {
            "simpler_problem": "Let me try a different approach.",
            "steps": [{"math": "", "explanation": raw}],
            "final_answer": "",
        }


def ask_followup_question(client, api_key: str, problem: str, conversation_history: list, question: str) -> str:
    """
    'Ask a question' feature — conversational follow-up at any point.
    """
    system = build_system_prompt()

    messages = []
    for msg in conversation_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": question})

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system + f"\n\nThe student is working on this problem: {problem}. They have a follow-up question. Be brief, clear, and direct. Answer in 2-4 sentences max.",
        messages=messages,
    )
    return response.content[0].text
