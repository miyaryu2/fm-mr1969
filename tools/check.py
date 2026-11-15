import functools, http.server, threading, sys
from playwright.sync_api import sync_playwright
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=sys.argv[1]); h.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8792), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
with sync_playwright() as pw:
    br = pw.chromium.launch(channel='chrome', headless=True)
    pg = br.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    for name in ('quick', 'manual'):
        pg.goto(f'http://127.0.0.1:8792/{name}.html'); pg.wait_for_timeout(500)
        pg.screenshot(path=f'check-{name}.png')
        r = pg.evaluate("""async () => { const v = document.querySelector('video'); v.muted = true; await v.play(); await new Promise(r => setTimeout(r, 1500));
          return {t: v.currentTime, dur: v.duration, w: v.videoWidth, h: v.videoHeight, overflow: document.documentElement.scrollWidth > innerWidth}; }""")
        print(name, r)
    br.close()
srv.shutdown()
