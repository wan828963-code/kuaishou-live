#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取指定快手主播的直播地址，生成 teacher.m3u
使用快手官方 API 接口，稳定可靠
"""
import json
import os
import sys
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


def fetch_live_url_by_api(user_id):
    """
    通过快手 live_api 接口获取指定主播的直播流地址
    原理：主播如果在热门列表中，接口会返回他的 playUrls
    """
    # 用 HOT 接口翻页，查找指定主播
    # 注意：如果主播不在热门列表里，这个接口是找不到的
    # 但第一财团这种热门主播，肯定在热门列表里
    api_url = 'https://live.kuaishou.com/live_api/hot/list'
    
    # 最多翻 20 页，每页 50 个房间，找指定主播
    max_pages = 20
    page_size = 50
    
    for page in range(1, max_pages + 1):
        url = f'{api_url}?type=HOT&filterType=0&page={page}&pageSize={page_size}'
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Referer': 'https://live.kuaishou.com/live/HOT',
        })
        
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
                body = json.load(r)
        except Exception as e:
            print(f'  翻页 {page} 失败: {e}')
            continue
        
        room_list = body.get('data', {}).get('list', [])
        if not room_list:
            break  # 没有更多数据了
        
        # 在列表中查找指定主播
        for room in room_list:
            author = room.get('author', {})
            author_id = author.get('id', '')
            # 注意：author.id 可能和 user_id 不同，需要用 id 匹配
            room_id = room.get('id', '')
            
            # 尝试多个匹配字段
            if (author_id == user_id or room_id == user_id or 
                author.get('eid', '') == user_id):
                # 找到主播，提取最高清播放地址
                play_urls = room.get('playUrls', [])
                if play_urls:
                    # 取最高清晰度
                    for pu in play_urls:
                        reps = pu.get('adaptationSet', {}).get('representation', [])
                        if reps:
                            best = sorted(reps, key=lambda x: (x.get('level', 0), x.get('bitrate', 0)))[-1]
                            stream_url = best.get('url')
                            if stream_url:
                                return stream_url
                break  # 找到了就跳出内层循环
    
    # 如果上面没找到，尝试用分享链接重定向方法（兜底）
    return fetch_live_url_by_share(user_id)


def fetch_live_url_by_share(user_id):
    """通过分享链接重定向获取流地址（兜底方法）"""
    try:
        share_url = f'https://v.kuaishou.com/{user_id}'
        req = urllib.request.Request(share_url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode('utf-8', errors='ignore')
            import re
            match = re.search(r'https://[^\s"\']+\.flv[^\s"\']*', html)
            if match:
                return match.group(0)
    except:
        pass
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
        stream_url = fetch_live_url_by_api(user_id)
        
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
    print('🚀 快手专属直播源更新工具（API版）')
    print(f'📋 共配置 {len(TEACHERS)} 个主播')
    print('=' * 40)
    generate_m3u()
    print('=' * 40)
    print('✅ 更新完成！')


if __name__ == '__main__':
    main()        pass
    
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
    online_list = []
    
    for teacher in TEACHERS:
        user_id = teacher["id"]
        name = teacher["name"]
        group = teacher["group"]
        
        print(f'🔍 正在获取 {name} ({user_id})...')
        stream_url = fetch_live_url(user_id)
        
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
    
    # 统计信息
    if online_list:
        lines.append(f'# ✅ 在线主播：{", ".join(online_list)}')
    lines.append(f'# 📊 共 {len(TEACHERS)} 个主播，在线 {online_count} 个')
    
    with open(M3U_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    
    print(f'\n📁 已写入 {M3U_PATH}，在线 {online_count}/{len(TEACHERS)}')
    if online_list:
        print(f'📺 在线主播：{", ".join(online_list)}')


def main():
    print('=' * 40)
    print('🚀 快手专属直播源更新工具（增强版）')
    print(f'📋 共配置 {len(TEACHERS)} 个主播')
    print('=' * 40)
    generate_m3u()
    print('=' * 40)
    print('✅ 更新完成！')


if __name__ == '__main__':
    main()
