#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手游戏直播 m3u 更新器（纯 HTTP，无浏览器、无签名）

支持两种模式：
1. 热门/分类大池子：GET https://live.kuaishou.com/live_api/hot/list
2. 指定单个主播：GET https://live.kuaishou.com/live_api/profile/public?principalId=xxx

用法：
    python3 update_m3u.py              # 按 sources.txt 抓取并写 kuaishou_live.m3u
    python3 update_m3u.py --pages 50   # 覆盖页数上限（默认取 sources.txt 配置）
    python3 update_m3u.py --dry-run    # 只打印统计，不写文件
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
M3U_PATH = os.path.join(BASE_DIR, 'kuaishou_live.m3u')
SOURCES_PATH = os.path.join(BASE_DIR, 'sources.txt')

UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36')

DEFAULT_PAGES = 50       # HOT 列表默认抓取页数
MAX_PAGES = 50           # 单来源最多抓取页数上限
PAGE_WORKERS = 8         # 单来源内并发翻页线程数
MAX_SOURCE_WORKERS = 2   # 多来源间并发
REQUEST_TIMEOUT = 20

HOT_API = 'https://live.kuaishou.com/live_api/hot/list'
USER_API = 'https://live.kuaishou.com/live_api/profile/public'


def parse_args(argv):
    pages_override = None
    dry_run = False
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--dry-run':
            dry_run = True
        elif a == '--pages' and i + 1 < len(argv):
            try:
                pages_override = int(argv[i + 1])
                i += 1
            except ValueError:
                print(f'忽略无效页数: {argv[i + 1]}')
        i += 1
    return dry_run, pages_override


def load_sources(pages_override=None):
    """解析 sources.txt，支持 HOT 和 中文主播昵称/URL"""
    if not os.path.exists(SOURCES_PATH):
        raise SystemExit(f'缺少来源配置文件 {SOURCES_PATH}')
    
    hot_sources = []
    user_sources = []

    for line in open(SOURCES_PATH, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        if '/u/' in line:
            user_id = line.split('/u/')[-1].split('/')[0].split('?')[0]
            if user_id:
                user_sources.append(user_id)
        elif not line.startswith('HOT'):
            # 直接填中文名字（如：第一财团）
            user_sources.append(line)
        else:
            pages = DEFAULT_PAGES if pages_override is None else pages_override
            name = line
            if ':' in line.split('/')[-1]:
                name, _, pages_s = line.rpartition(':')
                try:
                    pages = int(pages_s)
                except ValueError:
                    pass
            name = name.split('/live/')[-1].rstrip('/') or 'HOT'
            if pages_override is not None:
                pages = pages_override
            pages = max(1, min(pages, MAX_PAGES))
            hot_sources.append((name.upper(), pages))

    return hot_sources, user_sources


def fetch_page(source, page):
    """抓取一页热门直播列表。"""
    url = f'{HOT_API}?type={source}&filterType=0&page={page}&pageSize=24'
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Referer': f'https://live.kuaishou.com/live/{source}',
    })
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
            body = json.load(r)
    except Exception as e:
        print(f'  [{source}] 第{page}页失败: {e}')
        return page, []
    return page, body.get('data', {}).get('list', [])


def fetch_user(user_id, all_hot_rooms=None):
    """直接在已抓取的热门列表中精确匹配昵称（如 '第一财团'）"""
    if all_hot_rooms:
        for lid, room in all_hot_rooms.items():
            author = room.get('author') or {}
            name = author.get('name') or ''
            kwai_id = author.get('id') or author.get('principalId') or ''
            
            # 同时匹配中文昵称、拼音 ID 或快手号
            if user_id in name or user_id.lower() in kwai_id.lower():
                print(f'  [主播 {name}] 成功在热门直播列表中匹配找到！')
                return room

    print(f'  [主播 {user_id}] 未在列表中找到')
    return None


def best_play_url(room):
    """从 playUrls 中取最高清晰度 CDN 直链（优先 level 最大，其次码率最大）。"""
    reps = []
    for pu in room.get('playUrls') or []:
        reps.extend((pu.get('adaptationSet') or {}).get('representation') or [])
    if not reps:
        return None
    reps = sorted(reps, key=lambda x: (x.get('level', 0), x.get('bitrate', 0)))
    return reps[-1].get('url')


def room_to_entry(room):
    """把房间 dict 转成 (tvg_id, entry_text, url) 三元组。"""
    live_id = room.get('id') or ''
    author = (room.get('author') or {})
    nick = author.get('name') or ''
    caption = (room.get('caption') or '').strip() or '直播间'
    game = ((room.get('gameInfo') or {}).get('name') or '').strip() or '分类'
    title = f'{nick}-{caption}'
    url = best_play_url(room)
    entry = (f'#EXTINF:-1 tvg-logo="" group-title="{game}" '
             f'tvg-id="{live_id}", {title}')
    return live_id, entry, url


def fetch_source(source, pages):
    """并发翻页抓取分类来源。"""
    rooms = {}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=min(PAGE_WORKERS, pages)) as pool:
        futs = {pool.submit(fetch_page, source, p): p for p in range(1, pages + 1)}
        for fut in as_completed(futs):
            page, items = fut.result()
            for room in items:
                lid = room.get('id')
                if lid and lid not in rooms:
                    rooms[lid] = room
    print(f'  [{source}] {pages}页抓完: {len(rooms)} 个不重复房间，'
          f'用时 {time.time() - t0:.1f}s')
    return rooms


def run(dry_run=False, pages_override=None):
    hot_sources, user_sources = load_sources(pages_override)
    total_pages = sum(p for _, p in hot_sources)
    print(f'开始抓取 {len(hot_sources)} 个分类（共 {total_pages} 页），{len(user_sources)} 个自定义主播...')

    all_rooms = {}
    
    # 1. 抓取分类列表
    if hot_sources:
        with ThreadPoolExecutor(max_workers=MAX_SOURCE_WORKERS) as pool:
            futs = {pool.submit(fetch_source, s, p): s for s, p in hot_sources}
            for fut, s in futs.items():
                try:
                    rooms = fut.result()
                    for lid, room in rooms.items():
                        if lid not in all_rooms:
                            all_rooms[lid] = room
                except Exception as e:
                    print(f'  [{s}] 整个来源失败: {e}')

    # 2. 抓取指定个人主播（直接从热门列表中匹配）
    if user_sources:
        for u in user_sources:
            room = fetch_user(u, all_hot_rooms=all_rooms)
            if room and room.get('id'):
                all_rooms[room['id']] = room

    entries = []
    skipped_no_url = 0
    for lid, room in all_rooms.items():
        _, entry, url = room_to_entry(room)
        if not url:
            skipped_no_url += 1
            continue
        entries.append((entry, url))

    print(f'共抓到 {len(all_rooms)} 个有效开播房间，'
          f'其中 {len(entries)} 个成功解析出播放地址'
          + (f'，{skipped_no_url} 个无地址被跳过' if skipped_no_url else ''))

    if dry_run:
        print(f'[dry-run] 将写入 {len(entries)} 条 m3u 条目到 {M3U_PATH}')
        for entry, url in entries[:5]:
            print('  ' + entry)
            print('    ' + (url[:120] if url else '') + '...')
        return

    lines = ['#EXTM3U',
             f'# 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}',
             f'# 房间数: {len(entries)}',
             f'# 数据源: 快手直播 (热门分类 + 独立主播配置)']
    for entry, url in entries:
        lines.append(entry)
        lines.append(url)
    with open(M3U_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'已写入 {len(entries)} 条到 {M3U_PATH}')


if __name__ == '__main__':
    dry_run, pages_override = parse_args(sys.argv[1:])
    run(dry_run=dry_run, pages_override=pages_override)