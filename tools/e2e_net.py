import hashlib, json, secrets, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
URL = 'https://miyaryu2.github.io/fm-mr1969/'; DB = 'https://fm-mr1969-default-rtdb.asia-southeast1.firebasedatabase.app'
ROOM = 'e2e-' + secrets.token_hex(4); KEY = hashlib.sha256(('fieldmap:' + ROOM).encode()).digest()[:16].hex()
def g(lat, lon): return {'latitude': lat, 'longitude': lon, 'accuracy': 5}
def db(m, p):
    try:
        with urllib.request.urlopen(urllib.request.Request(f'{DB}/rooms/{KEY}{p}.json', method=m), timeout=10) as r: return json.loads(r.read().decode() or 'null')
    except urllib.error.HTTPError as e: return {'error': e.code}
PEER = "(() => { const q = SH.peers[0]; return q ? [q.lat, q.lon] : null; })()"
with sync_playwright() as pw:
    br = pw.chromium.launch(channel='chrome', headless=True)
    def dev(name, lat, lon):
        d = dict(pw.devices[name]); d.pop('default_browser_type', None)
        c = br.new_context(**d, locale='ja-JP', permissions=['geolocation'], geolocation=g(lat, lon)); p = c.new_page(); return c, p
    ca, A = dev('iPhone 14', 35.6000, 140.1000); cb, B = dev('Pixel 7', 35.6010, 140.1010)
    try:
        for pg, n in ((A, 'A'), (B, 'B')):
            pg.goto(URL); pg.wait_for_function("typeof S !== 'undefined' && S.imgW > 0 && !!S.pos", timeout=30000)
            pg.click('nav button[data-mode="share"]'); pg.fill('#shName', n); pg.fill('#shRoom', ROOM); pg.click('button[data-act="sh-join"]')
        for pg in (A, B): pg.wait_for_function("SH.status === 'ok' && SH.peers.length === 1", timeout=20000)
        sends = []
        B.on('requestfailed', lambda r: sends.append(('失敗', r.method)) if 'firebasedatabase' in r.url else None)
        B.on('requestfinished', lambda r: sends.append(('成功', r.method)) if 'firebasedatabase' in r.url and r.method == 'PUT' else None)
        print('圏外にする前: AからみたB =', A.evaluate(PEER))
        cb.set_offline(True)
        cb.set_geolocation(g(35.6020, 140.1020)); ca.set_geolocation(g(35.5990, 140.0990)); time.sleep(9)
        print('圏外中: Bの navigator.onLine =', B.evaluate("navigator.onLine"), '/ Bの共有表示 =', B.inner_text('#shChip'), '/ 受信の状態 readyState =', B.evaluate("SH.es.readyState"))
        print('圏外中: Bの送信 =', sends)
        print('圏外中: AからみたB =', A.evaluate(PEER), '(35.601 のままなら、Bの移動は届いていない=正しい)')
        print('圏外中: BからみたA =', B.evaluate(PEER), '(35.6 のままなら受信も止まっている。35.599 なら受信だけ続いている)')
        n0 = len(sends); cb.set_offline(False); t0 = time.time()
        while True:
            p = A.evaluate(PEER)
            if p and abs(p[0] - 35.6020) < 1e-5: break
            assert time.time() - t0 < 60, '60秒待ってもBの位置がAに届かない'; time.sleep(0.2)
        print(f'復帰後: Bの新しい位置がAに届くまで {time.time() - t0:.1f}秒 / その間のBの送信 = {sends[n0:]}')
        t0 = time.time(); ca.set_geolocation(g(35.5980, 140.0980))
        while True:
            p = B.evaluate(PEER)
            if p and abs(p[0] - 35.5980) < 1e-5: break
            assert time.time() - t0 < 60, '60秒待ってもAの位置がBに届かない'; time.sleep(0.2)
        print(f'復帰後: Aの移動がBに届くまで {time.time() - t0:.1f}秒 / Bの共有表示 = {B.inner_text("#shChip")}')
    finally:
        tree = db('GET', '') or {}
        for mid in (tree.get('members') or {}): db('DELETE', '/members/' + mid)
        print('後片付け: ルームの残り =', db('GET', '')); br.close()
