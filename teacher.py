#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取指定快手主播的直播地址，生成 teacher.m3u（增强版）
支持多个主播，自动去重，每天定时更新
"""
import json
import re
import time
import urllib.request
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M3U_PATH = os.path.join(BASE_DIR, 'teacher.m3u')

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36'

# ===== 在这里配置你要的主播列表（增删改都行） =====
TEACHERS = [
    {"id": "SJJC6688", "name": "爽姐讲财", "group": "财经"},
    {"id": "Diyicaituan", "name": "第一财团", "group": "财经"},
    # 新增主播按下面格式添加：
    # {"id": "主播ID", "name": "显示名称", "group": "分组"},
]
# ==================================================


def fetch_live_url(user_id):
    """
    从快手主播页面获取当前直播流地址（增强版）
    支持多种解析方式，提高成功率
    """
    url = f'https://live.kuaishou.com/u/{user_id}'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print(f'⚠️ 获取页面失败 ({user_id}): {e}')
        return None
    
    # ----- 方法1：从 __INITIAL_STATE__ 提取（主要方法） -----
    match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', html, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            
            # 路径1：liveStream.playUrls
            play_urls = data.get('liveStream', {}).get('playUrls', [])
            if play_urls:
                for pu in play_urls:
                    reps = pu.get('adaptationSet', {}).get('representation', [])
                    if reps:
                        best = sorted(reps, key=lambda x: (x.get('level', 0), x.get('bitrate', 0)))[-1]
                        stream_url = best.get('url')
                        if stream_url:
                            return stream_url
            
            # 路径2：room.playUrls
            room = data.get('room', {})
            if room:
                play_urls = room.get('playUrls', [])
                if play_urls:
                    for pu in play_urls:
                        reps = pu.get('adaptationSet', {}).get('representation', [])
                        if reps:
                            best = sorted(reps, key=lambda x: (x.get('level', 0), x.get('bitrate', 0)))[-1]
                            stream_url = best.get('url')
                            if stream_url:
                                return stream_url
        except Exception as e:
            print(f'⚠️ 解析 __INITIAL_STATE__ 失败 ({user_id}): {e}')
    
    # ----- 方法2：从页面中的 JSON 数据提取（更全面） -----
    try:
        # 搜索所有类似 playUrls 的 JSON 结构
        json_data = re.findall(r'\{[^{}]*"playUrls"[^{}]*\}', html)
        for item in json_data:
            try:
                data = json.loads(item)
                if 'playUrls' in data:
                    for pu in data['playUrls']:
                        reps = pu.get('adaptationSet', {}).get('representation', [])
                        if reps:
                            best = sorted(reps, key=lambda x: (x.get('level', 0), x.get('bitrate', 0)))[-1]
                            stream_url = best.get('url')
                            if stream_url and 'flv' in stream_url:
                                return stream_url
            except:
                continue
    except Exception as e:
        print(f'⚠️ 备用 JSON 提取失败 ({user_id}): {e}')
    
    # ----- 方法3：正则直接找 .flv 地址（兜底） -----
    match = re.search(r'https://[^\s"\']+\.flv[^\s"\']*', html)
    if match:
        return match.group(0)
    
    # ----- 方法4：尝试从分享链接重定向获取（最后手段） -----
    try:
        # 有些主播页面可能没有直接数据，尝试通过分享链接获取
        share_url = f'https://v.kuaishou.com/{user_id}'
        req_share = urllib.request.Request(share_url, headers={'User-Agent': UA})
        with urllib.request.urlopen(req_share, timeout=10) as r:
            html_share = r.read().decode('utf-8', errors='ignore')
            match = re.search(r'https://[^\s"\']+\.flv[^\s"\']*', html_share)
            if match:
                return match.group(0)
    except:
        pass
    
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
