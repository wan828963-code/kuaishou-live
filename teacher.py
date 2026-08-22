#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取指定快手主播的直播地址（使用 Playwright 浏览器自动化）
"""
import os
import re
import time
from playwright.sync_api import sync_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M3U_PATH = os.path.join(BASE_DIR, 'teacher.m3u')

TEACHERS = [
    {"id": "SJJC6688", "name": "爽姐讲财", "group": "财经"},
    {"id": "Diyicaituan", "name": "第一财团", "group": "财经"},
]


def fetch_live_url_with_browser(user_id):
    """使用浏览器访问主播页面，获取直播流地址"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = f'https://live.kuaishou.com/u/{user_id}'
        print(f'  浏览器访问: {url}')
        
        try:
            page.goto(url, timeout=30000)
            page.wait_for_timeout(5000)  # 等待5秒让页面加载完成
            
            # 获取页面 HTML
            html = page.content()
            browser.close()
            
            # 从 HTML 中提取 .flv 地址
            match = re.search(r'https://[^\s"\']+\.flv[^\s"\']*', html)
            if match:
                return match.group(0)
            
            # 尝试从 __INITIAL_STATE__ 提取
            match = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.+?});', html, re.DOTALL)
            if match:
                import json
                try:
                    data = json.loads(match.group(1))
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
                except:
                    pass
            
            return None
            
        except Exception as e:
            print(f'  浏览器访问失败: {e}')
            browser.close()
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
        stream_url = fetch_live_url_with_browser(user_id)
        
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
    print('快手专属直播源更新工具 (浏览器版)')
    print('共 ' + str(len(TEACHERS)) + ' 个主播')
    print('=' * 40)
    generate_m3u()
    print('=' * 40)


if __name__ == '__main__':
    main()
