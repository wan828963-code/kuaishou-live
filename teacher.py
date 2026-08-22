#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import re
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M3U_PATH = os.path.join(BASE_DIR, 'teacher.m3u')
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

TEACHERS = [
    {"id": "SJJC6688", "name": "爽姐讲财"},
    {"id": "Diyicaituan", "name": "第一财团"},
]

def fetch_live_url_direct(user_id):
    """从主播页面直接抓取 .flv 地址（不依赖JS执行）"""
    url = f'https://live.kuaishou.com/u/{user_id}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'  ⚠️ 页面获取失败: {e}')
        return None

    # 核心方法：在一个较宽的上下文中搜索 .flv 地址
    # 匹配类似 https://...xxx.flv?hwTime=... 的链接
    matches = re.findall(r'https://[^\s"\'<>]+\.flv[^\s"\'<>]*', html)
    if matches:
        # 去重并返回第一个有效的地址
        seen = set()
        for m in matches:
            if m not in seen:
                seen.add(m)
                # 简单过滤掉明显不是直播地址的链接（如日志上报地址）
                if 'flv' in m and 'pull' in m:
                    return m
        return matches[0]  # 如果没找到 pull，返回第一个
    return None

def generate_m3u():
    lines = ['#EXTM3U', f'# 生成: {time.strftime("%Y-%m-%d %H:%M:%S")}']
    online_count = 0
    for t in TEACHERS:
        print(f'🔍 正在查找 {t["name"]} ({t["id"]})...')
        url = fetch_live_url_direct(t["id"])
        if url:
            lines.append(f'#EXTINF:-1 tvg-logo="" group-title="财经" tvg-id="{t["id"]}", {t["name"]}')
            lines.append(url)
            print(f'✅ 成功: {t["name"]}')
            online_count += 1
        else:
            lines.append(f'#EXTINF:-1 tvg-logo="" group-title="财经" tvg-id="{t["id"]}", {t["name"]} (未开播)')
            lines.append('# 未开播')
            print(f'❌ 未开播: {t["name"]}')
    lines.append(f'# 在线: {online_count}/{len(TEACHERS)}')
    with open(M3U_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print('✅ 更新完成!')

if __name__ == '__main__':
    generate_m3u()
def main():
    print('=' * 40)
    print('快手专属直播源更新工具 (浏览器版)')
    print('共 ' + str(len(TEACHERS)) + ' 个主播')
    print('=' * 40)
    generate_m3u()
    print('=' * 40)


if __name__ == '__main__':
    main()
