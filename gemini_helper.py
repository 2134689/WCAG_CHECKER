import os
import google.generativeai as genai

def gemini_color_suggestion(text, fg, bg, ratio, level):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return "⚠️ API Key missing."

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = f"""
        System: Senior Accessibility Consultant.
        Text: "{text[:50]}" | Colors: {fg} on {bg} | Ratio: {ratio}:1 | Target: {level}
        
        Task: 
        1. Suggest a WCAG-compliant Hex.
        2. Give a one-sentence professional design reason.
        Format: [Fix] #HEX [Reason] Text.
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Unavailable: {str(e)}"
