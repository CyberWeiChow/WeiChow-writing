#!/usr/bin/env python3
"""
打包成单个 portfolio.html。双击打开 / 邮件附件均可。
用法：
    cd ~/Documents/GitHub/WeiChow\ writing
    python3 build.py
"""

import base64
import json
import mimetypes
from pathlib import Path

ROOT = Path(__file__).parent
WORKS_DIR = ROOT / 'works'
OUT = ROOT / 'portfolio.html'

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

# Inline each work's cover image as a data URL.
for w in manifest.get('works', []):
    if w.get('cover'):
        w['cover'] = inline_image(w['cover'])
works_text = {}
missing = []
for w in manifest.get('works', []):
    f = WORKS_DIR / w['file']
    if not f.exists():
        missing.append(w['file'])
        continue
    works_text[w['id']] = f.read_text(encoding='utf-8')

if missing:
    print(f'! 警告：以下文件不存在，已跳过：{missing}')

manifest['works'] = [w for w in manifest['works'] if w['id'] in works_text]

TEMPLATE = r'''<!DOCTYPE html>
<html lang="zh" data-theme="dark">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>周未</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,400&family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&family=Noto+Serif+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
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
      grid-template-columns: 0.9fr 1.1fr;
      gap: 96px;
      align-items: start;
      margin-bottom: 140px;
    }
    .bio-portrait {
      aspect-ratio: 1 / 1;
      background: var(--surface);
      background-size: cover;
      background-position: center;
      position: relative;
      overflow: hidden;
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
    .bio-content h1 {
      font-family: 'Noto Serif SC', 'Cormorant Garamond', serif;
      font-size: 56px;
      font-weight: 500;
      margin: 0 0 28px;
      letter-spacing: 0.02em;
      line-height: 1.05;
    }
    .bio-content h1 .en {
      display: block;
      font-family: 'Cormorant Garamond', 'Inter', serif;
      font-size: 18px;
      font-weight: 400;
      color: var(--muted);
      letter-spacing: 0.22em;
      margin-top: 20px;
      text-transform: uppercase;
    }
    .bio-tagline {
      font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
      font-size: 20px;
      font-style: italic;
      color: var(--accent);
      margin: 0 0 36px;
      letter-spacing: 0.02em;
    }
    .bio-content .bio-para {
      font-size: 16px;
      line-height: 1.85;
      color: color-mix(in srgb, var(--ink) 85%, transparent);
      margin: 0 0 18px;
      max-width: 520px;
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
      transform: translateY(52px);
      transition:
        opacity 420ms var(--ease-out),
        transform 560ms var(--ease-spring);
      transition-delay: calc(var(--i, 0) * 75ms);
    }
    .stratum.open .soil-card {
      opacity: 1;
      transform: translateY(0);
    }
    .soil-card:active { transform: translateY(0) scale(0.98); }
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
    @media (hover: hover) and (pointer: fine) {
      .soil-card:hover .soil-cover {
        transform: translateY(-8px);
        box-shadow: 0 24px 48px rgba(0,0,0,0.45), 0 6px 14px rgba(0,0,0,0.3);
      }
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
      stroke-width: 1.1;
      opacity: 0.55;
      transition: opacity 220ms var(--ease-out);
    }
    .stratum-line path.echo { opacity: 0.18; stroke-width: 1; }
    .stratum:hover .stratum-line path.main,
    .stratum.open .stratum-line path.main { opacity: 0.95; }
    .stratum:hover .stratum-line path.echo,
    .stratum.open .stratum-line path.echo { opacity: 0.35; }
    .stratum-label {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      font-family: 'Noto Serif SC', serif;
      font-size: 15px;
      font-weight: 500;
      letter-spacing: 0.42em;
      color: var(--muted);
      white-space: nowrap;
      line-height: 1;
      transition: color 220ms var(--ease-out), transform 300ms var(--ease-spring);
    }
    .stratum:hover .stratum-label, .stratum.open .stratum-label {
      color: var(--ink);
      transform: translateY(-50%) translateY(-1px);
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
    .stratum-line:active .stratum-label { transform: translateY(-50%) scale(0.97); }

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
      .bio-hero { grid-template-columns: 1fr; gap: 48px; }
      .bio-portrait { max-width: 360px; }
      .bio-content h1 { font-size: 42px; }
      .cat-page h1 { font-size: 48px; }
      .reader { padding: 72px 28px 120px; }
    }
    @media (max-width: 600px) {
      .topbar nav a { display: none; }
      .topbar nav a.theme-toggle, .topbar nav .menu-btn { display: inline-flex; }
      .topbar.menu-open nav a { display: inline-flex; }
      .topbar.menu-open { flex-wrap: wrap; }
      .topbar.menu-open nav { width: 100%; flex-direction: column; align-items: flex-start; gap: 16px; padding: 16px 0; }
      .bio-page { padding: 80px 24px 120px; }
      .cat-page { padding: 80px 24px 120px; }
      .works-grid { grid-template-columns: 1fr; }
      .contact-page h1 { font-size: 44px; }
    }
  </style>
</head>
<body>
  <div class="progress" id="progress"></div>
  <header class="topbar" id="topbar">
    <a href="#/" class="brand" id="brand">周未 · ZHOU WEI</a>
    <nav id="nav"></nav>
  </header>

  <main id="view"></main>

  <script>
    const MANIFEST = __MANIFEST_JSON__;
    const WORKS = __WORKS_JSON__;

    const BYLINE = {
      creative:  { prefix: '', suffix: '' },
      news:      { prefix: '记者　', suffix: '　报道' },
      criticism: { prefix: '', suffix: '　著' },
    };

    const $view = document.getElementById('view');
    const $nav = document.getElementById('nav');
    const $brand = document.getElementById('brand');
    const $progress = document.getElementById('progress');

    $brand.textContent = (MANIFEST.site.title || '周未') + ' · ' + (MANIFEST.site.name_en || 'ZHOU WEI');

    function buildNav() {
      $nav.innerHTML = `
        <a href="#/" data-route="bio">Bio</a>
        <a href="#/experience" data-route="experience">Experience</a>
        <a href="#/works" data-route="works">Works</a>
        <a href="#/contact" data-route="contact">Contact</a>
        <button class="theme-toggle" id="theme-toggle" aria-label="切换主题">◐</button>
      `;
      document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    }
    buildNav();

    // ---- theme toggle ----
    const savedTheme = localStorage.getItem('zw-theme');
    if (savedTheme) document.documentElement.dataset.theme = savedTheme;
    function toggleTheme() {
      const cur = document.documentElement.dataset.theme;
      const next = cur === 'dark' ? 'light' : 'dark';
      document.documentElement.dataset.theme = next;
      localStorage.setItem('zw-theme', next);
    }

    function setActiveNav(route) {
      document.querySelectorAll('#nav a').forEach(a => {
        a.classList.toggle('active', a.dataset.route === route);
      });
    }

    function route() {
      const h = location.hash || '#/';
      const m = h.match(/^#\/read\/(.+)$/);
      if (m) {
        window.scrollTo(0, 0);
        showRead(decodeURIComponent(m[1]));
        mountStaggers($view);
        return;
      }
      const tail = h.slice(2);
      showHome(tail || null);
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
    route();

    // ---- HOME (single continuous page: bio + strata + contact) ----
    function showHome(target) {
      const isCat = target && (MANIFEST.categories || []).some(c => c.id === target);
      const navKey = isCat || target === 'works' ? 'works'
        : (target === 'experience' || target === 'contact') ? target
        : 'bio';
      setActiveNav(navKey);
      document.title = (MANIFEST.site.title || '周未');

      if (!document.getElementById('home-root')) {
        renderHome();
        mountStaggers($view);
        drawInkLines();
        wireHome();
        // Re-measure once webfonts arrive: label widths shift when the
        // serif face replaces the fallback, and the line gap must follow.
        document.fonts.ready.then(() => drawInkLines());
      }

      if (isCat) {
        openStratum(target);
        setTimeout(() => {
          document.getElementById('stratum-' + target)?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 80);
      } else if (target === 'works') {
        document.getElementById('writing-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else if (target === 'experience') {
        document.getElementById('experience-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else if (target === 'contact') {
        document.getElementById('contact-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
      } else {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }

    function renderHome() {
      const s = MANIFEST.site || {};
      const bioParas = (s.bio || []).map(p => `<p class="bio-para">${escapeHtml(p)}</p>`).join('');
      const eduRows = (s.education || []).map(e => `
        <div class="edu-year">${escapeHtml(e.year)}</div>
        <div class="edu-info">
          <div><span class="school">${escapeHtml(e.school)}</span><span class="where">${escapeHtml(e.where || '')}</span></div>
          <div class="detail">${escapeHtml(e.detail || '')}</div>
        </div>
      `).join('');
      const expRows = (s.experience || []).map((e, idx) => {
        const isCurrent = idx === 0;
        return `
        <li class="exp-item${isCurrent ? ' current' : ''}">
          <div class="exp-year">${escapeHtml(e.year)}</div>
          <div class="exp-org">${escapeHtml(e.org)}${e.where ? `<span class="exp-where">${escapeHtml(e.where)}</span>` : ''}</div>
          ${e.role ? `<div class="exp-role">${escapeHtml(e.role)}</div>` : ''}
          ${(e.highlights && e.highlights.length) ? `<ul>${e.highlights.map(h => `<li>${escapeHtml(h)}</li>`).join('')}</ul>` : ''}
        </li>`;
      }).join('');
      const photoStyle = s.photo ? `style="background-image:url('${escapeHtml(s.photo)}')"` : '';
      const photoClass = s.photo ? '' : 'placeholder';

      const cats = (MANIFEST.categories || []).filter(c => MANIFEST.works.some(w => w.category === c.id));
      const labelPos = ['12%', '44%', '72%'];
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
              <path class="ink main" d="" />
              <path class="ink echo" d="" />
            </svg>
            <span class="stratum-label" style="left:${labelPos[ci % labelPos.length]}">
              ${escapeHtml(c.label)}<span class="count">${items.length}</span>
            </span>
          </button>
        </section>`;
      }).join('');

      const contact = MANIFEST.site.contact || {};
      const contactRows = Object.entries(contact).map(([k, v]) => `
        <div class="contact-row">
          <div class="label">${escapeHtml(k)}</div>
          <div class="value" data-copy="${escapeHtml(v)}">${escapeHtml(v)}</div>
        </div>
      `).join('');

      $view.innerHTML = `
        <div class="bio-page" id="home-root">
          <div class="fade-stagger">
            <div class="bio-hero">
              <div class="bio-portrait ${photoClass}" ${photoStyle}></div>
              <div class="bio-content fade-stagger">
                <h1>${escapeHtml(s.title || '周未')}<span class="en">${escapeHtml(s.name_en || 'ZHOU WEI')}</span></h1>
                ${s.tagline ? `<p class="bio-tagline">${escapeHtml(s.tagline)}</p>` : ''}
                ${bioParas}
              </div>
            </div>
            ${eduRows ? `
            <section class="bio-section">
              <h2>Education · 教育</h2>
              <div class="edu-list">${eduRows}</div>
            </section>` : ''}
            ${expRows ? `
            <section class="bio-section" id="experience-section">
              <h2>Experience · 实习经历</h2>
              <ol class="exp-list">${expRows}</ol>
            </section>` : ''}
            <section class="bio-section" id="writing-section">
              <h2>Writing · 写作</h2>
              <p class="strata-hint">点击墨线，翻开每一层</p>
              <div class="strata">${strataHTML}</div>
            </section>
            <section class="bio-section" id="contact-section">
              <h2>Contact · 联系</h2>
              <div class="contact-list">${contactRows}</div>
            </section>
          </div>
        </div>
      `;
    }

    // Hand-drawn ink line generator with an optional gap (for the label).
    // Draws two segments: [0, gapStart] and [gapEnd, 1000], easing the line
    // toward the label's baseline at the gap edges so text feels "threaded".
    function inkPathD(seed, amp, gapStart, gapEnd) {
      let rnd = seed;
      const rand = () => { rnd = (rnd * 9301 + 49297) % 233280; return rnd / 233280 - 0.5; };
      const segs = [];
      if (gapStart == null || gapEnd == null || gapEnd <= gapStart) {
        segs.push([0, 1000]);
      } else {
        if (gapStart > 8) segs.push([0, gapStart]);
        if (gapEnd < 992) segs.push([gapEnd, 1000]);
      }
      let d = '';
      for (const [x0, x1] of segs) {
        const len = x1 - x0;
        const steps = Math.max(4, Math.round(len / 55));
        const pts = [];
        for (let i = 0; i <= steps; i++) {
          const x = x0 + len * i / steps;
          // Flatten noise near gap edges so the line "settles" beside the text.
          const nearGap = Math.min(
            gapStart != null ? Math.abs(x - gapStart) : 1e9,
            gapEnd != null ? Math.abs(x - gapEnd) : 1e9
          );
          const damp = nearGap < 70 ? nearGap / 70 : 1;
          pts.push([x, 22 + rand() * amp * damp]);
        }
        d += ` M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`;
        for (let i = 1; i < pts.length - 1; i++) {
          const mx = (pts[i][0] + pts[i + 1][0]) / 2;
          const my = (pts[i][1] + pts[i + 1][1]) / 2;
          d += ` Q${pts[i][0].toFixed(1)},${pts[i][1].toFixed(1)} ${mx.toFixed(1)},${my.toFixed(1)}`;
        }
        const last = pts[pts.length - 1];
        d += ` L${last[0].toFixed(1)},${last[1].toFixed(1)}`;
      }
      return d.trim();
    }

    function drawInkLines() {
      document.querySelectorAll('.stratum').forEach((st, i) => {
        const line = st.querySelector('.stratum-line');
        const label = st.querySelector('.stratum-label');
        const main = st.querySelector('path.main');
        const echo = st.querySelector('path.echo');
        if (!line || !label || !main) return;
        const W = line.clientWidth || 1000;
        const lr = label.getBoundingClientRect();
        const cr = line.getBoundingClientRect();
        const pad = 20;
        const gapStart = Math.max(0, ((lr.left - cr.left - pad) / W) * 1000);
        const gapEnd = Math.min(1000, ((lr.right - cr.left + pad) / W) * 1000);
        const seed = 7919 * (i + 1);
        main.setAttribute('d', inkPathD(seed, 12, gapStart, gapEnd));
        if (echo) echo.setAttribute('d', inkPathD(seed + 431, 16, gapStart, gapEnd));
      });
    }

    let inkResizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(inkResizeTimer);
      inkResizeTimer = setTimeout(() => {
        if (document.getElementById('home-root')) drawInkLines();
      }, 120);
    });

    function openStratum(catId) {
      document.querySelectorAll('.stratum').forEach(st => {
        const open = st.dataset.cat === catId;
        st.classList.toggle('open', open);
        st.querySelector('.stratum-line')?.setAttribute('aria-expanded', open ? 'true' : 'false');
      });
    }

    function wireHome() {
      document.querySelectorAll('.stratum-line').forEach(btn => {
        btn.addEventListener('click', () => {
          const st = btn.closest('.stratum');
          const catId = st.dataset.cat;
          const willOpen = !st.classList.contains('open');
          openStratum(willOpen ? catId : null);
          if (willOpen) {
            setActiveNav(catId);
            history.replaceState(null, '', '#/' + catId);
            setTimeout(() => st.scrollIntoView({ behavior: 'smooth', block: 'center' }), 80);
          } else {
            setActiveNav('bio');
            history.replaceState(null, '', '#/');
          }
        });
      });
      document.querySelectorAll('#home-root .contact-row .value').forEach(el => {
        el.addEventListener('click', () => {
          navigator.clipboard.writeText(el.dataset.copy);
          el.classList.add('copied');
          setTimeout(() => el.classList.remove('copied'), 1500);
        });
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

    // ---- READER ----
    function showRead(id) {
      const work = MANIFEST.works.find(w => w.id === id);
      if (!work) { location.hash = '#/'; return; }
      setActiveNav(work.category);
      document.title = work.title;

      const cat = (MANIFEST.categories || []).find(c => c.id === work.category);
      const by = BYLINE[work.category] || BYLINE.creative;
      const bylineText = (by.prefix || '') + '周未' + (by.suffix || '');

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

      $view.innerHTML = `
        <article class="reader reader-variant-${work.category} fade-stagger">
          <a class="back" href="#/${work.category || ''}">← back</a>
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
            ${paragraphs.map(p => `<p class="para">${escapeHtml(p)}</p>`).join('')}
          </div>
          <div class="reader-end">— Fin —</div>
        </article>
      `;
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
  </script>
</body>
</html>
'''

html = TEMPLATE
html = html.replace('__MANIFEST_JSON__', json.dumps(manifest, ensure_ascii=False))
html = html.replace('__WORKS_JSON__', json.dumps(works_text, ensure_ascii=False))
OUT.write_text(html, encoding='utf-8')

size_kb = OUT.stat().st_size / 1024
print(f'✓ 已生成 {OUT.name}（{size_kb:.1f} KB）')
print(f'  路径：{OUT}')
print(f'  共打包 {len(works_text)} 篇作品')
print(f'  双击打开即可。')
