import os

try:
    import google.genai
except ImportError:
    genai = None


def gemini_color_suggestion(text, fg, bg, ratio, level):
    if genai is None:
        return None

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-pro")

    prompt = f"""
You are an accessibility expert.

Text: "{text}"
Foreground: {fg}
Background: {bg}
Current contrast ratio: {ratio}
Target WCAG level: {level}

Suggest a WCAG-compliant foreground color.
Explain WHY this color improves accessibility.

Respond in this format:
Color: #HEXCODE
Explanation: <professional explanation>
"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return None
