#!/usr/bin/env python3
"""AMG65 屏幕控制面板 — 本地服务 (macOS)
用法: python3 server.py [端口]   默认 http://127.0.0.1:8655
依赖: amg65.py (同目录上级 tool/ 也可), hidapi, pyusb, Pillow
"""
import io, json, os, sys, time, datetime, base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from PIL import Image  # noqa: 模块级导入, fit_image 依赖

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'tool'))   # tool/amg65.py + strip.py
sys.path.insert(0, HERE)
from amg65 import AMG65, SCREEN_W, SCREEN_H, FRAME_BYTES  # noqa
import strip as STRP  # noqa
import presets as PRESETS  # noqa

STATE = {'kb': None, 'lock': None}
import threading
STATE['lock'] = threading.Lock()


def get_kb():
    with STATE['lock']:
        return STATE['kb']


def reset_kb():
    with STATE['lock']:
        try:
            if STATE['kb']:
                STATE['kb'].close()
        except Exception:
            pass
        STATE['kb'] = None


def with_kb(fn):
    """执行 fn(kb)，连接失效时自动重连一次"""
    kb = get_kb()
    if kb is None:
        kb = reset_kb() or None
    try:
        if kb is None:
            with STATE['lock']:
                STATE['kb'] = AMG65(verbose=False)
                kb = STATE['kb']
        return fn(kb)
    except Exception as e:
        msg = str(e)
        if 'write' in msg or 'read' in msg or '找不到' in msg or '未找到' in msg or 'NO_DEVICE' in msg.upper():
            reset_kb()
            with STATE['lock']:
                STATE['kb'] = AMG65(verbose=False)
                kb = STATE['kb']
            return fn(kb)
        raise


def png_dataurl(pil_image):
    buf = io.BytesIO()
    pil_image.save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _cors(self):
        # The desktop shell loads the UI from file:// while the backend stays on
        # localhost. These headers also keep the browser dev server usable.
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')

    def _json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _file(self, name, ctype):
        path = os.path.join(HERE, name)
        try:
            data = open(path, 'rb').read()
        except FileNotFoundError:
            self._json({'error': 'not found'}, 404)
            return
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    # ------------ API ------------
    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            return self._file('index.html', 'text/html; charset=utf-8')
        if self.path == '/api/health':
            return self._json({'ok': True, 'service': 'amg65-panel', 'version': '1.1.0'})
        if self.path.startswith('/static/'):
            name = os.path.basename(self.path[len('/static/'):])
            ctype = 'image/png' if name.endswith('.png') else 'application/octet-stream'
            return self._file(os.path.join('static', name), ctype)
        if self.path == '/api/strip/status':
            return self._json({'mode': STRIP['mode'],
                               'color': '#%02x%02x%02x' % STRIP['color'],
                               'time': datetime.datetime.now().strftime('%H:%M:%S'),
                               'sit': sit_status(), 'agents': agent_status()})
        if self.path == '/api/agent/hooks':
            return self._json({'hooks': hooks_status(),
                               'autostart': bool(load_settings().get('agent_autostart'))})
        if self.path == '/api/strip/presets':
            if not preset_database_available():
                return self._json({'presets': [], 'available': False,
                                   'reason': '需要本机官方驱动中的 ledlayer_v2.data'})
            return self._json({'presets': [{'name': k, 'label': v[1]} for k, v in PRESETS.PRESETS.items()],
                               'available': True})
        if self.path == '/api/status':
            try:
                r = with_kb(lambda kb: locked_ping(kb))
                return self._json({'ok': bool(r),   # 任何应答都说明设备在线 (02 类固件回 FF 属正常)
                                   'device': 'LEOBOG AMG65', 'screen': [SCREEN_W, SCREEN_H]})
            except Exception as e:
                return self._json({'ok': False, 'error': str(e)})
        return self._json({'error': 'not found'}, 404)

    def do_POST(self):
        from urllib.parse import urlparse, parse_qs
        n = int(self.headers.get('Content-Length') or 0)
        body = self.rfile.read(n) if n else b''
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        try:
            if u.path == '/api/upload':
                return self._json(self.api_upload(body, q))
            if u.path == '/api/time':
                return self._json(self.api_time())
            if u.path == '/api/strip':
                return self._json(self.api_strip(u.path, q, body))
            if u.path == '/api/strip/upload':
                return self._json(self.api_strip_upload(body, q))
            if u.path == '/api/strip/sit':
                return self._json(self.api_sit(body))
            if u.path == '/api/agent':
                return self._json(agent_event(q.get('agent'), q.get('event'), body))
            if u.path == '/api/agent/hooks':
                req = json.loads(body or b'{}')
                agent, action = req.get('agent'), req.get('action')
                if agent not in HOOK_CONF or action not in ('install', 'uninstall'):
                    return self._json({'ok': False, 'error': '参数错误'}, 400)
                (hooks_install if action == 'install' else hooks_uninstall)(agent)
                return self._json({'ok': True, 'hooks': hooks_status()})
            if u.path == '/api/agent/settings':
                req = json.loads(body or b'{}')
                s = save_settings(agent_autostart=bool(req.get('autostart')))
                return self._json({'ok': True, 'settings': s})
            return self._json({'error': 'not found'}, 404)
        except Exception as e:
            return self._json({'ok': False, 'error': str(e)}, 500)

    # ------------ 实现 ------------
    def api_upload(self, body, q):
        from PIL import ImageDraw, ImageSequence
        kind = q.get('kind', 'gif')
        kbox = {}
        def _prep(kb): kbox['kb'] = kb
        with_kb(_prep)
        kb = kbox['kb']
        frames_rgb, delays = [], []

        if kind == 'image':
            im = Image.open(io.BytesIO(body)).convert('RGB')
            if im.size != (SCREEN_W, SCREEN_H):
                im = fit_image(im)
            frames_rgb = [im]
            delays = [int(q.get('delay', 100))]
        elif kind == 'gif':
            fps = q.get('fps')
            max_frames = int(q.get('max', 130))
            im = Image.open(io.BytesIO(body))
            for i, fr in enumerate(ImageSequence.Iterator(im)):
                if i >= max_frames:
                    break
                rgb = fr.convert('RGB')
                if rgb.size != (SCREEN_W, SCREEN_H):
                    rgb = fit_image(rgb)
                frames_rgb.append(rgb)
                d = fr.info.get('duration', 80)
                delays.append(max(20, int(d)))
            if fps:
                delays = [round(1000 / float(fps))] * len(frames_rgb)
        elif kind == 'text':
            q = json.loads(body.decode())
            img = Image.new('RGB', (SCREEN_W, SCREEN_H), hex2rgb(q.get('bg', '101020')))
            d = ImageDraw.Draw(img)
            font = load_font(int(q.get('size', 64)))
            bbox = d.textbbox((0, 0), q.get('text', ''), font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            d.text(((SCREEN_W - w) // 2 - bbox[0], (SCREEN_H - h) // 2 - bbox[1]),
                   q.get('text', ''), font=font, fill=hex2rgb(q.get('color', 'FFFFFF')))
            frames_rgb = [img]
            delays = [int(q.get('delay', 100))]
        elif kind == 'color':
            q = json.loads(body.decode())
            c = hex2rgb(q.get('rgb', 'FF6600'))
            img = Image.new('RGB', (SCREEN_W, SCREEN_H), c)
            frames_rgb = [img]
            delays = [int(q.get('delay', 100))]
        else:
            raise ValueError('未知类型 ' + kind)

        frames = [kb.rgb565_frame(f.tobytes()) for f in frames_rgb]
        t0 = time.time()
        with STATE['lock']:
            kb.upload_screen(frames, delays, brightness=int(q.get('brightness', 0)))
        prev = frames_rgb[0].resize((SCREEN_W * 2, SCREEN_H * 2), Image.NEAREST)
        return {'ok': True, 'frames': len(frames), 'seconds': round(time.time() - t0, 1),
                'preview': png_dataurl(prev)}

    def api_time(self):
        """时间同步 —— 有线模式走 04 28 (驱动 0x42ab10, 固件 0x4290):
        04 18 -> 04 28(D[8]=1) -> [00 01 5A 年 月 日 时 分 秒 00 星期 .. AA55@62] -> 04 02
        (旧代码发的 0C 10 是驱动无线模式用的包, 有线下固件只认 04 类, 回 FF 拒绝)"""
        kbox = {}
        with_kb(lambda kb: kbox.update(kb=kb))
        kb = kbox['kb']
        now = datetime.datetime.now()
        p = bytearray(64)
        p[1] = 1; p[2] = 0x5A
        p[3] = now.year % 2000; p[4] = now.month; p[5] = now.day
        p[6] = now.hour; p[7] = now.minute; p[8] = now.second
        p[10] = (now.weekday() + 1) % 7          # Windows wDayOfWeek: 周日=0
        p[62] = 0xAA; p[63] = 0x55
        acks = []
        with STATE['lock']:
            kb._drain(20)
            for pkt in ([0x04, 0x18], [0x04, 0x28, 0, 0, 0, 0, 0, 0, 1], p, [0x04, 0x02]):
                r = kb.cmd(pkt, timeout_ms=400, retries=1)
                acks.append(r.hex()[:8] if r else None)
                time.sleep(0.01)
        ok = all(a is not None and a[6:8] == '01' for a in acks)
        return {'ok': ok, 'acks': acks}

    def api_strip(self, path, q, body):
        q2 = json.loads(body or b'{}') if body else {}
        mode = q.get('mode') or q2.get('mode')
        if 'color' in q2:
            STRIP['color'] = hex2rgb(q2['color'])
        if 'refresh' in q2:
            STRIP['refresh'] = q2['refresh']
        if 'via' in q2:
            STRIP['via'] = q2['via']
        if mode == 'off':
            strip_start(None)
            return {'ok': True, 'mode': None}
        if mode == 'clock':
            strip_start('clock')
            return {'ok': True, 'mode': 'clock'}
        if mode == 'cpu':
            strip_start('cpubars')
            return {'ok': True, 'mode': 'cpu'}
        if mode == 'agent':
            strip_start('agent')
            return {'ok': True, 'mode': 'agent'}
        if mode == 'text':
            frame = STRP.text_frame(q2.get('text', 'HI'), color=STRIP['color'])
            if STRIP.get('via') in ('live', 'static35'):
                strip_start('live', frames=[frame])     # 不写 flash, 靠每秒补发
            else:
                strip_start('static', frames=[frame], delay=100)
            return {'ok': True, 'preview': strip_preview_dataurl(frame)}
        if mode == 'color':
            c = STRIP['color']
            frame = STRP.bars_frame([1.0] * STRP.COLS, color=c, bg=c)
            strip_start('static', frames=[frame], delay=100)
            return {'ok': True, 'preview': strip_preview_dataurl(frame)}
        if mode == 'rainbow':
            frames = [STRP.rainbow_frame(t) for t in range(STRP.COLS)]
            strip_start('static', frames=frames, delay=60)
            return {'ok': True, 'preview': strip_preview_dataurl(frames[0])}
        if mode == 'preset':
            name = q2.get('name') or q.get('name')
            if name not in PRESETS.PRESETS:
                return {'ok': False, 'error': '未知灯效 ' + str(name)}
            if not preset_database_available():
                return {'ok': False,
                        'error': '官方预制灯效需要 ledlayer_v2.data；请从官方 Windows 驱动中提取并设置 AMG65_PRESET_DB'}
            frames = PRESETS.preset_frames(name)
            delay = max(20, int(q2.get('delay', 80)))
            t0 = time.time()
            strip_start(None)
            _strip_push(frames, delay)           # 04 33 常驻循环
            ims = PRESETS.preset_images(name)
            prev = ims[len(ims) // 3].resize((STRP.COLS * 8, STRP.ROWS * 8), Image.NEAREST)
            return {'ok': True, 'frames': len(frames), 'seconds': round(time.time() - t0, 1),
                    'preview': png_dataurl(prev)}
        return {'ok': False, 'error': '未知模式'}

    def api_sit(self, body):
        """久坐提醒: {minutes: 0/30/45/60/90, color?, seconds?} ; {action: 'test'|'dismiss'}"""
        q = json.loads(body or b'{}') if body else {}
        if 'color' in q:
            SIT['color'] = hex2rgb(q['color'])
        action = q.get('action')
        if 'seconds' in q and action != 'test':
            SIT['seconds'] = max(5, int(q['seconds']))
        if 'minutes' in q:
            SIT['minutes'] = max(0, int(q['minutes']))
            SIT['until'] = 0
            SIT['next'] = time.time() + SIT['minutes'] * 60 if SIT['minutes'] else None
        if action == 'test':
            SIT['until'] = time.time() + max(3, int(q.get('seconds', SIT['seconds'])))
        elif action == 'dismiss':
            SIT['until'] = 0
            if SIT['minutes']:
                SIT['next'] = time.time() + SIT['minutes'] * 60
        sit_ensure_thread()
        return dict(ok=True, **sit_status())

    def api_strip_upload(self, body, q):
        from PIL import ImageSequence
        kind = q.get('kind', 'image')
        strip_start(None)
        frames = []
        if kind == 'gif':
            im = Image.open(io.BytesIO(body))
            maxf = int(q.get('max', 100))
            for i, fr in enumerate(ImageSequence.Iterator(im)):
                if i >= maxf:
                    break
                frames.append(STRP.image_to_frame(fr))
            delay = max(40, int(im.info.get('duration', 80)))
        else:
            im = Image.open(io.BytesIO(body))
            frames = [STRP.image_to_frame(im)]
            delay = 100
        t0 = time.time()
        strip_start(None)                       # 先停掉旧 worker
        _strip_push(frames, delay)              # 04 33 同步上传, 返回即常驻(无需线程)
        return {'ok': True, 'frames': len(frames), 'seconds': round(time.time() - t0, 1),
                'preview': strip_preview_dataurl(frames[0])}



# ------- 长条屏工作线程 -------
# 固件反汇编结论: 04 33(槽 6)无限循环, 传一次即常驻; 04 31 是开机动画, 只播一次。
STRIP = {'mode': None, 'thread': None, 'stop': None, 'color': (0, 255, 200),
         'frames': None, 'delay': 100, 'interval': 1.0, 'refresh': 'smooth', 'via': 'anim'}


def _with_data_channel(fn):
    """在数据通道(interface 3, libusb)打开期间执行 fn(kb)"""
    import usb.core, usb.util
    kb = get_kb()
    with STATE['lock']:
        if kb is None:
            STATE['kb'] = AMG65(verbose=False)
            kb = STATE['kb']
        dev = usb.core.find(idVendor=0x0C45, idProduct=0x800A)
        if dev is None:
            raise RuntimeError('libusb 找不到键盘')
        try:
            dev.set_configuration()
        except Exception:
            pass
        usb.util.claim_interface(dev, 3)
        kb._usb = dev
        kb._claimed = True
        try:
            return fn(kb)
        finally:
            try:
                usb.util.release_interface(dev, 3)
            except Exception:
                pass
            kb._claimed = False
            kb._usb = None


def _strip_push(frames, delay_ms=100):
    """04 33 写入灯效槽 6: 传一次即常驻(固件无限循环, 断电保留)。会擦写 flash, 别高频调用。"""
    return _with_data_channel(lambda kb: STRP.upload_anim(kb, frames, delay_ms=delay_ms))


def _strip_live(frame):
    """04 35 实时帧: 只走命令通道, 不写 flash; 固件保持约 2.5 秒, 需每秒补发"""
    kb = get_kb()
    with STATE['lock']:
        if kb is None:
            STATE['kb'] = AMG65(verbose=False)
            kb = STATE['kb']
        return STRP.live_frame(kb, frame)


_strip_push_static = _strip_live   # 旧名字


LIVE_INTERVAL = 1.0   # 实时帧补发间隔(秒); 固件约 2.5 秒超时


def strip_worker():
    """长条屏刷新策略(依据固件反汇编):
    - 静态图/文字/GIF: 04 33 传一次 -> 槽 6 无限循环, 不需要线程
    - 时钟/CPU 等动态内容: 04 35 实时帧每秒补发, 渲染被固件暂停, 内容不变时不会闪
    """
    import psutil
    psutil.cpu_percent(interval=None)
    smooth = [40.0]
    tick = 0
    while not STRIP['stop'].is_set():
        mode = STRIP['mode']
        t0 = time.time()
        try:
            if sit_active():
                pass                    # 久坐提醒正占用长条屏
            elif mode == 'clock':
                _strip_live(STRP.clock_frame(tick % 2 == 0, STRIP['color']))
            elif mode == 'cpubars':
                c = psutil.cpu_percent(interval=None)
                m = psutil.virtual_memory().percent
                smooth[0] = smooth[0] * 0.5 + c * 0.5
                vals = [smooth[0] / 100.0] * 21 + [m / 100.0] * 21 + \
                       [min(1.0, smooth[0] / 100.0 * 0.7)] * 21
                _strip_live(STRP.bars_frame(vals, color=STRIP['color']))
            elif mode == 'agent':
                _strip_live(STRP.agent_frame([('CC', agent_state('claude')),
                                              ('CX', agent_state('codex'))], tick))
            elif mode == 'live':
                _strip_live(STRIP['frames'][0])
            elif mode == 'static':
                _strip_push(STRIP['frames'], STRIP['delay'])   # 传一次就够
                STRIP['mode'] = None
            tick += 1
        except Exception as e:
            print('strip worker:', e, flush=True)
        interval = AGENT_INTERVAL if mode == 'agent' else LIVE_INTERVAL
        STRIP['stop'].wait(max(0.05, interval - (time.time() - t0)))


def strip_start(mode, frames=None, delay=500):
    if STRIP['thread'] and STRIP['thread'].is_alive():
        STRIP['stop'].set()
        STRIP['thread'].join(timeout=3)
    STRIP['mode'] = mode
    STRIP['frames'] = frames
    STRIP['delay'] = delay
    if frames:
        n = len(frames)
        STRIP['interval'] = max(0.5, n * delay / 1000.0 + 0.15)
    STRIP['stop'] = threading.Event()
    t = threading.Thread(target=strip_worker, daemon=True)
    STRIP['thread'] = t
    if mode:
        t.start()


# ------- Claude Code / Codex 编程状态 -------
# 两边都用同格式的 hooks (Claude: ~/.claude/settings.json, Codex: ~/.codex/hooks.json),
# 钩子脚本 tool/agent_hook.sh 把 stdin 的事件 JSON 转发到 /api/agent?agent=..&event=..
AGENT_INTERVAL = 0.25
AGENT_EVENTS = {
    'UserPromptSubmit': 'working', 'PreToolUse': 'working', 'PostToolUse': 'working',
    'SubagentStop': 'working', 'PreCompact': 'working',
    'Notification': 'waiting', 'PermissionRequest': 'waiting',
    'Stop': 'done', 'SessionStart': 'done',
    'SessionEnd': None,
}
AGENT_PRIORITY = {'waiting': 3, 'working': 2, 'done': 1, 'idle': 0}
AGENT_STALE = {'working': 30 * 60, 'done': 60 * 60}   # 太久没事件就当空闲 (进程被杀等情况)
AGENTS = {'claude': {}, 'codex': {}}                  # agent -> session_id -> {state, ts, cwd}
AGENT_LAST = {'claude': None, 'codex': None}          # 最近一次事件 (event, ts), 用来判断钩子通没通

HOOK_SCRIPT = os.environ.get('AMG65_HOOK_SCRIPT') or os.path.join(
    os.path.dirname(HERE), 'tool', 'agent_hook.sh')
HOOK_CONF = {
    'claude': {'path': os.path.expanduser('~/.claude/settings.json'),
               'events': ['UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'Notification', 'Stop', 'SessionEnd']},
    'codex': {'path': os.path.expanduser('~/.codex/hooks.json'),
              'events': ['UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PermissionRequest', 'Stop', 'SessionEnd']},
}
CODEX_CONFIG = os.path.expanduser('~/.codex/config.toml')


def _snake(name):
    import re
    return re.sub(r'(?<!^)([A-Z])', r'_\1', name).lower()


def _hook_cmd(agent, ev):
    return f'{HOOK_SCRIPT} {agent} {ev}'


def _load_hook_file(agent):
    p = HOOK_CONF[agent]['path']
    try:
        with open(p) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def _save_hook_file(agent, cfg):
    import shutil
    p = HOOK_CONF[agent]['path']
    if os.path.exists(p):
        shutil.copy2(p, p + '.bak-' + time.strftime('%Y%m%d%H%M%S'))
    tmp = p + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def hooks_status():
    """每个 agent: 装了几个事件; Codex 另查 config.toml 里有没有对应的信任记录
    (Codex 的信任键 = "<hooks.json 路径>:<事件 snake_case>:<组序号>:<钩子序号>")"""
    try:
        codex_toml = open(CODEX_CONFIG).read()
    except FileNotFoundError:
        codex_toml = ''
    out = {}
    for agent, conf in HOOK_CONF.items():
        hooks = _load_hook_file(agent).get('hooks', {})
        installed, trusted = [], []
        for ev in conf['events']:
            for gi, grp in enumerate(hooks.get(ev, [])):
                for hi, h in enumerate(grp.get('hooks', [])):
                    if h.get('command') == _hook_cmd(agent, ev):
                        installed.append(ev)
                        key = f'[hooks.state."{conf["path"]}:{_snake(ev)}:{gi}:{hi}"]'
                        if key in codex_toml:
                            trusted.append(ev)
        last = AGENT_LAST[agent]
        out[agent] = {'installed': len(set(installed)), 'total': len(conf['events']),
                      'trusted': len(set(trusted)) if agent == 'codex' else None,
                      'last_event': last[0] if last else None,
                      'last_ago': int(time.time() - last[1]) if last else None}
    return out


def hooks_install(agent):
    cfg = _load_hook_file(agent)
    hooks = cfg.setdefault('hooks', {})
    for ev in HOOK_CONF[agent]['events']:
        lst = hooks.setdefault(ev, [])
        if not any(h.get('command') == _hook_cmd(agent, ev) for g in lst for h in g.get('hooks', [])):
            lst.append({'hooks': [{'type': 'command', 'command': _hook_cmd(agent, ev), 'timeout': 3}]})
    _save_hook_file(agent, cfg)


def hooks_uninstall(agent):
    cfg = _load_hook_file(agent)
    hooks = cfg.get('hooks', {})
    for ev in list(hooks):
        groups = []
        for g in hooks[ev]:
            hs = [h for h in g.get('hooks', []) if HOOK_SCRIPT not in str(h.get('command', ''))]
            if hs:
                groups.append(dict(g, hooks=hs))
        if groups:
            hooks[ev] = groups
        else:
            del hooks[ev]
    _save_hook_file(agent, cfg)
    AGENTS[agent].clear()


# ------- 面板设置 (持久化) -------
SETTINGS_PATH = os.environ.get('AMG65_SETTINGS') or os.path.join(HERE, 'settings.json')


def load_settings():
    try:
        with open(SETTINGS_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(**kw):
    s = load_settings()
    s.update(kw)
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(s, f, ensure_ascii=False, indent=2)
    return s


def agent_event(agent, event, body):
    if agent not in AGENTS:
        return {'ok': False, 'error': '未知 agent'}
    try:
        info = json.loads(body or b'{}')
    except Exception:
        info = {}
    event = event or info.get('hook_event_name')
    if event not in AGENT_EVENTS:
        return {'ok': False, 'error': '未知事件 ' + str(event)}
    AGENT_LAST[agent] = (event, time.time())
    sid = str(info.get('session_id') or 'default')
    state = AGENT_EVENTS[event]
    # Claude 的 idle_prompt 通知 = 已经回复完在等下一句, 算"完成"而不是"要你操作"
    if event == 'Notification' and (info.get('notification_type') == 'idle_prompt' or
                                    'waiting for your input' in str(info.get('message', ''))):
        state = 'done'
    sessions = AGENTS[agent]
    if state is None:
        sessions.pop(sid, None)
    else:
        sessions[sid] = {'state': state, 'ts': time.time(), 'cwd': info.get('cwd', '')}
    return {'ok': True, 'agent': agent, 'state': agent_state(agent)}


def agent_state(agent):
    now, best = time.time(), 'idle'
    for s in list(AGENTS[agent].values()):
        st = s['state']
        if now - s['ts'] > AGENT_STALE.get(st, 1e12):
            st = 'idle'
        if AGENT_PRIORITY[st] > AGENT_PRIORITY[best]:
            best = st
    return best


def agent_status():
    now = time.time()
    return {a: {'state': agent_state(a),
                'sessions': [{'state': s['state'], 'cwd': os.path.basename(s['cwd'] or ''),
                              'ago': int(now - s['ts'])} for s in AGENTS[a].values()]}
            for a in AGENTS}


# ------- 久坐提醒 -------
# 驱动逆向: 计时和画面都在 PC 端 (mui.dll GetSitRemindLEDEffect -> 驱动 0x4352d0 走 04 35 实时帧),
# 固件不参与计时; 官方选项 关闭/30/45/60/90 分钟 (语言包 981-986)。
SIT = {'minutes': 0, 'next': None, 'until': 0, 'seconds': 60,
       'color': (255, 30, 60), 'thread': None}


def sit_active():
    return time.time() < SIT['until']


def sit_status():
    now = time.time()
    return {'minutes': SIT['minutes'], 'active': sit_active(),
            'remain': int(SIT['next'] - now) if SIT['next'] and not sit_active() else None,
            'color': '#%02x%02x%02x' % SIT['color'], 'seconds': SIT['seconds']}


def sit_worker():
    phase = 0
    while True:
        now = time.time()
        if SIT['next'] and now >= SIT['next'] and not sit_active():
            SIT['until'] = now + SIT['seconds']
            SIT['next'] = SIT['until'] + SIT['minutes'] * 60 if SIT['minutes'] else None
        if sit_active():
            try:
                _strip_live(STRP.sit_remind_frame(phase, SIT['color']))
            except Exception as e:
                print('sit worker:', e, flush=True)
            phase ^= 1
            time.sleep(0.5)
        else:
            time.sleep(1.0)


def sit_ensure_thread():
    if not (SIT['thread'] and SIT['thread'].is_alive()):
        SIT['thread'] = threading.Thread(target=sit_worker, daemon=True)
        SIT['thread'].start()


def strip_preview_dataurl(frame_bytes):
    im = Image.new('RGB', (STRP.COLS, STRP.ROWS))
    im.putdata([tuple(frame_bytes[i*3:i*3+3]) for i in range(STRP.COLS * STRP.ROWS)])
    buf = io.BytesIO()
    im.resize((STRP.COLS * 8, STRP.ROWS * 8), Image.NEAREST).save(buf, format='PNG')
    return 'data:image/png;base64,' + base64.b64encode(buf.getvalue()).decode()


def locked_ping(kb):
    with STATE['lock']:
        return kb.ping()


def fit_image(img):
    tw, th = SCREEN_W, SCREEN_H
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    nw, nh = round(sw * scale), round(sh * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    return img.crop(((nw - tw) // 2, (nh - th) // 2, (nw - tw) // 2 + tw, (nh - th) // 2 + th))


def hex2rgb(s):
    s = (s or '').lstrip('#')
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4)) if len(s) >= 6 else (255, 255, 255)


def load_font(size):
    from PIL import ImageFont
    for p in ('/System/Library/Fonts/PingFang.ttc',
              '/System/Library/Fonts/Supplemental/Arial Unicode.ttf'):
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def preset_database_available():
    return os.path.isfile(PRESETS.DB_PATH)


class ThreadingHTTPServerV4(ThreadingHTTPServer):
    allow_reuse_address = True


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get('AMG65_PORT', '8655'))
    print(f'AMG65 面板: http://127.0.0.1:{port}')
    if not preset_database_available():
        print('官方预制灯效: 未找到 ledlayer_v2.data，相关按钮会提示需要本机驱动素材', flush=True)
    if load_settings().get('agent_autostart'):
        strip_start('agent')
        print('编程状态灯: 已自动开启', flush=True)
    ThreadingHTTPServerV4(('127.0.0.1', port), Handler).serve_forever()


if __name__ == '__main__':
    main()
