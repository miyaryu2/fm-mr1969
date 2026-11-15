import functools, http.server, threading, sys
from playwright.sync_api import sync_playwright
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=sys.argv[1]); h.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8793), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
ST = "({mapId: S.mapId, sample: S.sample, w: S.imgW, offline: S.offline, pos: !!S.pos, ctrl: !!navigator.serviceWorker.controller})"
with sync_playwright() as pw:
    br = pw.chromium.launch(channel='chrome', headless=True)
    ctx = br.new_context(viewport={'width': 390, 'height': 844}, permissions=['geolocation'], geolocation={'latitude': 35.6, 'longitude': 140.1, 'accuracy': 6})
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    U = 'http://127.0.0.1:8793/'
    pg.goto(U); pg.wait_for_function("S.imgW > 0"); pg.wait_for_function("S.offline === true", timeout=30000)
    print('1 初回(オンライン)   ', pg.evaluate(ST))
    pg.reload(); pg.wait_for_function("S.imgW > 0"); pg.wait_for_function("S.offline === true", timeout=15000)
    print('2 再読込(オンライン) ', pg.evaluate(ST))
    ctx.set_offline(True)
    pg.reload(); pg.wait_for_function("typeof S !== 'undefined' && S.imgW > 0", timeout=15000); pg.wait_for_timeout(1500)
    print('3 再読込(オフライン) ', pg.evaluate(ST))
    pg.click('nav button[data-mode="menu"]'); pg.wait_for_timeout(300)
    print('  設定の表示:', pg.locator('#sheet p', has_text='電波がない場所').inner_text())
    pg.screenshot(path='offline-app.png')
    for name in ('quick.html', 'manual.html', 'index.html'):
        r = pg.goto(U + name); print('  オフラインで', name, r.status, pg.title())
    ctx.set_offline(False)
    print('errors', errs)
    br.close()
srv.shutdown()
