"""把 css/js/py 組合成單一自足的 index.html。修改個別檔案後,重新執行這支腳本即可。"""
import base64, os

BASE = os.path.dirname(os.path.abspath(__file__))

def read(rel):
    with open(os.path.join(BASE, rel), encoding='utf-8') as f:
        return f.read()

def main():
    css = read('css/style.css')
    config_js = read('js/config.js')
    date_js = read('js/dateUtils.js')
    loader_js = read('js/dataLoader.js')
    app_js = read('js/app.js')
    engine_py = read('py/lotto_engine.py')
    b64 = base64.b64encode(engine_py.encode('utf-8')).decode('ascii')

    bridge_js = read('js/engineBridge.src.js')

    body_head = read('index.body.head.html')
    body_tail = read('index.body.tail.html')

    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>星辰路引</title>
<meta name="description" content="星辰路引 —— 開獎資料整理與版路比對工具">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E%E2%9C%A6%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@600;700&family=Noto+Sans+TC:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{css}
</style>
</head>
<body>
{body_head}
<script type="application/octet-stream" id="lotto-engine-b64">
{b64}
</script>

<script>
{config_js}
</script>
<script>
{date_js}
</script>
<script>
{loader_js}
</script>
<script>
{bridge_js}
</script>
<script>
{app_js}
</script>
{body_tail}
</body>
</html>
"""
    with open(os.path.join(BASE, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html)
    print('已重建 index.html,大小:', len(html.encode('utf-8')), 'bytes')

if __name__ == '__main__':
    main()
