#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取指定快手主播的直播地址，生成 teacher.m3u
"""
import json
import re
import time
import urllib.request
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M3U_PATH = os.path.join(BASE_DIR, 'teacher.m3u')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'

# ===== 在这里配置你要的主播列表 =====
TEACHERS = [
    {"id": "SJJC6688", "name": "爽姐讲财", "group": "财经"},
    {"id": "KaIEMRmH", "name": "第一财团", "group": "财经"},
]
# ===================================


def fetch_live_url(user_id):
    """从快手主播页面获取当前直播流地址"""
    url = f'https://live.kuaishou.com/u/{user_id}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'获取页面失败 ({user_id}): {e}')
        return None
    
    # 方法1：从 __INITIAL_STATE__ 提取
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            play_urls = data.get('liveStream', {}).get('playUrls', [])
            for pu in play_urls:
                reps = pu.get('adaptationSet', {}).get('representation', [])
                if reps:
                    best = sorted(reps, key=lambda x: (x.get('level', 0), x.get('bitrate', 0)))[-1]
                    return best.get('url')
        except:
            pass
    
    # 方法2：正则找 .flv 地址
    match = re.search(r'https://[^\s"\']+\.flv[^\s"\']*', html)
    if match:
        return match.group(0)
    
    return None


def generate_m3u():
    """生成 teacher.m3u，包含所有配置的主播"""
    lines = [
        '#EXTM3U',
        f'# 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}',
        f'# 共 {len(TEACHERS)} 个主播',
        ''
    ]
    
    online_count = 0
    for teacher in TEACHERS:
        user_id = teacher["id"]
        name = teacher["name"]
        group = teacher["group"]
        
        print(f'正在获取 {name} ({user_id})...')
        url = fetch_live_url(user_id)
        
        if url:
            lines.append(f'#EXTINF:-1 tvg-logo="" group-title="{group}" tvg-id="{user_id}", {name}')
            lines.append(url)
            lines.append('')
            print(f'✅ {name} 直播地址获取成功')
            online_count += 1
        else:
            lines.append(f'#EXTINF:-1 tvg-logo="" group-title="{group}" tvg-id="{user_id}", {name} (未开播)')
            lines.append('# 当前未开播，请稍后再试')
            lines.append('')
            print(f'❌ {name} 当前未开播')
    
    lines.append(f'# 共 {len(TEACHERS)} 个主播，在线 {online_count} 个')
    
    with open(M3U_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    
    print(f'已写入 {M3U_PATH}，在线 {online_count}/{len(TEACHERS)}')


def main():
    print(f'开始获取 {len(TEACHERS)} 个主播的直播地址...')
    generate_m3u()


if __name__ == '__main__':
    main()
