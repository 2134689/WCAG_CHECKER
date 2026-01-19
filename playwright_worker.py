import sys
import json
import asyncio
from playwright.async_api import async_playwright


async def fully_load_page(page):
    """Scroll until page height stops increasing (lazy-load safe)."""
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


async def analyze(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized"]
        )

        context = await browser.new_context(viewport=None)
        page = await context.new_page()

        await page.goto(url, timeout=90000)
        await page.wait_for_load_state("networkidle")

        # 🔽 Ensure full page is rendered
        await fully_load_page(page)

        # 🔥 Compute WCAG + highlight FAILURES ONLY (JS-side)
        result = await page.evaluate("""
        () => {

            function luminance(r, g, b) {
                const a = [r, g, b].map(v => {
                    v /= 255;
                    return v <= 0.03928
                        ? v / 12.92
                        : Math.pow((v + 0.055) / 1.055, 2.4);
                });
                return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
            }

            function contrast(rgb1, rgb2) {
                const l1 = luminance(...rgb1);
                const l2 = luminance(...rgb2);
                return (Math.max(l1, l2) + 0.05) /
                       (Math.min(l1, l2) + 0.05);
            }

            function parseRGB(str) {
                const m = str.match(/\\d+/g);
                return m ? m.map(Number).slice(0, 3) : null;
            }

            let totalCount = 0;
            const failures = [];

            document.querySelectorAll('*').forEach((el, i) => {
                const style = window.getComputedStyle(el);

                if (
                    !el.innerText ||
                    !el.innerText.trim() ||
                    style.display === "none" ||
                    style.visibility === "hidden"
                ) return;

                totalCount++; // ✅ count EVERY visible text element

                const fg = parseRGB(style.color);
                const bg = parseRGB(style.backgroundColor);
                if (!fg || !bg) return;

                const ratio = contrast(fg, bg);
                const fontSize = parseFloat(style.fontSize);
                const large = fontSize >= 18;
                const required = large ? 3 : 4.5;

                if (ratio >= required) return; // ✅ PASS → no highlight

                // ❌ FAIL → highlight
                const level = ratio < required ? "AAA Fail" : "AA Fail";
                const outlineColor = level.includes("AAA") ? "red" : "yellow";

                el.style.outline = `3px solid ${outlineColor}`;
                el.style.outlineOffset = "2px";

                const r = el.getBoundingClientRect();

                failures.push({
                    id: i,
                    text: el.innerText.trim(),
                    color: style.color,
                    background: style.backgroundColor,
                    fontSize: style.fontSize,
                    contrast: Number(ratio.toFixed(2)),
                    required,
                    level,
                    x: r.x,
                    y: r.y,
                    w: r.width,
                    h: r.height
                });
            });

            return {
                totalCount,
                failures
            };
        }
        """)

        # 📸 Screenshot WITH FAIL-ONLY annotations
        screenshot = "wcag_report.png"
        await page.screenshot(path=screenshot, full_page=True)

        await page.wait_for_timeout(2000)
        await browser.close()

        return {
            "total_elements": result["totalCount"],
            "failed_elements": result["failures"],
            "screenshot": screenshot
        }


if __name__ == "__main__":
    print(json.dumps(asyncio.run(analyze(sys.argv[1]))))
