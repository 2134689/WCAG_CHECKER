import sys
import asyncio
import os
from playwright.async_api import async_playwright
from gemini_helper import gemini_color_suggestion

AXE_CDN = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.9.1/axe.min.js"

async def live_audit(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(viewport=None)
        page = await context.new_page()

        # Bridge Gemini Python function to Browser Javascript
        async def get_ai_fix(text, fg, bg, ratio):
            return gemini_color_suggestion(text, fg, bg, ratio, "WCAG AA")
        
        await page.expose_function("getGeminiFix", get_ai_fix)

        async def run_axe_scan():
            try:
                await page.add_script_tag(url=AXE_CDN)
                # Specifically run color-contrast rule for performance
                results = await page.evaluate("axe.run(document, { rules: { 'color-contrast': { enabled: true } } })")
                contrast_fails = [v for v in results.get("violations", []) if v["id"] == "color-contrast"]

                # Initialize UI Container
                await page.evaluate("""() => {
                    document.querySelectorAll("[data-wcag-mark]").forEach(el => {
                        el.style.outline = "";
                        el.removeAttribute("data-wcag-mark");
                    });
                    if (!document.getElementById("__wcag_tip")) {
                        const tip = document.createElement("div");
                        tip.id = "__wcag_tip";
                        tip.style = `
                            position:fixed; z-index:2147483647; background:#18181b; color:#f4f4f5; 
                            padding:16px; border-radius:12px; font-size:13px; width:320px; 
                            display:none; pointer-events:none; font-family: 'Segoe UI', system-ui, sans-serif;
                            box-shadow: 0 20px 25px -5px rgba(0,0,0,0.4); border: 1px solid #3f3f46;
                            line-height: 1.5;
                        `;
                        document.body.appendChild(tip);
                    }
                }""")

                for fail in contrast_fails:
                    for node in fail["nodes"]:
                        selector = node["target"][0]
                        summary = node["failureSummary"]
                        
                        await page.evaluate("""async (data) => {
                            const el = document.querySelector(data.selector);
                            if (!el || el.hasAttribute("data-wcag-mark")) return;

                            el.style.outline = "3px solid #ef4444";
                            el.style.outlineOffset = "2px";
                            el.setAttribute("data-wcag-mark", "1");

                            el.addEventListener("mouseenter", async () => {
                                const tip = document.getElementById("__wcag_tip");
                                tip.style.display = "block";
                                tip.innerHTML = `
                                    <div style="color:#ef4444; font-weight:bold; font-size:11px; text-transform:uppercase; margin-bottom:4px;">Contrast Violation</div>
                                    <div style="color:#a1a1aa; font-size:12px; margin-bottom:12px;">${data.summary}</div>
                                    <div style="border-top: 1px solid #3f3f46; padding-top:10px;">
                                        <span style="color:#60a5fa; font-size:12px;">✨ Consulting Gemini AI...</span>
                                    </div>
                                `;
                                
                                const style = window.getComputedStyle(el);
                                const aiFix = await window.getGeminiFix(el.innerText, style.color, style.backgroundColor, "4.5:1");
                                
                                tip.innerHTML = `
                                    <div style="color:#ef4444; font-weight:bold; font-size:11px; text-transform:uppercase; letter-spacing:0.05em; margin-bottom:4px;">Contrast Violation</div>
                                    <div style="color:#a1a1aa; font-size:12px; margin-bottom:12px;">${data.summary}</div>
                                    <div style="border-top: 1px solid #3f3f46; padding-top:12px;">
                                        <div style="color:#60a5fa; font-weight:600; margin-bottom:6px; display:flex; align-items:center;">
                                            <span style="margin-right:6px;">✨</span> Professional Fix
                                        </div>
                                        <div style="background:#27272a; padding:10px; border-radius:8px; font-size:12px; color:#e4e4e7; border: 1px solid #3f3f46;">
                                            ${aiFix.replace(/\\n/g, '<br>')}
                                        </div>
                                    </div>
                                `;
                            });

                            el.addEventListener("mousemove", (e) => {
                                const tip = document.getElementById("__wcag_tip");
                                const gap = 20;
                                let x = e.clientX + gap;
                                let y = e.clientY + gap;
                                
                                // Boundary check to prevent off-screen tooltips
                                if (x + 340 > window.innerWidth) x = e.clientX - 340;
                                if (y + 240 > window.innerHeight) y = e.clientY - 240;
                                
                                tip.style.left = x + "px";
                                tip.style.top = y + "px";
                            });

                            el.addEventListener("mouseleave", () => {
                                document.getElementById("__wcag_tip").style.display = "none";
                            });
                        }""", {"selector": selector, "summary": summary})
            except Exception as e:
                print(f"Audit step failed: {e}")

        # Automatically re-audit on navigation
        page.on("load", lambda _: asyncio.create_task(run_axe_scan()))
        
        await page.goto(url)
        await run_axe_scan()
        
        # Keep process alive while browser is active
        while True:
            if not browser.is_connected():
                break
            await asyncio.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(live_audit(sys.argv[1]))
