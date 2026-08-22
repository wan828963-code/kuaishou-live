#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取指定快手主播的直播地址（硬编码版）
直接访问主播页面，从 HTML 中提取流地址
"""
import json
import os
import re
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M3U_PATH = os.path.join(BASE_DIR, 'teacher.m3u')

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36')

REQUEST_TIMEOUT = 20

# ===== 在这里配置你要的主播列表 =====
TEACHERS = [
    {"id": "SJJC6688", "name": "爽姐讲财", "group": "财经"},
    {"id": "Diyicaituan", "name": "第一财团", "group": "财经"},
]
# ===================================


def fetch_live_url_from_page(user_id):
    """
    直接访问主播页面 https://live.kuaishou.com/u/{user_id}
    从页面中提取直播流地址
    """
    url = f'https://live.kuaishou.com/u/{user_id}'
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
    })
    
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            html = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'  获取页面失败: {e}')
        return None
    
    # 方法1：从 window.__INITIAL_STATE__ 提取
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            # 尝试多个路径
            for path in ['liveStream', 'room', 'detail']:
                if path in data:
                    play_urls = data[path].get('playUrls', [])
                    if play_urls:
                        for pu in play_urls:
                            reps = pu.get('adaptationSet', {}).get('representation', [])
                            if reps:
                                best = sorted(reps, key=lambda x: (x.get('level', 0), x.get('bitrate', 0)))[-1]
                                stream_url = best.get('url')
                                if stream_url and 'flv' in stream_url:
                                    return stream_url
        except Exception as e:
            print(f'  解析 __INITIAL_STATE__ 失败: {e}')
    
    # 方法2：直接从 HTML 中搜索 .flv 地址
    match = re.search(r'https://[^\s"\']+\.flv[^\s"\']*', html)
    if match:
        return match.group(0)
    
    return None


def generate_m3u():
    """生成 teacher.m3u"""
    lines = [
        '#EXTM3U',
        f'# 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}',
        f'# 共 {len(TEACHERS)} 个主播',
        ''
    ]
    
    online_count = 0
    online_list = []
    
    for teacher in TEACHERS:
        user_id = teacher["id"]
        name = teacher["name"]
        group = teacher["group"]
        
        print(f'🔍 正在获取 {name} ({user_id})...')
        stream_url = fetch_live_url_from_page(user_id)
        
        if stream_url:
            lines.append(f'#EXTINF:-1 tvg-logo="" group-title="{group}" tvg-id="{user_id}", {name}')
            lines.append(stream_url)
            lines.append('')
            print(f'✅ {name} 直播地址获取成功')
            online_count += 1
            online_list.append(name)
        else:
            lines.append(f'#EXTINF:-1 tvg-logo="" group-title="{group}" tvg-id="{user_id}", {name} ⏸️ 未开播')
            lines.append('# 主播当前未开播，请稍后再试')
            lines.append('')
            print(f'❌ {name} 当前未开播')
    
    if online_list:
        lines.append(f'# ✅ 在线主播：{", ".join(online_list)}')
    lines.append(f'# 📊 共 {len(TEACHERS)} 个主播，在线 {online_count} 个')
    
    with open(M3U_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    
    print(f'\n📁 已写入 {M3U_PATH}，在线 {online_count}/{len(TEACHERS)}')


def main():
    print('=' * 40)
    print('🚀 快手专属直播源更新工具（页面解析版）')
    print(f'📋 共配置 {len(TEACHERS)} 个主播')
    print('=' * 40)
    generate_m3u()
    print('=' * 40)


if __name__ == '__main__':
    main()        else:
            lines.append(f'#EXTINF:-1 tvg-logo="" group-title="{group}" tvg-id="{user_id}", {name} ⏸️ 未开播')
            lines.append('# 主播当前未开播，请稍后再试')
            lines.append('')
            print(f'❌ {name} 当前未开播')
    
    if online_list:
        lines.append(f'# ✅ 在线主播：{", ".join(online_list)}')
    lines.append(f'# 📊 共 {len(TEACHERS)} 个主播，在线 {online_count} 个')
    
    with open(M3U_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    
    print(f'\n📁 已写入 {M3U_PATH}，在线 {online_count}/{len(TEACHERS)}')


def main():
    print('=' * 40)
    print('🚀 快手财经主播专属直播源更新工具')
    print(f'📋 共配置 {len(TEACHERS)} 个主播')
    print('=' * 40)
    generate_m3u()
    print('=' * 40)
    print('✅ 更新完成！')


if __name__ == '__main__':
    main()
