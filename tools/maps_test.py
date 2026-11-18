"""フィールドマップの切り替え・フィールドごとの保存・旧データの引き継ぎ・圏外を、手元のファイルに対して確認する。

使い方: python maps_test.py <開発フォルダ>
"""
import functools, http.server, threading, sys, json
from playwright.sync_api import sync_playwright
h = functools.partial(http.server.SimpleHTTPRequestHandler, directory=sys.argv[1]); h.log_message = lambda *a: None
srv = http.server.ThreadingHTTPServer(('127.0.0.1', 8794), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
U = 'http://127.0.0.1:8794/'; OFFICIAL = 'https://survivalgameparadise.com/wp-content/uploads/2025/04/ver06_01.png'
ST = "({id: S.mapId, sel: S.sel, w: S.imgW, sample: S.sample, start: !!S.start, cal: S.cal.length, credit: document.getElementById('credit').hidden ? '' : document.getElementById('credit').textContent, offline: S.offline})"
res = []
def ok(name, cond, info=''): res.append(bool(cond)); print(('OK  ' if cond else 'NG  ') + name, '…', info, flush=True)
def ready(pg): pg.wait_for_function("typeof S !== 'undefined' && S.imgW > 0 && S.mapId !== ''", timeout=30000); pg.wait_for_timeout(400)
def click_map(pg, name): pg.click('nav button[data-mode="menu"]') if pg.evaluate("S.mode") != 'menu' else None; pg.click(f'#sheet button[data-act="map"]:has-text("{name}")'); pg.wait_for_timeout(800)
with sync_playwright() as pw:
    br = pw.chromium.launch(channel='chrome', headless=True)
    def ctx(**kw):
        d = dict(pw.devices['iPhone 14']); d.pop('default_browser_type', None)
        c = br.new_context(**d, permissions=['geolocation'], geolocation={'latitude': 35.6, 'longitude': 140.1, 'accuracy': 5}, **kw)
        p = c.new_page(); errs = []; p.on('pageerror', lambda e: errs.append(str(e))); return c, p, errs
    # 1. 新規利用者
    c, p, errs = ctx()
    p.goto(U); ready(p); s = p.evaluate(ST)
    ok('初回は標準マップ(サバゲーパラダイス)', s['id'] == 'sabapara-v6' and s['w'] == 1344 and not s['credit'], s)
    p.click('nav button[data-mode="menu"]'); p.wait_for_timeout(300)
    names = p.locator('#sheet button[data-act="map"]').all_inner_texts()
    ok('設定にフィールドの選択肢が2つ出る', names == ['サバゲーパラダイス', '廃墟サバゲ'], names)
    ok('設定画面が横にはみ出さない', not p.evaluate("document.documentElement.scrollWidth > innerWidth"))
    p.evaluate("S.pending = {x: 100, y: 100}; addCal(35.6, 140.1)")
    click_map(p, '廃墟サバゲ'); s = p.evaluate(ST)
    ok('廃墟サバゲに切り替わり、位置合わせ4点が最初から入っている', s['id'] == 'haikyo-v1' and s['w'] == 810 and s['cal'] == 4, s)
    c.set_geolocation({'latitude': 35.952802, 'longitude': 139.5917058, 'accuracy': 5}); p.wait_for_timeout(1200)
    me = p.evaluate("(() => { const m = mePoint(); return m && [Math.round(m.x), Math.round(m.y)]; })()")
    ok('位置合わせなしで、青い丸が画像の正しい位置(中央)に出る', me and abs(me[0] - 405) <= 2 and abs(me[1] - 420) <= 2 and p.locator('#mkMe .me').is_visible(), me)
    c.set_geolocation({'latitude': 35.9525414, 'longitude': 139.5913392, 'accuracy': 5}); p.wait_for_timeout(1200)
    me = p.evaluate("(() => { const m = mePoint(); return [Math.round(m.x), Math.round(m.y)]; })()")
    ok('別の地点(左下寄り)でも正しい位置に出る', abs(me[0] - 200) <= 2 and abs(me[1] - 600) <= 2, me)
    ok('廃墟サバゲでは出典(国土地理院)が表示される', '国土地理院' in s['credit'], s['credit'])
    ok('選んだボタンが緑になる', p.locator('#sheet button.pri[data-act="map"]').inner_text() == '廃墟サバゲ')
    p.screenshot(path='maps-menu.png')
    p.evaluate("S.start = {x: 400, y: 500}; save(); S.pending = {x: 100, y: 100}; addCal(35.601, 140.101); S.pending = {x: 800, y: 900}; addCal(35.600, 140.102)")
    click_map(p, 'サバゲーパラダイス'); s = p.evaluate(ST)
    ok('サバゲーパラダイスに戻すと、そちらの位置合わせ(1点)が戻る', s['id'] == 'sabapara-v6' and s['cal'] == 1 and not s['start'] and not s['credit'], s)
    click_map(p, '廃墟サバゲ'); s = p.evaluate(ST)
    ok('廃墟サバゲに戻すと、そちらのピンと位置合わせ(4+2点)が戻る', s['cal'] == 6 and s['start'], s)
    p.click('#sheet button[data-act="reset-cal"]'); p.wait_for_timeout(300); s = p.evaluate(ST)
    ok('「位置合わせを初期状態に戻す」で4点に戻る', s['cal'] == 4 and p.locator('#sheet button[data-act="reset-cal"]').inner_text() == '位置合わせを初期状態に戻す', s)
    p.evaluate("S.pending = {x: 10, y: 10}; addCal(35.6011, 140.1011); S.pending = {x: 20, y: 20}; addCal(35.6012, 140.1012)")
    p.reload(); ready(p); p.wait_for_function("S.offline === true", timeout=20000); s = p.evaluate(ST)
    ok('再読み込みしても廃墟サバゲのまま', s['id'] == 'haikyo-v1' and s['cal'] == 6 and s['start'] and s['offline'], s)
    c.set_offline(True); p.reload(); ready(p); s = p.evaluate(ST)
    ok('圏外で開き直しても廃墟サバゲが出る', s['id'] == 'haikyo-v1' and not s['sample'] and s['w'] == 810 and s['cal'] == 6, s)
    click_map(p, 'サバゲーパラダイス'); s = p.evaluate(ST)
    ok('圏外でもサバゲーパラダイスに切り替えられる(保存済み)', s['id'] == 'sabapara-v6' and s['w'] == 1344 and s['cal'] == 1, s)
    c.set_offline(False)
    p.screenshot(path='maps-sabapara.png')
    ok('[新規] プログラムエラーなし', not errs, errs); c.close()

    # 2. 旧版の利用者(サバゲーパラダイスで位置合わせ済み)
    c, p, errs = ctx()
    p.goto(U + 'quick.html')
    p.evaluate("localStorage.setItem('fieldmap.v1', JSON.stringify({start: {x: 5, y: 6}, flag: null, cal: [{x: 1, y: 2, lat: 35.6, lon: 140.1}, {x: 900, y: 700, lat: 35.599, lon: 140.102}], wake: true, map: 'sabapara-v6'}))")
    p.goto(U); ready(p); s = p.evaluate(ST)
    ok('[旧版] 位置合わせ2点とピンを引き継ぐ', s['id'] == 'sabapara-v6' and s['cal'] == 2 and s['start'], s)
    click_map(p, '廃墟サバゲ'); click_map(p, 'サバゲーパラダイス'); s = p.evaluate(ST)
    ok('[旧版] 切り替えて戻っても消えない', s['cal'] == 2 and s['start'] and p.evaluate("S.wake"), s)
    ok('[旧版] プログラムエラーなし', not errs, errs); c.close()

    # 3. 旧版で画像を読み込んでいた利用者
    c, p, errs = ctx()
    p.goto(U); ready(p)
    p.evaluate("""async () => { const cv = document.createElement('canvas'); cv.width = 300; cv.height = 200; cv.getContext('2d').fillRect(0, 0, 300, 200);
      const b = await new Promise(r => cv.toBlob(r, 'image/jpeg')); await idbSet('image', b);
      localStorage.setItem('fieldmap.v1', JSON.stringify({start: null, flag: null, cal: [{x: 1, y: 2, lat: 35.6, lon: 140.1}], wake: false})); }""")
    p.reload(); ready(p); s = p.evaluate(ST)
    ok('[旧版・読込画像] 読み込んだ画像と位置合わせを引き継ぐ', s['id'] == 'custom' and s['w'] == 300 and s['cal'] == 1, s)
    p.click('nav button[data-mode="menu"]'); names = p.locator('#sheet button[data-act="map"]').all_inner_texts()
    ok('[旧版・読込画像] 選択肢に「読み込んだ画像」が加わる', names == ['サバゲーパラダイス', '廃墟サバゲ', '読み込んだ画像'], names)
    click_map(p, '廃墟サバゲ'); click_map(p, '読み込んだ画像'); s = p.evaluate(ST)
    ok('[旧版・読込画像] 切り替えて戻っても残る', s['id'] == 'custom' and s['w'] == 300 and s['cal'] == 1, s)
    ok('[旧版・読込画像] プログラムエラーなし', not errs, errs); c.close()

    # 4. 公式マップが取れないとき
    c, p, errs = ctx(service_workers='block')
    c.route(OFFICIAL, lambda r: r.abort())
    p.goto(U); ready(p); s = p.evaluate(ST)
    ok('[公式取得失敗] サンプル表示になる', s['id'] == 'sample' and s['sample'], s)
    click_map(p, '廃墟サバゲ'); s = p.evaluate(ST)
    ok('[公式取得失敗] 廃墟サバゲには切り替えられる', s['id'] == 'haikyo-v1' and s['cal'] == 4 and not s['sample'] and not p.locator('#sampleTag').is_visible(), s)
    click_map(p, 'サバゲーパラダイス'); s = p.evaluate(ST); m = p.inner_text('#menuMsg')
    ok('[公式取得失敗] 切り替えに失敗しても廃墟サバゲのまま残り、理由が出る', s['id'] == 'haikyo-v1' and s['w'] == 810 and '読み込めません' in m, (s, m))
    ok('[公式取得失敗] プログラムエラーなし', not errs, errs); c.close()
    br.close()
srv.shutdown()
print(f'\n結果: {sum(res)} / {len(res)} 件成功')
