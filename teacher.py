#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取指定快手主播的直播地址，生成 teacher.m3u
使用 update_m3u.py 同款 API 接口
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M3U_PATH = os.path.join(BASE_DIR, 'teacher.m3u')

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36')

REQUEST_TIMEOUT = 20
HOT_API = 'https://live.kuaishou.com/live_api/hot/list'

# ===== 在这里配置你要的主播列表 =====
TEACHERS = [
    {"id": "SJJC6688", "name": "爽姐讲财", "group": "财经"},
    {"id": "Diyicaituan", "name": "第一财团", "group": "财经"},
]
# ===================================


def fetch_room_by_id(user_id):
    """翻页查找指定主播的房间数据"""
    for page in range(1, 30):
        url = f'{HOT_API}?type=HOT&filterType=0&page={page}&pageSize=50'
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Referer': 'https://live.kuaishou.com/live/HOT',
        })
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
                body = json.load(r)
        except Exception as e:
            print(f'  第{page}页请求失败: {e}')
            continue
        
        room_list = body.get('data', {}).get('list', [])
        if not room_list:
            break
        
        for room in room_list:
            # 用多种方式匹配 ID
            room_id = room.get('id', '')
            author = room.get('author', {})
            author_id = author.get('id', '')
            eid = author.get('eid', '')
            
            if user_id in (room_id, author_id, eid):
                return room
    
    return None


def get_best_url(room):
    """从房间数据中提取最高清播放地址"""
    if not room:
        return None
    play_urls = room.get('playUrls', [])
    if not play_urls:
        return None
    for pu in play_urls:
        reps = pu.get('adaptationSet', {}).get('representation', [])
        if reps:
            best = sorted(reps, key=lambda x: (x.get('level', 0), x.get('bitrate', 0)))[-1]
            return best.get('url')
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
        
        print(f'🔍 正在查找 {name} ({user_id})...')
        room = fetch_room_by_id(user_id)
        stream_url = get_best_url(room)
        
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
    print('🚀 快手专属直播源更新工具')
    print(f'📋 共配置 {len(TEACHERS)} 个主播')
    print('=' * 40)
    generate_m3u()
    print('=' * 40)


if __name__ == '__main__':
    main()
