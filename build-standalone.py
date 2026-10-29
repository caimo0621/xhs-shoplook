#!/usr/bin/env python3
"""把 index.html 打包成单文件版，14 张商品图以 data URI 内联。

产出 dist/index.html —— 只依赖同目录下一个 look.mp4，别的什么都不需要。
为的是方便上传到 REDCowork 这类只能传少量文件、而且目录结构不由你决定的平台。

    python3 build-standalone.py              # 原图，约 1.9 MB
    python3 build-standalone.py --compact    # 图压到 480 宽，约 0.8 MB
    python3 build-standalone.py --mini       # 图压到 340 宽，约 0.4 MB

平台有上传体积限制时往下降一档。商详页大图在 --mini 下会有点软，
但小圆点和抽屉里的卡片看不出区别。
"""
import base64
import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).parent
SRC = ROOT / 'index.html'
PDIR = ROOT / 'assets' / 'p'
DIST = ROOT / 'dist'

TIERS = {           # 后缀 -> (最长边, JPEG 质量)
    '':         None,
    '-compact': (640, 70),
    '-mini':    (453, 62),
}
flag = next((a for a in sys.argv[1:] if a.startswith('--')), '')
suffix = {'--compact': '-compact', '--mini': '-mini'}.get(flag, '')
tier = TIERS[suffix]

html = SRC.read_text()

# 1. 14 张商品图 -> data URI（必要时先用 sips 缩一道）
imgs = {}
with tempfile.TemporaryDirectory() as tmp:
    for f in sorted(PDIR.glob('*.jpg')):
        data = f.read_bytes()
        if tier:
            longest, q = tier
            out = pathlib.Path(tmp) / f.name
            subprocess.run(
                ['sips', '-Z', str(longest), '-s', 'format', 'jpeg',
                 '-s', 'formatOptions', str(q), str(f), '--out', str(out)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            data = out.read_bytes()
        imgs[f.stem] = 'data:image/jpeg;base64,' + base64.b64encode(data).decode()
avg = sum(len(v) for v in imgs.values()) / len(imgs) / 1024
print(f'内联 {len(imgs)} 张商品图'
      + (f'（缩到 {tier[0]}px / 质量 {tier[1]}）' if tier else '（原图）')
      + f'，平均 {avg:.0f} KB')

# 2. 注入到 window.IMGS，index.html 里的 img() 会优先读它
inject = '<script>window.IMGS=' + json.dumps(imgs, separators=(',', ':')) + ';</script>\n'
html = html.replace('<script>\nconst P =', inject + '<script>\nconst P =', 1)

# 3. 视频换成同目录下的 look.mp4（不再有 assets/ 这一层）
html = html.replace('assets/look.mp4', 'look.mp4')

# 4. 顶部加一句说明，免得以后搞不清这份是哪来的
html = html.replace(
    '<title>',
    '<!-- 自动生成，请勿直接编辑。改 ../index.html 后重新跑 build-standalone.py -->\n<title>',
    1)

DIST.mkdir(exist_ok=True)
out = DIST / f'index{suffix}.html'
out.write_text(html)
print(f'{out.name} -> {out.stat().st_size/1024:.0f} KB')

# 5. 校验：不该再有任何外部资源引用。
#    只看静态 HTML 属性，跳过 JS 模板字符串（${...} / '+...+'），那些运行时才解析。
leftover = [
    u for u in re.findall(r'(?:src|href)="(?!data:|#)([^"]+)"', html)
    if '${' not in u and "'+" not in u and u != 'look.mp4'
]
print('外部依赖:', leftover if leftover else '仅 look.mp4 ✅')
