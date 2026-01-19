import sys
import json
import subprocess
import pandas as pd
import streamlit as st
import os
from dotenv import load_dotenv
import os
import subprocess

# Auto-install Playwright browsers if they are missing on the Cloud
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except Exception as e:
        st.error(f"Failed to install Playwright: {e}")

# Force a clean Light Theme UI
st.markdown("""
    <style>
    /* Force background to white and text to dark gray */
    .stApp {
        background-color: white !important;
    }
    h1, h2, h3, p, span, div, label {
        color: #262730 !important;
    }
    /* Fix button text visibility */
    .stButton button {
        color: white !important;
        background-color: #262730 !important;
    }
    /* Fix info box text */
    .stAlert p {
        color: #1f2937 !important;
    }
    </style>
""", unsafe_allow_html=True)
# Load environment variables
load_dotenv()

from wcag_utils import (
    parse_rgb,
    star_rating,
    suggest_wcag_color,
    rgb_to_hex,
)

try:
    from gemini_helper import gemini_color_suggestion
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False

# 1. Detect Environment
# Streamlit Cloud sets specific environment variables. 
# We use this to disable features that require a physical monitor.
IS_CLOUD = os.getenv("STREAMLIT_SERVER_RUNNING") or os.getenv("HOME") == "/home/appuser"

st.set_page_config(
    page_title="WCAG AI Auditor",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS for professional look
# Custom CSS to fix visibility and force contrast
st.markdown("""
    <style>
    /* Force the main area to have a consistent background and text color */
    .stApp {
        background-color: #FFFFFF !important;
    }
    h1, h2, h3, p, span, label {
        color: #1A1A1A !important;
    }
    /* Style the metrics cards specifically */
    [data-testid="stMetricValue"] {
        color: #1A1A1A !important;
    }
    .stMetric {
        background-color: #F0F2F6 !important;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #DDE1E6;
    }
    </style>
    """, unsafe_allow_html=True)
# Sidebar Configuration
with st.sidebar:
    st.header("Settings")
    url = st.text_input("Website URL", placeholder="https://example.com")
    
    use_gemini = st.checkbox(
        "Use Gemini AI recommendations", 
        value=True,
        disabled=not GEMINI_AVAILABLE,
        help="Provides professional design justifications for color fixes."
    )
    
    if not GEMINI_AVAILABLE:
        st.error("Gemini API not configured. Check your GEMINI_API_KEY.")

st.divider()

# 2. Audit Functions
def run_batch_audit(target_url: str):
    """Runs the Playwright worker and captures JSON output."""
    # On Streamlit Cloud, we must ensure playwright browsers are installed
    # Usually handled by a post-install script, but we can verify here.
    try:
        result = subprocess.run(
            [sys.executable, "playwright_worker.py", target_url],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        st.error("Playwright audit failed.")
        with st.expander("Show Technical Error"):
            st.code(e.stderr)
        return None
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return None

def run_live_audit(target_url: str):
    """Launches the interactive browser window (Local Only)."""
    subprocess.Popen([sys.executable, "playwright_live_worker.py", target_url])

# 3. UI Layout
col1, col2 = st.columns(2)

with col1:
    run_audit_btn = st.button("🚀 Run Full Batch Audit", use_container_width=True)

with col2:
    live_help = "Disabled on Cloud (requires a local display)" if IS_CLOUD else "Launches interactive browser"
    live_audit_btn = st.button(
        "👁️ Launch Live Audit", 
        disabled=IS_CLOUD, 
        use_container_width=True,
        help=live_help
    )

if IS_CLOUD:
    st.info("💡 **Tip:** Running on the cloud? Full Batch Audits are fully supported. Live Audits require a local machine to open a browser window.")

# -----------------------------
# Processing Logic
# -----------------------------
if run_audit_btn:
    if not url:
        st.warning("Please enter a valid URL first.")
    else:
        with st.spinner("🔍 Analyzing page structure and contrast..."):
            data = run_batch_audit(url)

        if data:
            total_elements = data.get("total_elements", 0)
            failed_elements = data.get("failed_elements", [])
            screenshot_path = data.get("screenshot")

            # Prepare Report Data
            rows = []
            for el in failed_elements:
                bg_rgb = parse_rgb(el.get("background"))
                if not bg_rgb: continue

                required = el.get("required", 4.5)
                
                # Default logic from wcag_utils
                suggested_rgb = suggest_wcag_color(bg_rgb, required)
                suggested_hex = rgb_to_hex(suggested_rgb)

                gemini_text = "Standard Fix"
                if use_gemini:
                    gemini_text = gemini_color_suggestion(
                        el.get("text", ""),
                        el.get("color", ""),
                        el.get("background", ""),
                        el.get("contrast", 0),
                        el.get("level", "Fail"),
                    )

                rows.append({
                    "Element Text": el.get("text", "")[:50],
                    "Font": el.get("fontSize"),
                    "Current Contrast": f"{el.get('contrast')}:1",
                    "Required": f"{required}:1",
                    "Status": el.get("level"),
                    "Suggested Hex": suggested_hex,
                    "AI Recommendation": gemini_text
                })

            # Dashboard Metrics
            failures = len(failed_elements)
            pass_ratio = (total_elements - failures) / max(total_elements, 1)
            stars = star_rating(pass_ratio)

            m1, m2, m3 = st.columns(3)
            m1.metric("Compliance Score", f"{pass_ratio * 100:.1f}%")
            m2.metric("Violations Found", failures, delta=-failures, delta_color="inverse")
            m3.metric("Rating", "⭐" * stars)

            # Detailed Report
            st.subheader("📋 Detailed Violation Report")
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Screenshot
            if screenshot_path and os.path.exists(screenshot_path):
                st.subheader("📸 Annotated Failure Map")
                st.image(screenshot_path, caption="Red outlines indicate contrast failures.", use_container_width=True)
                
                # Download Button for the report
                with open(screenshot_path, "rb") as file:
                    st.download_button(
                        label="Download Annotated Screenshot",
                        data=file,
                        file_name="wcag_audit_report.png",
                        mime="image/png"
                    )

if live_audit_btn and not IS_CLOUD:
    if not url:
        st.warning("Please enter a URL.")
    else:
        st.success(f"Launching Live Audit for {url}...")
        run_live_audit(url)


