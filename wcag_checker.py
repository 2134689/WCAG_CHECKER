import sys
import json
import subprocess
import pandas as pd
import streamlit as st
import os

IS_CLOUD = os.getenv("STREAMLIT_SERVER_RUNNING") == "true"

from wcag_utils import (
    parse_rgb,          # ✅ IMPORTANT
    star_rating,
    suggest_wcag_color,
    rgb_to_hex,
)

try:
    from gemini_helper import gemini_color_suggestion
    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False


# -----------------------------
# Streamlit Page Setup
# -----------------------------
st.set_page_config(layout="wide")
st.title("WCAG Accessibility Audit – Professional Report")

url = st.text_input("Website URL")
USE_GEMINI = st.checkbox(
    "Use Gemini AI recommendations",
    disabled=not GEMINI_AVAILABLE
)


# -----------------------------
# Helpers
# -----------------------------
def run_batch_audit(url: str):
    """Runs batch WCAG audit and returns JSON result."""
    result = subprocess.run(
        [sys.executable, "playwright_worker.py", url],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        st.error("Playwright batch audit failed.")
        st.code(result.stderr)
        return None

    return json.loads(result.stdout)


def run_live_audit(url: str):
    """Launches live WCAG audit in a separate process."""
    subprocess.Popen(
        [sys.executable, "playwright_live_worker.py", url],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


# -----------------------------
# UI – Buttons
# -----------------------------
col1, col2 = st.columns(2)

with col1:
    run_audit_btn = st.button("Run WCAG Audit")

with col2:
    live_audit_btn = st.button("Live WCAG Audit")

st.caption(
    "ℹ️ Run WCAG Audit generates a report with annotated screenshot. "
    "Live WCAG Audit opens an interactive browser with hover tooltips."
)

live_audit_btn = st.button(
    "Live WCAG Audit",
    disabled=IS_CLOUD
)

if IS_CLOUD:
    st.warning(
        "Live WCAG Audit is disabled on Streamlit Cloud. "
        "Run locally for interactive auditing."
    )


# -----------------------------
# Live WCAG Audit
# -----------------------------
if live_audit_btn:
    if not url:
        st.warning("Please enter a website URL.")
    else:
        st.info("Launching Live WCAG Audit in a browser window…")
        run_live_audit(url)


# -----------------------------
# Batch WCAG Audit
# -----------------------------
if run_audit_btn:
    if not url:
        st.warning("Please enter a website URL.")
    else:
        with st.spinner("Running WCAG audit…"):
            data = run_batch_audit(url)

        if not data:
            st.stop()

        total_elements = data.get("total_elements", 0)
        failed_elements = data.get("failed_elements", [])
        screenshot = data.get("screenshot")

        # -----------------------------
        # Prepare Table Rows
        # -----------------------------
        rows = []

        for el in failed_elements:
            # 🔒 SAFE background parsing (handles rgb / rgba / skips invalid)
            bg_rgb = parse_rgb(el.get("background"))
            if not bg_rgb:
                continue

            required = el["required"]

            # deterministic WCAG-safe grayscale suggestion
            suggested_rgb = suggest_wcag_color(bg_rgb, required)
            suggested_hex = rgb_to_hex(suggested_rgb)

            gemini_text = None
            if USE_GEMINI:
                gemini_text = gemini_color_suggestion(
                    el["text"],
                    el["color"],
                    el["background"],
                    el["contrast"],
                    el["level"]
                )

            rows.append({
                "Text": el["text"][:80],
                "Font Size": el["fontSize"],
                "Foreground": el["color"],
                "Background": el["background"],
                "Contrast Ratio": el["contrast"],
                "WCAG Required": required,
                "Status": el["level"],
                "Suggested Color": f"{suggested_hex} / rgb{suggested_rgb}",
                "Gemini Recommendation": (
                    gemini_text
                    or "WCAG-compliant grayscale color improves readability."
                ),
            })

        df = pd.DataFrame(rows)

        # -----------------------------
        # Accessibility Score (CORRECT)
        # -----------------------------
        failures = len(failed_elements)
        pass_ratio = (total_elements - failures) / max(total_elements, 1)
        stars = star_rating(pass_ratio)

        # -----------------------------
        # Results UI
        # -----------------------------
        st.subheader("Accessibility Score")
        st.metric("WCAG Pass %", f"{pass_ratio * 100:.1f}%")
        st.metric("Star Rating", "⭐" * stars)

        st.subheader(f"WCAG Violations ({failures})")
        st.dataframe(df, width="stretch")

        if screenshot:
            st.subheader("Annotated Screenshot (Failures Only)")
            st.image(screenshot, width="stretch")
