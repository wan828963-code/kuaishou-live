#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快手游戏直播 m3u 更新器（纯 HTTP，无浏览器、无签名）
支持：热门列表 (HOT) + 指定主播 (USER:xxx)
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

DEFAULT_PAGES = 50
MAX_PAGES = 50
PAGE_WORKERS = 8
MAX_SOURCE_WORKERS = 2
REQUEST_TIMEOUT = 20

HOT_API = 'https://live.kuaishou.com/live_api/hot/list'


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
    """解析 sources.txt，支持 HOT 和 USER:xxx"""
    if not os.path.exists(SOURCES_PATH):
        raise SystemExit(f'缺少来源配置文件 {SOURCES_PATH}')
    out = []
    for line in open(SOURCES_PATH, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        pages = DEFAULT_PAGES if pages_override is None else pages_override

        # ===== 新增: 支持 USER:xxx =====
        if line.startswith('USER:'):
            user_id = line.replace('USER:', '').strip()
            if user_id:
                out.append((f'USER:{user_id}', 1))
            continue

        # 原有 HOT 逻辑
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
        out.append((name.upper(), pages))
    if not out:
        raise SystemExit('sources.txt 中没有有效来源')
    return out


def fetch_page(source, page):
    """抓取一页热门直播列表"""
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


def best_play_url(room):
    """从 playUrls 中取最高清晰度 CDN 直链"""
    reps = []
    for pu in room.get('playUrls') or []:
        reps.extend((pu.get('adaptationSet') or {}).get('representation') or [])
    if not reps:
        return None
    reps = sorted(reps, key=lambda x: (x.get('level', 0), x.get('bitrate', 0)))
    return reps[-1].get('url')


def room_to_entry(room):
    """把房间 dict 转成 (tvg_id, entry_text, url) 三元组"""
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
    """并发翻页抓取一个来源（HOT）"""
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


# ===== 新增: 抓取指定主播 =====
def fetch_user(user_id):
    """从热门列表中翻页查找指定主播"""
    print(f'  [USER:{user_id}] 开始查找...')
    for page in range(1, 31):
        url = f'{HOT_API}?type=HOT&filterType=0&page={page}&pageSize=50'
        req = urllib.request.Request(url, headers={
            'User-Agent': UA,
            'Referer': 'https://live.kuaishou.com/live/HOT',
        })
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as r:
                body = json.load(r)
        except Exception as e:
            print(f'    [USER:{user_id}] 第{page}页请求失败: {e}')
            continue

        room_list = body.get('data', {}).get('list', [])
        if not room_list:
            break

        for room in room_list:
            room_id = room.get('id', '')
            author = room.get('author', {})
            author_id = author.get('id', '')
            eid = author.get('eid', '')
            if user_id in (room_id, author_id, eid):
                print(f'    ✅ [USER:{user_id}] 找到主播!')
                return {user_id: room}  # 用 user_id 作为 key

    print(f'    ❌ [USER:{user_id}] 未找到 (可能未开播或不在热门列表)')
    return {}


def run(dry_run=False, pages_override=None):
    sources = load_sources(pages_override)
    total_pages = sum(p for _, p in sources if not _[0].startswith('USER:'))
    print(f'开始抓取 {len(sources)} 个来源...')

    all_rooms = {}

    # 1. 处理 HOT 来源 (用线程池)
    hot_sources = [(s, p) for s, p in sources if not s.startswith('USER:')]
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

    # 2. 处理 USER 来源 (逐个抓取)
    user_sources = [(s, p) for s, p in sources if s.startswith('USER:')]
    for source, _ in user_sources:
        user_id = source.replace('USER:', '')
        user_rooms = fetch_user(user_id)
        for lid, room in user_rooms.items():
            if lid not in all_rooms:
                all_rooms[lid] = room
                print(f'    ➕ 已添加 {user_id}')
            else:
                # 如果已存在，用新数据覆盖（更新地址）
                all_rooms[lid] = room
                print(f'    🔄 已更新 {user_id}')

    entries = []
    skipped_no_url = 0
    for lid, room in all_rooms.items():
        _, entry, url = room_to_entry(room)
        if not url:
            skipped_no_url += 1
            continue
        entries.append((entry, url))

    print(f'共抓到 {len(all_rooms)} 个房间，'
          f'其中 {len(entries)} 个有播放地址'
          + (f'，{skipped_no_url} 个无地址被跳过' if skipped_no_url else ''))

    if dry_run:
        print(f'[dry-run] 将写入 {len(entries)} 条 m3u 条目到 {M3U_PATH}')
        for entry, url in entries[:5]:
            print('  ' + entry)
            print('    ' + url[:120] + '...')
        return

    lines = ['#EXTM3U',
             f'# 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}',
             f'# 房间数: {len(entries)}',
             f'# 来源: HOT + 指定主播']
    for entry, url in entries:
        lines.append(entry)
        lines.append(url)
    with open(M3U_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'已写入 {len(entries)} 条到 {M3U_PATH}')


if __name__ == '__main__':
    dry_run, pages_override = parse_args(sys.argv[1:])
    run(dry_run=dry_run, pages_override=pages_override)    """从 playUrls 中取最高清晰度 CDN 直链（优先 level 最大，其次码率最大）。"""
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
    """并发翻页抓取一个来源，按页序合并去重（首次出现保留）。"""
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
    sources = load_sources(pages_override)
    total_pages = sum(p for _, p in sources)
    print(f'开始抓取 {len(sources)} 个来源（共 {total_pages} 页）...')

    all_rooms = {}
    with ThreadPoolExecutor(max_workers=MAX_SOURCE_WORKERS) as pool:
        futs = {pool.submit(fetch_source, s, p): s for s, p in sources}
        for fut, s in futs.items():
            try:
                rooms = fut.result()
                for lid, room in rooms.items():
                    if lid not in all_rooms:
                        all_rooms[lid] = room
            except Exception as e:
                print(f'  [{s}] 整个来源失败: {e}')

    entries = []
    skipped_no_url = 0
    for lid, room in all_rooms.items():
        _, entry, url = room_to_entry(room)
        if not url:
            skipped_no_url += 1
            continue
        entries.append((entry, url))

    print(f'共抓到 {len(all_rooms)} 个房间，'
          f'其中 {len(entries)} 个有播放地址'
          + (f'，{skipped_no_url} 个无地址被跳过' if skipped_no_url else ''))

    if dry_run:
        print(f'[dry-run] 将写入 {len(entries)} 条 m3u 条目到 {M3U_PATH}')
        for entry, url in entries[:5]:
            print('  ' + entry)
            print('    ' + url[:120] + '...')
        return

    lines = ['#EXTM3U',
             f'# 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}',
             f'# 房间数: {len(entries)}',
             f'# 数据源: https://live.kuaishou.com/live/HOT (live_api/hot/list，{total_pages}页并发)']
    for entry, url in entries:
        lines.append(entry)
        lines.append(url)
    with open(M3U_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f'已写入 {len(entries)} 条到 {M3U_PATH}')


if __name__ == '__main__':
    dry_run, pages_override = parse_args(sys.argv[1:])
    run(dry_run=dry_run, pages_override=pages_override)
