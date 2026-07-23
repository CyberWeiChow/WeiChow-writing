#!/usr/bin/env python3
"""
打包成单个 index.html（GitHub Pages 直接服务）。
同时输出 portfolio.html 供本地双击预览。
用法：
    cd ~/Documents/GitHub/WeiChow\ writing
    python3 build.py
"""

import base64
import json
import mimetypes
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
WORKS_DIR = ROOT / 'works'
OUT = ROOT / 'index.html'       # GitHub Pages serves index.html by default
OUT_COPY = ROOT / 'portfolio.html'  # keep a copy for local preview

def inline_image(path_str):
    """Convert a local image path to a base64 data URL. Skip if URL or empty."""
    if not path_str:
        return ''
    if path_str.startswith(('http://', 'https://', 'data:')):
        return path_str
    # Try ROOT, then WORKS_DIR, then covers/
    for base in (ROOT, WORKS_DIR, ROOT / 'covers'):
        p = base / path_str
        if p.exists():
            mime, _ = mimetypes.guess_type(p.name)
            mime = mime or 'image/jpeg'
            b64 = base64.b64encode(p.read_bytes()).decode('ascii')
            return f'data:{mime};base64,{b64}'
    print(f'! 警告：找不到图片 {path_str}（已查找根目录和 works/）')
    return ''

manifest = json.loads((WORKS_DIR / 'manifest.json').read_text(encoding='utf-8'))

# Inline the bio photo as a data URL.
site = manifest.get('site', {})
if site.get('photo'):
    site['photo'] = inline_image(site['photo'])

# ---------- world map (Natural Earth 110m via world-atlas, public domain) ----------
# Decoded at build time into projected SVG path strings, cropped to East Asia.
# Projection must mirror the JS projCN(): equirectangular with cos(35°) x-scale.
PROJ_K = 15.24
PROJ_LON0, PROJ_LAT1 = 68.0, 58.0
PROJ_XSCALE = 0.82

def proj_cn(lon, lat):
    return ((lon - PROJ_LON0) * PROJ_XSCALE * PROJ_K, (PROJ_LAT1 - lat) * PROJ_K)

def build_world_paths():
    src = ROOT / 'assets' / 'world-110m.json'
    if not src.exists():
        print('! assets/world-110m.json 不存在，地图退回手绘轮廓')
        return []
    topo = json.loads(src.read_text(encoding='utf-8'))
    tr = topo.get('transform', {})
    scale = tr.get('scale', [1, 1])
    translate = tr.get('translate', [0, 0])

    decoded = []
    for arc in topo['arcs']:
        pts, x, y = [], 0, 0
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * scale[0] + translate[0], y * scale[1] + translate[1]))
        decoded.append(pts)

    def ring_points(arc_ids):
        ring = []
        for ai in arc_ids:
            pts = decoded[ai] if ai >= 0 else list(reversed(decoded[~ai]))
            ring.extend(pts[1:] if ring else pts)
        return ring

    # Crop window (lon/lat) slightly larger than the viewBox region.
    LON_MIN, LON_MAX, LAT_MIN, LAT_MAX = 55.0, 160.0, -5.0, 65.0

    paths = []
    for geom in topo['objects']['countries']['geometries']:
        gtype = geom.get('type')
        poly_sets = geom.get('arcs', [])
        if gtype == 'Polygon':
            poly_sets = [poly_sets]
        elif gtype != 'MultiPolygon':
            continue
        d_parts = []
        for polygon in poly_sets:
            for ring_arcs in polygon:
                ring = ring_points(ring_arcs)
                if not ring:
                    continue
                lons = [p[0] for p in ring]
                lats = [p[1] for p in ring]
                if max(lons) < LON_MIN or min(lons) > LON_MAX:
                    continue
                if max(lats) < LAT_MIN or min(lats) > LAT_MAX:
                    continue
                cmds, last = [], None
                for lon, lat in ring:
                    x, y = proj_cn(lon, lat)
                    pt = (round(x, 1), round(y, 1))
                    if pt == last:
                        continue
                    cmds.append(('M' if not cmds else 'L') + f'{pt[0]},{pt[1]}')
                    last = pt
                if len(cmds) >= 3:
                    d_parts.append(''.join(cmds) + 'Z')
        if d_parts:
            paths.append(''.join(d_parts))
    print(f'✓ 世界地图已生成（{len(paths)} 个国家/地区，裁剪至东亚区域）')
    return paths

world_paths = build_world_paths()

# Inline each work's cover image as a data URL.
for w in manifest.get('works', []):
    if w.get('cover'):
        w['cover'] = inline_image(w['cover'])
works_text = {}
novels = {}
missing = []
for w in manifest.get('works', []):
    if w.get('format') == 'novel':
        chapter_texts = []
        for chapter in w.get('chapters', []):
            chapter_file = WORKS_DIR / chapter['file']
            if not chapter_file.exists():
                missing.append(chapter['file'])
                continue
            chapter_texts.append({
                'title': chapter.get('title', chapter_file.stem),
                'text': chapter_file.read_text(encoding='utf-8')
            })
        if chapter_texts:
            novels[w['id']] = chapter_texts
            works_text[w['id']] = '\n\n'.join(c['text'] for c in chapter_texts)
        continue
    f = WORKS_DIR / w['file']
    if not f.exists():
        missing.append(w['file'])
        continue
    works_text[w['id']] = f.read_text(encoding='utf-8')

if missing:
    print(f'! 警告：以下文件不存在，已跳过：{missing}')

manifest['works'] = [w for w in manifest['works'] if w['id'] in works_text]

TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh" data-theme="light">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>周未 · ZHOU WEI</title>
  <meta name="description" content="周未 — 写作者与批评者，跨越创意写作、文化批评与财经新闻三种语境。" />
  <meta name="author" content="周未 ZHOU WEI" />

  <!-- Favicon: 「未」字 SVG data URI -->
  <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%23f5f2eb'/%3E%3Ctext x='32' y='46' font-family='Noto Serif SC, serif' font-size='38' font-weight='500' text-anchor='middle' fill='%231f1c17'%3E%E6%9C%AA%3C/text%3E%3C/svg%3E" />
  <link rel="apple-touch-icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%23f5f2eb'/%3E%3Ctext x='32' y='46' font-family='Noto Serif SC, serif' font-size='38' font-weight='500' text-anchor='middle' fill='%231f1c17'%3E%E6%9C%AA%3C/text%3E%3C/svg%3E" />

  <!-- Open Graph / Twitter Card -->
  <meta property="og:type" content="website" />
  <meta property="og:site_name" content="周未 · ZHOU WEI" />
  <meta property="og:title" content="周未 · ZHOU WEI" />
  <meta property="og:description" content="周未 — 写作者与批评者，跨越创意写作、文化批评与财经新闻三种语境。" />
  <meta property="og:image" content="__OG_IMAGE__" />
  <meta property="og:locale" content="zh_CN" />
  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="周未 · ZHOU WEI" />
  <meta name="twitter:description" content="周未 — 写作者与批评者，跨越创意写作、文化批评与财经新闻三种语境。" />
  <meta name="twitter:image" content="__OG_IMAGE__" />
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,400&family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&family=Noto+Serif+SC:wght@300;400;500;700&family=Roboto+Condensed:ital,wght@0,500;1,500&display=swap" rel="stylesheet">
  <style>
    :root[data-theme="dark"] {
      --bg: #0f0e0d;
      --surface: #1a1917;
      --ink: #ece7dd;
      --muted: #9a9285;
      --rule: #272522;
      --hover: #ffffff;
      --accent: #c4b49a;
    }
    :root[data-theme="light"] {
      --bg: #f5f2eb;
      --surface: #ede8dd;
      --ink: #1f1c17;
      --muted: #948b7d;
      --rule: #ddd7ca;
      --hover: #000;
      --accent: #8a7d6b;
    }
    :root {
      --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
      --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
      --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: 'Inter', 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
      font-weight: 400;
      -webkit-font-smoothing: antialiased;
      font-feature-settings: "kern", "liga", "ss01";
      transition: background 220ms var(--ease-out), color 220ms var(--ease-out);
      min-height: 100vh;
    }
    a { color: inherit; text-decoration: none; }

    /* ---- route transitions: pages leave before the next view is mounted ---- */
    #view {
      opacity: 1;
      transform: translateY(0);
      filter: blur(0);
      transition:
        opacity 180ms var(--ease-out),
        transform 180ms var(--ease-out),
        filter 180ms var(--ease-out);
    }
    #view.view-leaving {
      opacity: 0;
      transform: translateY(-8px);
      filter: blur(4px);
    }
    #view.view-entering {
      opacity: 0;
      transform: translateY(14px);
      filter: blur(5px);
      transition: none;
    }

    /* Theme changes bloom outward from the toggle when View Transitions exist. */
    ::view-transition-old(root),
    ::view-transition-new(root) { animation: none; mix-blend-mode: normal; }
    ::view-transition-new(root) { z-index: 9999; }
    ::view-transition-old(root) { z-index: 1; }

    /* A restrained ink halo appears only around the interactive Works strata. */
    .ink-cursor {
      position: fixed;
      left: 0;
      top: 0;
      z-index: 120;
      width: 76px;
      height: 76px;
      border-radius: 50%;
      pointer-events: none;
      opacity: 0;
      transform: translate3d(calc(var(--cursor-x, -100px) - 50%), calc(var(--cursor-y, -100px) - 50%), 0) scale(.72);
      background: radial-gradient(circle, color-mix(in srgb, var(--ink) 12%, transparent) 0, transparent 68%);
      border: 1px solid color-mix(in srgb, var(--ink) 18%, transparent);
      transition: opacity 180ms var(--ease-out), width 220ms var(--ease-spring), height 220ms var(--ease-spring), background 220ms var(--ease-out), border-color 220ms var(--ease-out);
      will-change: transform;
    }
    @media (hover: hover) and (pointer: fine) {
      body.works-cursor .ink-cursor { opacity: 1; }
      body.works-cursor .ink-cursor.over-line {
        width: 38px;
        height: 38px;
        background: radial-gradient(circle, color-mix(in srgb, var(--ink) 22%, transparent) 0, transparent 70%);
        border-color: color-mix(in srgb, var(--ink) 38%, transparent);
      }
      body.works-cursor .ink-cursor.over-card {
        width: 54px;
        height: 54px;
        background: transparent;
        border-color: color-mix(in srgb, var(--ink) 52%, transparent);
      }
    }

    /* ---- stagger container: fades children in one-by-one on mount ---- */
    .fade-stagger > * {
      opacity: 0;
      transform: translateY(8px);
      transition: opacity 520ms var(--ease-out), transform 520ms var(--ease-out);
      transition-delay: calc(var(--i, 0) * 55ms);
    }
    .fade-stagger.mounted > * {
      opacity: 1;
      transform: translateY(0);
    }

    /* ---- reduced motion: keep fade, drop movement ---- */
    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 150ms !important;
      }
      .fade-stagger > * { transform: none !important; transition-delay: 0ms !important; }
      #view { filter: none !important; transform: none !important; }
      .ink-cursor { display: none !important; }
    }
    button { font: inherit; color: inherit; background: none; border: none; cursor: pointer; padding: 0; }

    /* =============== TOP NAV =============== */
    .topbar {
      position: sticky;
      top: 0;
      z-index: 50;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 24px 48px;
      background: color-mix(in srgb, var(--bg) 92%, transparent);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--rule);
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    .topbar .brand {
      font-weight: 500;
      letter-spacing: 0.28em;
      transition: opacity 180ms var(--ease-out), transform 140ms var(--ease-out);
    }
    .topbar .brand:active { transform: scale(0.97); }
    @media (hover: hover) and (pointer: fine) {
      .topbar .brand:hover { opacity: 0.65; }
    }
    .topbar nav {
      display: flex;
      align-items: center;
      gap: 42px;
    }
    .topbar nav a {
      color: var(--muted);
      transition: color 180ms var(--ease-out), transform 140ms var(--ease-out);
      font-weight: 400;
      position: relative;
    }
    .topbar nav a::after {
      content: '';
      position: absolute;
      left: 0;
      bottom: -6px;
      width: 100%;
      height: 1px;
      background: currentColor;
      transform: scaleX(0);
      transform-origin: right;
      transition: transform 300ms var(--ease-out);
    }
    .topbar nav a.active { color: var(--hover); }
    .topbar nav a.active::after { transform: scaleX(1); transform-origin: left; }
    .topbar nav a:active { transform: scale(0.96); }
    @media (hover: hover) and (pointer: fine) {
      .topbar nav a:hover { color: var(--hover); }
      .topbar nav a:hover::after { transform: scaleX(1); transform-origin: left; }
    }
    .topbar .theme-toggle {
      width: 28px; height: 28px;
      border-radius: 50%;
      display: flex; align-items: center; justify-content: center;
      color: var(--muted);
      transition: color 180ms var(--ease-out), transform 200ms var(--ease-out);
    }
    .topbar .theme-toggle:active { transform: scale(0.9) rotate(0deg); }
    @media (hover: hover) and (pointer: fine) {
      .topbar .theme-toggle:hover { color: var(--hover); transform: rotate(-18deg); }
    }

    /* =============== BIO PAGE =============== */
    .bio-page { padding: 120px 48px 160px; max-width: 1280px; margin: 0 auto; }
    .bio-hero {
      display: grid;
      grid-template-columns: minmax(300px, 380px) 1fr;
      gap: 80px;
      align-items: stretch;
      margin-bottom: 140px;
    }
    .bio-portrait {
      background: var(--surface);
      background-size: cover;
      background-position: center;
      position: relative;
      overflow: hidden;
      min-height: 500px;
    }
    .bio-portrait.placeholder::after {
      content: '〔 portrait 〕';
      position: absolute;
      inset: 0;
      display: flex; align-items: center; justify-content: center;
      color: var(--muted);
      font-size: 13px;
      letter-spacing: 0.3em;
    }
    .bio-content {
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: 8px 0;
    }
    .bio-content h1 {
      font-family: 'Noto Serif SC', 'Cormorant Garamond', serif;
      font-size: 52px;
      font-weight: 500;
      margin: 0 0 18px;
      letter-spacing: 0.04em;
      line-height: 1.05;
      display: flex;
      align-items: baseline;
      gap: 20px;
      flex-wrap: wrap;
    }
    .bio-content h1 .en {
      font-family: 'Cormorant Garamond', 'Inter', serif;
      font-size: 15px;
      font-weight: 400;
      color: var(--muted);
      letter-spacing: 0.32em;
      text-transform: uppercase;
      transform: translateY(-4px);
    }
    .bio-tagline {
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: 19px;
      font-style: italic;
      color: var(--accent);
      margin: 0 0 0;
      letter-spacing: 0.02em;
    }
    .bio-rule {
      width: 48px;
      height: 1px;
      background: var(--rule);
      margin: 32px 0 36px;
    }
    .bio-content .bio-para {
      font-family: 'Noto Serif SC', serif;
      font-size: 15.5px;
      line-height: 2;
      color: color-mix(in srgb, var(--ink) 88%, transparent);
      margin: 0 0 22px;
      max-width: 560px;
    }
    .bio-content .bio-para.latin {
      font-family: 'Cormorant Garamond', 'EB Garamond', serif;
      font-style: italic;
      font-size: 14.5px;
      line-height: 1.75;
      color: var(--muted);
      margin: -12px 0 26px;
    }
    .bio-content .bio-para:last-child { margin-bottom: 0; }

    .bio-section {
      border-top: 1px solid var(--rule);
      padding-top: 64px;
      margin-bottom: 100px;
    }
    .bio-section h2 {
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: 30px;
      font-weight: 500;
      margin: 0 0 40px;
      letter-spacing: 0.02em;
      font-style: italic;
    }
    .edu-list {
      display: grid;
      grid-template-columns: 100px 1fr;
      row-gap: 28px;
      column-gap: 48px;
    }
    .edu-year { color: var(--muted); font-size: 13px; letter-spacing: 0.06em; padding-top: 2px; font-variant-numeric: tabular-nums; }
    .edu-info .school { font-weight: 600; font-size: 16px; }
    .edu-info .where  { color: var(--muted); font-size: 13px; margin-left: 6px; }
    .edu-info .detail { color: var(--muted); font-size: 13px; margin-top: 4px; }

    /* Timeline-style experience list */
    .exp-list {
      position: relative;
      list-style: none;
      padding: 8px 0 0 32px;
      margin: 0;
    }
    .exp-list::before {
      content: '';
      position: absolute;
      left: 5px;
      top: 14px;
      bottom: 14px;
      width: 1px;
      background: var(--rule);
    }
    .exp-item {
      position: relative;
      padding-bottom: 52px;
    }
    .exp-item:last-child { padding-bottom: 0; }
    .exp-item::before {
      content: '';
      position: absolute;
      left: -32px;
      top: 8px;
      width: 11px;
      height: 11px;
      border-radius: 50%;
      background: var(--bg);
      border: 1.5px solid var(--ink);
      transition: background 200ms var(--ease-out), transform 200ms var(--ease-out);
    }
    .exp-item:hover::before { background: var(--ink); transform: scale(1.15); }
    .exp-item.current::before { background: var(--ink); }
    .exp-year {
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      margin-bottom: 8px;
      font-variant-numeric: tabular-nums;
    }
    .exp-org { font-weight: 600; font-size: 16px; line-height: 1.4; }
    .exp-where {
      color: var(--muted);
      font-size: 13px;
      margin-left: 8px;
      font-weight: 400;
    }
    .exp-role {
      color: var(--muted);
      font-size: 12px;
      margin-top: 4px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }
    .exp-item ul {
      list-style: none;
      padding: 0;
      margin: 14px 0 0;
    }
    .exp-item li {
      position: relative;
      padding-left: 16px;
      font-size: 13.5px;
      line-height: 1.7;
      color: color-mix(in srgb, var(--ink) 88%, transparent);
      margin-bottom: 8px;
    }
    .exp-item li::before {
      content: '—';
      position: absolute;
      left: 0;
      color: var(--muted);
    }
    .exp-item li:last-child { margin-bottom: 0; }
    @media (max-width: 700px) {
      .edu-list { grid-template-columns: 1fr; row-gap: 16px; }
      .edu-year { font-size: 12px; }
    }

    /* =============== CATEGORY (works list) =============== */
    .cat-page { padding: 120px 48px 160px; max-width: 1300px; margin: 0 auto; }
    .cat-page h1 {
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: 72px;
      font-weight: 500;
      margin: 0 0 14px;
      letter-spacing: 0.01em;
      line-height: 1.0;
    }
    .cat-page .cat-sub {
      color: var(--accent);
      font-family: 'Cormorant Garamond', serif;
      font-size: 20px;
      font-style: italic;
      letter-spacing: 0.04em;
      margin: 0 0 72px;
    }
    .cat-divider {
      height: 14px;
      margin: 0 0 72px;
      color: var(--muted);
      opacity: 0.45;
    }
    .cat-divider svg {
      width: 100%;
      height: 100%;
      display: block;
    }
    /* =============== WORKS GRID (cover cards) =============== */
    .works-grid {
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
      gap: 64px 44px;
    }
    .work-card {
      display: block;
      cursor: pointer;
      transition: transform 220ms var(--ease-out);
    }
    .work-card:active { transform: scale(0.985); }
    .work-cover {
      aspect-ratio: 4 / 3;
      background-color: var(--surface);
      background-size: cover;
      background-position: center;
      margin-bottom: 22px;
      overflow: hidden;
      position: relative;
      transition: transform 500ms var(--ease-out), filter 400ms var(--ease-out);
      filter: grayscale(12%) contrast(98%);
    }
    @media (hover: hover) and (pointer: fine) {
      .work-card:hover .work-cover { transform: scale(1.02); filter: grayscale(0%) contrast(100%); }
    }
    .work-cover::after {
      content: '';
      position: absolute;
      inset: 0;
      background: rgba(0,0,0,0);
      transition: background 300ms var(--ease-out);
    }
    @media (hover: hover) and (pointer: fine) {
      .work-card:hover .work-cover::after { background: rgba(0,0,0,0.1); }
    }
    .work-cover.no-image::before {
      content: attr(data-placeholder);
      position: absolute;
      inset: 0;
      display: flex; align-items: center; justify-content: center;
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.3em;
      text-transform: uppercase;
    }
    .work-meta {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 16px;
      margin-bottom: 8px;
    }
    .work-card .title {
      font-family: 'Noto Serif SC', serif;
      font-size: 17px;
      font-weight: 600;
      line-height: 1.45;
      color: var(--ink);
      flex: 1;
    }
    .work-card .year {
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      white-space: nowrap;
      font-variant-numeric: tabular-nums;
    }
    .work-card .desc {
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
      margin: 0;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    /* =============== VIEWPORT PAGES (menu-switched, no long scroll) =============== */
    body:not(.reader-mode) { overflow: hidden; height: 100dvh; }
    .page {
      height: calc(100dvh - 65px);
      overflow-y: auto;
      overflow-x: hidden;
    }
    .bio-fit {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 48px 56px;
    }
    .bio-fit .bio-hero {
      width: min(1020px, 100%);
      margin: 0;
      margin-bottom: 0;
    }
    .contact-fit {
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .contact-fit .contact-page { padding: 40px; width: min(720px, 92vw); }
    .works-page {
      display: flex;
      align-items: center;
    }
    .works-inner {
      width: min(1100px, 94vw);
      margin: 0 auto;
      padding: 24px 0 48px;
    }

    /* =============== EXPERIENCE MAP =============== */
    .exp-page { position: relative; overflow: hidden; }
    .map-wrap {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: flex-start;
      padding: 3vh 2vw 3vh 4vw;
    }
    .map-wrap svg {
      height: 94%;
      max-width: 68vw;
    }
    .country {
      fill: color-mix(in srgb, var(--ink) 7%, var(--bg));
      stroke: var(--bg);
      stroke-width: 0.8;
      stroke-linejoin: round;
    }
    .pin { transform-box: fill-box; }
    .pin-dot {
      fill: var(--muted);
      transform-box: fill-box;
      transform-origin: center;
      transition: transform 260ms var(--ease-spring), fill 200ms var(--ease-out);
    }
    .pin-ring {
      fill: none;
      stroke: var(--muted);
      stroke-width: 1;
      transform-box: fill-box;
      transform-origin: center;
      animation: pinBreathe 3s var(--ease-out) infinite;
      opacity: 0;
    }
    @keyframes pinBreathe {
      0%   { transform: scale(0.35); opacity: 0.55; }
      70%  { transform: scale(1.15); opacity: 0; }
      100% { transform: scale(1.15); opacity: 0; }
    }
    .pin-label {
      font-family: 'EB Garamond', serif;
      font-style: italic;
      font-size: 13px;
      fill: var(--muted);
      opacity: 0;
      transition: opacity 240ms var(--ease-out);
    }
    .pin.active .pin-dot { fill: var(--ink); transform: scale(1.7); }
    .pin.active .pin-ring { stroke: var(--ink); }
    .pin.active .pin-label { opacity: 1; fill: var(--ink); }
    @media (hover: hover) and (pointer: fine) {
      .pin:hover .pin-dot { fill: var(--ink); transform: scale(1.5); }
      .pin:hover .pin-label { opacity: 1; }
    }

    .journey-panel {
      position: absolute;
      top: 28px;
      right: 32px;
      bottom: 28px;
      width: min(480px, 88vw);
      overflow-y: auto;
      background: color-mix(in srgb, var(--bg) 55%, transparent);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid var(--rule);
      scrollbar-width: thin;
      scrollbar-color: var(--rule) transparent;
    }
    .journey-panel::-webkit-scrollbar { width: 5px; }
    .journey-panel::-webkit-scrollbar-thumb { background: var(--rule); }
    .j-card {
      padding: 20px 26px;
      cursor: pointer;
      border-bottom: 1px solid color-mix(in srgb, var(--rule) 55%, transparent);
      transition: background 220ms var(--ease-out);
      position: relative;
    }
    .j-card:last-child { border-bottom: none; }
    .j-card::before {
      content: '';
      position: absolute;
      left: 0; top: 0; bottom: 0;
      width: 2px;
      background: var(--ink);
      transform: scaleY(0);
      transform-origin: top;
      transition: transform 280ms var(--ease-out);
    }
    .j-card.active { background: color-mix(in srgb, var(--ink) 5%, transparent); }
    .j-card.active::before { transform: scaleY(1); }
    .j-card:active { background: color-mix(in srgb, var(--ink) 9%, transparent); }
    .j-top {
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      gap: 12px;
      margin-bottom: 8px;
    }
    .j-year {
      font-size: 11px;
      letter-spacing: 0.12em;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }
    .j-city {
      font-family: 'EB Garamond', serif;
      font-style: italic;
      font-size: 11px;
      color: var(--muted);
      white-space: nowrap;
    }
    .j-org {
      font-size: 14.5px;
      font-weight: 600;
      line-height: 1.45;
      color: var(--ink);
      margin-bottom: 4px;
    }
    .j-role {
      font-size: 12px;
      color: var(--muted);
      letter-spacing: 0.04em;
    }
    .j-type {
      font-family: 'EB Garamond', serif;
      font-style: italic;
      font-size: 10px;
      letter-spacing: 0.14em;
      margin-left: 10px;
      opacity: 0.7;
      text-transform: uppercase;
    }
    .j-hl {
      list-style: none;
      padding: 0;
      margin: 12px 0 0;
    }
    .j-hl li {
      position: relative;
      padding-left: 15px;
      font-size: 12.5px;
      line-height: 1.7;
      color: color-mix(in srgb, var(--ink) 82%, transparent);
      margin-bottom: 7px;
    }
    .j-hl li::before {
      content: '—';
      position: absolute;
      left: 0;
      color: var(--muted);
    }
    .j-hl li:last-child { margin-bottom: 0; }

    /* Group dividers inside the journey panel */
    .j-group { padding-top: 8px; }
    .j-group + .j-group { margin-top: 12px; }
    .j-group-head {
      display: flex;
      align-items: baseline;
      gap: 12px;
      padding: 22px 26px 14px;
      position: sticky;
      top: 0;
      background: color-mix(in srgb, var(--bg) 82%, transparent);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      z-index: 2;
    }
    .j-group:first-child .j-group-head { padding-top: 26px; }
    .j-group-title {
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-style: italic;
      font-size: 22px;
      font-weight: 500;
      color: var(--ink);
      letter-spacing: 0.02em;
    }
    .j-group-sub {
      font-family: 'EB Garamond', serif;
      font-style: italic;
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .j-group-head::after {
      content: '';
      flex: 1;
      height: 1px;
      background: var(--rule);
      margin-bottom: 4px;
    }

    @media (max-width: 900px) {
      .map-wrap { justify-content: center; padding: 2vh 4vw 42vh; }
      .map-wrap svg { max-width: 92vw; height: auto; }
      .journey-panel {
        top: auto;
        left: 16px; right: 16px; bottom: 16px;
        height: 42vh;
        width: auto;
      }
    }

    /* =============== STRATA (ink-line layers, works grow from the line) =============== */
    .strata-hint {
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.12em;
      margin: -20px 0 40px;
      font-style: italic;
    }
    .stratum { position: relative; }
    .stratum-works {
      display: grid;
      grid-template-rows: 0fr;
      transition: grid-template-rows 640ms var(--ease-in-out);
    }
    .stratum.open .stratum-works { grid-template-rows: 1fr; }
    .stratum-works > .inner { overflow: hidden; min-height: 0; }
    .works-row {
      display: flex;
      align-items: flex-end;
      gap: 32px;
      padding: 56px 12px 40px;
      flex-wrap: wrap;
    }
    .soil-card {
      width: 190px;
      display: block;
      opacity: 0;
      --card-rx: 0deg;
      --card-ry: 0deg;
      --card-lift: 0px;
      transform: translateY(52px) perspective(900px) rotateX(var(--card-rx)) rotateY(var(--card-ry));
      transform-style: preserve-3d;
      will-change: transform;
      transition:
        opacity 420ms var(--ease-out),
        transform 560ms var(--ease-spring);
      transition-delay: calc(var(--i, 0) * 75ms);
    }
    .stratum.open .soil-card {
      opacity: 1;
      transform: translateY(var(--card-lift)) perspective(900px) rotateX(var(--card-rx)) rotateY(var(--card-ry));
    }
    .soil-card:active { transform: translateY(var(--card-lift)) perspective(900px) rotateX(var(--card-rx)) rotateY(var(--card-ry)) scale(0.98); }
    .soil-cover {
      aspect-ratio: 3 / 4;
      background-size: cover;
      background-position: center;
      background-color: var(--surface);
      box-shadow: 0 14px 36px rgba(0,0,0,0.35), 0 3px 10px rgba(0,0,0,0.25);
      position: relative;
      overflow: hidden;
      transition: transform 280ms var(--ease-spring), box-shadow 280ms var(--ease-out);
    }
    .soil-cover::after {
      content: '';
      position: absolute;
      inset: 0;
      pointer-events: none;
      opacity: 0;
      background: radial-gradient(circle at var(--shine-x, 50%) var(--shine-y, 50%), rgba(255,255,255,.18), transparent 48%);
      transition: opacity 220ms var(--ease-out);
    }
    @media (hover: hover) and (pointer: fine) {
      .soil-card:hover { --card-lift: -8px; }
      .soil-card:hover .soil-cover {
        box-shadow: 0 24px 48px rgba(0,0,0,0.45), 0 6px 14px rgba(0,0,0,0.3);
      }
      .soil-card:hover .soil-cover::after { opacity: 1; }
    }
    .soil-cover.no-image::before {
      content: attr(data-placeholder);
      position: absolute;
      inset: 0;
      display: flex; align-items: center; justify-content: center;
      color: rgba(255,248,235,0.85);
      font-size: 12px;
      letter-spacing: 0.2em;
      padding: 12px;
      text-align: center;
      line-height: 1.8;
    }
    .soil-title {
      margin-top: 12px;
      font-size: 13px;
      font-weight: 500;
      line-height: 1.5;
      color: var(--ink);
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .stratum-line {
      position: relative;
      display: block;
      width: 100%;
      height: 44px;
      cursor: pointer;
      background: none;
      border: none;
      padding: 0;
    }
    .stratum-line svg {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      overflow: visible;
    }
    .stratum-line path.ink {
      fill: none;
      stroke: var(--ink);
      stroke-linecap: round;
      transition: opacity 220ms var(--ease-out);
    }
    /* Four thin strands, braided: heavier lead + fading companions. */
    .stratum-line path.s0 { stroke-width: 0.9;  opacity: 0.65; }
    .stratum-line path.s1 { stroke-width: 0.7;  opacity: 0.42; }
    .stratum-line path.s2 { stroke-width: 0.55; opacity: 0.30; }
    .stratum-line path.s3 { stroke-width: 0.5;  opacity: 0.20; }
    .stratum:hover .stratum-line path.s0, .stratum.open .stratum-line path.s0 { opacity: 0.95; }
    .stratum:hover .stratum-line path.s1, .stratum.open .stratum-line path.s1 { opacity: 0.6; }
    .stratum:hover .stratum-line path.s2, .stratum.open .stratum-line path.s2 { opacity: 0.45; }
    .stratum:hover .stratum-line path.s3, .stratum.open .stratum-line path.s3 { opacity: 0.32; }
    .stratum-label {
      position: absolute;
      top: 50%;
      z-index: 2;
      /* Characters float just above the braid; halo masks any strand grazing the glyphs. */
      transform: translateY(calc(-100% - 2px));
      text-shadow:
        -1px -1px 0 var(--bg), 1px -1px 0 var(--bg),
        -1px 1px 0 var(--bg), 1px 1px 0 var(--bg),
        0 2px 3px var(--bg);
      font-family: 'Noto Serif SC', serif;
      font-size: 15px;
      font-weight: 500;
      letter-spacing: 0.42em;
      color: var(--muted);
      white-space: nowrap;
      line-height: 1;
      transition: color 220ms var(--ease-out);
    }
    .stratum:hover .stratum-label, .stratum.open .stratum-label {
      color: var(--ink);
    }
    .stratum-label.pos-0 { left: 12%; }
    .stratum-label.pos-1 { left: 44%; }
    .stratum-label.pos-2 { left: 72%; }
    @media (max-width: 600px) {
      .stratum-label { font-size: 13px; letter-spacing: 0.3em; }
      .stratum-label.pos-0 { left: 6%; }
      .stratum-label.pos-1 { left: 34%; }
      .stratum-label.pos-2 { left: 56%; }
    }
    .stratum-label .lch {
      display: inline-block;
      will-change: transform;
      transform-origin: 50% 100%;
    }
    .stratum-label .count {
      font-family: 'EB Garamond', serif;
      font-style: italic;
      font-size: 11px;
      color: var(--muted);
      margin-left: 12px;
      letter-spacing: 0;
      vertical-align: 0.5em;
    }

    @media (max-width: 700px) {
      .works-row { gap: 20px; padding: 40px 4px 28px; }
      .soil-card { width: calc(50% - 10px); }
    }

    /* =============== READER (base) =============== */
    .reader { max-width: 720px; margin: 0 auto; padding: 100px 48px 160px; position: relative; }
    .reader .back {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      margin-bottom: 64px;
      transition: color 180ms var(--ease-out), transform 140ms var(--ease-out), gap 220ms var(--ease-out);
    }
    .reader .back:active { transform: scale(0.97); }
    @media (hover: hover) and (pointer: fine) {
      .reader .back:hover { color: var(--hover); gap: 12px; }
    }
    .reader .cat-tag {
      color: var(--accent);
      font-family: 'Cormorant Garamond', serif;
      font-size: 13px;
      font-style: italic;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      margin-bottom: 22px;
    }
    .reader h1.headline {
      font-family: 'Noto Serif SC', 'Cormorant Garamond', serif;
      font-size: 34px;
      font-weight: 500;
      line-height: 1.35;
      margin: 0 0 16px;
      letter-spacing: 0.005em;
    }
    .reader .lede {
      font-family: 'Noto Serif SC', 'Cormorant Garamond', serif;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.75;
      margin: 0 0 18px;
      font-style: italic;
    }
    .reader .byline {
      font-size: 11px;
      letter-spacing: 0.2em;
      color: var(--muted);
      text-transform: uppercase;
      margin: 0 0 56px;
      padding-bottom: 28px;
      border-bottom: 1px solid var(--rule);
    }
    .paper-meta {
      margin: 0 0 48px;
      padding: 26px 28px;
      border: 1px solid var(--rule);
      background: color-mix(in srgb, var(--surface) 55%, transparent);
    }
    .paper-meta .meta-block + .meta-block { margin-top: 18px; padding-top: 18px; border-top: 1px solid var(--rule); }
    .paper-meta .meta-label {
      font-size: 10px;
      letter-spacing: 0.28em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 10px;
    }
    .paper-meta p {
      font-family: 'Noto Serif SC', 'Inter', serif;
      font-size: 14px;
      line-height: 1.85;
      color: color-mix(in srgb, var(--ink) 92%, transparent);
      margin: 0;
    }
    .paper-meta p.keywords {
      letter-spacing: 0.05em;
      color: var(--muted);
    }

    /* ---- shared reader body base ---- */
    .reader-body { color: var(--ink); }
    .reader-body .para { margin: 0 0 1.1em; }
    /* 「dialogue」 speaks in its own voice: warm accent, quote marks recede. */
    .reader-body .dlg {
      color: var(--accent);
      font-weight: 500;
    }
    .reader-body .dlg .q {
      color: var(--muted);
      opacity: 0.7;
      font-weight: 400;
    }
    .reader-variant-creative .reader-body .dlg {
      letter-spacing: 0.03em;
    }
    .reader-end {
      margin-top: 80px;
      text-align: center;
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.4em;
    }

    /* ============ CREATIVE WRITING ============ */
    .reader-variant-creative .reader-body {
      font-family: 'Noto Serif SC', 'Inter', serif;
      font-size: 18px;
      line-height: 2.15;
      letter-spacing: 0.01em;
      color: color-mix(in srgb, var(--ink) 94%, transparent);
    }
    .reader-variant-creative .byline {
      margin-bottom: 64px;
      padding-bottom: 32px;
      border-bottom-style: double;
    }
    .reader-variant-creative .lede {
      color: color-mix(in srgb, var(--ink) 70%, transparent);
      font-size: 17px;
      line-height: 1.85;
    }
    .reader-variant-creative .reader-end { font-style: italic; letter-spacing: 0.5em; }
    .novel-chapter-kicker {
      display: flex;
      align-items: center;
      gap: 14px;
      margin: -4px 0 18px;
      color: var(--muted);
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: 13px;
      font-style: italic;
      letter-spacing: .14em;
    }
    .novel-chapter-kicker::after { content: ''; flex: 1; height: 1px; background: var(--rule); }
    .novel-page-title {
      margin: 0 0 20px;
      font-family: 'Noto Serif SC', serif;
      font-size: 30px;
      font-weight: 500;
      letter-spacing: .08em;
    }
    .novel-directory {
      margin-top: 88px;
      padding-top: 36px;
      border-top: 3px double var(--ink);
    }
    .novel-directory-head {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 20px;
      margin-bottom: 28px;
    }
    .novel-directory-head h2 {
      margin: 0;
      font-family: 'Noto Serif SC', serif;
      font-size: 28px;
      font-weight: 500;
      letter-spacing: .08em;
    }
    .novel-directory-head span {
      color: var(--muted);
      font-family: 'Cormorant Garamond', serif;
      font-size: 13px;
      font-style: italic;
      letter-spacing: .12em;
    }
    .novel-directory-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      border-top: 1px solid var(--ink);
      border-left: 1px solid var(--ink);
    }
    .novel-directory-item {
      min-height: 112px;
      display: grid;
      grid-template-columns: 42px minmax(0, 1fr) auto;
      align-items: start;
      gap: 14px;
      padding: 19px 18px;
      border-right: 1px solid var(--ink);
      border-bottom: 1px solid var(--ink);
      transition: color 180ms var(--ease-out), background 180ms var(--ease-out), transform 160ms var(--ease-out);
    }
    .novel-directory-item .chapter-no {
      color: var(--muted);
      font-family: 'Cormorant Garamond', serif;
      font-size: 19px;
      font-style: italic;
    }
    .novel-directory-item .chapter-name {
      padding-top: 2px;
      font-family: 'Noto Serif SC', serif;
      font-size: 17px;
      line-height: 1.45;
    }
    .novel-directory-item .chapter-mark { color: var(--muted); font-size: 13px; }
    .novel-directory-item.active {
      color: #f5efe2;
      background: var(--ink);
    }
    .novel-directory-item.active .chapter-no,
    .novel-directory-item.active .chapter-mark { color: #f5efe2; opacity: .72; }
    @media (hover: hover) and (pointer: fine) {
      .novel-directory-item:not(.active):hover { color: var(--bg); background: var(--ink); transform: translate(-3px, -3px); box-shadow: 3px 3px 0 var(--accent); }
      .novel-directory-item:not(.active):hover .chapter-no,
      .novel-directory-item:not(.active):hover .chapter-mark { color: var(--bg); }
    }
    @media (max-width: 600px) {
      .novel-directory-grid { grid-template-columns: 1fr; }
      .novel-directory-item { min-height: 88px; }
      .novel-directory-head { align-items: flex-end; }
    }

    /* ============ CRITICISM ============ */
    .reader-variant-criticism .reader-body {
      font-family: 'Noto Serif SC', 'Inter', serif;
      font-size: 16.5px;
      line-height: 1.9;
      letter-spacing: 0.005em;
      color: var(--ink);
      text-align: justify;
    }
    .reader-variant-criticism .byline {
      padding-bottom: 24px;
      margin-bottom: 48px;
    }
    .reader-variant-criticism h1.headline {
      font-size: 28px;
      font-weight: 600;
    }
    .reader-variant-criticism .lede {
      color: var(--muted);
      font-size: 15px;
      line-height: 1.8;
      font-style: normal;
    }

    /* ============ FINANCIAL NEWS ============ */
    .reader-variant-news .reader-body {
      font-family: 'Noto Sans SC', 'Inter', -apple-system, sans-serif;
      font-size: 16px;
      line-height: 1.82;
      letter-spacing: 0;
      color: var(--ink);
    }
    .reader-variant-news h1.headline {
      font-family: 'Noto Sans SC', 'Inter', -apple-system, sans-serif;
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 0;
    }
    .reader-variant-news .byline {
      font-weight: 600;
      letter-spacing: 0.12em;
      font-size: 10px;
      padding-bottom: 20px;
      margin-bottom: 44px;
      border-bottom-width: 2px;
    }
    .reader-variant-news .lede {
      font-family: 'Noto Sans SC', 'Inter', sans-serif;
      font-size: 15px;
      line-height: 1.75;
      font-style: normal;
      color: var(--muted);
      border-left: 3px solid var(--rule);
      padding-left: 16px;
    }
    .reader-variant-news .reader-body .para {
      margin: 0 0 0.85em;
    }

    /* ============ TOC (Table of Contents) ============ */
    .reader-toc {
      display: none;
      position: fixed;
      top: 110px;
      left: calc(50% + 380px);
      width: 190px;
      max-height: calc(100vh - 160px);
      overflow-y: auto;
      font-size: 12px;
      line-height: 1.6;
      scrollbar-width: thin;
      scrollbar-color: var(--rule) transparent;
      z-index: 20;
    }
    .reader-toc::-webkit-scrollbar { width: 3px; }
    .reader-toc::-webkit-scrollbar-thumb { background: var(--rule); }
    .reader-toc .toc-title {
      font-family: 'Cormorant Garamond', serif;
      font-style: italic;
      font-size: 13px;
      color: var(--muted);
      margin-bottom: 16px;
      letter-spacing: 0.08em;
    }
    .reader-toc ol {
      list-style: none;
      padding: 0;
      margin: 0;
      border-left: 1px solid var(--rule);
    }
    .reader-toc li { margin: 0; }
    .reader-toc a {
      display: block;
      padding: 5px 0 5px 14px;
      color: var(--muted);
      line-height: 1.5;
      border-left: 2px solid transparent;
      margin-left: -1px;
      transition: color 180ms var(--ease-out), border-color 180ms var(--ease-out);
    }
    .reader-toc a.active {
      color: var(--ink);
      border-left-color: var(--accent);
    }
    @media (hover: hover) and (pointer: fine) {
      .reader-toc a:hover { color: var(--hover); }
    }
    @media (min-width: 1280px) {
      .reader-toc { display: block; }
    }

    /* Section headings inside reader-body */
    .reader-body h2.toc-heading {
      font-family: 'Noto Serif SC', serif;
      font-size: 20px;
      font-weight: 600;
      margin: 2.4em 0 0.9em;
      letter-spacing: 0.02em;
      scroll-margin-top: 100px;
      line-height: 1.4;
    }
    .reader-variant-criticism .reader-body h2.toc-heading {
      font-size: 18px;
    }
    .reader-variant-news .reader-body h2.toc-heading {
      font-family: 'Noto Sans SC', sans-serif;
      font-size: 17px;
      font-weight: 700;
    }

    /* ============ PREV / NEXT NAVIGATION ============ */
    .reader-nav {
      display: flex;
      justify-content: space-between;
      gap: 24px;
      margin-top: 72px;
      padding-top: 40px;
      border-top: 1px solid var(--rule);
    }
    .reader-nav > a {
      flex: 1;
      max-width: 48%;
      display: flex;
      flex-direction: column;
      gap: 8px;
      transition: color 180ms var(--ease-out), transform 140ms var(--ease-out);
    }
    .reader-nav > a:active { transform: scale(0.98); }
    @media (hover: hover) and (pointer: fine) {
      .reader-nav > a:hover { color: var(--hover); }
    }
    .reader-nav a.next { text-align: right; align-items: flex-end; }
    .reader-nav .nav-label {
      font-size: 10px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--muted);
    }
    .reader-nav .nav-title {
      font-family: 'Noto Serif SC', serif;
      font-size: 15px;
      font-weight: 500;
      line-height: 1.45;
    }

    /* ============ RELATED ARTICLES ============ */
    .reader-related {
      margin-top: 64px;
      padding-top: 40px;
      border-top: 1px solid var(--rule);
    }
    .reader-related .related-title {
      font-family: 'Cormorant Garamond', serif;
      font-style: italic;
      font-size: 18px;
      color: var(--muted);
      margin: 0 0 24px;
      letter-spacing: 0.04em;
    }
    .reader-related .related-list {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 16px;
    }
    .reader-related .related-item {
      display: block;
      padding: 18px 20px;
      border: 1px solid var(--rule);
      transition: border-color 200ms var(--ease-out), background 200ms var(--ease-out), transform 140ms var(--ease-out);
    }
    .reader-related .related-item:active { transform: scale(0.98); }
    @media (hover: hover) and (pointer: fine) {
      .reader-related .related-item:hover {
        border-color: var(--muted);
        background: color-mix(in srgb, var(--surface) 50%, transparent);
      }
    }
    .reader-related .ri-year {
      font-size: 10px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      color: var(--accent);
      margin-bottom: 8px;
    }
    .reader-related .ri-title {
      font-family: 'Noto Serif SC', serif;
      font-size: 14px;
      font-weight: 500;
      line-height: 1.45;
      color: var(--ink);
    }
    .reader-related .ri-desc {
      font-size: 12px;
      color: var(--muted);
      margin-top: 6px;
      line-height: 1.5;
      display: -webkit-box;
      -webkit-line-clamp: 1;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    /* ============ SHARE BAR ============ */
    .share-bar {
      margin-top: 32px;
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .share-btn {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      padding: 8px 18px;
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      border: 1px solid var(--rule);
      background: transparent;
      cursor: pointer;
      transition: color 180ms var(--ease-out), border-color 180ms var(--ease-out), transform 120ms var(--ease-out);
    }
    .share-btn:active { transform: scale(0.96); }
    @media (hover: hover) and (pointer: fine) {
      .share-btn:hover { color: var(--hover); border-color: var(--muted); }
    }
    .share-btn.copied { color: var(--accent); border-color: var(--accent); }
    .share-btn svg { width: 14px; height: 14px; flex-shrink: 0; }
    .share-qr {
      display: none;
      margin-top: 20px;
      padding: 20px;
      border: 1px solid var(--rule);
      background: #fff;
      max-width: 220px;
    }
    .share-qr.visible { display: block; }
    .share-qr img { display: block; width: 180px; height: 180px; }
    .share-qr .qr-hint {
      font-size: 11px;
      letter-spacing: 0.1em;
      color: #888;
      text-align: center;
      margin-top: 10px;
      text-transform: uppercase;
    }

    /* ============ READING TIME + BACK TO TOP ============ */
    .reader-meta-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 56px;
      padding-bottom: 14px;
      border-bottom: 1px solid var(--rule);
    }
    .reader-meta-bar .reading-time {
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .reader-meta-bar .reading-time::before {
      content: '';
      width: 8px; height: 8px;
      border-radius: 50%;
      background: var(--muted);
      opacity: 0.45;
    }
    .reader-meta-bar .word-count {
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.12em;
    }
    .back-to-top {
      position: fixed;
      bottom: 32px;
      right: 32px;
      width: 40px; height: 40px;
      border-radius: 50%;
      background: var(--surface);
      border: 1px solid var(--rule);
      display: flex; align-items: center; justify-content: center;
      color: var(--muted);
      cursor: pointer;
      opacity: 0;
      pointer-events: none;
      transform: translateY(12px);
      transition: opacity 260ms var(--ease-out), transform 260ms var(--ease-out), color 180ms var(--ease-out), background 180ms var(--ease-out);
      z-index: 60;
      font-size: 14px;
    }
    .back-to-top.visible {
      opacity: 1;
      pointer-events: auto;
      transform: translateY(0);
    }
    .back-to-top:active { transform: scale(0.92); }
    @media (hover: hover) and (pointer: fine) {
      .back-to-top:hover { color: var(--hover); background: var(--bg); }
    }

    /* =============== CURATED HOME · AN UNFINISHED LINE =============== */
    .curated-page {
      --spine-progress: 0;
      height: calc(100dvh - 65px);
      overflow-y: auto;
      overflow-x: hidden;
      scroll-behavior: smooth;
      position: relative;
    }
    .curated-stage {
      width: min(1240px, calc(100% - 96px));
      margin: 0 auto;
      position: relative;
      padding-bottom: 120px;
    }
    .curator-spine {
      position: absolute;
      top: 14vh;
      bottom: 8vh;
      left: 50%;
      width: 1px;
      background: color-mix(in srgb, var(--ink) 13%, transparent);
      pointer-events: none;
      z-index: 0;
    }
    .curator-spine::after {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(to bottom, var(--muted), var(--ink) 82%, transparent);
      transform: scaleY(var(--spine-progress));
      transform-origin: top;
      box-shadow: 0 0 14px color-mix(in srgb, var(--ink) 18%, transparent);
      will-change: transform;
    }
    .curator-section {
      position: relative;
      z-index: 1;
      min-height: 86vh;
      padding: 110px 0;
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 112px;
      align-items: center;
      scroll-margin-top: 24px;
    }
    .curator-section::before {
      content: '';
      position: absolute;
      left: 50%;
      top: 50%;
      width: 9px;
      height: 9px;
      border-radius: 50%;
      border: 1px solid var(--ink);
      background: var(--bg);
      transform: translate(-50%, -50%);
      box-shadow: 0 0 0 8px var(--bg);
    }
    .curator-origin { min-height: calc(100dvh - 65px); padding-top: 70px; }
    .curator-origin::before { top: 65%; }
    .curator-index {
      display: inline-flex;
      align-items: center;
      gap: 12px;
      color: var(--muted);
      font-size: 10px;
      letter-spacing: .24em;
      text-transform: uppercase;
      margin-bottom: 26px;
    }
    .curator-index::after { content: ''; width: 42px; height: 1px; background: var(--rule); }
    .curator-copy h1 {
      margin: 0 0 30px;
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: clamp(58px, 7vw, 104px);
      font-weight: 400;
      line-height: .94;
      letter-spacing: -.025em;
    }
    .curator-copy h1 .en {
      display: block;
      margin-top: 18px;
      color: var(--muted);
      font-size: .26em;
      font-style: italic;
      letter-spacing: .12em;
    }
    .curator-thesis {
      max-width: 520px;
      margin: 0;
      font-family: 'Noto Serif SC', serif;
      font-size: clamp(18px, 2vw, 24px);
      line-height: 1.85;
      font-weight: 300;
    }
    .curator-thesis .quiet { color: var(--muted); }
    .curator-caption {
      margin-top: 30px;
      max-width: 460px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.9;
      letter-spacing: .04em;
    }
    .curator-portrait {
      width: min(360px, 82%);
      aspect-ratio: 3 / 4;
      justify-self: center;
      position: relative;
      background: var(--surface) center / cover no-repeat;
      filter: grayscale(16%) contrast(102%);
      box-shadow: 24px 28px 0 color-mix(in srgb, var(--ink) 4%, transparent);
    }
    .curator-portrait::after {
      content: 'ZHOU WEI · WRITER / CRITIC';
      position: absolute;
      right: -25px;
      bottom: 28px;
      writing-mode: vertical-rl;
      color: var(--muted);
      font-size: 9px;
      letter-spacing: .22em;
    }
    .curator-section-head h2 {
      margin: 0 0 24px;
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: clamp(46px, 5vw, 72px);
      line-height: 1;
      font-weight: 400;
    }
    .curator-section-head h2 span {
      display: block;
      margin-top: 12px;
      color: var(--muted);
      font-size: 16px;
      font-style: italic;
      letter-spacing: .14em;
    }
    .curator-section-head p {
      max-width: 430px;
      margin: 0;
      color: color-mix(in srgb, var(--ink) 78%, transparent);
      font-family: 'Noto Serif SC', serif;
      font-size: 15px;
      line-height: 2;
    }
    .curator-works { display: grid; gap: 14px; }
    .curator-card {
      display: grid;
      grid-template-columns: 92px 1fr 18px;
      gap: 18px;
      align-items: center;
      padding: 14px;
      border: 1px solid var(--rule);
      background: color-mix(in srgb, var(--bg) 88%, transparent);
      backdrop-filter: blur(10px);
      transition: transform 260ms var(--ease-spring), border-color 220ms var(--ease-out), background 220ms var(--ease-out);
    }
    .curator-card-cover {
      aspect-ratio: 3 / 4;
      background: var(--surface) center / cover no-repeat;
      filter: grayscale(18%);
      transition: filter 260ms var(--ease-out), transform 260ms var(--ease-spring);
    }
    .curator-card-kind {
      color: var(--muted);
      font-size: 9px;
      letter-spacing: .18em;
      text-transform: uppercase;
      margin-bottom: 8px;
    }
    .curator-card-title {
      font-family: 'Noto Serif SC', serif;
      font-size: 15px;
      line-height: 1.55;
      font-weight: 500;
    }
    .curator-card-desc {
      margin-top: 7px;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.6;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .curator-card-arrow { color: var(--muted); transition: transform 220ms var(--ease-out); }
    @media (hover: hover) and (pointer: fine) {
      .curator-card:hover {
        transform: translateX(8px);
        border-color: color-mix(in srgb, var(--ink) 38%, var(--rule));
        background: color-mix(in srgb, var(--ink) 4%, var(--bg));
      }
      .curator-card:hover .curator-card-cover { filter: grayscale(0); transform: scale(1.025); }
      .curator-card:hover .curator-card-arrow { transform: translateX(3px); color: var(--ink); }
    }
    .curator-section.is-reversed .curator-section-head { order: 2; padding-left: 18px; }
    .curator-section.is-reversed .curator-works,
    .curator-section.is-reversed .curator-journey { order: 1; }
    .curator-journey { display: grid; gap: 0; }
    .curator-stop {
      display: grid;
      grid-template-columns: 88px 1fr;
      gap: 18px;
      padding: 18px 0;
      border-top: 1px solid var(--rule);
    }
    .curator-stop:last-child { border-bottom: 1px solid var(--rule); }
    .curator-stop-year { color: var(--muted); font-size: 10px; line-height: 1.6; }
    .curator-stop-city {
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: 21px;
      margin-bottom: 4px;
    }
    .curator-stop-detail { color: var(--muted); font-size: 11px; line-height: 1.6; }
    .curator-unfinished {
      min-height: 78vh;
      grid-template-columns: 1fr 1fr;
    }
    .curator-contact { display: grid; gap: 0; }
    .curator-contact a,
    .curator-contact button {
      padding: 20px 0;
      border-top: 1px solid var(--rule);
      display: flex;
      justify-content: space-between;
      color: var(--muted);
      text-align: left;
      transition: color 180ms var(--ease-out), padding 220ms var(--ease-out);
    }
    .curator-contact a:last-child,
    .curator-contact button:last-child { border-bottom: 1px solid var(--rule); }
    .curator-contact strong { color: var(--ink); font-weight: 400; }
    @media (hover: hover) and (pointer: fine) {
      .curator-contact a:hover,
      .curator-contact button:hover { color: var(--ink); padding-left: 8px; }
    }
    .curator-endmark {
      position: absolute;
      left: 50%;
      bottom: 46px;
      transform: translateX(-50%);
      color: var(--muted);
      font-family: 'Cormorant Garamond', serif;
      font-style: italic;
      font-size: 12px;
      letter-spacing: .14em;
      background: var(--bg);
      padding: 12px 0;
    }
    @media (max-width: 800px) {
      .curated-stage { width: calc(100% - 40px); padding-bottom: 80px; }
      .curator-spine { left: 22px; }
      .curator-section {
        min-height: auto;
        grid-template-columns: 1fr;
        gap: 54px;
        padding: 96px 8px 96px 58px;
      }
      .curator-section::before { left: 22px; top: 104px; }
      .curator-origin { min-height: calc(100dvh - 96px); padding-top: 70px; }
      .curator-origin::before { top: 104px; }
      .curator-portrait { width: min(290px, 90%); justify-self: start; }
      .curator-section.is-reversed .curator-section-head,
      .curator-section.is-reversed .curator-works,
      .curator-section.is-reversed .curator-journey { order: initial; padding-left: 0; }
      .curator-unfinished { grid-template-columns: 1fr; }
      .curator-endmark { left: 22px; transform: translateX(-50%); }
    }
    @media (max-width: 520px) {
      .curator-copy h1 { font-size: 52px; }
      .curator-card { grid-template-columns: 72px 1fr 14px; gap: 12px; padding: 10px; }
      .curator-card-desc { display: none; }
      .curator-stop { grid-template-columns: 68px 1fr; gap: 12px; }
    }

    /* =============== CONTACT =============== */
    .contact-page { padding: 140px 48px; max-width: 760px; margin: 0 auto; }
    .contact-page h1 {
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: 64px;
      font-weight: 500;
      margin: 0 0 64px;
      letter-spacing: 0.01em;
      line-height: 1.05;
      font-style: italic;
    }
    .contact-row {
      display: grid;
      grid-template-columns: 120px 1fr;
      gap: 24px;
      padding: 20px 0;
      border-top: 1px solid var(--rule);
      align-items: baseline;
    }
    .contact-row:last-child { border-bottom: 1px solid var(--rule); }
    .contact-row .label {
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
    }
    .contact-row .value {
      font-size: 16px;
      cursor: pointer;
      transition: color 180ms var(--ease-out), transform 140ms var(--ease-out);
      display: inline-block;
      position: relative;
    }
    .contact-row .value:active { transform: scale(0.97); }
    @media (hover: hover) and (pointer: fine) {
      .contact-row .value:hover { color: var(--hover); }
    }
    .contact-row .value.copied::after {
      content: '  · copied';
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      animation: copyFade 1.5s var(--ease-out);
    }
    @keyframes copyFade {
      0%   { opacity: 0; transform: translateY(2px); }
      15%  { opacity: 1; transform: translateY(0); }
      80%  { opacity: 1; }
      100% { opacity: 0; }
    }

    /* =============== MEDIA (social / new media gallery) =============== */
    .media-page {
      width: min(1200px, 100%);
      margin: 0 auto;
      padding: 48px 40px 120px;
    }
    .media-page h1 {
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: 64px;
      font-weight: 500;
      font-style: italic;
      margin: 0 0 10px;
      letter-spacing: 0.01em;
      line-height: 1.05;
    }
    .media-page .media-sub {
      color: var(--muted);
      font-size: 16px;
      letter-spacing: 0.06em;
      margin: 0 0 48px;
    }
    .media-accounts {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 24px;
      margin-bottom: 64px;
    }
    .m-account {
      border: 1px solid var(--rule);
      padding: 28px;
      display: flex;
      gap: 18px;
      align-items: flex-start;
      transition: border-color 220ms var(--ease-out), background 220ms var(--ease-out);
    }
    .m-account:hover { background: color-mix(in srgb, var(--ink) 3%, transparent); }
    .m-account .platform-icon {
      width: 44px; height: 44px;
      border-radius: 10px;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
      color: #fff;
      font-size: 20px;
      font-weight: 700;
    }
    .m-account.platform-wechat .platform-icon { background: #07C160; }
    .m-account.platform-xiaohongshu .platform-icon { background: #FF2442; }
    .m-account .platform-info { flex: 1; }
    .m-account .name {
      font-size: 18px;
      font-weight: 600;
      margin: 0 0 4px;
    }
    .m-account .handle {
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.08em;
      margin: 0 0 10px;
    }
    .m-account .bio {
      font-size: 13.5px;
      line-height: 1.6;
      color: color-mix(in srgb, var(--ink) 82%, transparent);
      margin: 0 0 14px;
    }
    .m-account .followers {
      font-size: 12px;
      color: var(--muted);
      letter-spacing: 0.08em;
    }
    .m-account .followers strong {
      color: var(--ink);
      font-size: 18px;
      font-weight: 600;
      margin-right: 6px;
      letter-spacing: 0;
    }

    .media-gallery {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 28px;
    }
    .m-card {
      display: block;
      cursor: pointer;
      border: 1px solid var(--rule);
      overflow: hidden;
      transition: transform 240ms var(--ease-out), box-shadow 240ms var(--ease-out), border-color 240ms var(--ease-out);
    }
    @media (hover: hover) and (pointer: fine) {
      .m-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 16px 40px rgba(0,0,0,0.08);
        border-color: color-mix(in srgb, var(--ink) 25%, var(--rule));
      }
    }
    .m-card .cover {
      aspect-ratio: 4 / 5;
      background-size: cover;
      background-position: center;
      position: relative;
    }
    .m-card .cover::after {
      content: '';
      position: absolute;
      inset: 0;
      background: rgba(0,0,0,0);
      transition: background 220ms var(--ease-out);
    }
    @media (hover: hover) and (pointer: fine) {
      .m-card:hover .cover::after { background: rgba(0,0,0,0.06); }
    }
    .m-card .cover.no-image::before {
      content: attr(data-placeholder);
      position: absolute;
      inset: 0;
      display: flex; align-items: center; justify-content: center;
      padding: 24px;
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.15em;
      text-transform: uppercase;
      text-align: center;
      line-height: 1.6;
    }
    .m-card .badge {
      position: absolute;
      top: 12px; left: 12px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 5px 10px;
      border-radius: 20px;
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #fff;
      z-index: 2;
    }
    .m-card .badge.wechat { background: #07C160; }
    .m-card .badge.xiaohongshu { background: #FF2442; }
    .m-card .info { padding: 18px; }
    .m-card .title {
      font-size: 15px;
      font-weight: 600;
      line-height: 1.45;
      color: var(--ink);
      margin: 0 0 8px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .m-card .subtitle {
      font-size: 12.5px;
      line-height: 1.55;
      color: var(--muted);
      margin: 0 0 16px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .m-card .meta {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      color: var(--muted);
      letter-spacing: 0.08em;
    }
    .m-card .metrics {
      display: flex;
      gap: 12px;
    }
    .m-card .metrics span::before {
      margin-right: 4px;
      opacity: 0.7;
    }
    .m-card .metrics .reads::before { content: '👁'; }
    .m-card .metrics .likes::before { content: '♥'; }
    .m-card .metrics .collects::before { content: '★'; }
    .m-card .metrics .comments::before { content: '✎'; }

    /* Lightbox */
    .m-lightbox {
      position: fixed;
      inset: 0;
      z-index: 200;
      background: color-mix(in srgb, var(--bg) 92%, transparent);
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 40px;
      opacity: 0;
      pointer-events: none;
      transition: opacity 260ms var(--ease-out);
    }
    .m-lightbox.open { opacity: 1; pointer-events: auto; }
    .m-lightbox .lb-inner {
      max-width: 760px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      border: 1px solid var(--rule);
      background: var(--bg);
    }
    .m-lightbox .lb-cover {
      width: 100%;
      aspect-ratio: 4 / 5;
      background-size: cover;
      background-position: center;
      background-color: var(--surface);
    }
    .m-lightbox .lb-info { padding: 28px; }
    .m-lightbox .lb-title {
      font-size: 22px;
      font-weight: 600;
      line-height: 1.4;
      margin: 0 0 10px;
    }
    .m-lightbox .lb-subtitle {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.65;
      margin: 0 0 20px;
    }
    .m-lightbox .lb-actions {
      display: flex;
      gap: 16px;
      align-items: center;
      flex-wrap: wrap;
    }
    .m-lightbox .lb-link {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 18px;
      border: 1px solid var(--ink);
      color: var(--ink);
      font-size: 11px;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      transition: background 180ms var(--ease-out), color 180ms var(--ease-out);
    }
    .m-lightbox .lb-link:hover { background: var(--ink); color: var(--bg); }
    .m-lightbox .lb-close {
      position: absolute;
      top: 24px; right: 24px;
      width: 40px; height: 40px;
      display: flex; align-items: center; justify-content: center;
      color: var(--muted);
      font-size: 24px;
      transition: color 180ms var(--ease-out), transform 140ms var(--ease-out);
    }
    .m-lightbox .lb-close:hover { color: var(--hover); transform: rotate(90deg); }
    .m-lightbox .lb-metrics {
      display: flex;
      gap: 20px;
      font-size: 12px;
      color: var(--muted);
      letter-spacing: 0.06em;
    }

    /* =============== PROGRESS =============== */
    .progress {
      position: fixed;
      top: 0; left: 0;
      height: 1px;
      background: var(--hover);
      width: 0;
      z-index: 100;
      opacity: 0.4;
    }

    /* =============== MOBILE =============== */
    @media (max-width: 900px) {
      .topbar { padding: 18px 24px; gap: 16px; }
      .topbar nav { gap: 22px; }
      .bio-hero { grid-template-columns: 1fr; gap: 40px; }
      .bio-portrait { max-width: 300px; }
      .bio-content h1 { font-size: 42px; }
      .cat-page h1 { font-size: 48px; }
      .reader { padding: 72px 28px 120px; }
      .reader-related .related-list { grid-template-columns: 1fr; }
    }
    @media (max-width: 600px) {
      /* Two-row topbar: brand row on top (toggle pinned right), nav links row below. */
      .topbar {
        flex-wrap: wrap;
        row-gap: 12px;
        padding: 14px 20px;
      }
      .topbar .brand {
        white-space: nowrap;
        font-size: 11px;
        letter-spacing: 0.18em;
      }
      .topbar nav {
        order: 3;
        width: 100%;
        justify-content: space-between;
        gap: 8px;
      }
      .topbar nav a {
        font-size: 10.5px;
        letter-spacing: 0.14em;
        white-space: nowrap;
      }
      .topbar nav .theme-toggle {
        position: absolute;
        top: 10px;
        right: 16px;
      }
      /* page height accounts for the taller two-row topbar */
      .page { height: calc(100dvh - 96px); }
      .curated-page { height: calc(100dvh - 96px); }

      /* Bio: top-anchor so nothing is cropped; photo smaller so the name shows sooner. */
      .bio-fit { align-items: flex-start; padding: 24px 24px 48px; }
      .bio-fit .bio-hero { margin: 0 auto; }
      .bio-portrait { max-width: 220px; }
      .bio-content h1 { font-size: 36px; }

      .bio-page { padding: 80px 24px 120px; }
      .cat-page { padding: 80px 24px 120px; }
      .works-grid { grid-template-columns: 1fr; }
      .contact-page h1 { font-size: 44px; }
      .reader-nav { gap: 16px; }
      .reader-nav .nav-title { font-size: 13px; }
      .share-qr { max-width: 180px; }
      .share-qr img { width: 140px; height: 140px; }
    }

    /* ================================================================
       PRINT EDITION
       A paper-first editorial layer: serif typography, measured rules,
       asymmetrical columns, and one structural axis. No glass or glow.
       ================================================================ */
    :root[data-theme="light"] {
      --bg: #f3f0e8;
      --surface: #e9e5dc;
      --ink: #171714;
      --muted: #77736a;
      --rule: #bdb8ad;
      --hover: #171714;
      --accent: #7d2e22;
    }
    html { background: var(--bg); }
    body {
      font-family: 'Noto Serif SC', 'Songti SC', 'STSong', Georgia, serif;
      font-weight: 400;
      letter-spacing: .01em;
      background: var(--bg);
      color: var(--ink);
      transition: none;
    }
    .ink-cursor { display: none !important; }
    #view {
      filter: none;
      transition: opacity 120ms linear;
    }
    #view.view-leaving,
    #view.view-entering { transform: none; filter: none; }
    .fade-stagger > * {
      transform: none;
      transition: opacity 240ms linear;
      transition-delay: calc(var(--i, 0) * 28ms);
    }
    .topbar {
      padding: 17px 32px 15px;
      background: var(--bg);
      backdrop-filter: none;
      -webkit-backdrop-filter: none;
      border-bottom: 1px solid var(--ink);
      font-family: 'Inter', 'Noto Sans SC', sans-serif;
      font-size: 10px;
      letter-spacing: .12em;
    }
    .topbar .brand { font-weight: 500; letter-spacing: .1em; }
    .topbar nav { gap: 28px; }
    .topbar nav a { color: var(--ink); }
    .topbar nav a::after {
      bottom: -16px;
      height: 2px;
      transition: none;
    }
    .topbar nav a:not(.active) { color: var(--muted); }

    .curated-page {
      height: calc(100dvh - 50px);
      scroll-behavior: auto;
      scrollbar-color: var(--ink) var(--bg);
    }
    .curated-stage {
      width: min(1460px, calc(100% - 64px));
      padding-bottom: 96px;
    }
    .curator-spine {
      left: 33.333%;
      top: 0;
      bottom: 0;
      background: var(--rule);
    }
    .curator-spine::after {
      background: var(--ink);
      box-shadow: none;
    }
    .curator-section,
    .curator-unfinished {
      min-height: auto;
      grid-template-columns: minmax(230px, 1fr) minmax(0, 2fr);
      gap: 64px;
      align-items: start;
      padding: 96px 0 112px;
      border-top: 1px solid var(--rule);
    }
    .curator-section::before {
      left: 33.333%;
      top: -1px;
      width: 16px;
      height: 3px;
      border: 0;
      border-radius: 0;
      background: var(--ink);
      box-shadow: 0 0 0 6px var(--bg);
      transform: translateX(-50%);
    }
    .curator-origin {
      min-height: calc(100dvh - 50px);
      padding: 64px 0 86px;
      border-top: 0;
      align-items: start;
    }
    .curator-origin::before { top: 64px; }
    .curator-index {
      margin-bottom: 44px;
      font-family: 'Inter', 'Noto Sans SC', sans-serif;
      font-size: 9px;
      letter-spacing: .16em;
      color: var(--ink);
    }
    .curator-index::after { background: var(--ink); width: 28px; }
    .curator-copy { padding-right: 12px; }
    .curator-copy h1 {
      margin: 0 0 38px;
      font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
      font-size: clamp(52px, 6vw, 88px);
      font-weight: 400;
      line-height: 1.08;
      letter-spacing: -.045em;
    }
    .curator-copy h1 .en {
      margin-top: 15px;
      font-family: 'Cormorant Garamond', Georgia, serif;
      font-size: .28em;
      font-style: italic;
      font-weight: 400;
      letter-spacing: .025em;
      color: var(--ink);
    }
    .curator-thesis {
      font-size: clamp(17px, 1.65vw, 22px);
      line-height: 1.95;
      letter-spacing: .03em;
    }
    .curator-caption {
      margin-top: 42px;
      padding-top: 14px;
      border-top: 1px solid var(--rule);
      font-family: 'Inter', 'Noto Sans SC', sans-serif;
      font-size: 10px;
      line-height: 1.75;
      letter-spacing: .025em;
    }
    .curator-portrait {
      width: 100%;
      aspect-ratio: 16 / 10;
      justify-self: stretch;
      background-position: center 28%;
      filter: grayscale(100%) contrast(104%);
      box-shadow: none;
      border: 0;
    }
    .curator-portrait::after {
      right: auto;
      left: 0;
      bottom: -24px;
      writing-mode: horizontal-tb;
      font-family: 'Inter', sans-serif;
      font-size: 8px;
      letter-spacing: .12em;
    }
    .curator-section-head,
    .curator-section.is-reversed .curator-section-head {
      order: 1;
      padding: 0 20px 0 0;
      position: sticky;
      top: 84px;
    }
    .curator-section-head h2 {
      margin: 0 0 32px;
      font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
      font-size: clamp(40px, 4.2vw, 62px);
      font-weight: 400;
      line-height: 1.05;
      letter-spacing: -.035em;
    }
    .curator-section-head h2 span {
      margin-top: 16px;
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: 18px;
      font-weight: 400;
      letter-spacing: .035em;
      color: var(--ink);
    }
    .curator-section-head p {
      max-width: 340px;
      color: var(--ink);
      font-size: 14px;
      line-height: 2.05;
      letter-spacing: .025em;
      text-align: justify;
    }
    .curator-works,
    .curator-section.is-reversed .curator-works,
    .curator-journey,
    .curator-section.is-reversed .curator-journey {
      order: 2;
      gap: 0;
    }
    .curator-card {
      grid-template-columns: minmax(110px, 24%) 1fr 24px;
      gap: 24px;
      padding: 18px 0 22px;
      border: 0;
      border-top: 1px solid var(--ink);
      background: transparent;
      backdrop-filter: none;
      transition: none;
    }
    .curator-card:last-child { border-bottom: 1px solid var(--ink); }
    .curator-card-cover {
      aspect-ratio: 4 / 3;
      filter: grayscale(100%) contrast(102%);
      transition: filter 180ms linear;
    }
    .curator-card-kind {
      font-family: 'Inter', 'Noto Sans SC', sans-serif;
      font-size: 8px;
      letter-spacing: .12em;
      color: var(--muted);
    }
    .curator-card-title {
      font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
      font-size: clamp(18px, 2vw, 27px);
      line-height: 1.45;
      font-weight: 500;
      letter-spacing: -.018em;
    }
    .curator-card-desc {
      max-width: 640px;
      margin-top: 12px;
      color: var(--ink);
      font-size: 12px;
      line-height: 1.8;
      letter-spacing: .02em;
      -webkit-line-clamp: 3;
    }
    .curator-card-arrow {
      align-self: start;
      padding-top: 2px;
      color: var(--ink);
      font-family: Georgia, serif;
      font-size: 20px;
    }
    @media (hover: hover) and (pointer: fine) {
      .curator-card:hover { transform: none; background: transparent; border-color: var(--ink); }
      .curator-card:hover .curator-card-cover { transform: none; filter: grayscale(0); }
      .curator-card:hover .curator-card-title { text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 4px; }
      .curator-card:hover .curator-card-arrow { transform: none; }
    }
    .curator-stop {
      grid-template-columns: 118px 1fr;
      gap: 24px;
      padding: 20px 0 24px;
      border-top: 1px solid var(--ink);
    }
    .curator-stop:last-child { border-bottom-color: var(--ink); }
    .curator-stop-year {
      font-family: 'Inter', 'Noto Sans SC', sans-serif;
      font-size: 9px;
      letter-spacing: .04em;
      color: var(--ink);
    }
    .curator-stop-city {
      font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
      font-size: 24px;
      letter-spacing: -.02em;
    }
    .curator-stop-detail { font-size: 11px; line-height: 1.75; }
    .curator-contact a,
    .curator-contact button {
      border-top-color: var(--ink);
      font-family: 'Inter', 'Noto Sans SC', sans-serif;
      font-size: 10px;
      letter-spacing: .04em;
    }
    .curator-contact a:last-child,
    .curator-contact button:last-child { border-bottom-color: var(--ink); }
    .curator-endmark {
      left: 33.333%;
      bottom: 24px;
      color: var(--ink);
      font-size: 11px;
      box-shadow: 0 0 0 10px var(--bg);
    }

    /* Article pages use the same typographic sheet. */
    .reader {
      max-width: 880px;
      padding-top: 92px;
    }
    .reader .headline {
      font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
      font-weight: 500;
      letter-spacing: -.035em;
      line-height: 1.2;
    }
    .reader .lede,
    .reader-body .para {
      font-family: 'Noto Serif SC', 'Songti SC', Georgia, serif;
      text-align: justify;
      text-justify: inter-ideograph;
    }
    .reader-body .para { line-height: 2.05; letter-spacing: .025em; }
    .reader-meta-bar,
    .byline,
    .cat-tag,
    .back,
    .reader-toc,
    .share-bar,
    .reader-nav .nav-label {
      font-family: 'Inter', 'Noto Sans SC', sans-serif;
    }
    .reader-toc { border-left: 1px solid var(--ink); }
    .share-btn,
    .reader-related,
    .reader-nav { border-color: var(--ink); }

    @media (max-width: 800px) {
      .curated-stage { width: calc(100% - 32px); }
      .curator-spine { left: 28px; }
      .curator-section,
      .curator-unfinished {
        grid-template-columns: 1fr;
        gap: 52px;
        padding: 76px 8px 84px 54px;
      }
      .curator-section::before { left: 28px; top: -1px; }
      .curator-origin { min-height: auto; padding-top: 54px; }
      .curator-origin::before { top: 54px; }
      .curator-section-head,
      .curator-section.is-reversed .curator-section-head { position: static; padding: 0; }
      .curator-portrait { width: 100%; }
      .curator-endmark { left: 28px; }
    }
    @media (max-width: 600px) {
      .topbar { padding: 14px 18px 12px; border-bottom-width: 1px; }
      .topbar nav { overflow-x: auto; justify-content: flex-start; gap: 18px; scrollbar-width: none; }
      .topbar nav::-webkit-scrollbar { display: none; }
      .curated-page { height: calc(100dvh - 92px); }
      .curator-card { grid-template-columns: 82px 1fr 16px; gap: 14px; }
      .curator-card-title { font-size: 16px; }
      .curator-card-desc { display: none; }
      .reader { padding-left: 22px; padding-right: 22px; }
    }

    /* ================================================================
       FRONTIER EDITION
       Adapted structural language: a persistent chapter rail, oversized
       condensed chapter bands, saturated covers, and cream reading sheets.
       ================================================================ */
    :root {
      --fd-blue: #1a16ee;
      --fd-cream: #f8f0e2;
      --fd-ink: #252521;
      --fd-pink: #ff71bd;
      --fd-lime: #8df51f;
      --fd-orange: #ff7b16;
      --fd-cyan: #16cdef;
      --fd-purple: #be46ef;
      --fd-rail: 86px;
      --fd-display: 'Roboto Condensed', 'Noto Sans SC', sans-serif;
      --fd-mono: 'Inter', 'Noto Sans SC', sans-serif;
    }
    body { background: var(--fd-blue); }
    body:not(.reader-mode) { height: 100dvh; overflow: hidden; }
    #view {
      margin-left: var(--fd-rail);
      background: var(--fd-blue);
    }
    .topbar {
      position: fixed;
      inset: 0 auto 0 0;
      z-index: 180;
      width: var(--fd-rail);
      height: 100dvh;
      padding: 14px 10px 12px;
      display: flex;
      flex-direction: column;
      align-items: stretch;
      justify-content: space-between;
      gap: 20px;
      overflow: hidden;
      background: var(--fd-blue);
      color: var(--fd-cream);
      border: 0;
      border-right: 3px solid var(--fd-cream);
      transition: width 420ms cubic-bezier(.65,0,.35,1), background 180ms linear;
    }
    .topbar::after {
      content: '';
      position: absolute;
      top: 0;
      right: -3px;
      bottom: 0;
      width: 3px;
      background: repeating-linear-gradient(to bottom, transparent 0 5px, var(--fd-cream) 5px 8px);
    }
    .topbar .brand {
      color: var(--fd-cream);
      font-family: var(--fd-display);
      font-size: 17px;
      line-height: .92;
      letter-spacing: -.035em;
      white-space: normal;
      text-transform: uppercase;
    }
    .topbar nav {
      width: 100%;
      display: flex;
      flex-direction: column;
      align-items: stretch;
      gap: 3px;
    }
    .topbar nav a {
      min-height: 54px;
      padding: 8px 5px 6px;
      display: grid;
      grid-template-columns: 56px 1fr;
      align-items: center;
      color: var(--fd-cream);
      font-family: var(--fd-display);
      text-transform: uppercase;
      overflow: hidden;
    }
    .topbar nav a::after { display: none; }
    .topbar nav a.active,
    .topbar nav a:hover { color: var(--fd-blue); background: var(--fd-cream); }
    .nav-code {
      font-size: 46px;
      line-height: .8;
      letter-spacing: -.08em;
    }
    .nav-label {
      opacity: 0;
      transform: translateX(16px);
      font-size: 30px;
      line-height: .9;
      letter-spacing: -.04em;
      white-space: nowrap;
      transition: opacity 220ms linear, transform 420ms cubic-bezier(.65,0,.35,1);
    }
    @media (hover: hover) and (pointer: fine) {
      .topbar:hover { width: 260px; }
      .topbar:hover .nav-label { opacity: 1; transform: translateX(0); }
    }

    .curated-page {
      height: 100dvh;
      background: var(--fd-blue);
      color: var(--fd-ink);
      scrollbar-color: var(--fd-cream) var(--fd-blue);
    }
    .curated-stage { width: 100%; padding: 0; }
    .curator-spine { display: none; }
    .curator-section::before { display: none; }

    .curator-origin {
      min-height: 100dvh;
      padding: 26px 28px 54px;
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(340px, .9fr);
      gap: 34px;
      align-items: end;
      color: var(--fd-cream);
      background: var(--fd-blue);
      border: 0;
    }
    .curator-origin .curator-index,
    .curator-origin .curator-thesis,
    .curator-origin .curator-caption,
    .curator-origin .curator-copy h1 .en { color: var(--fd-cream); }
    .curator-origin .curator-index::after { background: var(--fd-cream); }
    .curator-copy { align-self: stretch; display: flex; flex-direction: column; }
    .curator-copy h1 {
      margin: auto 0 28px;
      font-family: var(--fd-display);
      font-size: clamp(86px, 14vw, 220px);
      font-weight: 500;
      line-height: .72;
      letter-spacing: -.075em;
      text-transform: uppercase;
    }
    .curator-copy h1 > span:not(.en) { display: block; }
    .curator-copy h1 .en {
      margin-top: 24px;
      font-family: var(--fd-mono);
      font-size: 12px;
      line-height: 1;
      letter-spacing: .08em;
      font-style: normal;
    }
    .curator-thesis {
      max-width: 720px;
      font-family: var(--fd-display);
      font-size: clamp(30px, 4vw, 62px);
      line-height: .96;
      letter-spacing: -.035em;
      text-transform: uppercase;
    }
    .curator-thesis .quiet { color: inherit; }
    .curator-caption {
      max-width: 620px;
      margin-top: 28px;
      padding-top: 0;
      border: 0;
      font-family: var(--fd-mono);
      font-size: 11px;
      line-height: 1.45;
      letter-spacing: .04em;
      text-transform: uppercase;
    }
    .curator-portrait {
      width: 100%;
      height: min(82vh, 920px);
      aspect-ratio: auto;
      background-position: center top;
      filter: grayscale(100%) contrast(115%);
      mix-blend-mode: luminosity;
    }
    .curator-portrait::after { color: var(--fd-cream); }

    .curator-section:not(.curator-origin) {
      min-height: auto;
      padding: 0;
      display: block;
      border: 0;
      background: var(--fd-cream);
    }
    .curator-section-head,
    .curator-section.is-reversed .curator-section-head {
      min-height: min(58vw, 680px);
      padding: 18px 28px 26px;
      position: relative;
      top: auto;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      color: var(--fd-ink);
    }
    #curated-body .curator-section-head { background: var(--fd-pink); }
    #curated-reading .curator-section-head { background: var(--fd-lime); }
    #curated-field .curator-section-head { background: var(--fd-orange); }
    #curated-journey .curator-section-head { background: var(--fd-cyan); }
    #curated-unfinished .curator-section-head { background: var(--fd-purple); }
    .curator-section-head::before {
      content: '未完成的线';
      display: block;
      margin: auto 0 0 -.045em;
      font-family: var(--fd-display);
      font-size: clamp(118px, 22vw, 340px);
      font-weight: 500;
      line-height: .68;
      letter-spacing: -.085em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .curator-section-head .curator-index {
      position: absolute;
      top: 18px;
      left: 28px;
      margin: 0;
      z-index: 2;
      color: var(--fd-ink);
      font-family: var(--fd-mono);
      font-size: 11px;
      letter-spacing: .06em;
    }
    .curator-section-head .curator-index::after { background: var(--fd-ink); }
    .curator-section-head h2 {
      margin: 18px 0 0 -.03em;
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 32px;
      font-family: var(--fd-display);
      font-size: clamp(96px, 16vw, 250px);
      line-height: .7;
      letter-spacing: -.075em;
      text-transform: uppercase;
      white-space: nowrap;
    }
    .curator-section-head h2 span {
      margin: 0 0 .12em;
      max-width: 300px;
      font-family: var(--fd-mono);
      font-size: 11px;
      line-height: 1.05;
      letter-spacing: .04em;
      font-style: normal;
      text-transform: uppercase;
      white-space: normal;
      text-align: right;
    }
    .curator-section-head p {
      position: absolute;
      right: 28px;
      top: 60px;
      width: min(360px, 32vw);
      margin: 0;
      color: var(--fd-ink);
      font-family: var(--fd-mono);
      font-size: 11px;
      line-height: 1.45;
      letter-spacing: .025em;
      text-align: left;
      text-transform: uppercase;
    }

    .curator-works,
    .curator-section.is-reversed .curator-works {
      padding: 82px 28px 128px;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 34px;
      background: var(--fd-cream);
    }
    .curator-card {
      display: block;
      padding: 0 0 26px;
      border: 0;
      border-bottom: 2px solid var(--fd-ink);
      background: transparent;
    }
    .curator-card:last-child { border-bottom: 2px solid var(--fd-ink); }
    .curator-card-cover {
      width: 100%;
      aspect-ratio: 4 / 3;
      margin-bottom: 22px;
      filter: grayscale(0);
      background-color: #ddd3c3;
    }
    .curator-card-kind {
      margin-bottom: 14px;
      color: var(--fd-ink);
      font-family: var(--fd-mono);
      font-size: 10px;
      line-height: 1;
      letter-spacing: .06em;
      text-transform: uppercase;
    }
    .curator-card-title {
      font-family: var(--fd-display);
      font-size: clamp(30px, 3.5vw, 54px);
      line-height: .95;
      letter-spacing: -.045em;
      font-weight: 500;
      text-transform: uppercase;
    }
    .curator-card-desc {
      margin-top: 22px;
      color: var(--fd-ink);
      font-family: 'Noto Serif SC', serif;
      font-size: 14px;
      line-height: 1.8;
      letter-spacing: .02em;
      -webkit-line-clamp: 5;
    }
    .curator-card-arrow { display: none; }
    @media (hover: hover) and (pointer: fine) {
      .curator-card:hover .curator-card-title { font-style: italic; text-decoration: none; }
      .curator-card:hover .curator-card-cover { filter: saturate(1.2) contrast(1.05); }
    }

    /* Creative writing is one landscape, rather than four isolated cards. */
    .creative-world {
      --scene-x: 0px;
      --scene-y: 0px;
      position: relative;
      min-height: min(78vw, 860px);
      overflow: hidden;
      isolation: isolate;
      color: #241d18;
      background:
        linear-gradient(180deg, #ead8b8 0%, #d8ccb0 38%, #75806b 38.2%, #34483d 100%);
      border-top: 2px solid var(--fd-ink);
      border-bottom: 2px solid var(--fd-ink);
    }
    .creative-world::before {
      content: '';
      position: absolute;
      inset: 0;
      z-index: 7;
      pointer-events: none;
      opacity: .34;
      mix-blend-mode: multiply;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 180 180' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.72' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.12'/%3E%3C/svg%3E");
    }
    .creative-world-head {
      position: absolute;
      left: 26px;
      top: 22px;
      z-index: 8;
      display: flex;
      align-items: center;
      gap: 14px;
      font-family: var(--fd-mono);
      font-size: 10px;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .creative-world-head::after { content: ''; width: 64px; height: 1px; background: currentColor; }
    .creative-layer {
      position: absolute;
      inset: 0;
      pointer-events: none;
      transition: transform 700ms cubic-bezier(.16,1,.3,1);
      will-change: transform;
    }
    .creative-layer.far { transform: translate3d(calc(var(--scene-x) * -.18), calc(var(--scene-y) * -.10), 0); }
    .creative-layer.mid { transform: translate3d(calc(var(--scene-x) * -.38), calc(var(--scene-y) * -.20), 0); }
    .creative-layer.near { transform: translate3d(calc(var(--scene-x) * -.62), calc(var(--scene-y) * -.32), 0); }
    .creative-landscape-svg { width: 100%; height: 100%; display: block; }
    .creative-mist {
      position: absolute;
      left: -10%;
      right: -10%;
      top: 34%;
      height: 16%;
      opacity: .46;
      filter: blur(18px);
      background: linear-gradient(90deg, transparent, rgba(244,233,209,.82) 22%, rgba(244,233,209,.52) 64%, transparent);
    }
    .creative-river {
      position: absolute;
      z-index: 2;
      left: 26%;
      bottom: -18%;
      width: 68%;
      height: 66%;
      border-radius: 48% 58% 0 0;
      transform: rotate(-7deg);
      background:
        repeating-linear-gradient(168deg, transparent 0 18px, rgba(239,230,204,.14) 19px 20px),
        linear-gradient(118deg, #263b36 0%, #63776f 36%, #253b38 72%, #172d2a 100%);
      box-shadow: inset 28px 0 50px rgba(231,220,191,.14);
    }
    .creative-road {
      position: absolute;
      z-index: 3;
      left: -7%;
      bottom: 10%;
      width: 54%;
      height: 14%;
      transform: rotate(-11deg) skewX(-18deg);
      border: 1px solid rgba(237,218,182,.44);
      border-left: 0;
      border-right: 0;
      border-radius: 50%;
      opacity: .78;
    }
    .creative-city {
      position: absolute;
      z-index: 3;
      left: 4%;
      top: 30%;
      width: 24%;
      height: 24%;
      opacity: .7;
      background:
        linear-gradient(90deg, transparent 0 5%, #263730 5% 13%, transparent 13% 17%, #35463b 17% 28%, transparent 28% 31%, #22342d 31% 39%, transparent 39% 42%, #3b4c40 42% 55%, transparent 55% 59%, #26372f 59% 73%, transparent 73% 77%, #314238 77% 92%, transparent 92%);
      clip-path: polygon(0 100%,0 52%,8% 52%,8% 25%,20% 25%,20% 48%,30% 48%,30% 8%,40% 8%,40% 58%,49% 58%,49% 35%,63% 35%,63% 0,74% 0,74% 47%,84% 47%,84% 20%,94% 20%,94% 62%,100% 62%,100% 100%);
    }
    .creative-object {
      position: absolute;
      z-index: 10;
      display: grid;
      place-items: center;
      color: inherit;
      text-decoration: none;
      transform: translate3d(0,0,0);
      transition: transform 260ms cubic-bezier(.16,1,.3,1), filter 180ms ease, opacity 180ms ease;
      outline: none;
    }
    .creative-object::after {
      content: attr(data-index) '  ' attr(data-title);
      position: absolute;
      white-space: nowrap;
      padding: 7px 9px 6px;
      border: 1px solid rgba(36,29,24,.62);
      background: rgba(238,224,195,.86);
      backdrop-filter: blur(7px);
      font-family: var(--fd-mono);
      font-size: 9px;
      letter-spacing: .06em;
      text-transform: uppercase;
      box-shadow: 3px 4px 0 rgba(36,29,24,.12);
      transition: transform 220ms cubic-bezier(.16,1,.3,1), background 180ms ease;
    }
    .creative-object.is-active { z-index: 14; filter: saturate(1.12); }
    .creative-object:focus-visible { outline: 2px solid #c52f25; outline-offset: 7px; }
    .creative-object:active { transform: scale(.97); }
    @media (hover: hover) and (pointer: fine) {
      .creative-object:hover { transform: translateY(-8px); }
      .creative-object:hover::after { transform: translateY(-3px); background: #f2dfb8; }
      .creative-world:has(.creative-object:hover) .creative-object:not(:hover) { opacity: .62; }
    }
    .creative-symbol { width: 100%; height: 100%; display: block; overflow: visible; }
    .creative-object.mountain { right: 12%; top: 18%; width: 25%; height: 18%; }
    .creative-object.mountain .mountain-line {
      fill: none;
      stroke: rgba(236,221,188,.78);
      stroke-width: 2;
      vector-effect: non-scaling-stroke;
      transition: stroke 180ms ease, transform 260ms cubic-bezier(.16,1,.3,1);
      transform-origin: center;
    }
    .creative-object.mountain .tram-track {
      stroke: #2c3932;
      stroke-width: 1.4;
      vector-effect: non-scaling-stroke;
    }
    .creative-object.mountain .tram-car {
      fill: #8f302b;
      stroke: #e6d4ad;
      stroke-width: 0;
      vector-effect: non-scaling-stroke;
      transition: transform 260ms cubic-bezier(.16,1,.3,1);
      transform-box: fill-box;
      transform-origin: center;
    }
    @media (hover: hover) and (pointer: fine) {
      .creative-object.mountain:hover .mountain-line:nth-child(2) { transform: translateY(-3px); stroke: rgba(247,232,198,.98); }
      .creative-object.mountain:hover .tram-car { transform: translate(-6px,-4px); }
    }
    .creative-object.mountain::after { right: 4%; bottom: -19px; }
    .creative-object.raft { left: 46%; bottom: 20%; width: 22%; height: 9%; transform: rotate(-5deg); }
    .creative-object.raft::before {
      content: '';
      width: 100%; height: 46%;
      background: repeating-linear-gradient(0deg, #a98650 0 5px, #59422d 5px 7px);
      box-shadow: 0 14px 18px rgba(12,25,22,.34);
      border-radius: 42% 40% 16% 20%;
    }
    .creative-object.raft::after { left: 50%; bottom: -24px; transform: translateX(-50%); }
    .creative-object.road { left: 10%; bottom: 17%; width: 16%; height: 8%; }
    .creative-object.road::before {
      content: '';
      width: 72%; height: 56%;
      border-radius: 24% 30% 16% 18%;
      background: #a83b2f;
      box-shadow: inset 20px 0 rgba(241,213,170,.24), 0 10px 14px rgba(18,26,22,.32);
    }
    .creative-object.road::after { left: 26%; bottom: -17px; }
    .creative-object.city { left: 10%; top: 33%; width: 18%; height: 11%; }
    .creative-object.city .city-block-a { fill: #293b33; }
    .creative-object.city .city-block-b { fill: #6f765f; }
    .creative-object.city .city-bridge {
      fill: none;
      stroke: #9c312b;
      stroke-width: 2;
      vector-effect: non-scaling-stroke;
      transition: stroke-width 180ms ease, transform 240ms cubic-bezier(.16,1,.3,1);
      transform-origin: center;
    }
    .creative-object.city .city-node { fill: #9c312b; }
    @media (hover: hover) and (pointer: fine) {
      .creative-object.city:hover .city-bridge { stroke-width: 3; transform: scaleX(1.04); }
    }
    .creative-object.city::after { left: 50%; bottom: -22px; transform: translateX(-50%); }
    .creative-manuscript {
      position: absolute;
      z-index: 12;
      right: 28px;
      bottom: 26px;
      width: min(340px, 31vw);
      min-height: 190px;
      padding: 18px 20px 17px;
      border: 1px solid rgba(47,38,31,.6);
      color: #2b241e;
      background: rgba(239,225,195,.92);
      box-shadow: 10px 12px 0 rgba(25,34,28,.2), 0 24px 50px rgba(19,29,24,.2);
      transform: rotate(.7deg);
      transition: opacity 160ms ease, transform 240ms cubic-bezier(.16,1,.3,1), filter 180ms ease;
    }
    .creative-manuscript.is-changing { opacity: .42; transform: rotate(.7deg) translateY(4px); filter: blur(1.5px); }
    .creative-manuscript-kicker { font-family: var(--fd-mono); font-size: 9px; letter-spacing: .12em; text-transform: uppercase; }
    .creative-manuscript h3 { margin: 30px 0 11px; font-family: 'Noto Serif SC', serif; font-size: clamp(23px, 2.4vw, 35px); line-height: 1.25; font-weight: 600; }
    .creative-manuscript p { margin: 0; font-family: 'Noto Serif SC', serif; font-size: 12px; line-height: 1.75; }
    .creative-manuscript-link { display: inline-flex; margin-top: 18px; padding-bottom: 2px; border-bottom: 1px solid currentColor; font-family: var(--fd-mono); font-size: 9px; letter-spacing: .1em; text-transform: uppercase; }
    @media (max-width: 900px) {
      .creative-world { min-height: 760px; }
      .creative-manuscript { width: 330px; }
      .creative-object.mountain { right: 8%; }
    }
    @media (max-width: 600px) {
      .creative-world { min-height: 920px; background: linear-gradient(180deg,#ead8b8 0 28%,#536457 28.2%,#263b35 100%); }
      .creative-world-head { left: 14px; top: 16px; }
      .creative-city { top: 20%; width: 45%; }
      .creative-object.city { left: 8%; top: 25%; width: 36%; height: 12%; }
      .creative-object.mountain { right: 5%; top: 22%; width: 42%; height: 14%; }
      .creative-object.road { left: 8%; bottom: 43%; width: 36%; }
      .creative-object.raft { left: 48%; bottom: 43%; width: 42%; }
      .creative-river { left: 18%; bottom: 0; width: 100%; height: 70%; }
      .creative-manuscript { left: 14px; right: 14px; bottom: 24px; width: auto; min-height: 210px; }
      .creative-manuscript h3 { margin-top: 24px; font-size: 27px; }
    }

    .curator-journey,
    .curator-section.is-reversed .curator-journey,
    .curator-contact {
      padding: 72px 28px 120px;
      background: var(--fd-blue);
      color: var(--fd-cream);
    }
    .curator-stop {
      grid-template-columns: 150px 1fr;
      gap: 28px;
      padding: 22px 0 28px;
      border-top: 2px solid var(--fd-cream);
    }
    .curator-stop:last-child { border-bottom: 2px solid var(--fd-cream); }
    .curator-stop-year { color: var(--fd-cream); font-family: var(--fd-mono); }
    .curator-stop-city {
      color: var(--fd-cream);
      font-family: var(--fd-display);
      font-size: clamp(40px, 7vw, 104px);
      line-height: .84;
      text-transform: uppercase;
    }
    .curator-stop-detail { margin-top: 12px; color: var(--fd-cream); font-family: var(--fd-mono); text-transform: uppercase; }
    .curator-contact a,
    .curator-contact button {
      padding: 22px 0;
      border-top: 2px solid var(--fd-cream);
      color: var(--fd-cream);
      font-family: var(--fd-display);
      font-size: clamp(28px, 5vw, 70px);
      line-height: .9;
      letter-spacing: -.04em;
      text-transform: uppercase;
    }
    .curator-contact a:last-child,
    .curator-contact button:last-child { border-bottom: 2px solid var(--fd-cream); }
    .curator-contact strong { color: var(--fd-cream); font-weight: 500; }
    .curator-endmark {
      position: relative;
      left: auto;
      bottom: auto;
      padding: 30px 28px;
      transform: none;
      display: block;
      color: var(--fd-cream);
      background: var(--fd-blue);
      box-shadow: none;
      font-family: var(--fd-mono);
      text-align: right;
      text-transform: uppercase;
    }

    /* Reading pages keep the cream sheet and adopt the chapter typography. */
    body.reader-mode { background: var(--fd-cream); }
    body.reader-mode #view { background: var(--fd-cream); }
    .reader {
      max-width: 1100px;
      padding: 84px 42px 140px;
      border-top: 18px solid var(--fd-blue);
    }
    .reader-variant-creative { border-top-color: var(--fd-pink); }
    .reader-variant-criticism { border-top-color: var(--fd-lime); }
    .reader-variant-news { border-top-color: var(--fd-orange); }
    .reader .headline {
      font-family: var(--fd-display);
      font-size: clamp(58px, 8.5vw, 128px);
      line-height: .88;
      letter-spacing: -.055em;
      text-transform: uppercase;
    }
    .reader-body .para { font-size: 18px; line-height: 1.9; }
    .toc-heading {
      font-family: var(--fd-display);
      font-size: clamp(38px, 5vw, 70px);
      line-height: .95;
      letter-spacing: -.035em;
    }

    @media (max-width: 900px) {
      :root { --fd-rail: 56px; }
      .topbar { width: 56px; padding: 8px 4px; }
      .topbar .brand { font-size: 13px; }
      .topbar nav a { min-height: 45px; padding: 5px 2px; grid-template-columns: 48px 1fr; }
      .nav-code { font-size: 36px; }
      .curator-origin { grid-template-columns: 1fr; align-items: start; }
      .curator-copy h1 { font-size: clamp(76px, 20vw, 150px); }
      .curator-portrait { height: 70vh; }
      .curator-section-head { min-height: 72vw; }
      .curator-section-head::before { font-size: 27vw; }
      .curator-section-head h2 { font-size: 21vw; }
      .curator-section-head p { display: none; }
      .curator-works { grid-template-columns: 1fr; gap: 54px; }
    }
    @media (max-width: 600px) {
      :root { --fd-rail: 0px; }
      #view { margin-left: 0; padding-top: 56px; }
      .topbar {
        inset: 0 0 auto 0;
        width: 100%;
        height: 56px;
        padding: 7px 8px;
        flex-direction: row;
        align-items: center;
        gap: 8px;
        border-right: 0;
        border-bottom: 2px solid var(--fd-cream);
      }
      .topbar::after { display: none; }
      .topbar .brand { width: 68px; flex: 0 0 auto; }
      .topbar nav { flex: 1; flex-direction: row; justify-content: flex-end; gap: 2px; overflow: visible; }
      .topbar nav a { min-height: 38px; width: 38px; padding: 4px; display: block; text-align: center; }
      .nav-code { font-size: 27px; }
      .nav-label { display: none; }
      .curated-page { height: calc(100dvh - 56px); }
      .curator-origin { min-height: calc(100dvh - 56px); padding: 18px 10px 36px; }
      .curator-copy h1 { font-size: 21vw; }
      .curator-thesis { font-size: 10vw; }
      .curator-portrait { height: 58vh; }
      .curator-section-head { min-height: 118vw; padding: 14px 10px 18px; }
      .curator-section-head .curator-index { top: 14px; left: 10px; }
      .curator-section-head::before { font-size: 34vw; white-space: normal; }
      .curator-section-head h2 { display: block; font-size: 31vw; white-space: normal; }
      .curator-section-head h2 span { display: block; margin-top: 18px; text-align: left; }
      .curator-works { padding: 52px 10px 80px; }
      .curator-card-title { font-size: 42px; }
      .curator-card-desc { display: block; }
      .curator-journey,
      .curator-contact { padding: 48px 10px 72px; }
      .curator-stop { grid-template-columns: 76px 1fr; gap: 12px; }
      .reader { padding: 58px 18px 110px; }
      .reader .headline { font-size: 54px; }
    }

    /* Type safety: expressive scale without collisions or canvas overflow. */
    .curator-origin > *,
    .curator-section-head > *,
    .curator-card,
    .curator-card > *,
    .curator-stop > *,
    .reader,
    .reader > * { min-width: 0; max-width: 100%; }
    .curator-copy h1,
    .curator-thesis,
    .curator-section-head h2,
    .curator-section-head p,
    .curator-card-title,
    .curator-card-desc,
    .curator-stop-city,
    .curator-stop-detail,
    .curator-contact strong,
    .reader .headline,
    .toc-heading {
      overflow-wrap: anywhere;
      word-break: normal;
      hyphens: auto;
    }
    .curator-copy h1 {
      font-size: clamp(68px, 9.5vw, 150px);
      line-height: .84;
      letter-spacing: -.055em;
    }
    .curator-copy h1 > span:not(.en) { max-width: 100%; }
    .curator-thesis { line-height: 1.04; }

    /* Keep the portrait photographic: no monochrome, contrast, or blend filter. */
    .curator-portrait {
      filter: none;
      mix-blend-mode: normal;
      background-color: var(--fd-cream);
    }

    /* Chapter metadata now participates in flow instead of sitting on top of type. */
    .curator-section-head,
    .curator-section.is-reversed .curator-section-head {
      min-height: clamp(500px, 58vw, 720px);
    }
    .curator-section-head .curator-index {
      position: static;
      order: 0;
      align-self: flex-start;
      flex: 0 0 auto;
    }
    .curator-section-head p {
      position: static;
      order: 1;
      align-self: flex-end;
      width: min(380px, 36%);
      margin-top: 18px;
      flex: 0 0 auto;
    }
    .curator-section-head::before {
      order: 2;
      width: 100%;
      max-width: 100%;
      margin: auto 0 0;
      font-size: clamp(76px, 15vw, 220px);
      line-height: .82;
      letter-spacing: -.065em;
      white-space: nowrap;
      overflow: hidden;
    }
    .curator-section-head h2 {
      order: 3;
      width: 100%;
      max-width: 100%;
      margin: 26px 0 0;
      flex-wrap: wrap;
      font-size: clamp(72px, 14vw, 200px);
      line-height: .82;
      letter-spacing: -.06em;
      white-space: normal;
    }
    .curator-section-head h2 span {
      flex: 0 1 300px;
      max-width: 100%;
      line-height: 1.15;
    }
    .curator-card-title { line-height: 1.02; }
    .curator-stop-city { line-height: .92; }
    .curator-contact a,
    .curator-contact button { gap: 24px; flex-wrap: wrap; }
    .curator-contact strong { text-align: right; }
    .reader .headline { line-height: .95; }

    @media (max-width: 900px) {
      .curator-copy h1 { font-size: clamp(66px, 15vw, 118px); }
      .curator-section-head,
      .curator-section.is-reversed .curator-section-head { min-height: auto; }
      .curator-section-head p {
        display: block;
        width: min(420px, 58%);
        margin-top: 24px;
      }
      .curator-section-head::before {
        font-size: 14.5vw;
        margin-top: 72px;
      }
      .curator-section-head h2 { font-size: 18vw; }
    }
    @media (max-width: 600px) {
      .curator-copy h1 { font-size: 17vw; line-height: .88; }
      .curator-thesis { font-size: 8.5vw; line-height: 1.06; }
      .curator-section-head,
      .curator-section.is-reversed .curator-section-head { min-height: auto; }
      .curator-section-head p {
        display: block;
        width: 100%;
        margin-top: 22px;
        font-size: 10px;
      }
      .curator-section-head::before {
        margin-top: 58px;
        font-size: 17vw;
        line-height: .86;
        white-space: nowrap;
      }
      .curator-section-head h2 {
        margin-top: 22px;
        font-size: 25vw;
        line-height: .86;
      }
      .curator-section-head h2 span { font-size: 10px; line-height: 1.2; }
      .curator-card-title { font-size: clamp(30px, 10vw, 42px); }
      .curator-contact a,
      .curator-contact button {
        display: block;
        font-size: clamp(25px, 9vw, 40px);
      }
      .curator-contact strong { display: block; margin-top: 10px; text-align: left; }
      .reader .headline { font-size: clamp(40px, 13vw, 54px); }
    }

    /* =============== BEIJING BEIJING · PAPER EDITION =============== */
    .novel-card-cover {
      position: relative;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      justify-content: center;
      padding: 8px;
      color: #f4eddf;
      background: #c92e23;
      filter: none;
    }
    .novel-card-cover span {
      display: block;
      font-family: 'Noto Serif SC', serif;
      font-size: clamp(16px, 2.4vw, 32px);
      font-weight: 700;
      line-height: .88;
      letter-spacing: -.08em;
      white-space: nowrap;
    }
    .novel-card-cover small {
      position: absolute;
      right: 7px;
      bottom: 7px;
      max-width: calc(100% - 14px);
      overflow: hidden;
      font-size: 5px;
      line-height: 1.2;
      letter-spacing: .12em;
      white-space: nowrap;
    }
    body.novel-mode { overflow: hidden; background: #d7d2c8; }
    body.novel-mode .topbar { display: none; }
    body.novel-mode #view { margin-left: 0; }
    .novel-reader {
      --paper: #f6f0e3;
      --paper-deep: #e8dfcf;
      --book-ink: #211d18;
      height: 100dvh;
      min-height: 520px;
      display: grid;
      grid-template-rows: 58px minmax(0, 1fr) 48px;
      overflow: hidden;
      color: var(--book-ink);
      background: #d7d2c8;
    }
    .novel-toolbar {
      display: grid;
      grid-template-columns: minmax(120px, 1fr) minmax(0, 2fr) minmax(120px, 1fr);
      align-items: center;
      gap: 18px;
      padding: 0 24px;
      border-bottom: 1px solid rgba(33, 29, 24, .32);
      background: #ece6da;
      font-size: 10px;
      letter-spacing: .12em;
      text-transform: uppercase;
    }
    .novel-toolbar a,
    .novel-toolbar button { color: inherit; }
    .novel-toolbar a { justify-self: start; }
    .novel-toolbar-title {
      min-width: 0;
      overflow: hidden;
      text-align: center;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-family: 'Noto Serif SC', serif;
      font-size: 14px;
      letter-spacing: .18em;
    }
    .novel-toolbar-actions { justify-self: end; display: flex; align-items: center; gap: 18px; }
    .novel-toolbar button {
      border-bottom: 1px solid transparent;
      padding: 4px 0;
      font-size: 10px;
      letter-spacing: .12em;
      text-transform: uppercase;
      cursor: pointer;
    }
    .novel-toolbar button:hover { border-color: currentColor; }
    .novel-stage {
      min-height: 0;
      display: grid;
      grid-template-columns: 56px minmax(0, 1fr) 56px;
      align-items: center;
      gap: 12px;
      padding: 24px clamp(12px, 3vw, 50px);
      perspective: 2200px;
      overflow: hidden;
    }
    .novel-turn {
      width: 44px;
      height: 44px;
      border: 1px solid rgba(33, 29, 24, .42);
      border-radius: 50%;
      justify-self: center;
      color: var(--book-ink);
      background: transparent;
      font-size: 19px;
      cursor: pointer;
      transition: background 180ms ease, color 180ms ease, opacity 180ms ease;
    }
    .novel-turn:hover { color: #f6f0e3; background: #211d18; }
    .novel-turn:disabled { opacity: .18; pointer-events: none; }
    .novel-book {
      justify-self: center;
      width: min(1120px, 100%);
      height: min(760px, 100%);
      min-height: 0;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      filter: drop-shadow(0 22px 22px rgba(42, 36, 27, .22));
      transform-style: preserve-3d;
    }
    .novel-paper {
      position: relative;
      min-width: 0;
      min-height: 0;
      overflow: hidden;
      background:
        radial-gradient(circle at 18% 20%, rgba(96, 77, 48, .035) 0 1px, transparent 1.5px),
        linear-gradient(105deg, rgba(255,255,255,.28), transparent 34%),
        var(--paper);
      background-size: 8px 8px, auto, auto;
      border: 1px solid rgba(33, 29, 24, .2);
    }
    .novel-paper:first-child { border-radius: 3px 0 0 3px; box-shadow: inset -18px 0 26px -26px rgba(0,0,0,.8); }
    .novel-paper:last-child { border-radius: 0 3px 3px 0; box-shadow: inset 18px 0 26px -26px rgba(0,0,0,.8); }
    .novel-paper-inner {
      height: 100%;
      min-height: 0;
      overflow-y: auto;
      overscroll-behavior: contain;
      scrollbar-width: none;
      padding: clamp(34px, 5.5vh, 62px) clamp(32px, 4.6vw, 70px) 38px;
    }
    .novel-paper-inner::-webkit-scrollbar { display: none; }
    .novel-running-head {
      display: flex;
      justify-content: space-between;
      gap: 20px;
      padding-bottom: 12px;
      border-bottom: 1px solid rgba(33, 29, 24, .28);
      font-size: 8px;
      line-height: 1.3;
      letter-spacing: .15em;
      text-transform: uppercase;
    }
    .novel-page-body {
      padding-top: clamp(28px, 4vh, 46px);
      font-family: 'Noto Serif SC', 'Songti SC', serif;
      font-size: clamp(14px, 1.18vw, 17px);
      font-weight: 400;
      line-height: 1.92;
      letter-spacing: .035em;
      text-align: justify;
      text-justify: inter-ideograph;
    }
    .novel-page-body p {
      max-width: 100%;
      margin: 0 0 .72em;
      overflow-wrap: anywhere;
      word-break: normal;
      text-indent: 2em;
    }
    .novel-folio {
      position: absolute;
      right: 24px;
      bottom: 16px;
      font-family: 'Cormorant Garamond', serif;
      font-size: 11px;
      font-style: italic;
    }
    .novel-paper:first-child .novel-folio { right: auto; left: 24px; }
    .novel-cover-page,
    .novel-end-page {
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      overflow: hidden;
      padding: clamp(30px, 6vh, 70px);
      color: #f3ead9;
      background: #c92e23;
    }
    .novel-cover-page h1 {
      max-width: 100%;
      margin: 0;
      font-family: 'Noto Serif SC', serif;
      font-size: clamp(62px, 8vw, 122px);
      font-weight: 700;
      line-height: .78;
      letter-spacing: -.09em;
      overflow-wrap: normal;
      white-space: normal;
    }
    .novel-cover-page h1 span { display: block; }
    .novel-cover-meta { display: flex; justify-content: space-between; gap: 20px; font-size: 9px; letter-spacing: .18em; }
    .novel-title-page,
    .novel-contents-page,
    .novel-end-page {
      height: 100%;
      overflow-y: auto;
      scrollbar-width: none;
      padding: clamp(40px, 7vh, 78px) clamp(34px, 5vw, 72px);
    }
    .novel-title-page { display: flex; flex-direction: column; justify-content: center; }
    .novel-title-page h2 { margin: 0; font-family: 'Noto Serif SC', serif; font-size: clamp(40px, 5vw, 72px); font-weight: 500; letter-spacing: .08em; }
    .novel-title-page p { margin: 22px 0 0; font-size: 10px; letter-spacing: .2em; text-transform: uppercase; }
    .novel-contents-page h2 { margin: 0 0 26px; font-family: 'Cormorant Garamond', serif; font-size: 34px; font-weight: 500; font-style: italic; }
    .novel-contents-list { margin: 0; padding: 0; list-style: none; border-top: 1px solid rgba(33,29,24,.35); }
    .novel-contents-list button {
      width: 100%;
      display: flex;
      justify-content: space-between;
      gap: 20px;
      padding: 10px 0;
      border-bottom: 1px solid rgba(33,29,24,.22);
      color: inherit;
      font-family: 'Noto Serif SC', serif;
      font-size: 13px;
      text-align: left;
      cursor: pointer;
    }
    .novel-end-page { justify-content: center; text-align: center; color: #f3ead9; background: #211d18; }
    .novel-end-page strong { font-family: 'Noto Serif SC', serif; font-size: clamp(38px, 5vw, 68px); font-weight: 500; }
    .novel-end-page span { margin-top: 22px; font-size: 9px; letter-spacing: .2em; }
    .novel-book.turn-next .novel-paper:last-child { animation: novelTurnNext 440ms cubic-bezier(.55,.05,.35,1) both; transform-origin: left center; }
    .novel-book.turn-prev .novel-paper:first-child { animation: novelTurnPrev 440ms cubic-bezier(.55,.05,.35,1) both; transform-origin: right center; }
    @keyframes novelTurnNext { to { transform: rotateY(-92deg); filter: brightness(.78); } }
    @keyframes novelTurnPrev { to { transform: rotateY(92deg); filter: brightness(.78); } }
    .novel-footer {
      display: grid;
      grid-template-columns: 1fr minmax(160px, 420px) 1fr;
      align-items: center;
      gap: 20px;
      padding: 0 24px;
      border-top: 1px solid rgba(33, 29, 24, .32);
      background: #ece6da;
      font-size: 9px;
      letter-spacing: .1em;
    }
    .novel-footer span:last-child { text-align: right; }
    .novel-range { width: 100%; accent-color: #211d18; cursor: pointer; }
    .novel-toc-dialog {
      width: min(420px, calc(100% - 32px));
      max-height: min(720px, calc(100dvh - 40px));
      overflow-y: auto;
      padding: 28px;
      border: 1px solid #211d18;
      color: #211d18;
      background: #f6f0e3;
      box-shadow: 0 22px 60px rgba(0,0,0,.25);
    }
    .novel-toc-dialog::backdrop { background: rgba(33, 29, 24, .55); backdrop-filter: blur(3px); }
    .novel-toc-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
    .novel-toc-head strong { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-style: italic; font-weight: 500; }
    @media (max-width: 760px) {
      .novel-reader { grid-template-rows: 52px minmax(0, 1fr) 42px; min-height: 440px; }
      .novel-toolbar { grid-template-columns: 80px minmax(0, 1fr) 80px; gap: 8px; padding: 0 12px; }
      .novel-toolbar-actions { gap: 0; }
      .novel-toolbar-actions .novel-page-label { display: none; }
      .novel-stage { grid-template-columns: 34px minmax(0, 1fr) 34px; gap: 5px; padding: 12px 4px; }
      .novel-turn { width: 32px; height: 32px; border: 0; font-size: 18px; }
      .novel-book { width: 100%; height: 100%; grid-template-columns: minmax(0, 1fr); filter: drop-shadow(0 10px 13px rgba(42,36,27,.2)); }
      .novel-paper { display: none; border-radius: 2px !important; box-shadow: none !important; }
      .novel-paper:first-child { display: block; }
      .novel-paper-inner { padding: 30px clamp(24px, 8vw, 42px) 34px; }
      .novel-page-body { padding-top: 25px; font-size: clamp(14px, 4vw, 16px); line-height: 1.86; }
      .novel-cover-page h1 { font-size: clamp(72px, 25vw, 118px); }
      .novel-footer { grid-template-columns: 54px minmax(0, 1fr) 54px; gap: 10px; padding: 0 10px; }
      .novel-footer span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .novel-card-cover span { font-size: 22px; }
    }
    @media (prefers-reduced-motion: reduce) {
      .novel-book.turn-next .novel-paper:last-child,
      .novel-book.turn-prev .novel-paper:first-child { animation: none; }
    }
  </style>
</head>
<body>
  <div class="progress" id="progress"></div>
  <div class="ink-cursor" id="ink-cursor" aria-hidden="true"></div>
  <header class="topbar" id="topbar">
    <a href="#curated-origin" class="brand" id="brand">周未 · ZHOU WEI</a>
    <nav id="nav"></nav>
  </header>

  <main id="view"></main>

  <script>
    const MANIFEST = __MANIFEST_JSON__;
    const WORKS = __WORKS_JSON__;
    const NOVELS = __NOVELS_JSON__;
    const WORLD_PATHS = __WORLD_PATHS__;

    const BYLINE = {
      creative:  { prefix: '', suffix: '' },
      news:      { prefix: '记者　', suffix: '　报道' },
      criticism: { prefix: '', suffix: '　著' },
    };

    const $view = document.getElementById('view');
    const $nav = document.getElementById('nav');
    const $brand = document.getElementById('brand');
    const $progress = document.getElementById('progress');
    const $inkCursor = document.getElementById('ink-cursor');

    let viewCleanups = [];
    function onViewCleanup(fn) { viewCleanups.push(fn); }
    function cleanupView() {
      viewCleanups.splice(0).forEach(fn => fn());
      document.body.classList.remove('works-cursor', 'novel-mode');
    }

    $brand.textContent = (MANIFEST.site.title || '周未') + ' · ' + (MANIFEST.site.name_en || 'ZHOU WEI');

    function buildNav() {
      $nav.innerHTML = `
        <a href="#curated-origin" data-route="origin" aria-label="起点"><span class="nav-code">00</span><span class="nav-label">起点</span></a>
        <a href="#curated-body" data-route="body" aria-label="身体"><span class="nav-code">01</span><span class="nav-label">身体</span></a>
        <a href="#curated-reading" data-route="reading" aria-label="阅读"><span class="nav-code">02</span><span class="nav-label">阅读</span></a>
        <a href="#curated-field" data-route="field" aria-label="现场"><span class="nav-code">03</span><span class="nav-label">现场</span></a>
        <a href="#curated-journey" data-route="journey" aria-label="行路"><span class="nav-code">04</span><span class="nav-label">行路</span></a>
      `;
      $nav.querySelectorAll('a[data-route]').forEach(link => {
        link.addEventListener('click', e => {
          const page = document.querySelector('.curated-page');
          if (!page) return;
          e.preventDefault();
          const id = link.dataset.route;
          history.pushState(null, '', '#curated-' + id);
          scrollCuratedTo(id);
        });
      });
    }
    buildNav();

    // ---- theme toggle ----
    document.documentElement.dataset.theme = 'light';
    localStorage.removeItem('zw-theme');
    function toggleTheme() {
      const cur = document.documentElement.dataset.theme;
      const next = cur === 'dark' ? 'light' : 'dark';
      const apply = () => {
        document.documentElement.dataset.theme = next;
        localStorage.setItem('zw-theme', next);
      };
      if (!document.startViewTransition || REDUCED_MOTION) {
        apply();
        return;
      }
      const toggle = document.getElementById('theme-toggle');
      const rect = toggle.getBoundingClientRect();
      const x = rect.left + rect.width / 2;
      const y = rect.top + rect.height / 2;
      const radius = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
      const transition = document.startViewTransition(apply);
      transition.ready.then(() => {
        document.documentElement.animate(
          { clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${radius}px at ${x}px ${y}px)`] },
          { duration: 620, easing: 'cubic-bezier(.16,1,.3,1)', pseudoElement: '::view-transition-new(root)' }
        );
      });
    }

    function setActiveNav(route) {
      document.querySelectorAll('#nav a').forEach(a => {
        a.classList.toggle('active', a.dataset.route === route);
      });
    }

    function renderRoute() {
      cleanupView();
      const h = location.hash || '#curated-origin';
      const curatedMatch = h.match(/^#curated-(origin|body|reading|field|journey|unfinished)$/);
      const m = h.match(/^#\/read\/([^/]+)(?:\/chapter\/(\d+))?$/);
      document.body.classList.toggle('reader-mode', !!m);
      if (m) {
        window.scrollTo(0, 0);
        showRead(decodeURIComponent(m[1]), m[2] ? Number(m[2]) : null);
        mountStaggers($view);
        return;
      }
      if (curatedMatch || h === '#/' || h === '#') {
        showCurated(curatedMatch ? curatedMatch[1] : 'origin');
        mountStaggers($view);
        return;
      }
      if (!h.startsWith('#/')) {
        showCurated('origin');
        mountStaggers($view);
        return;
      }
      const tail = h.slice(2);
      // Keep the previously published Media URL working after the curated
      // homepage redesign. It remains a standalone gallery until real post
      // covers and metrics are supplied in the manifest.
      if (tail === 'media') {
        showMedia();
        mountStaggers($view);
        return;
      }
      const legacySection = {
        experience: 'journey',
        works: 'body',
        creative: 'body',
        criticism: 'reading',
        news: 'field',
        contact: 'unfinished'
      }[tail] || 'origin';
      showCurated(legacySection);
      mountStaggers($view);
    }

    let routeTimer = null;
    function route() {
      clearTimeout(routeTimer);
      const curatorTarget = (location.hash || '').match(/^#curated-(origin|body|reading|field|journey|unfinished)$/);
      if (curatorTarget && document.querySelector('.curated-page') && !document.body.classList.contains('reader-mode')) {
        scrollCuratedTo(curatorTarget[1]);
        return;
      }
      if (!$view.firstElementChild || REDUCED_MOTION) {
        renderRoute();
        return;
      }
      $view.classList.remove('view-entering');
      $view.classList.add('view-leaving');
      routeTimer = setTimeout(() => {
        $view.classList.remove('view-leaving');
        $view.classList.add('view-entering');
        renderRoute();
        requestAnimationFrame(() => requestAnimationFrame(() => {
          $view.classList.remove('view-entering');
        }));
      }, 180);
    }

    function mountStaggers(root) {
      const containers = root.querySelectorAll('.fade-stagger');
      containers.forEach(c => {
        [...c.children].forEach((el, i) => el.style.setProperty('--i', i));
      });
      // Double rAF ensures the browser commits the opacity-0 state before
      // we flip to mounted, so the transition actually plays.
      requestAnimationFrame(() => requestAnimationFrame(() => {
        containers.forEach(c => c.classList.add('mounted'));
      }));
    }

    window.addEventListener('hashchange', route);
    window.addEventListener('popstate', route);
    // NOTE: initial route() is invoked at the very end of this script,
    // after all view functions and their constants are initialized.

    // ---- CURATED HOME: one continuous line through every kind of work ----
    function scrollCuratedTo(id, behavior) {
      const page = document.querySelector('.curated-page');
      const target = document.getElementById('curated-' + id);
      if (!page || !target) return;
      setActiveNav(id === 'unfinished' ? 'journey' : id);
      page.scrollTo({
        top: Math.max(0, target.offsetTop - 8),
        behavior: behavior || (REDUCED_MOTION ? 'auto' : 'smooth')
      });
    }

    function showCurated(initialSection) {
      setActiveNav(initialSection === 'unfinished' ? 'journey' : initialSection);
      updateMeta({
        title: '一条未完成的线 · ' + (MANIFEST.site.title || '周未'),
        desc: '周未在个人经验、历史记忆与现实结构之间写作。'
      });
      const s = MANIFEST.site || {};

      const chapterInfo = {
        creative: { index: '01', label: '身体', en: 'Body / Sensation' },
        criticism: { index: '02', label: '阅读', en: 'Reading / History' },
        news: { index: '03', label: '现场', en: 'Field / Structure' }
      };

      function workCards(category) {
        const info = chapterInfo[category];
        return (MANIFEST.works || []).filter(w => w.category === category).map(w => {
          const cover = w.cover ? `style="background-image:url('${w.cover}')"` : '';
          const novelCover = w.format === 'novel' ? `
            <div class="curator-card-cover novel-card-cover" aria-hidden="true">
              <span>北京</span><span>北京</span><small>A NOVEL · TEN CHAPTERS</small>
            </div>` : `<div class="curator-card-cover" ${cover}></div>`;
          return `
            <a class="curator-card${w.format === 'novel' ? ' is-novel' : ''}" href="#/read/${encodeURIComponent(w.id)}">
              ${novelCover}
              <div>
                <div class="curator-card-kind">${info.en}</div>
                <div class="curator-card-title">${escapeHtml(w.title)}</div>
                ${w.subtitle ? `<div class="curator-card-desc">${escapeHtml(w.subtitle)}</div>` : ''}
              </div>
              <span class="curator-card-arrow">↗</span>
            </a>`;
        }).join('');
      }

      function creativeWorld() {
        const works = (MANIFEST.works || []).filter(w => w.category === 'creative');
        const slots = {
          'beijing-beijing': ['city', '01'],
          'victoria-peak': ['mountain', '02'],
          'drifting-water': ['raft', '03'],
          'carsick-cars': ['road', '04']
        };
        const objects = works.map((w, i) => {
          const [kind, index] = slots[w.id] || ['road', String(i + 1).padStart(2, '0')];
          const symbol = kind === 'city' ? `
            <svg class="creative-symbol" viewBox="0 0 260 100" aria-hidden="true">
              <g class="city-block-a"><rect x="18" y="26" width="27" height="58" rx="3"/><rect x="51" y="8" width="38" height="76" rx="3"/><rect x="95" y="38" width="23" height="46" rx="3"/></g>
              <g class="city-block-b"><rect x="142" y="34" width="25" height="50" rx="3"/><rect x="173" y="15" width="39" height="69" rx="3"/><rect x="218" y="45" width="24" height="39" rx="3"/></g>
              <path class="city-bridge" d="M46 54 C87 17 122 17 157 51 C185 78 207 72 229 49"/>
              <circle class="city-node" cx="46" cy="54" r="6"/><circle class="city-node" cx="229" cy="49" r="6"/>
            </svg>` : kind === 'mountain' ? `
            <svg class="creative-symbol" viewBox="0 0 320 130" aria-hidden="true">
              <path class="mountain-line" d="M14 106 C65 101 98 91 131 60 C151 41 166 22 183 25 C204 29 216 65 241 79 C261 91 282 96 308 97"/>
              <path class="mountain-line" d="M19 118 C76 113 111 100 143 72 C163 54 174 40 188 42 C207 45 220 76 244 89 C265 101 286 105 309 106" opacity=".48"/>
              <path class="tram-track" d="M91 99 L230 65"/>
              <g class="tram-car" transform="translate(164 81) rotate(-14)"><rect x="-22" y="-9" width="44" height="18" rx="9"/></g>
            </svg>` : '';
          return `<a class="creative-object ${kind}${i === 0 ? ' is-active' : ''}"
            href="#/read/${encodeURIComponent(w.id)}"
            data-id="${escapeHtml(w.id)}"
            data-index="${index}"
            data-title="${escapeHtml(w.title)}"
            data-subtitle="${escapeHtml(w.subtitle || '')}">${symbol}</a>`;
        }).join('');
        const first = works[0] || {};
        return `<div class="creative-world" id="creative-world">
          <div class="creative-world-head">Writing atlas · 创意写作地景</div>
          <div class="creative-layer far" aria-hidden="true">
            <svg class="creative-landscape-svg" viewBox="0 0 1200 760" preserveAspectRatio="none">
              <path d="M0 270 C125 210 210 250 315 180 C420 106 510 232 620 150 C755 48 845 184 950 112 C1045 49 1110 101 1200 65 L1200 420 L0 420Z" fill="#7d846f"/>
              <path d="M0 315 C150 250 280 324 410 225 C560 111 682 302 825 187 C954 83 1062 190 1200 130 L1200 440 L0 440Z" fill="#566755"/>
            </svg>
          </div>
          <div class="creative-mist" aria-hidden="true"></div>
          <div class="creative-layer mid" aria-hidden="true">
            <div class="creative-city"></div><div class="creative-river"></div><div class="creative-road"></div>
          </div>
          <div class="creative-layer near" aria-hidden="true"></div>
          ${objects}
          <aside class="creative-manuscript" id="creative-manuscript" aria-live="polite">
            <div class="creative-manuscript-kicker">Selected fiction · ${works.length} pieces</div>
            <h3 id="creative-manuscript-title">${escapeHtml(first.title || '创意写作')}</h3>
            <p id="creative-manuscript-desc">${escapeHtml(first.subtitle || '沿着地景进入作品。')}</p>
            ${first.id ? `<a class="creative-manuscript-link" id="creative-manuscript-link" href="#/read/${encodeURIComponent(first.id)}">enter this story ↗</a>` : ''}
          </aside>
        </div>`;
      }

      const journeyHTML = (s.journey || []).map(j => `
        <div class="curator-stop">
          <div class="curator-stop-year">${escapeHtml(j.year || '')}</div>
          <div>
            <div class="curator-stop-city">${escapeHtml(j.city || '')} · ${escapeHtml(j.cityEn || '')}</div>
            <div class="curator-stop-detail">${escapeHtml(j.org || '')}<br>${escapeHtml(j.role || '')}</div>
          </div>
        </div>`).join('');

      const contactHTML = Object.entries(s.contact || {}).map(([key, value]) => {
        if (key.toLowerCase() === 'email') {
          return `<a href="mailto:${escapeHtml(value)}"><span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong></a>`;
        }
        return `<button type="button" data-curator-copy="${escapeHtml(value)}"><span>${escapeHtml(key)}</span><strong>${escapeHtml(value)}</strong></button>`;
      }).join('');

      const portraitStyle = s.photo ? `style="background-image:url('${s.photo}')"` : '';
      $view.innerHTML = `
        <div class="curated-page" id="curated-page">
          <div class="curated-stage">
            <div class="curator-spine" aria-hidden="true"></div>

            <section class="curator-section curator-origin fade-stagger" id="curated-origin" data-curator-section="origin">
              <div class="curator-copy">
                <div class="curator-index">Origin / 起点</div>
                <h1><span>一条</span><span>未完成的线</span><span class="en">An Unfinished Line · Zhou Wei</span></h1>
                <p class="curator-thesis">一个人如何穿过城市、记忆、文学与商业结构，<span class="quiet">并用写作留下痕迹？</span></p>
                <p class="curator-caption">周未是写作者与批评者。他的写作从身体经验出发，经过文学与历史，抵达正在发生的现实结构。</p>
              </div>
              <div class="curator-portrait" ${portraitStyle} aria-label="${escapeHtml(s.title || '周未')}的照片"></div>
            </section>

            <section class="curator-section" id="curated-body" data-curator-section="body">
              <div class="curator-section-head fade-stagger">
                <div class="curator-index">Body / 身体</div>
                <h2>身体<span>感受先于解释</span></h2>
                <p>晕眩、水流、山顶与炎热构成写作最早的坐标。个人经验并非封闭的私人世界，而是时代进入身体时留下的触感。</p>
              </div>
              ${creativeWorld()}
            </section>

            <section class="curator-section is-reversed" id="curated-reading" data-curator-section="reading">
              <div class="curator-section-head fade-stagger">
                <div class="curator-index">Reading / 阅读</div>
                <h2>阅读<span>进入历史的裂缝</span></h2>
                <p>文本并不只是解释历史。它保存被征服者、次要语言与感官主体没有说完的部分，并让另一种现代性浮现出来。</p>
              </div>
              <div class="curator-works fade-stagger">${workCards('criticism')}</div>
            </section>

            <section class="curator-section" id="curated-field" data-curator-section="field">
              <div class="curator-section-head fade-stagger">
                <div class="curator-index">Field / 现场</div>
                <h2>现场<span>结构正在发生</span></h2>
                <p>当历史不再只存在于文学中，它表现为企业、资本、制度和人的选择。新闻写作是对现实结构的另一种细读。</p>
              </div>
              <div class="curator-works fade-stagger">${workCards('news')}</div>
            </section>

            <section class="curator-section is-reversed" id="curated-journey" data-curator-section="journey">
              <div class="curator-section-head fade-stagger">
                <div class="curator-index">Journey / 行路</div>
                <h2>行路<span>写作发生过的地方</span></h2>
                <p>杭州、香港、上海、北京不是履历上的背景，而是观察方式不断改变的坐标。每一次移动，都让这条线获得新的方向。</p>
              </div>
              <div class="curator-journey fade-stagger">${journeyHTML}</div>
            </section>

            <section class="curator-section curator-unfinished" id="curated-unfinished" data-curator-section="unfinished">
              <div class="curator-section-head fade-stagger">
                <div class="curator-index">Unfinished / 未完</div>
                <h2>未完<span>The line continues</span></h2>
                <p>这条线还没有抵达终点。下一段将在北京继续：从写作走向文艺学，也从个人经验继续走向更辽阔的历史与现实。</p>
              </div>
              <div class="curator-contact fade-stagger">${contactHTML}</div>
            </section>

            <div class="curator-endmark">to be continued · 未完</div>
          </div>
        </div>`;

      const page = document.getElementById('curated-page');
      const creativeScene = document.getElementById('creative-world');
      if (creativeScene) {
        const creativeWorks = (MANIFEST.works || []).filter(w => w.category === 'creative');
        const manuscript = document.getElementById('creative-manuscript');
        const manuscriptTitle = document.getElementById('creative-manuscript-title');
        const manuscriptDesc = document.getElementById('creative-manuscript-desc');
        const manuscriptLink = document.getElementById('creative-manuscript-link');
        let previewTimer = null;
        let sceneRAF = null;
        const activateObject = (object) => {
          const work = creativeWorks.find(w => w.id === object.dataset.id);
          if (!work) return;
          creativeScene.querySelectorAll('.creative-object').forEach(el => el.classList.toggle('is-active', el === object));
          manuscript.classList.add('is-changing');
          clearTimeout(previewTimer);
          previewTimer = setTimeout(() => {
            manuscriptTitle.textContent = work.title;
            manuscriptDesc.textContent = work.subtitle || '进入作品';
            if (manuscriptLink) manuscriptLink.href = '#/read/' + encodeURIComponent(work.id);
            manuscript.classList.remove('is-changing');
          }, 120);
        };
        creativeScene.querySelectorAll('.creative-object').forEach(object => {
          object.addEventListener('pointerenter', () => activateObject(object));
          object.addEventListener('focus', () => activateObject(object));
        });
        const moveScene = (event) => {
          if (REDUCED_MOTION || matchMedia('(pointer: coarse)').matches) return;
          const rect = creativeScene.getBoundingClientRect();
          const x = Math.max(-1, Math.min(1, (event.clientX - rect.left) / rect.width * 2 - 1));
          const y = Math.max(-1, Math.min(1, (event.clientY - rect.top) / rect.height * 2 - 1));
          if (sceneRAF) cancelAnimationFrame(sceneRAF);
          sceneRAF = requestAnimationFrame(() => {
            creativeScene.style.setProperty('--scene-x', (x * 14).toFixed(2) + 'px');
            creativeScene.style.setProperty('--scene-y', (y * 10).toFixed(2) + 'px');
          });
        };
        creativeScene.addEventListener('pointermove', moveScene, { passive: true });
        creativeScene.addEventListener('pointerleave', () => {
          creativeScene.style.setProperty('--scene-x', '0px');
          creativeScene.style.setProperty('--scene-y', '0px');
        });
        onViewCleanup(() => {
          clearTimeout(previewTimer);
          if (sceneRAF) cancelAnimationFrame(sceneRAF);
        });
      }
      const sections = [...page.querySelectorAll('[data-curator-section]')];
      let scrollRAF = null;
      const syncCurator = () => {
        scrollRAF = null;
        const max = Math.max(1, page.scrollHeight - page.clientHeight);
        const progress = Math.max(0, Math.min(1, page.scrollTop / max));
        page.style.setProperty('--spine-progress', progress.toFixed(4));
        $progress.style.width = (progress * 100) + '%';
        const marker = page.scrollTop + page.clientHeight * .42;
        let active = 'origin';
        sections.forEach(section => {
          if (section.offsetTop <= marker) active = section.dataset.curatorSection;
        });
        setActiveNav(active === 'unfinished' ? 'journey' : active);
      };
      const onCuratorScroll = () => {
        if (!scrollRAF) scrollRAF = requestAnimationFrame(syncCurator);
      };
      page.addEventListener('scroll', onCuratorScroll, { passive: true });
      page.querySelectorAll('[data-curator-copy]').forEach(button => {
        button.addEventListener('click', async () => {
          await navigator.clipboard.writeText(button.dataset.curatorCopy);
          const label = button.querySelector('span');
          const original = label.textContent;
          label.textContent = 'copied';
          setTimeout(() => { label.textContent = original; }, 1400);
        });
      });
      onViewCleanup(() => {
        page.removeEventListener('scroll', onCuratorScroll);
        if (scrollRAF) cancelAnimationFrame(scrollRAF);
      });
      requestAnimationFrame(() => {
        if (initialSection && initialSection !== 'origin') scrollCuratedTo(initialSection, 'auto');
        syncCurator();
      });
    }

    // ---- BIO (single-screen page) ----
    function showBio() {
      setActiveNav('bio');
      updateMeta({});
      const s = MANIFEST.site || {};
      // Latin-only paragraphs render as italic translations, visually subordinate
      // to the Chinese paragraph they follow.
      const isLatin = (t) => !/[一-鿿]/.test(t);
      const bioParas = (s.bio || []).map(p =>
        `<p class="bio-para${isLatin(p) ? ' latin' : ''}">${escapeHtml(p)}</p>`
      ).join('');
      const photoStyle = s.photo ? `style="background-image:url('${escapeHtml(s.photo)}')"` : '';
      const photoClass = s.photo ? '' : 'placeholder';
      $view.innerHTML = `
        <div class="page bio-fit">
          <div class="bio-hero fade-stagger">
            <div class="bio-portrait ${photoClass}" ${photoStyle}></div>
            <div class="bio-content fade-stagger">
              <h1>${escapeHtml(s.title || '周未')}<span class="en">${escapeHtml(s.name_en || 'ZHOU WEI')}</span></h1>
              ${s.tagline ? `<p class="bio-tagline">${escapeHtml(s.tagline)}</p>` : ''}
              <div class="bio-rule"></div>
              ${bioParas}
            </div>
          </div>
        </div>
      `;
    }

    // ---- EXPERIENCE (minimal China map + frosted journey panel) ----
    const CITY_XY = {
      'Beijing':   [116.4, 39.9],
      'Shanghai':  [121.47, 31.23],
      'Hangzhou':  [120.15, 30.28],
      'Hong Kong': [114.17, 22.32],
    };
    // Equirectangular projection, cos(35°)-corrected; must mirror build.py's proj_cn().
    function projCN(lon, lat) {
      const K = 15.24;
      return [(lon - 68) * 0.82 * K, (58 - lat) * K];
    }

    function showExperience() {
      setActiveNav('experience');
      updateMeta({ title: 'Experience · ' + (MANIFEST.site.title || '周未') });
      const journey = MANIFEST.site.journey || [];

      const TYPE_LABEL = { work: 'Work', education: 'Education', event: 'Event' };
      function cardHTML(j, i) {
        return `
        <div class="j-card" data-i="${i}" data-city="${escapeHtml(j.cityEn)}">
          <div class="j-top">
            <span class="j-year">${escapeHtml(j.year)}</span>
            <span class="j-city">${escapeHtml(j.city)} · ${escapeHtml(j.cityEn)}</span>
          </div>
          <div class="j-org">${escapeHtml(j.org)}</div>
          <div class="j-role">${escapeHtml(j.role)}</div>
          ${(j.highlights && j.highlights.length) ? `<ul class="j-hl">${j.highlights.map(h => `<li>${escapeHtml(h)}</li>`).join('')}</ul>` : ''}
        </div>`;
      }
      function groupHTML(title, sub, items, baseIdx) {
        if (!items.length) return '';
        return `
        <div class="j-group">
          <div class="j-group-head">
            <span class="j-group-title">${escapeHtml(title)}</span>
            <span class="j-group-sub">${escapeHtml(sub)}</span>
          </div>
          ${items.map((j, k) => cardHTML(j, baseIdx + k)).join('')}
        </div>`;
      }

      const edu = journey.filter(j => j.type === 'education');
      const work = journey.filter(j => j.type === 'work' || j.type === 'event');
      const cardsHTML =
        groupHTML('教育经历', 'Education', edu, 0) +
        groupHTML('工作与项目', 'Work & Projects', work, edu.length);

      // One pin per distinct city.
      const cities = [...new Set(journey.map(j => j.cityEn))];
      const pinsHTML = cities.map(cityEn => {
        const [lon, lat] = CITY_XY[cityEn] || [104, 35];
        const [x, y] = projCN(lon, lat);
        return `
          <g class="pin" data-city="${escapeHtml(cityEn)}" transform="translate(${x.toFixed(1)},${y.toFixed(1)})">
            <circle class="pin-hit" r="26" fill="transparent"/>
            <circle class="pin-ring" r="14"/>
            <circle class="pin-dot" r="4.5"/>
            <text class="pin-label" x="12" y="4">${escapeHtml(cityEn)}</text>
          </g>`;
      }).join('');

      const countriesHTML = WORLD_PATHS.map(d => `<path class="country" d="${d}"/>`).join('');

      $view.innerHTML = `
        <div class="page exp-page">
          <div class="map-wrap" aria-hidden="true">
            <svg viewBox="0 0 1000 762" preserveAspectRatio="xMidYMid meet">
              <g class="countries">${countriesHTML}</g>
              ${pinsHTML}
            </svg>
          </div>
          <aside class="journey-panel fade-stagger">${cardsHTML}</aside>
        </div>
      `;

      const cards = [...document.querySelectorAll('.j-card')];
      const pins = [...document.querySelectorAll('.pin')];

      function activateCity(cityEn, sourceCardIdx) {
        pins.forEach(p => p.classList.toggle('active', p.dataset.city === cityEn));
        cards.forEach((c, i) => {
          const on = sourceCardIdx != null ? i === sourceCardIdx : c.dataset.city === cityEn;
          c.classList.toggle('active', on);
        });
      }

      cards.forEach((card, i) => {
        card.addEventListener('mouseenter', () => activateCity(card.dataset.city, i));
        card.addEventListener('click', () => activateCity(card.dataset.city, i));
      });
      pins.forEach(pin => {
        pin.addEventListener('click', () => {
          const cityEn = pin.dataset.city;
          activateCity(cityEn, null);
          const first = cards.find(c => c.dataset.city === cityEn);
          first?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        });
        pin.style.cursor = 'pointer';
      });

      // Default: newest entry active.
      if (cards.length) activateCity(cards[0].dataset.city, 0);
    }

    // ---- WORKS (strata page) ----
    function showWorks(openCat) {
      setActiveNav('works');
      document.body.classList.add('works-cursor');
      updateMeta({ title: 'Works · ' + (MANIFEST.site.title || '周未') });

      const cats = (MANIFEST.categories || []).filter(c => MANIFEST.works.some(w => w.category === c.id));
      // Label positions come from CSS classes (pos-0/1/2) so media queries can
      // pull them inward on narrow screens.
      const strataHTML = cats.map((c, ci) => {
        const items = MANIFEST.works.filter(w => w.category === c.id);
        const cards = items.map((w, i) => {
          const hasCover = !!w.cover;
          const style = hasCover
            ? `style="--i:${i};background-image:url('${w.cover}')"`
            : `style="--i:${i};background: linear-gradient(135deg, ${w.color || '#2a2a2a'}, ${shadeColor(w.color || '#2a2a2a', -30)})"`;
          return `
            <a class="soil-card" href="#/read/${encodeURIComponent(w.id)}" style="--i:${i}">
              <div class="soil-cover${hasCover ? '' : ' no-image'}" ${style} ${hasCover ? '' : `data-placeholder="${escapeHtml(w.title)}"`}></div>
              <div class="soil-title">${escapeHtml(w.title)}</div>
            </a>`;
        }).join('');
        return `
        <section class="stratum" id="stratum-${c.id}" data-cat="${c.id}">
          <div class="stratum-works"><div class="inner">
            <div class="works-row">${cards}</div>
          </div></div>
          <button class="stratum-line" aria-expanded="false" aria-label="${escapeHtml(c.label)}">
            <svg viewBox="0 0 1000 44" preserveAspectRatio="none">
              <path class="ink s0" d="" />
              <path class="ink s1" d="" />
              <path class="ink s2" d="" />
              <path class="ink s3" d="" />
            </svg>
            <span class="stratum-label pos-${ci % 3}">
              ${Array.from(c.label).map(ch => `<span class="lch">${escapeHtml(ch)}</span>`).join('')}<span class="count">${items.length}</span>
            </span>
          </button>
        </section>`;
      }).join('');

      $view.innerHTML = `
        <div class="page works-page">
          <div class="works-inner fade-stagger">
            <p class="strata-hint">点击墨线，翻开每一层</p>
            <div class="strata">${strataHTML}</div>
          </div>
        </div>
      `;

      initInkLife();
      document.fonts.ready.then(() => {
        if (document.querySelector('.stratum')) initInkLife();
      });
      initPaperTilt();
      onViewCleanup(() => {
        if (inkRAF) cancelAnimationFrame(inkRAF);
        inkRAF = null;
        inkStrata = [];
      });

      document.querySelectorAll('.stratum-line').forEach(btn => {
        btn.addEventListener('click', (e) => {
          const st = btn.closest('.stratum');
          const catId = st.dataset.cat;
          const willOpen = !st.classList.contains('open');
          openStratum(willOpen ? catId : null);
          inkPulse(st, e.clientX);
          history.replaceState(null, '', willOpen ? '#/' + catId : '#/works');
        });
      });

      if (openCat) openStratum(openCat);
    }

    // ---- MEDIA (social gallery) ----
    function showMedia() {
      setActiveNav('media');
      updateMeta({ title: 'Media · ' + (MANIFEST.site.title || '周未') });
      const media = MANIFEST.media || { accounts: [], posts: [] };

      const PLATFORM_LABEL = { wechat: 'WeChat', xiaohongshu: '小红书' };
      const PLATFORM_ICON = {
        wechat: '<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M8.5 2C4.9 2 2 4.5 2 7.6c0 1.8.9 3.4 2.3 4.5-.1.6-.4 1.7-.4 1.7s-.1.3.2.3c.4 0 1.5-.9 2-1.5.8.3 1.7.5 2.6.5 3.6 0 6.5-2.5 6.5-5.6S12.1 2 8.5 2zm6.8 6.6c-3.1 0-5.6 2.2-5.6 5 0 2.7 2.5 5 5.6 5 .8 0 1.5-.1 2.2-.4.4.5 1.3 1.3 1.7 1.3.2 0 .3-.2.3-.2s-.3-1-.4-1.5c1.2-1 2-2.4 2-4.1 0-2.8-2.5-5.1-5.8-5.1z"/></svg>',
        xiaohongshu: '<svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.2 14.3h-1.9l-.6 1.8h-1.5l.6-1.8H9.8l-.6 1.8H7.7l.6-1.8H7v-1.4h1.8l.9-2.6H8.4V11h2l.6-1.8h1.5l-.6 1.8h2.9l.6-1.8h1.5l-.6 1.8h1.4v1.4h-1.7l-.9 2.6h1.7v1.5zm-3-1.4h-2.9l.9-2.6h2.9l-.9 2.6z"/></svg>'
      };

      const accountsHTML = media.accounts.map(a => `
        <div class="m-account platform-${a.platform} fade-stagger">
          <div class="platform-icon">${PLATFORM_ICON[a.platform] || '◆'}</div>
          <div class="platform-info">
            <div class="name">${escapeHtml(a.name || '')}</div>
            <div class="handle">${escapeHtml(a.handle || '')}</div>
            <p class="bio">${escapeHtml(a.bio || '')}</p>
            ${a.followers ? `<div class="followers"><strong>${escapeHtml(a.followers)}</strong> followers</div>` : ''}
          </div>
        </div>
      `).join('');

      const postsHTML = (media.posts || []).map((p, i) => {
        const hasCover = !!p.cover;
        const style = hasCover
          ? `style="background-image:url('${p.cover}')"`
          : `style="background: linear-gradient(135deg, ${p.color || '#7d6b56'}, ${shadeColor(p.color || '#7d6b56', -30)})"`;
        const placeholder = hasCover ? '' : `data-placeholder="${escapeHtml(PLATFORM_LABEL[p.platform] || 'Media')}"`;
        const metrics = p.metrics || {};
        const metricSpans = [];
        if (metrics.read) metricSpans.push(`<span class="reads">${escapeHtml(metrics.read)}</span>`);
        if (metrics.like) metricSpans.push(`<span class="likes">${escapeHtml(metrics.like)}</span>`);
        if (metrics.collect) metricSpans.push(`<span class="collects">${escapeHtml(metrics.collect)}</span>`);
        if (metrics.comment) metricSpans.push(`<span class="comments">${escapeHtml(metrics.comment)}</span>`);
        return `
        <article class="m-card fade-stagger" data-i="${i}">
          <div class="cover ${hasCover ? '' : 'no-image'}" ${style} ${placeholder}>
            <span class="badge ${p.platform}">${PLATFORM_LABEL[p.platform] || p.platform}</span>
          </div>
          <div class="info">
            <h3 class="title">${escapeHtml(p.title || '')}</h3>
            ${p.subtitle ? `<p class="subtitle">${escapeHtml(p.subtitle)}</p>` : ''}
            <div class="meta">
              <span>${escapeHtml(p.date || '')}</span>
              <div class="metrics">${metricSpans.join('')}</div>
            </div>
          </div>
        </article>`;
      }).join('');

      $view.innerHTML = `
        <div class="page media-fit">
          <div class="media-page fade-stagger">
            <h1>新媒体 · New Media</h1>
            <p class="media-sub">微信公众号 & 小红书运营</p>
            <div class="media-accounts fade-stagger">${accountsHTML || ''}</div>
            <div class="media-gallery fade-stagger">${postsHTML || '<p style="color:var(--muted)">暂无内容</p>'}</div>
          </div>
        </div>
        <div class="m-lightbox" id="m-lightbox" aria-hidden="true">
          <button class="lb-close" aria-label="关闭">×</button>
          <div class="lb-inner">
            <div class="lb-cover" id="lb-cover"></div>
            <div class="lb-info">
              <span class="badge" id="lb-badge"></span>
              <h2 class="lb-title" id="lb-title"></h2>
              <p class="lb-subtitle" id="lb-subtitle"></p>
              <div class="lb-actions">
                <div class="lb-metrics" id="lb-metrics"></div>
                <a class="lb-link" id="lb-link" href="#" target="_blank" rel="noopener">查看原文 →</a>
              </div>
            </div>
          </div>
        </div>
      `;

      const cards = [...document.querySelectorAll('.m-card')];
      const lightbox = document.getElementById('m-lightbox');
      const lbCover = document.getElementById('lb-cover');
      const lbBadge = document.getElementById('lb-badge');
      const lbTitle = document.getElementById('lb-title');
      const lbSubtitle = document.getElementById('lb-subtitle');
      const lbMetrics = document.getElementById('lb-metrics');
      const lbLink = document.getElementById('lb-link');

      function openLightbox(idx) {
        const p = media.posts[idx];
        if (!p) return;
        const hasCover = !!p.cover;
        lbCover.style.backgroundImage = hasCover ? `url('${p.cover}')` : 'none';
        lbCover.style.background = hasCover ? '' : `linear-gradient(135deg, ${p.color || '#7d6b56'}, ${shadeColor(p.color || '#7d6b56', -30)})`;
        lbCover.classList.toggle('no-image', !hasCover);
        lbBadge.className = 'badge ' + (p.platform || '');
        lbBadge.textContent = PLATFORM_LABEL[p.platform] || p.platform;
        lbTitle.textContent = p.title || '';
        lbSubtitle.textContent = p.subtitle || '';
        lbLink.href = p.url || '#';
        lbLink.style.display = p.url ? 'inline-flex' : 'none';
        const m = p.metrics || {};
        const parts = [];
        if (m.read) parts.push(`阅读 ${m.read}`);
        if (m.like) parts.push(`点赞 ${m.like}`);
        if (m.collect) parts.push(`收藏 ${m.collect}`);
        if (m.comment) parts.push(`评论 ${m.comment}`);
        lbMetrics.innerHTML = parts.map(s => `<span>${escapeHtml(s)}</span>`).join('');
        lightbox.classList.add('open');
        lightbox.setAttribute('aria-hidden', 'false');
      }
      function closeLightbox() {
        lightbox.classList.remove('open');
        lightbox.setAttribute('aria-hidden', 'true');
      }
      cards.forEach((c, i) => c.addEventListener('click', () => openLightbox(i)));
      lightbox.querySelector('.lb-close').addEventListener('click', closeLightbox);
      lightbox.addEventListener('click', e => { if (e.target === lightbox) closeLightbox(); });
      const onMediaKeydown = e => {
        if (e.key === 'Escape' && lightbox.classList.contains('open')) closeLightbox();
      };
      document.addEventListener('keydown', onMediaKeydown);
      onViewCleanup(() => document.removeEventListener('keydown', onMediaKeydown));
    }

    // ---- CONTACT (single-screen page) ----
    function showContact() {
      setActiveNav('contact');
      updateMeta({ title: 'Contact · ' + (MANIFEST.site.title || '周未') });
      const c = MANIFEST.site.contact || {};
      const rows = Object.entries(c).map(([k, v]) => `
        <div class="contact-row">
          <div class="label">${escapeHtml(k)}</div>
          <div class="value" data-copy="${escapeHtml(v)}">${escapeHtml(v)}</div>
        </div>
      `).join('');
      $view.innerHTML = `
        <div class="page contact-fit">
          <div class="contact-page fade-stagger">
            <h1>Get in touch.</h1>
            <div class="contact-list fade-stagger">${rows}</div>
          </div>
        </div>
      `;
      document.querySelectorAll('.contact-row .value').forEach(el => {
        el.addEventListener('click', () => {
          navigator.clipboard.writeText(el.dataset.copy);
          el.classList.add('copied');
          setTimeout(() => el.classList.remove('copied'), 1500);
        });
      });
    }

    // ===== Living ink lines =====
    // Lines undulate continuously; a click sends a ripple outward from the
    // click point; label characters ride the line like clothes on a wire.
    const REDUCED_MOTION = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    let inkRAF = null;
    let inkStrata = [];

    const STRANDS = 4;

    // Desktop-only paper tilt: restrained enough to keep the editorial tone.
    function initPaperTilt() {
      if (REDUCED_MOTION || !window.matchMedia('(hover: hover) and (pointer: fine)').matches) return;
      document.querySelectorAll('.soil-card').forEach(card => {
        const move = e => {
          const r = card.getBoundingClientRect();
          const px = Math.max(0, Math.min(1, (e.clientX - r.left) / r.width));
          const py = Math.max(0, Math.min(1, (e.clientY - r.top) / r.height));
          card.style.setProperty('--card-rx', `${((.5 - py) * 4).toFixed(2)}deg`);
          card.style.setProperty('--card-ry', `${((px - .5) * 4).toFixed(2)}deg`);
          card.style.setProperty('--shine-x', `${(px * 100).toFixed(1)}%`);
          card.style.setProperty('--shine-y', `${(py * 100).toFixed(1)}%`);
        };
        const leave = () => {
          card.style.setProperty('--card-rx', '0deg');
          card.style.setProperty('--card-ry', '0deg');
        };
        card.addEventListener('pointermove', move);
        card.addEventListener('pointerleave', leave);
      });
    }

    if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
      window.addEventListener('pointermove', e => {
        document.documentElement.style.setProperty('--cursor-x', `${e.clientX}px`);
        document.documentElement.style.setProperty('--cursor-y', `${e.clientY}px`);
        const overLine = !!e.target.closest?.('.stratum-line');
        const overCard = !!e.target.closest?.('.soil-card');
        $inkCursor.classList.toggle('over-line', overLine);
        $inkCursor.classList.toggle('over-card', overCard);
      }, { passive: true });
    }
    // Base drift shared by all strands of one stratum (the braid's spine).
    function spineYAt(s, x, t) {
      let y = 22
        + Math.sin(x * 0.006 + t * 0.55 + s.ph1) * 2.2 * s.amp
        + Math.sin(x * 0.014 - t * 0.38 + s.ph2) * 1.3 * s.amp;
      for (const p of s.pulses) {
        const dt = t - p.t0;
        if (dt < 0 || dt > 2.6) continue;
        const dist = Math.abs(x - p.x);
        const g = Math.exp(-Math.pow(dist - dt * 340, 2) / 5200);
        y += g * Math.sin(dt * 13) * 10 * Math.exp(-dt * 1.7);
      }
      return y;
    }
    // Each strand weaves around the spine with a phase-shifted twist, so the
    // four threads cross and wrap one another as they drift.
    function strandYAt(s, k, x, t) {
      const phase = k * (Math.PI * 2 / STRANDS);
      const twist =
        Math.sin(x * 0.021 + t * 0.65 + phase + s.ph1) * 2.6 +
        Math.sin(x * 0.009 - t * 0.42 + phase * 1.6 + s.ph2) * 1.4;
      return spineYAt(s, x, t) + twist * (0.55 + 0.45 * s.amp);
    }

    function buildPathD(s, k, t) {
      const steps = 30;
      const pts = [];
      for (let i = 0; i <= steps; i++) {
        const x = 1000 * i / steps;
        pts.push([x, strandYAt(s, k, x, t)]);
      }
      let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
      for (let i = 1; i < pts.length - 1; i++) {
        const mx = (pts[i][0] + pts[i + 1][0]) / 2;
        const my = (pts[i][1] + pts[i + 1][1]) / 2;
        d += ` Q${pts[i][0].toFixed(1)},${pts[i][1].toFixed(1)} ${mx.toFixed(1)},${my.toFixed(1)}`;
      }
      const last = pts[pts.length - 1];
      d += ` L${last[0].toFixed(1)},${last[1].toFixed(1)}`;
      return d;
    }

    function inkFrame(now) {
      if (document.hidden) {
        inkRAF = null;
        return;
      }
      const t = now / 1000;
      let alive = false;
      for (const s of inkStrata) {
        if (!s.paths.length || !document.contains(s.paths[0])) continue;
        alive = true;
        s.amp += (s.targetAmp - s.amp) * 0.06;
        s.pulses = s.pulses.filter(p => t - p.t0 < 2.6);

        s.paths.forEach((path, k) => path.setAttribute('d', buildPathD(s, k, t)));

        // Characters float above the braid, following the spine's motion.
        const scaleY = s.svgH / 44;
        for (const ch of s.chars) {
          const dy = (spineYAt(s, ch.x, t) - 22) * scaleY;
          const slope = (spineYAt(s, ch.x + 14, t) - spineYAt(s, ch.x - 14, t)) * scaleY / 28;
          const deg = Math.atan(slope) * 57.3 * 0.55;
          ch.el.style.transform = `translateY(${dy.toFixed(2)}px) rotate(${deg.toFixed(2)}deg)`;
        }
      }
      inkRAF = alive ? requestAnimationFrame(inkFrame) : null;
    }

    document.addEventListener('visibilitychange', () => {
      if (document.hidden && inkRAF) {
        cancelAnimationFrame(inkRAF);
        inkRAF = null;
      } else if (!document.hidden && !inkRAF && inkStrata.some(s => document.contains(s.el)) && !REDUCED_MOTION) {
        inkRAF = requestAnimationFrame(inkFrame);
      }
    });

    function initInkLife() {
      if (inkRAF) { cancelAnimationFrame(inkRAF); inkRAF = null; }
      inkStrata = [...document.querySelectorAll('.stratum')].map((st, i) => {
        const lineBtn = st.querySelector('.stratum-line');
        const label = st.querySelector('.stratum-label');
        const svg = st.querySelector('svg');
        const cr = lineBtn.getBoundingClientRect();
        const W = cr.width || 1000;
        const chars = [...label.querySelectorAll('.lch')].map(el => {
          const r = el.getBoundingClientRect();
          return { el, x: ((r.left + r.width / 2) - cr.left) / W * 1000 };
        });
        return {
          paths: [...st.querySelectorAll('path.ink')],
          svgH: svg.clientHeight || 44,
          chars,
          ph1: i * 2.1 + 0.7,
          ph2: i * 4.3 + 1.9,
          amp: 1,
          targetAmp: 1,
          pulses: [],
          el: st,
        };
      });
      if (!inkStrata.length) return;

      if (REDUCED_MOTION) {
        // Draw one calm static braid; no loop, no bobbing.
        const t = 1.234;
        for (const s of inkStrata) {
          s.paths.forEach((path, k) => path.setAttribute('d', buildPathD(s, k, t)));
        }
        return;
      }

      // Hover/open drive amplitude targets.
      for (const s of inkStrata) {
        s.el.addEventListener('mouseenter', () => { s.targetAmp = s.el.classList.contains('open') ? 1.7 : 2.3; });
        s.el.addEventListener('mouseleave', () => { s.targetAmp = s.el.classList.contains('open') ? 1.5 : 1; });
      }
      inkRAF = requestAnimationFrame(inkFrame);
    }

    function inkPulse(stEl, clientX) {
      const s = inkStrata.find(k => k.el === stEl);
      if (!s) return;
      const cr = stEl.querySelector('.stratum-line').getBoundingClientRect();
      const x = clientX != null ? (clientX - cr.left) / cr.width * 1000 : 500;
      s.pulses.push({ x, t0: performance.now() / 1000 });
      s.targetAmp = stEl.classList.contains('open') ? 1.5 : 1;
    }

    let inkResizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(inkResizeTimer);
      inkResizeTimer = setTimeout(() => {
        if (document.querySelector('.stratum')) initInkLife();
      }, 120);
    });

    function openStratum(catId) {
      document.querySelectorAll('.stratum').forEach(st => {
        const open = st.dataset.cat === catId;
        st.classList.toggle('open', open);
        st.querySelector('.stratum-line')?.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }

    function shadeColor(hex, percent) {
      const n = parseInt(hex.replace('#',''), 16);
      let r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
      const f = 1 + percent / 100;
      r = Math.max(0, Math.min(255, Math.round(r * f)));
      g = Math.max(0, Math.min(255, Math.round(g * f)));
      b = Math.max(0, Math.min(255, Math.round(b * f)));
      return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0');
    }

    // ---- dynamic OG/meta tags ----
    function updateMeta(opts) {
      const title = opts.title || ((MANIFEST.site.title || '周未') + ' · ' + (MANIFEST.site.name_en || 'ZHOU WEI'));
      const desc  = opts.desc  || '周未 — 写作者与批评者，跨越创意写作、文化批评与财经新闻三种语境。';
      const img   = opts.img   || (MANIFEST.site.photo || '');
      document.title = title;
      const set = (sel, val) => { const el = document.querySelector(sel); if (el) el.setAttribute('content', val); };
      set('meta[property="og:title"]', title);
      set('meta[property="og:description"]', desc);
      set('meta[property="og:image"]', img);
      set('meta[name="twitter:title"]', title);
      set('meta[name="twitter:description"]', desc);
      set('meta[name="twitter:image"]', img);
    }

    // ---- NOVEL READER: a bound-paper edition with responsive pagination ----
    function showNovelBookLegacy(work) {
      const chapters = NOVELS[work.id] || [];
      if (!chapters.length) { location.hash = '#curated-body'; return; }
      document.body.classList.add('novel-mode');
      setActiveNav('body');
      updateMeta({ title: work.title + ' · 周未', desc: work.subtitle || '长篇小说' });

      const compact = () => window.matchMedia('(max-width: 760px)').matches;
      const charTarget = () => compact() ? 360 : 520;
      const pages = [];
      const chapterStarts = [];
      pages.push({ kind: 'cover', chapter: '封面' });
      pages.push({ kind: 'title', chapter: '扉页' });
      pages.push({ kind: 'contents', chapter: '目录' });

      function cleanParagraphs(text) {
        return String(text || '')
          .replace(/\r\n?/g, '\n')
          .split(/\n+/)
          .map(p => p.trim().replace(/^#{1,6}\s*/, '').replace(/^[-*]\s+/, ''))
          .filter(Boolean);
      }

      chapters.forEach((chapter, chapterIndex) => {
        chapterStarts[chapterIndex] = pages.length;
        const paragraphs = cleanParagraphs(chapter.text);
        let group = [];
        let count = 0;
        const flush = () => {
          if (!group.length) return;
          pages.push({
            kind: 'text',
            chapter: chapter.title,
            chapterIndex,
            paragraphs: group,
            pageInChapter: pages.filter(p => p.chapterIndex === chapterIndex).length + 1
          });
          group = [];
          count = 0;
        };
        paragraphs.forEach(p => {
          const length = p.replace(/\s/g, '').length;
          if (group.length && count + length > charTarget()) flush();
          group.push(p);
          count += length;
          if (count >= charTarget()) flush();
        });
        flush();
      });
      pages.push({ kind: 'end', chapter: '终章' });

      const saved = Number(localStorage.getItem('zw-novel-' + work.id + '-page'));
      let current = Number.isFinite(saved) ? Math.max(0, Math.min(pages.length - 1, saved)) : 0;
      let turning = false;

      $view.innerHTML = `
        <main class="novel-reader" aria-label="《${escapeHtml(work.title)}》翻页阅读器">
          <header class="novel-toolbar">
            <a href="#curated-body">← 返回作品集</a>
            <div class="novel-toolbar-title">${escapeHtml(work.title)} · 周未</div>
            <div class="novel-toolbar-actions">
              <span class="novel-page-label" id="novel-page-label"></span>
              <button type="button" id="novel-open-toc">目录</button>
            </div>
          </header>
          <section class="novel-stage" id="novel-stage">
            <button class="novel-turn" id="novel-prev" type="button" aria-label="上一页">←</button>
            <div class="novel-book" id="novel-book" aria-live="polite"></div>
            <button class="novel-turn" id="novel-next" type="button" aria-label="下一页">→</button>
          </section>
          <footer class="novel-footer">
            <span id="novel-chapter-label">封面</span>
            <input class="novel-range" id="novel-range" type="range" min="0" max="${pages.length - 1}" value="${current}" aria-label="阅读进度">
            <span id="novel-folio-label">1 / ${pages.length}</span>
          </footer>
          <dialog class="novel-toc-dialog" id="novel-toc-dialog">
            <div class="novel-toc-head"><strong>Contents</strong><button type="button" id="novel-close-toc" aria-label="关闭目录">×</button></div>
            <ol class="novel-contents-list">
              ${chapters.map((chapter, i) => `<li><button type="button" data-novel-jump="${chapterStarts[i]}"><span>${String(i + 1).padStart(2, '0')}　${escapeHtml(chapter.title)}</span><span>${chapterStarts[i] + 1}</span></button></li>`).join('')}
            </ol>
          </dialog>
        </main>`;

      const book = document.getElementById('novel-book');
      const prev = document.getElementById('novel-prev');
      const next = document.getElementById('novel-next');
      const range = document.getElementById('novel-range');
      const chapterLabel = document.getElementById('novel-chapter-label');
      const folioLabel = document.getElementById('novel-folio-label');
      const pageLabel = document.getElementById('novel-page-label');
      const dialog = document.getElementById('novel-toc-dialog');

      function contentsMarkup() {
        return `<div class="novel-contents-page"><h2>Contents</h2><ol class="novel-contents-list">
          ${chapters.map((chapter, i) => `<li><button type="button" data-novel-jump="${chapterStarts[i]}"><span>${String(i + 1).padStart(2, '0')}　${escapeHtml(chapter.title)}</span><span>${chapterStarts[i] + 1}</span></button></li>`).join('')}
        </ol></div>`;
      }

      function pageMarkup(page, index) {
        if (!page) return '<article class="novel-paper" aria-hidden="true"></article>';
        if (page.kind === 'cover') return `<article class="novel-paper"><div class="novel-cover-page"><div class="novel-cover-meta"><span>ZHOU WEI</span><span>A NOVEL</span></div><h1><span>北京</span><span>北京</span></h1><div class="novel-cover-meta"><span>中篇小说</span><span>十章</span></div></div></article>`;
        if (page.kind === 'title') return `<article class="novel-paper"><div class="novel-title-page"><h2>${escapeHtml(work.title)}</h2><p>周未 著 · a novel in ten chapters</p></div><span class="novel-folio">${index + 1}</span></article>`;
        if (page.kind === 'contents') return `<article class="novel-paper">${contentsMarkup()}<span class="novel-folio">${index + 1}</span></article>`;
        if (page.kind === 'end') return `<article class="novel-paper"><div class="novel-end-page"><strong>北京，北京。</strong><span>— FIN —</span></div></article>`;
        return `<article class="novel-paper">
          <div class="novel-paper-inner">
            <div class="novel-running-head"><span>${escapeHtml(work.title)}</span><span>${escapeHtml(page.chapter)} · ${page.pageInChapter}</span></div>
            <div class="novel-page-body">${page.paragraphs.map(p => `<p>${escapeHtml(p)}</p>`).join('')}</div>
          </div>
          <span class="novel-folio">${index + 1}</span>
        </article>`;
      }

      function normalizedCurrent(value) {
        if (compact()) return Math.max(0, Math.min(pages.length - 1, value));
        return Math.max(0, Math.min(pages.length - 1, value - (value % 2)));
      }

      function render() {
        current = normalizedCurrent(current);
        const secondIndex = compact() ? null : current + 1;
        book.innerHTML = pageMarkup(pages[current], current) + (compact() ? '' : pageMarkup(pages[secondIndex], secondIndex));
        book.querySelectorAll('[data-novel-jump]').forEach(button => button.addEventListener('click', () => jumpTo(Number(button.dataset.novelJump))));
        const shown = pages[current] || pages[0];
        chapterLabel.textContent = shown.chapter;
        folioLabel.textContent = `${current + 1} / ${pages.length}`;
        pageLabel.textContent = `${current + 1} / ${pages.length}`;
        range.value = current;
        prev.disabled = current <= 0;
        next.disabled = compact() ? current >= pages.length - 1 : current >= pages.length - 2;
        $progress.style.width = ((current + 1) / pages.length * 100) + '%';
        localStorage.setItem('zw-novel-' + work.id + '-page', String(current));
      }

      function jumpTo(index) {
        current = normalizedCurrent(index);
        render();
        if (dialog.open) dialog.close();
      }

      function turn(direction) {
        if (turning) return;
        const step = compact() ? 1 : 2;
        const target = Math.max(0, Math.min(pages.length - 1, current + direction * step));
        if (target === current) return;
        if (REDUCED_MOTION) { current = target; render(); return; }
        turning = true;
        book.classList.add(direction > 0 ? 'turn-next' : 'turn-prev');
        window.setTimeout(() => {
          current = target;
          book.classList.remove('turn-next', 'turn-prev');
          render();
          turning = false;
        }, 430);
      }

      prev.addEventListener('click', () => turn(-1));
      next.addEventListener('click', () => turn(1));
      range.addEventListener('input', () => jumpTo(Number(range.value)));
      document.getElementById('novel-open-toc').addEventListener('click', () => dialog.showModal());
      document.getElementById('novel-close-toc').addEventListener('click', () => dialog.close());
      dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
      dialog.querySelectorAll('[data-novel-jump]').forEach(button => button.addEventListener('click', () => jumpTo(Number(button.dataset.novelJump))));

      const onKey = e => {
        if (dialog.open && e.key !== 'Escape') return;
        if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') { e.preventDefault(); turn(1); }
        if (e.key === 'ArrowLeft' || e.key === 'PageUp') { e.preventDefault(); turn(-1); }
      };
      window.addEventListener('keydown', onKey);
      onViewCleanup(() => window.removeEventListener('keydown', onKey));

      let pointerX = null;
      const stage = document.getElementById('novel-stage');
      const onPointerDown = e => { pointerX = e.clientX; };
      const onPointerUp = e => {
        if (pointerX == null) return;
        const delta = e.clientX - pointerX;
        pointerX = null;
        if (Math.abs(delta) > 46) turn(delta < 0 ? 1 : -1);
      };
      stage.addEventListener('pointerdown', onPointerDown);
      stage.addEventListener('pointerup', onPointerUp);

      let wasCompact = compact();
      const onNovelResize = () => {
        const nowCompact = compact();
        if (nowCompact !== wasCompact) { wasCompact = nowCompact; render(); }
      };
      window.addEventListener('resize', onNovelResize, { passive: true });
      onViewCleanup(() => window.removeEventListener('resize', onNovelResize));
      render();
    }

    // ---- NOVEL READER: one chapter per route, with the complete directory
    // as the designed closing element on every chapter page. ----
    function showChapteredNovel(work, requestedChapter) {
      const chapters = NOVELS[work.id] || [];
      if (!chapters.length) { location.hash = '#curated-body'; return; }

      setActiveNav('body');
      const cat = (MANIFEST.categories || []).find(c => c.id === work.category);
      const chapterItems = chapters.map((chapter, index) => {
        const id = `chapter-${index + 1}`;
        const paragraphs = String(chapter.text || '')
          .replace(/\r\n?/g, '\n')
          .split(/\n+/)
          .map(p => p.trim())
          .filter(Boolean);
        return { id, title: chapter.title || `第${index + 1}章`, paragraphs };
      });
      const chapterIndex = Math.max(0, Math.min(chapterItems.length - 1, (Number(requestedChapter) || 1) - 1));
      const currentChapter = chapterItems[chapterIndex];
      const rawCharCount = currentChapter.paragraphs.join('').replace(/\s/g, '').length;
      const estMinutes = Math.max(1, Math.round(rawCharCount / 350));

      updateMeta({
        title: `${work.title} · ${currentChapter.title} · 周未`,
        desc: `${currentChapter.title} · ${rawCharCount.toLocaleString()}字`,
        img: work.cover || (MANIFEST.site.photo || '')
      });

      $view.innerHTML = `
        <article class="reader reader-variant-creative fade-stagger">
          <a class="back" href="#curated-body">← back to the line</a>
          <div class="cat-tag">${cat ? escapeHtml(cat.label) + ' · ' : ''}中篇小说</div>
          <h1 class="headline">${escapeHtml(work.title)}</h1>
          <div class="novel-chapter-kicker"><span>Chapter ${String(chapterIndex + 1).padStart(2, '0')} / ${String(chapters.length).padStart(2, '0')}</span></div>
          <h2 class="novel-page-title">${escapeHtml(currentChapter.title)}</h2>
          <p class="byline">周未</p>
          <div class="reader-meta-bar">
            <span class="reading-time">${estMinutes} min read</span>
            <span class="word-count">${rawCharCount.toLocaleString()} 字</span>
          </div>
          <div class="reader-body" id="reader-body">
            ${currentChapter.paragraphs.map(p => `<p class="para">${renderProse('　　' + p)}</p>`).join('')}
          </div>
          <div class="reader-end">— ${escapeHtml(currentChapter.title)}完 —</div>
          <div class="share-bar">
            <button class="share-btn" id="share-copy" aria-label="复制链接">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
              <span>复制链接</span>
            </button>
            <button class="share-btn" id="share-qr-btn" aria-label="二维码">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h3v3M21 14v7M14 21h3"/></svg>
              <span>二维码</span>
            </button>
          </div>
          <div class="share-qr" id="share-qr">
            <img id="qr-img" alt="QR Code" />
            <p class="qr-hint">扫码在手机上阅读</p>
          </div>
          <nav class="novel-directory" aria-label="《${escapeHtml(work.title)}》总目录">
            <div class="novel-directory-head">
              <h2>总目录</h2>
              <span>Contents · ${chapters.length} Chapters</span>
            </div>
            <div class="novel-directory-grid">
              ${chapterItems.map((chapter, index) => `
                <a class="novel-directory-item${index === chapterIndex ? ' active' : ''}"
                   href="#/read/${encodeURIComponent(work.id)}/chapter/${index + 1}"
                   ${index === chapterIndex ? 'aria-current="page"' : ''}>
                  <span class="chapter-no">${String(index + 1).padStart(2, '0')}</span>
                  <span class="chapter-name">${escapeHtml(chapter.title)}</span>
                  <span class="chapter-mark">${index === chapterIndex ? '正在阅读' : '↗'}</span>
                </a>`).join('')}
            </div>
          </nav>
        </article>`;

      initShare();
    }

    // ---- READER ----
    function showRead(id, chapterNumber) {
      const work = MANIFEST.works.find(w => w.id === id);
      if (!work) { location.hash = '#curated-origin'; return; }
      if (work.format === 'novel') { showChapteredNovel(work, chapterNumber); return; }
      setActiveNav({ creative: 'body', criticism: 'reading', news: 'field' }[work.category] || 'origin');
      const cat = (MANIFEST.categories || []).find(c => c.id === work.category);
      const by = BYLINE[work.category] || BYLINE.creative;
      const bylineText = (by.prefix || '') + '周未' + (by.suffix || '');
      const curatedBack = {
        creative: '#curated-body',
        criticism: '#curated-reading',
        news: '#curated-field'
      }[work.category] || '#curated-origin';

      const text = WORKS[id] || '';
      let paragraphs = text
        .replace(/\r\n/g, '\n').replace(/\r/g, '\n')
        .split(/\n+/)
        .map(p => p.trim().replace(/^[　\s]+/, ''))
        .filter(p => p.length > 0);

      // Detect academic-paper preamble (abstract + keywords).
      let abstractText = null, keywordsText = null;
      const rest = [];
      for (const p of paragraphs) {
        const mAbs = p.match(/^(内容提要|摘要|Abstract)\s*[:：]\s*(.*)$/);
        const mKw  = p.match(/^(关键词|Keywords)\s*[:：]\s*(.*)$/);
        if (!abstractText && mAbs) { abstractText = mAbs[2]; continue; }
        if (!keywordsText && mKw)  { keywordsText = mKw[2]; continue; }
        rest.push(p);
      }
      paragraphs = rest.map(p => '　　' + p);

      // Detect section headings for TOC (Chinese numeral, 第X章, 【...】 patterns)
      const HEADING_RE = /^[一二三四五六七八九十]{1,3}[、.．]|^第[一二三四五六七八九十百千\d]+[章节部分编]|^【[^】]+】$/;
      const headings = [];
      const bodyItems = rest.map(p => {
        if (p.length < 50 && HEADING_RE.test(p)) {
          const hid = 'sec-' + headings.length;
          headings.push({ id: hid, text: p });
          return { type: 'h', id: hid, text: p };
        }
        return { type: 'p', text: '　　' + p };
      });

      // Reading-time estimate (from raw paragraphs, before adding indent)
      const rawCharCount = rest.join('').replace(/\s/g, '').length;
      const wpm = /[\u4e00-\u9fff]/.test(rest.join('')) ? 350 : 200;
      const estMinutes = Math.max(1, Math.round(rawCharCount / wpm));

      const showLede = work.subtitle && !abstractText;
      const paperMeta = (abstractText || keywordsText) ? `
        <div class="paper-meta">
          ${abstractText ? `
            <div class="meta-block">
              <div class="meta-label">Abstract · 内容提要</div>
              <p>${escapeHtml(abstractText)}</p>
            </div>` : ''}
          ${keywordsText ? `
            <div class="meta-block">
              <div class="meta-label">Keywords · 关键词</div>
              <p class="keywords">${escapeHtml(keywordsText)}</p>
            </div>` : ''}
        </div>` : '';

      // Prev/next navigation within same category
      const catWorks = MANIFEST.works.filter(w => w.category === work.category);
      const curIdx = catWorks.findIndex(w => w.id === id);
      const prevWork = curIdx > 0 ? catWorks[curIdx - 1] : null;
      const nextWork = curIdx >= 0 && curIdx < catWorks.length - 1 ? catWorks[curIdx + 1] : null;

      // Related works (same category, excluding current)
      const related = MANIFEST.works
        .filter(w => w.category === work.category && w.id !== id)
        .slice(0, 3);

      // TOC (only if 3+ headings)
      const showTOC = headings.length >= 3;

      // Update OG/meta for sharing
      const ogDesc = work.subtitle || abstractText || `${cat ? cat.label + ' · ' : ''}${rawCharCount.toLocaleString()}字 · ${estMinutes} min read`;
      const ogImg = work.cover || (MANIFEST.site.photo || '');
      updateMeta({ title: work.title + ' · 周未', desc: ogDesc, img: ogImg });

      $view.innerHTML = `
        ${showTOC ? `
        <nav class="reader-toc" id="reader-toc">
          <div class="toc-title">Contents</div>
          <ol>${headings.map((h, i) => `<li><a href="#${h.id}" data-toc-target="${h.id}" class="${i === 0 ? 'active' : ''}">${escapeHtml(h.text)}</a></li>`).join('')}</ol>
        </nav>` : ''}
        <article class="reader reader-variant-${work.category} fade-stagger">
          <a class="back" href="${curatedBack}">← back to the line</a>
          ${cat ? `<div class="cat-tag">${escapeHtml(cat.label)}</div>` : ''}
          <h1 class="headline">${escapeHtml(work.title)}</h1>
          ${showLede ? `<p class="lede">${escapeHtml(work.subtitle)}</p>` : ''}
          <p class="byline">${escapeHtml(bylineText)}</p>
          <div class="reader-meta-bar">
            <span class="reading-time">${estMinutes} min read</span>
            <span class="word-count">${rawCharCount.toLocaleString()} 字</span>
          </div>
          ${paperMeta}
          <div class="reader-body" id="reader-body">
            ${bodyItems.map(item => item.type === 'h' ? `<h2 class="toc-heading" id="${item.id}">${escapeHtml(item.text)}</h2>` : `<p class="para">${renderProse(item.text)}</p>`).join('')}
          </div>
          <div class="reader-end">— Fin —</div>
          <div class="share-bar">
            <button class="share-btn" id="share-copy" aria-label="复制链接">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
              <span>复制链接</span>
            </button>
            <button class="share-btn" id="share-qr-btn" aria-label="二维码">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><path d="M14 14h3v3M21 14v7M14 21h3"/></svg>
              <span>二维码</span>
            </button>
          </div>
          <div class="share-qr" id="share-qr">
            <img id="qr-img" alt="QR Code" />
            <p class="qr-hint">扫码在手机上阅读</p>
          </div>
          ${related.length ? `
          <div class="reader-related">
            <p class="related-title">More from ${escapeHtml(cat ? cat.label : '')}</p>
            <div class="related-list">
              ${related.map(w => `
                <a class="related-item" href="#/read/${encodeURIComponent(w.id)}">
                  <div class="ri-year">${escapeHtml(w.year || '')}</div>
                  <div class="ri-title">${escapeHtml(w.title)}</div>
                  ${w.subtitle ? `<div class="ri-desc">${escapeHtml(w.subtitle)}</div>` : ''}
                </a>
              `).join('')}
            </div>
          </div>` : ''}
          ${(prevWork || nextWork) ? `
          <div class="reader-nav">
            ${prevWork ? `<a class="prev" href="#/read/${encodeURIComponent(prevWork.id)}"><span class="nav-label">← Previous</span><span class="nav-title">${escapeHtml(prevWork.title)}</span></a>` : '<span></span>'}
            ${nextWork ? `<a class="next" href="#/read/${encodeURIComponent(nextWork.id)}"><span class="nav-label">Next →</span><span class="nav-title">${escapeHtml(nextWork.title)}</span></a>` : ''}
          </div>` : ''}
        </article>
      `;
      initTOCTracking();
      initShare();
    }

    // ---- share: copy link + QR code ----
    function initShare() {
      const copyBtn = document.getElementById('share-copy');
      const qrBtn = document.getElementById('share-qr-btn');
      const qrBox = document.getElementById('share-qr');
      const qrImg = document.getElementById('qr-img');

      if (copyBtn) {
        copyBtn.addEventListener('click', async () => {
          const url = window.location.href;
          try {
            await navigator.clipboard.writeText(url);
          } catch {
            // Fallback for older browsers
            const ta = document.createElement('textarea');
            ta.value = url;
            ta.style.position = 'fixed'; ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
          }
          const label = copyBtn.querySelector('span');
          const orig = label.textContent;
          label.textContent = '已复制 ✓';
          copyBtn.classList.add('copied');
          setTimeout(() => { label.textContent = orig; copyBtn.classList.remove('copied'); }, 2000);
        });
      }

      if (qrBtn && qrBox && qrImg) {
        qrBtn.addEventListener('click', () => {
          const isVisible = qrBox.classList.toggle('visible');
          if (isVisible && !qrImg.src) {
            const url = encodeURIComponent(window.location.href);
            qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&margin=8&data=${url}`;
          }
        });
      }
    }

    // Wrap 「…」 dialogue runs so speech carries its own voice on the page.
    function renderProse(text) {
      const re = /「([^」]*)」/g;
      let out = '', last = 0, m;
      while ((m = re.exec(text)) !== null) {
        out += escapeHtml(text.slice(last, m.index));
        out += `<span class="dlg"><span class="q">「</span>${escapeHtml(m[1])}<span class="q">」</span></span>`;
        last = m.index + m[0].length;
      }
      out += escapeHtml(text.slice(last));
      return out;
    }

    // ---- TOC scroll tracking via IntersectionObserver ----
    let tocObserver = null;
    function initTOCTracking() {
      if (tocObserver) { tocObserver.disconnect(); tocObserver = null; }
      const toc = document.getElementById('reader-toc');
      if (!toc) return;
      const links = [...toc.querySelectorAll('a[data-toc-target]')];
      const targets = links.map(l => document.getElementById(l.dataset.tocTarget)).filter(Boolean);
      if (!targets.length) return;
      tocObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const id = entry.target.id;
            links.forEach(l => l.classList.toggle('active', l.dataset.tocTarget === id));
          }
        });
      }, { rootMargin: '-100px 0px -70% 0px' });
      targets.forEach(t => tocObserver.observe(t));

      // Click handler: smooth-scroll instead of changing location.hash
      links.forEach(link => {
        link.addEventListener('click', (e) => {
          e.preventDefault();
          const target = document.getElementById(link.dataset.tocTarget);
          if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            links.forEach(l => l.classList.remove('active'));
            link.classList.add('active');
          }
        });
      });
    }

    // ---- scroll: progress bar + back-to-top ----
    const $btt = document.createElement('div');
    $btt.className = 'back-to-top';
    $btt.innerHTML = '↑';
    $btt.title = '返回顶部';
    $btt.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
    document.body.appendChild($btt);

    window.addEventListener('scroll', () => {
      const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      $progress.style.width = (window.scrollY / max * 100) + '%';
      $btt.classList.toggle('visible', window.scrollY > 400);
    }, { passive: true });

    function escapeHtml(s) {
      return String(s).replace(/[&<>"']/g, c => ({
        '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
      }[c]));
    }

    // Kick off the initial view now that everything above is initialized.
    route();
  </script>
</body>
</html>
'''

html = TEMPLATE
html = html.replace('__MANIFEST_JSON__', json.dumps(manifest, ensure_ascii=False))
html = html.replace('__WORKS_JSON__', json.dumps(works_text, ensure_ascii=False))
html = html.replace('__NOVELS_JSON__', json.dumps(novels, ensure_ascii=False))
html = html.replace('__WORLD_PATHS__', json.dumps(world_paths))
html = html.replace('__OG_IMAGE__', site.get('photo', ''))
OUT.write_text(html, encoding='utf-8')
shutil.copy2(OUT, OUT_COPY)  # also update portfolio.html for local preview

size_kb = OUT.stat().st_size / 1024
print(f'✓ 已生成 {OUT.name}（{size_kb:.1f} KB）')
print(f'  路径：{OUT}')
print(f'  共打包 {len(works_text)} 篇作品')
print(f'  index.html → GitHub Pages  |  portfolio.html → 本地预览')
