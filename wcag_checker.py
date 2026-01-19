import streamlit as st
import os, sys, subprocess, json, pandas as pd
from dotenv import load_dotenv

# MUST BE FIRST
st.set_page_config(page_title="WCAG Auditor", page_icon="🛡️", layout="wide")

# Force Light Theme Visibility
st.markdown("""<style>
    .stApp { background-color: white !important; }
    h1, h2, h3, p, span, label, div { color: #262730 !important; }
    .stButton button { background-color: #262730 !important; color: white !important; }
</style>""", unsafe_allow_html=True)

load_dotenv()
from wcag_utils import parse_rgb, star_rating, suggest_wcag_color, rgb_to_hex
from gemini_helper import gemini_color_suggestion

# Detect Streamlit Cloud environment
IS_CLOUD = os.getenv("STREAMLIT_SERVER_RUNNING") or os.getenv("HOME") == "/home/appuser"

# Playwright Install for Cloud
if not os.path.exists("/home/appuser/.cache/ms-playwright"):
    try: 
        subprocess.run(["playwright", "install", "chromium"], check=True)
    except: 
        pass

st.title("🛡️ WCAG AI Accessibility Auditor")

url = st.text_input("Website URL", "https://3fitech.com/blogs/")

# --- Buttons Section with Unique Keys ---
col1, col2 = st.columns(2)

with col1:
    # Unique key 'btn_full_audit' prevents duplicate ID errors
    run_audit_btn = st.button("🚀 Run Full Audit", key="btn_full_audit", use_container_width=True)

with col2:
    # Unique key 'btn_live_audit' and environment check
    live_audit_btn = st.button(
        "👁️ Launch Live Audit", 
        key="btn_live_audit", 
        disabled=IS_CLOUD, 
        use_container_width=True,
        help="Live Audit is only available when running locally." if IS_CLOUD else "Launches interactive browser"
    )

# --- Full Audit Logic ---
if run_audit_btn:
    with st.spinner("Auditing..."):
        res = subprocess.run([sys.executable, "playwright_worker.py", url], capture_output=True, text=True)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            fails = data.get("failed_elements", [])
            total = data.get("total_elements", 0)
            
            score = (total - len(fails)) / max(total, 1)
            c1, c2 = st.columns(2)
            c1.metric("Compliance", f"{score*100:.1f}%")
            c2.metric("Rating", "⭐" * star_rating(score))
            
            rows = []
            for f in fails:
                bg = parse_rgb(f['background'])
                fix = rgb_to_hex(suggest_wcag_color(bg, f['required']))
                ai = gemini_color_suggestion(f['text'], f['color'], f['background'], f['contrast'], "AA")
                rows.append({
                    "Text": f['text'][:30], 
                    "Contrast": f['contrast'], 
                    "Fix": fix, 
                    "AI Advice": ai
                })
            
            st.subheader("Violation Report")
            st.table(pd.DataFrame(rows))
            
            if os.path.exists("wcag_report.png"): 
                st.subheader("Annotated Screenshot")
                st.image("wcag_report.png", use_container_width=True)
        else: 
            st.error("Audit failed. Check logs.")
            with st.expander("Technical Error"):
                st.code(res.stderr)

# --- Live Audit Logic (Local Only) ---
if live_audit_btn and not IS_CLOUD:
    st.info("Launching Live Audit browser window...")
    subprocess.Popen([sys.executable, "playwright_live_worker.py", url])
