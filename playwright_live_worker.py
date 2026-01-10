import sys
import asyncio
from playwright.async_api import async_playwright
import os

# Force Playwright to use a shared cache directory
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/tmp/ms-playwright"

async def fully_load_page(page):
    """Scroll through entire page to load lazy-loaded content."""
    last_height = 0
    while True:
        height = await page.evaluate("document.body.scrollHeight")
        if height == last_height:
            break
        last_height = height
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await page.wait_for_timeout(1200)
    
    await page.evaluate("window.scrollTo(0, 0)")
    await page.wait_for_timeout(1000)


async def live_audit(url):
    """Launch browser and inject WCAG 2.0 live audit."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )
        context = await browser.new_context(viewport=None)
        page = await context.new_page()
        
        await page.goto(url, timeout=90000)
        await page.wait_for_load_state("networkidle")
        await fully_load_page(page)
        
        # Inject WCAG audit script
        await page.evaluate(inject_wcag_audit())
        
        print("LIVE WCAG AUDIT RUNNING — close the browser manually when finished.")
        await page.wait_for_timeout(10**9)


def inject_wcag_audit():
    """Return WCAG audit JavaScript code."""
    return """
    () => {
        function luminance(r, g, b) {
            const a = [r, g, b].map(v => {
                v /= 255;
                return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
            });
            return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
        }

        function contrast(rgb1, rgb2) {
            const l1 = luminance(...rgb1);
            const l2 = luminance(...rgb2);
            return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
        }

        function parseRGB(str) {
            const m = str.match(/\\d+/g);
            return m ? m.map(Number).slice(0, 3) : null;
        }

        function rgbToHex([r, g, b]) {
            return "#" + [r, g, b]
                .map(x => x.toString(16).padStart(2, "0"))
                .join("")
                .toUpperCase();
        }

        function suggestColor(bg, minRatio) {
            for (let i = 0; i <= 255; i++) {
                const c = [i, i, i];
                if (contrast(c, bg) >= minRatio) return c;
            }
            return [0, 0, 0];
        }

        // Create tooltip
        const tooltip = document.createElement("div");
        tooltip.style.position = "fixed";
        tooltip.style.zIndex = "999999";
        tooltip.style.background = "#111";
        tooltip.style.color = "#fff";
        tooltip.style.padding = "10px";
        tooltip.style.borderRadius = "6px";
        tooltip.style.fontSize = "12px";
        tooltip.style.maxWidth = "320px";
        tooltip.style.display = "none";
        document.body.appendChild(tooltip);

        // Audit all elements
        document.querySelectorAll('*').forEach(el => {
            const style = window.getComputedStyle(el);
            if (!el.innerText || !el.innerText.trim()) return;

            const fg = parseRGB(style.color);
            const bg = parseRGB(style.backgroundColor);
            if (!fg || !bg) return;

            const ratio = contrast(fg, bg);
            const fontSize = parseFloat(style.fontSize);
            const large = fontSize >= 18;
            const required = large ? 3 : 4.5;

            if (ratio >= required) return;

            const level = ratio < required ? "AAA Fail" : "AA Fail";
            const outlineColor = level.includes("AAA") ? "red" : "yellow";
            const suggested = suggestColor(bg, required);
            const suggestedHex = rgbToHex(suggested);

            el.style.outline = `3px solid ${outlineColor}`;
            el.style.outlineOffset = "2px";
            el.style.cursor = "help";

            el.addEventListener("mouseenter", e => {
                tooltip.innerHTML = `
                    <b>WCAG Live Audit</b><br>
                    <hr style="border:none;border-top:1px solid #444;margin:6px 0;">
                    <b>Status:</b> ${level}<br>
                    <b>Contrast:</b> ${ratio.toFixed(2)}<br>
                    <b>Required:</b> ${required}<br><br>
                    <b>Suggested Color:</b><br>
                    <span style="display:inline-block; width:14px; height:14px; background:${suggestedHex}; border:1px solid #ccc; margin-right:6px;"></span>
                    <b>${suggestedHex}</b>
                `;
                tooltip.style.display = "block";
            });

            el.addEventListener("mousemove", e => {
                tooltip.style.left = (e.clientX + 12) + "px";
                tooltip.style.top = (e.clientY + 12) + "px";
            });

            el.addEventListener("mouseleave", () => {
                tooltip.style.display = "none";
            });
        });
    }
    """


if __name__ == "__main__":

    asyncio.run(live_audit(sys.argv[1]))
