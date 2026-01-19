import sys, json, asyncio
from playwright.async_api import async_playwright

async def analyze(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 800})
        page = await context.new_page()
        try:
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            result = await page.evaluate("""
            () => {
                function lum(r,g,b){const a=[r,g,b].map(v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return a[0]*.2126+a[1]*.7152+a[2]*.0722}
                function parse(s){const m=s.match(/\\d+/g);return m?m.map(Number).slice(0,3):null}
                let total=0; const fails=[];
                document.querySelectorAll('*').forEach((el, i) => {
                    const s = window.getComputedStyle(el);
                    if(!el.innerText || !el.innerText.trim() || s.display==='none') return;
                    total++;
                    const fg=parse(s.color), bg=parse(s.backgroundColor);
                    if(!fg || !bg) return;
                    const l1=lum(...fg), l2=lum(...bg), ratio=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);
                    const req = parseFloat(s.fontSize) >= 18 ? 3 : 4.5;
                    if(ratio < req) {
                        el.style.outline="3px solid red";
                        fails.push({text:el.innerText.trim(), color:s.color, background:s.backgroundColor, contrast:ratio.toFixed(2), required:req, level:"Fail"});
                    }
                });
                return {total, fails};
            }""")
            await page.screenshot(path="wcag_report.png", full_page=True)
            return {"total_elements": result["total"], "failed_elements": result["fails"], "screenshot": "wcag_report.png"}
        finally: await browser.close()

if __name__ == "__main__":
    if len(sys.argv) > 1: print(json.dumps(asyncio.run(analyze(sys.argv[1]))))
