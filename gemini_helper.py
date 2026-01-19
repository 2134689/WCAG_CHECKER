import os
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()  

def gemini_color_suggestion(text, fg, bg, ratio, level):
    # Ensure your .env file uses GEMINI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return "⚠️ API Key missing. Please set GEMINI_API_KEY."

    try:
        genai.configure(api_key=api_key)
        # Use flash model for high-speed live interactions
        model = genai.GenerativeModel("gemini-2.5-flash")

        prompt = f"""
        System: You are a Senior UI/UX Accessibility Consultant.
        
        Element Context:
        - Content: "{text[:50]}"
        - Current Colors: Text {fg} on Background {bg}
        - Current Ratio: {ratio}:1
        - Target Level: {level}

        Task:
        1. Provide a specific WCAG-compliant Hex code for the foreground.
        2. Provide a one-sentence professional design rationale.

        Format:
        [Fix] #HEXCODE
        [Rationale] Professional explanation here.
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Recommendation currently unavailable: {str(e)}"
