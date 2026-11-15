"""フィールドマップの解説動画用に、アプリ画面を自動操作してフレーム画像を書き出す。

使い方: 作業用フォルダで `python record.py <開発フォルダ> [出力先フォルダ]` を実行する。
出力先(省略時は現在のフォルダ)に serve/ と frames/ ができる。mp4 への変換は README.md を参照。
"""
import functools, hashlib, http.server, json, math, os, re, shutil, sys, threading, time, urllib.request

from playwright.sync_api import sync_playwright

REPO = sys.argv[1]
HERE = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else os.getcwd())  # 出力先。リポジトリ内には書き出さない
SERVE = os.path.join(HERE, 'serve')
FRAMES = os.path.join(HERE, 'frames')
PORT = 8791
FPS = 10
W, H, CAP = 432, 768, 96

DB = 'https://fm-mr1969-default-rtdb.asia-southeast1.firebasedatabase.app'
ROOM = 'akagumi-demo'
KEY = hashlib.sha256(('fieldmap:' + ROOM).encode()).digest()[:16].hex()

# サンプルマップ(1200x800px)を 120m x 80m の架空フィールドとして扱う
LAT0, LON0, MPP = 35.6000, 140.1000, 0.1


def geo(x, y):
    return (LAT0 - y * MPP / 110540, LON0 + x * MPP / (111320 * math.cos(math.radians(LAT0))))


def db(method, path, body=None):
    req = urllib.request.Request(f'{DB}/rooms/{KEY}{path}.json', method=method,
                                 data=None if body is None else json.dumps(body).encode())
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.status


def peer_id(color_index):
    i = 0
    while True:
        pid = hashlib.md5(f'demo{color_index}-{i}'.encode()).hexdigest()[:16]
        if sum(map(ord, pid)) % 6 == color_index:
            return pid
        i += 1


def lerp(path, t):
    """折れ線 path 上の t(0..1) の位置。"""
    t = max(0.0, min(1.0, t)) * (len(path) - 1)
    i = min(int(t), len(path) - 2)
    f = t - i
    return (path[i][0] + (path[i + 1][0] - path[i][0]) * f, path[i][1] + (path[i + 1][1] - path[i][1]) * f)


PEERS = [
    {'id': peer_id(0), 'n': 'たろう', 'path': [(300, 300), (420, 360), (520, 300), (420, 360), (300, 300)]},
    {'id': peer_id(1), 'n': 'はなこ', 'path': [(900, 520), (820, 470), (760, 520), (820, 470), (900, 520)]},
]
peer_stop = threading.Event()


def peer_loop():
    t0 = time.time()
    while not peer_stop.is_set():
        ph = ((time.time() - t0) % 24) / 24
        for p in PEERS:
            x, y = lerp(p['path'], ph)
            lat, lon = geo(x, y)
            try:
                db('PUT', '/members/' + p['id'], {'n': p['n'], 'lat': round(lat, 6), 'lon': round(lon, 6), 'acc': 6, 't': {'.sv': 'timestamp'}})
            except Exception as e:
                print('peer put failed', e)
        peer_stop.wait(1.0)


STAGE = """<!doctype html><html lang="ja"><head><meta charset="utf-8"><style>
html,body{margin:0;width:%(W)dpx;height:%(H)dpx;overflow:hidden;background:#1f4a2a;
  font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans",sans-serif}
#cap{height:%(CAP)dpx;box-sizing:border-box;padding:12px 16px;color:#fff;display:flex;align-items:center;gap:12px}
#badge{flex:none;width:40px;height:40px;border-radius:50%%;background:#fff;color:#1f4a2a;font-weight:800;font-size:22px;
  display:grid;place-items:center}
#badge:empty{display:none}
#main{font-size:19px;font-weight:700;line-height:1.3}
#sub{font-size:13.5px;line-height:1.4;opacity:.92;margin-top:3px}
iframe{display:block;border:0;width:%(W)dpx;height:%(IH)dpx;background:#fff}
#ring{position:fixed;left:0;top:0;width:44px;height:44px;margin:-22px 0 0 -22px;border-radius:50%%;
  background:rgba(255,196,0,.45);border:3px solid #ffb300;box-shadow:0 0 0 2px rgba(0,0,0,.25);pointer-events:none;display:none}
</style></head><body>
<div id="cap"><div id="badge"></div><div><div id="main"></div><div id="sub"></div></div></div>
<iframe id="app" src="index.html"></iframe>
<div id="ring"></div>
<script>
function setCap(b,m,s){badge.textContent=b;main.textContent=m;sub.textContent=s}
function ring(x,y){const r=document.getElementById('ring');r.style.transform=`translate(${x}px,${y}px)`;r.style.display='block'}
function ringOff(){document.getElementById('ring').style.display='none'}
</script></body></html>""" % {'W': W, 'H': H, 'CAP': CAP, 'IH': H - CAP}


def main():
    for d in (SERVE, FRAMES):
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
    src = open(os.path.join(REPO, 'index.html'), encoding='utf-8').read()
    open(os.path.join(SERVE, 'index.html'), 'w', encoding='utf-8').write(src)
    open(os.path.join(SERVE, 'stage.html'), 'w', encoding='utf-8').write(STAGE)
    svg = re.search(r'const svg = `(.*?)`;', src, re.S).group(1)
    sample = os.path.join(HERE, 'sample.svg')
    open(sample, 'w', encoding='utf-8').write(svg)

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=SERVE)
    handler.log_message = lambda *a: None
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()

    print('room key', KEY, 'db test', db('PUT', '/members/' + PEERS[0]['id'], {'n': 'test', 'lat': LAT0, 'lon': LON0, 'acc': 6, 't': {'.sv': 'timestamp'}}))
    threading.Thread(target=peer_loop, daemon=True).start()

    n = [0]
    me = {'p': (600, 690)}
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch(channel='chrome', headless=True)
            lat, lon = geo(*me['p'])
            ctx = br.new_context(viewport={'width': W, 'height': H}, device_scale_factor=2, locale='ja-JP', color_scheme='light',
                                 permissions=['geolocation'], geolocation={'latitude': lat, 'longitude': lon, 'accuracy': 6})
            page = ctx.new_page()
            page.goto(f'http://127.0.0.1:{PORT}/stage.html')
            fr = page.frame_locator('#app')
            frame = next(f for f in page.frames if f.url.endswith('index.html'))
            frame.wait_for_function("typeof S !== 'undefined' && S.imgW > 0")
            # 公式マップ画像を動画に含めないよう、サンプルマップを「読み込んだ画像」として使う
            frame.set_input_files('#file', sample)
            frame.wait_for_function("S.mapId === 'custom' && S.imgW === 1200 && S.mode === 'view'")
            frame.wait_for_function("!!S.pos")

            def shot():
                page.screenshot(path=os.path.join(FRAMES, f'f{n[0]:05d}.jpg'), type='jpeg', quality=95)
                n[0] += 1

            def set_me(p):
                me['p'] = p
                la, lo = geo(*p)
                ctx.set_geolocation({'latitude': la, 'longitude': lo, 'accuracy': 6})

            def hold(sec, walk=None):
                k = max(1, round(sec * FPS))
                start = me['p']
                for i in range(k):
                    t0 = time.time()
                    if walk:
                        set_me(lerp([start] + walk, (i + 1) / k))
                    shot()
                    dt = 1 / FPS - (time.time() - t0)
                    if dt > 0:
                        time.sleep(dt)

            def cap(b, m, s):
                page.evaluate('([b,m,s]) => setCap(b,m,s)', [b, m, s])

            def tap_xy(x, y, pre=0.6, post=0.5):
                page.evaluate('([x,y]) => ring(x,y)', [x, y])
                hold(pre)
                page.mouse.click(x, y)
                page.evaluate('ringOff()')
                hold(post)

            def tap(sel, **kw):
                b = fr.locator(sel).first.bounding_box()
                tap_xy(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2, **kw)

            def tap_map(x, y, **kw):
                s = frame.evaluate("(() => { const r = map.getBoundingClientRect(); return {tx: S.tx, ty: S.ty, k: S.k, l: r.left, t: r.top}; })()")
                tap_xy(s['l'] + s['tx'] + x * s['k'], CAP + s['t'] + s['ty'] + y * s['k'], **kw)

            def typing(sel, text):
                tap(sel, pre=0.4, post=0.2)
                for ch in text:
                    page.keyboard.insert_text(ch)
                    hold(0.15)
                hold(0.3)

            # タイトル
            cap('', 'フィールドマップの使い方', '仲間の現在地をマップで共有するアプリです')
            hold(3)
            cap('1', '位置情報を許可する', 'アプリを開いたときに「許可」を選びます')
            hold(3.5)

            cap('2', '「画面を消灯しない」をオンにする', '「設定」を開いて切り替えます')
            hold(1.2)
            tap('nav button[data-mode="menu"]', post=0.9)
            tap('button[data-act="wake"]', post=1.4)
            tap('button[data-act="done"]')

            cap('3', '合言葉で共有に参加する', 'チーム全員が同じ合言葉を入れます')
            hold(1.2)
            tap('nav button[data-mode="share"]', post=0.9)
            typing('#shName', 'じろう')
            typing('#shRoom', ROOM)
            tap('button[data-act="sh-join"]', post=0.3)
            frame.wait_for_function("SH.status === 'ok' && SH.peers.length === 2", timeout=20000)
            cap('3', '合言葉で共有に参加する', '「共有 3人」と緑で出れば参加できています')
            hold(3.5)
            tap('button[data-act="done"]')

            cap('4', '位置合わせをする', 'チームで1人だけ行います。全員に反映されます')
            hold(2.2)
            tap('nav button[data-mode="cal"]', post=1.0)
            marks = [((105, 400), 'A陣地'), ((635, 215), '小屋'), ((1095, 400), 'B陣地')]
            for i, (pt, name) in enumerate(marks):
                cap('4', '位置合わせをする', f'目印({name})まで歩き、マップ上の同じ場所をタップ' if i == 0 else f'離れた目印({name})でも同じように登録します')
                hold(2.0 if i == 0 else 2.4, walk=[pt])
                tap_map(*pt, post=0.9)
                if i == 0:
                    cap('4', '位置合わせをする', '数秒立ち止まって「登録」を押します')
                    hold(1.6)
                tap('button[data-act="cal-gps"]', post=1.2)
            cap('4', '位置合わせをする', '3か所登録して「位置合わせ 3点」と出れば完了です')
            hold(2.5)
            tap('button[data-act="done"]', post=0.8)

            cap('5', 'これで準備完了', '青い丸が自分、名前付きの丸が仲間です')
            hold(8, walk=[(1000, 420), (880, 400), (760, 430), (640, 470)])

            cap('!', '画面はつけたままにする', '消えると仲間から見えなくなります。合言葉は相手チームに教えないでください')
            hold(4.5, walk=[(560, 470)])
            cap('', '詳しくは「使い方」を見てください', 'アプリ左上の「使い方」から開けます')
            hold(3)
            br.close()
    finally:
        peer_stop.set()
        time.sleep(1.2)
        try:  # ルーム全体の削除は権限がないので、参加者と位置合わせを個別に消す
            with urllib.request.urlopen(f'{DB}/rooms/{KEY}.json', timeout=10) as r:
                tree = json.loads(r.read().decode() or 'null') or {}
            for mid in (tree.get('members') or {}):
                db('DELETE', '/members/' + mid)
            if 'cal' in tree:
                db('DELETE', '/cal')
            with urllib.request.urlopen(f'{DB}/rooms/{KEY}.json', timeout=10) as r:
                print('cleanup: room =', r.read().decode())
        except Exception as e:
            print('cleanup failed', e)
        srv.shutdown()
    print('frames', n[0], 'seconds', n[0] / FPS)


main()
