"""改寫版面段落的小工具。給一個唯一的錨點字串，換掉整個元素的內容。

為什麼不用整段字串比對：原始碼的換行位置會變，比對就會失敗。
錨點只認一段不會被改動的文字，可靠得多。這支只在改稿時用，不進建置流程。
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent


def replace(path, anchor, new_inner, tag=None):
    """把含有 anchor 的那一個元素的內容換成 new_inner。"""
    p = ROOT / path
    s = p.read_text(encoding='utf-8')
    i = s.find(anchor)
    if i < 0:
        sys.exit(f'{path}：找不到錨點「{anchor[:30]}」')
    if s.find(anchor, i + 1) > 0:
        sys.exit(f'{path}：錨點「{anchor[:30]}」不只一處')
    # 往回找開標籤
    start = max(s.rfind(f'<{t}', 0, i) for t in (tag,) if tag) if tag else \
        max(s.rfind(f'<{t}', 0, i) for t in ('p', 'li', 'h2', 'h3', 'h4'))
    open_end = s.index('>', start) + 1
    name = re.match(r'<(\w+)', s[start:]).group(1)
    close = s.index(f'</{name}>', open_end)
    p.write_text(s[:open_end] + new_inner + s[close:], encoding='utf-8')
