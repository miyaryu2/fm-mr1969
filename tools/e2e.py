"""公開中のフィールドマップを2台(iPhone相当・Android相当)で開き、共有・位置合わせ・圏外復帰を確認する。"""
import hashlib, json, math, secrets, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright

URL = 'https://miyaryu2.github.io/fm-mr1969/'
DB = 'https://fm-mr1969-default-rtdb.asia-southeast1.firebasedatabase.app'
ROOM = 'e2e-' + secrets.token_hex(4)
KEY = hashlib.sha256(('fieldmap:' + ROOM).encode()).digest()[:16].hex()
LAT0, LON0, MPP = 35.6000, 140.1000, 0.15
results = []

def geo(x, y):
    return {'latitude': LAT0 - y * MPP / 110540, 'longitude': LON0 + x * MPP / (111320 * math.cos(math.radians(LAT0))), 'accuracy': 5}

def check(name, ok, note=''):
    results.append((name, ok, note)); print(('OK  ' if ok else 'NG  ') + name + (f' … {note}' if note else ''), flush=True)

def step(name, fn):
    try:
        r = fn(); check(name, True, r or '')
    except Exception as e:
        check(name, False, str(e).splitlines()[0][:110])

def db(method, path):
    try:
        with urllib.request.urlopen(urllib.request.Request(f'{DB}/rooms/{KEY}{path}.json', method=method), timeout=10) as r:
            return json.loads(r.read().decode() or 'null')
    except urllib.error.HTTPError as e:
        return {'error': e.code}

def go(ctx, pg, p):
    ctx.set_geolocation(geo(*p)); la = geo(*p)['latitude']; lo = geo(*p)['longitude']
    pg.wait_for_function(f"S.pos && Math.abs(S.pos.lat - {la}) < 1e-6 && Math.abs(S.pos.lon - {lo}) < 1e-6", timeout=10000)

def peer_err(pg, p):
    return pg.evaluate("([x,y]) => { const q = SH.peers[0]; if (!q || !S.fit) return 9999; const i = geoToImg(q.lat, q.lon, S.fit); return Math.hypot(i.x - x, i.y - y); }", list(p))

with sync_playwright() as pw:
    br = pw.chromium.launch(channel='chrome', headless=True)
    def dev(name, start):
        d = dict(pw.devices[name]); d.pop('default_browser_type', None)
        ctx = br.new_context(**d, locale='ja-JP', permissions=['geolocation'], geolocation=geo(*start))
        pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        return ctx, pg, errs
    ca, A, ea = dev('iPhone 14', (700, 900))
    cb, B, eb = dev('Pixel 7', (400, 600))
    try:
        for nm, pg in (('iPhone相当', A), ('Android相当', B)):
            def t(pg=pg):
                pg.goto(URL); pg.wait_for_function("typeof S !== 'undefined' && S.imgW > 0", timeout=30000)
                s = pg.evaluate("({id: S.mapId, w: S.imgW, sample: S.sample, of: document.documentElement.scrollWidth > innerWidth, re: typeof shResume})")
                assert s['id'] == 'sabapara-v6' and s['w'] == 1344 and not s['sample'] and not s['of'], s
                assert s['re'] == 'function', '公開版が最新ではない'
                return f"公式マップ {s['w']}px、横はみ出しなし"
            step(f'[{nm}] アプリが開き、公式マップが表示される', t)
            step(f'[{nm}] GPS が取得され、緑で表示される', lambda pg=pg: (pg.wait_for_function("document.getElementById('gpsChip').className.includes('ok')", timeout=15000), pg.inner_text('#gpsChip'))[1])
            step(f'[{nm}] 「電波がない場所での表示: 準備済み」になる', lambda pg=pg: (pg.wait_for_function("S.offline === true", timeout=40000), '')[1])

        def join(pg, name):
            pg.click('nav button[data-mode="share"]'); pg.fill('#shName', name); pg.fill('#shRoom', ROOM); pg.click('button[data-act="sh-join"]')
            pg.wait_for_function("SH.status === 'ok'", timeout=20000); pg.click('button[data-act="done"]')
        step('[共有] iPhone相当が合言葉で参加できる', lambda: join(A, 'あいふぉん'))
        step('[共有] Android相当が同じ合言葉で参加できる', lambda: join(B, 'あんどろ'))
        def t():
            for pg in (A, B): pg.wait_for_function("SH.peers.length === 1 && document.getElementById('shChip').textContent === '共有 2人'", timeout=20000)
            return f"相手の名前: {A.evaluate('SH.peers[0].n')} / {B.evaluate('SH.peers[0].n')}"
        step('[共有] 互いに「共有 2人」と表示され、相手の名前が見える', t)

        pts = [(130, 537), (1028, 172), (1075, 810)]
        def t():
            A.click('nav button[data-mode="cal"]')
            for p in pts:
                go(ca, A, p)
                s = A.evaluate("(() => { const r = map.getBoundingClientRect(); return {x: r.left + S.tx, y: r.top + S.ty, k: S.k}; })()")
                A.mouse.click(s['x'] + p[0] * s['k'], s['y'] + p[1] * s['k'])
                A.wait_for_function("!!S.pending", timeout=5000); A.click('button[data-act="cal-gps"]')
            A.wait_for_function("S.cal.length === 3 && S.fit && S.fit.kind === 'affine'", timeout=5000); A.click('button[data-act="done"]')
            return A.inner_text('#calChip')
        step('[位置合わせ] iPhone相当が目印3か所を登録できる', t)
        step('[位置合わせ] Android相当に自動で反映される(操作なし)', lambda: (B.wait_for_function("S.cal.length === 3 && !!S.fit", timeout=15000), B.inner_text('#calChip'))[1])
        def t():
            e = A.evaluate("(() => { const m = mePoint(); return Math.hypot(m.x - 1075, m.y - 810); })()"); assert e < 2, e
            assert A.evaluate("!document.getElementById('mkMe').hidden")
            return f'誤差 {e:.1f}px'
        step('[位置合わせ] 青い丸が自分の場所(3点目)に表示される', t)

        def t():
            target = (600, 500); go(ca, A, target); t0 = time.time()
            B.wait_for_function("SH.peers.length === 1", timeout=10000)
            while peer_err(B, target) > 3:
                assert time.time() - t0 < 20, f'20秒待っても反映されない(誤差 {peer_err(B, target):.0f}px)'; time.sleep(0.25)
            vis = B.evaluate("document.getElementById('peerMarks').children.length === 1 && !document.getElementById('peerMarks').children[0].hidden")
            assert vis, 'マーカーが表示されていない'
            return f'{time.time() - t0:.1f}秒で反映、誤差 {peer_err(B, target):.1f}px'
        step('[共有] iPhone相当が移動すると、Android相当のマップ上で追従する', t)

        def t():
            cb.set_offline(True); time.sleep(8)
            st = B.evaluate("SH.status"); target = (900, 300); go(ca, A, target); go(cb, B, (300, 700)); time.sleep(4)
            assert peer_err(B, target) > 3, '圏外なのに更新された'
            before = A.evaluate("(SH.tree.members[Object.keys(SH.tree.members).find(k => k !== SH.id)] || {}).t")
            cb.set_offline(False); t0 = time.time()
            while peer_err(B, target) > 3:
                assert time.time() - t0 < 60, '60秒待っても相手の位置が戻らない'; time.sleep(0.25)
            t1 = time.time() - t0
            while A.evaluate("(SH.tree.members[Object.keys(SH.tree.members).find(k => k !== SH.id)] || {}).t") == before:
                assert time.time() - t0 < 60, '60秒待っても自分の位置が相手に届かない'; time.sleep(0.25)
            return f'圏外中の表示「{B.inner_text("#shChip") if False else st}」、復帰後 受信 {t1:.1f}秒 / 送信 {time.time() - t0:.1f}秒で再開'
        step('[電波] Android相当が圏外になり、戻ると共有が自動で再開する', t)

        def t():
            cb.set_offline(True); B.reload(); B.wait_for_function("typeof S !== 'undefined' && S.imgW > 0", timeout=20000); time.sleep(1.5)
            s = B.evaluate("({id: S.mapId, sample: S.sample, cal: S.cal.length, me: !document.getElementById('mkMe').hidden})")
            cb.set_offline(False)
            assert s['id'] == 'sabapara-v6' and not s['sample'] and s['cal'] == 3 and s['me'], s
            return '公式マップ・位置合わせ3点・青い丸を表示'
        step('[電波] 圏外で開き直しても、マップと自分の位置が表示される', t)
        step('[電波] 電波が戻ると、開き直したあとも共有に自動で復帰する', lambda: (B.wait_for_function("SH.status === 'ok' && SH.peers.length === 1", timeout=40000), B.inner_text('#shChip'))[1])

        def t():
            B.click('nav button[data-mode="cal"]'); B.locator('button[data-act="cal-del"]').first.click(); B.click('button[data-act="done"]')
            A.wait_for_function("S.cal.length === 2", timeout=15000)
            return '確認なしで全員分が消える(誤消去の危険あり)'
        step('[位置合わせ] 1人が点を削除すると、相手の端末からも消える', t)

        def t():
            B.click('nav button[data-mode="share"]'); B.click('button[data-act="sh-leave"]')
            A.wait_for_function("SH.peers.length === 0 && document.getElementById('shChip').textContent === '共有 1人'", timeout=15000)
        step('[共有] 「共有をやめる」と、相手の画面から消える', t)

        for name, title in (('quick.html', 'かんたんガイド'), ('manual.html', '使い方')):
            def t(name=name, title=title):
                B.goto(URL + name); assert title in B.title(), B.title()
                r = B.evaluate("""async () => { const v = document.querySelector('video'); v.muted = true; await v.play(); await new Promise(r => setTimeout(r, 1500));
                  return {t: v.currentTime, of: document.documentElement.scrollWidth > innerWidth}; }""")
                assert r['t'] > 0.5 and not r['of'], r
                return '動画が再生でき、横はみ出しなし'
            step(f'[マニュアル] Android相当で {name} が開き、動画が再生できる', t)
        check('[全体] 画面上のプログラムエラーなし', not ea and not eb, '; '.join(ea + eb)[:120])
    finally:
        try: A.evaluate("typeof shLeave === 'function' && shLeave()")
        except Exception: pass
        time.sleep(1); tree = db('GET', '') or {}
        for mid in (tree.get('members') or {}): db('DELETE', '/members/' + mid)
        if 'cal' in tree: db('DELETE', '/cal')
        print('後片付け: ルームの残り =', db('GET', ''), flush=True)
        br.close()
ng = [r for r in results if not r[1]]
print(f'\n結果: {len(results) - len(ng)} / {len(results)} 件成功')
