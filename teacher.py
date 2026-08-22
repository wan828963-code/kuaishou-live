#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取指定快手主播的直播地址（使用 room/enter API）
"""
import json
import os
import re
import time
import urllib.request
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M3U_PATH = os.path.join(BASE_DIR, 'teacher.m3u')

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36')

TEACHERS = [
    {"id": "SJJC6688", "name": "爽姐讲财", "group": "财经"},
    {"id": "Diyicaituan", "name": "第一财团", "group": "财经"},
]


def get_room_id(user_id):
    """从主播页面获取 roomId"""
    url = f'https://live.kuaishou.com/u/{user_id}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'  获取页面失败: {e}')
        return None
    
    # 从页面中提取 roomId
    match = re.search(r'"roomId"\s*:\s*"(\d+)"', html)
    if match:
        return match.group(1)
    
    # 尝试从 __INITIAL_STATE__ 提取
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            room_id = data.get('room', {}).get('roomId') or data.get('liveStream', {}).get('roomId')
            if room_id:
                return str(room_id)
        except:
            pass
    
    return None


def fetch_live_url_via_api(user_id):
    """通过 room/enter 接口获取流地址"""
    # 先获取 roomId
    room_id = get_room_id(user_id)
    if not room_id:
        print(f'  无法获取 roomId')
        return None
    
    print(f'  roomId: {room_id}')
    
    # 调用 room/enter 接口
    api_url = 'https://live.kuaishou.com/live_api/room/enter'
    data = urllib.parse.urlencode({'roomId': room_id}).encode('utf-8')
    req = urllib.request.Request(
        api_url,
        data=data,
        headers={
            'User-Agent': UA,
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': f'https://live.kuaishou.com/u/{user_id}',
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = json.load(r)
    except Exception as e:
        print(f'  API请求失败: {e}')
        return None
    
    # 提取流地址
    try:
        data = body.get('data', {})
        play_urls = data.get('playUrls', [])
        if not play_urls:
            print(f'  没有 playUrls 数据')
            return None
        
        for pu in play_urls:
            reps = pu.get('adaptationSet', {}).get('representation', [])
            if reps:
                best = sorted(reps, key=lambda x: (x.get('level', 0), x.get('bitrate', 0)))[-1]
                stream_url = best.get('url')
                if stream_url:
                    return stream_url
    except Exception as e:
        print(f'  解析数据失败: {e}')
    
    return None


def generate_m3u():
    lines = [
        '#EXTM3U',
        '# 生成时间: ' + time.strftime("%Y-%m-%d %H:%M:%S"),
        '# 共 ' + str(len(TEACHERS)) + ' 个主播',
        ''
    ]
    
    online_count = 0
    online_list = []
    
    for teacher in TEACHERS:
        user_id = teacher["id"]
        name = teacher["name"]
        group = teacher["group"]
        
        print('正在获取 ' + name + ' (' + user_id + ')...')
        stream_url = fetch_live_url_via_api(user_id)
        
        if stream_url:
            lines.append('#EXTINF:-1 tvg-logo="" group-title="' + group + '" tvg-id="' + user_id + '", ' + name)
            lines.append(stream_url)
            lines.append('')
            print('✅ 成功: ' + name)
            online_count += 1
            online_list.append(name)
        else:
            lines.append('#EXTINF:-1 tvg-logo="" group-title="' + group + '" tvg-id="' + user_id + '", ' + name + ' (未开播)')
            lines.append('# 未开播')
            lines.append('')
            print('❌ 未开播: ' + name)
    
    if online_list:
        lines.append('# 在线主播：' + ', '.join(online_list))
    lines.append('# 共 ' + str(len(TEACHERS)) + ' 个主播，在线 ' + str(online_count) + ' 个')
    
    with open(M3U_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    
    print('已写入 ' + M3U_PATH)


def main():
    print('=' * 40)
    print('快手专属直播源更新工具 (API版)')
    print('共 ' + str(len(TEACHERS)) + ' 个主播')
    print('=' * 40)
    generate_m3u()
    print('=' * 40)


if __name__ == '__main__':
    main()
