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
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&family=Noto+Serif+SC:wght@300;400;500;700&display=swap" rel="stylesheet">
  <style>
    :root[data-theme="dark"] {
      --bg: #0c0c0c;
      --surface: #161616;
      --ink: #e8e4dc;
      --muted: #808080;
      --rule: #1f1f1f;
      --hover: #ffffff;
    }
    :root[data-theme="light"] {
      --bg: #f7f5f0;
      --surface: #efece4;
      --ink: #1a1714;
      --muted: #8a8278;
      --rule: #d8d4cb;
      --hover: #000;
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
      .char { transform: none !important; }
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
      padding: 22px 40px;
      background: color-mix(in srgb, var(--bg) 90%, transparent);
      backdrop-filter: blur(10px);
      border-bottom: 1px solid var(--rule);
      font-size: 12px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }
    .topbar .brand {
      font-weight: 700;
      letter-spacing: 0.24em;
      transition: opacity 180ms var(--ease-out), transform 140ms var(--ease-out);
    }
    .topbar .brand:active { transform: scale(0.97); }
    @media (hover: hover) and (pointer: fine) {
      .topbar .brand:hover { opacity: 0.7; }
    }
    .topbar nav {
      display: flex;
      align-items: center;
      gap: 36px;
    }
    .topbar nav a {
      color: var(--muted);
      transition: color 180ms var(--ease-out), transform 140ms var(--ease-out);
      font-weight: 400;
    }
    .topbar nav a.active { color: var(--hover); }
    .topbar nav a:active { transform: scale(0.96); }
    @media (hover: hover) and (pointer: fine) {
      .topbar nav a:hover { color: var(--hover); }
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
    .bio-page { padding: 80px 40px 120px; max-width: 1200px; margin: 0 auto; }
    .bio-hero {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 80px;
      align-items: start;
      margin-bottom: 120px;
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
      font-size: 38px;
      font-weight: 600;
      margin: 0 0 18px;
      letter-spacing: -0.005em;
      line-height: 1.15;
    }
    .bio-content h1 .en {
      display: block;
      font-size: 18px;
      font-weight: 400;
      color: var(--muted);
      letter-spacing: 0.25em;
      margin-top: 14px;
      text-transform: uppercase;
    }
    .bio-content .bio-para {
      font-size: 15.5px;
      line-height: 1.75;
      color: color-mix(in srgb, var(--ink) 90%, transparent);
      margin: 0 0 16px;
      max-width: 480px;
    }
    .bio-content .bio-para:last-child { margin-bottom: 0; }

    .bio-section {
      border-top: 1px solid var(--rule);
      padding-top: 56px;
      margin-bottom: 80px;
    }
    .bio-section h2 {
      font-size: 22px;
      font-weight: 600;
      margin: 0 0 36px;
      letter-spacing: -0.005em;
    }
    .edu-list {
      display: grid;
      grid-template-columns: 80px 1fr;
      row-gap: 24px;
      column-gap: 40px;
    }
    .edu-year { color: var(--muted); font-size: 13px; letter-spacing: 0.04em; padding-top: 2px; }
    .edu-info .school { font-weight: 600; font-size: 15px; }
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
    .cat-page { padding: 80px 40px 120px; max-width: 1100px; margin: 0 auto; }
    .cat-page h1 {
      font-size: 48px;
      font-weight: 600;
      margin: 0 0 8px;
      letter-spacing: -0.015em;
    }
    .cat-page .cat-sub {
      color: var(--muted);
      font-size: 13px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      margin: 0 0 56px;
    }
    /* =============== COVERFLOW (curved 3D carousel) =============== */
    .coverflow { margin-top: 32px; }
    .cf-stage {
      position: relative;
      height: 420px;
      perspective: 1800px;
      perspective-origin: 50% 55%;
      overflow: hidden;
      cursor: grab;
    }
    .cf-stage:active { cursor: grabbing; }
    .cf-track {
      position: absolute;
      inset: 0;
      transform-style: preserve-3d;
    }
    .cf-card {
      position: absolute;
      top: 50%;
      left: 50%;
      width: 220px;
      height: 300px;
      margin: -150px 0 0 -110px;
      border-radius: 16px;
      overflow: hidden;
      cursor: pointer;
      transition: transform 520ms var(--ease-spring), box-shadow 320ms var(--ease-out);
      transform-style: preserve-3d;
      will-change: transform;
      box-shadow:
        0 18px 50px rgba(0,0,0,0.45),
        0 4px 16px rgba(0,0,0,0.35),
        0 0 0 1px rgba(255,255,255,0.04) inset;
    }
    .cf-card.active {
      box-shadow:
        0 32px 80px rgba(0,0,0,0.55),
        0 8px 24px rgba(0,0,0,0.4),
        0 0 0 1px rgba(255,255,255,0.06) inset;
    }
    .cf-cover {
      position: absolute;
      inset: 0;
      background-size: cover;
      background-position: center;
      background-color: var(--surface);
    }
    .cf-cover::after {
      content: '';
      position: absolute;
      inset: 0;
      background: linear-gradient(115deg,
        rgba(255,255,255,0.08) 0%,
        rgba(255,255,255,0) 30%,
        rgba(0,0,0,0) 70%,
        rgba(0,0,0,0.35) 100%);
      pointer-events: none;
      transition: opacity 320ms var(--ease-out);
    }
    .cf-card.active .cf-cover::after { opacity: 0.5; }
    /* subtle glow under the active card */
    .cf-card.active::before {
      content: '';
      position: absolute;
      left: 50%;
      bottom: -28px;
      width: 80%;
      height: 18px;
      transform: translateX(-50%);
      background: radial-gradient(ellipse at center, rgba(0,0,0,0.5), transparent 70%);
      filter: blur(8px);
      pointer-events: none;
    }

    .cf-meta {
      text-align: center;
      margin-top: 40px;
      min-height: 140px;
      transition: opacity 220ms var(--ease-out), transform 320ms var(--ease-spring);
    }
    .cf-meta.swap { opacity: 0; transform: translateY(6px); }
    .cf-meta h2 {
      font-size: 26px;
      font-weight: 600;
      line-height: 1.3;
      margin: 0 0 10px;
      letter-spacing: -0.005em;
    }
    .cf-meta .year {
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.24em;
      text-transform: uppercase;
      margin: 0 0 16px;
    }
    .cf-meta .desc {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.7;
      max-width: 560px;
      margin: 0 auto 24px;
    }
    .cf-meta .read-link {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      letter-spacing: 0.22em;
      text-transform: uppercase;
      color: var(--ink);
      border-bottom: 1px solid var(--ink);
      padding-bottom: 3px;
      transition: gap 220ms var(--ease-out), transform 140ms var(--ease-out), opacity 180ms var(--ease-out);
    }
    .cf-meta .read-link:active { transform: scale(0.97); }
    @media (hover: hover) and (pointer: fine) {
      .cf-meta .read-link:hover { gap: 14px; }
    }

    /* tiny dot indicators below */
    .cf-dots {
      display: flex;
      justify-content: center;
      gap: 10px;
      margin-top: 28px;
    }
    .cf-dot {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: var(--rule);
      cursor: pointer;
      transition: background 200ms var(--ease-out), transform 200ms var(--ease-out);
      border: none;
      padding: 0;
    }
    .cf-dot.active { background: var(--ink); transform: scale(1.4); }
    .cf-dot:active { transform: scale(1.1); }

    @media (max-width: 700px) {
      .cf-stage { height: 340px; }
      .cf-card { width: 170px; height: 235px; margin: -117px 0 0 -85px; }
      .cf-meta h2 { font-size: 22px; }
    }

    /* =============== READER =============== */
    .reader { max-width: 720px; margin: 0 auto; padding: 80px 40px 140px; position: relative; }
    .reader .back {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.2em;
      text-transform: uppercase;
      margin-bottom: 56px;
      transition: color 180ms var(--ease-out), transform 140ms var(--ease-out), gap 220ms var(--ease-out);
    }
    .reader .back:active { transform: scale(0.97); }
    @media (hover: hover) and (pointer: fine) {
      .reader .back:hover { color: var(--hover); gap: 12px; }
    }
    .reader .cat-tag {
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.25em;
      text-transform: uppercase;
      margin-bottom: 18px;
    }
    .reader h1.headline {
      font-family: 'Noto Serif SC', 'Inter', serif;
      font-size: 32px;
      font-weight: 500;
      line-height: 1.35;
      margin: 0 0 14px;
      letter-spacing: 0.005em;
    }
    .reader .lede {
      font-family: 'Noto Serif SC', 'Inter', serif;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.75;
      margin: 0 0 16px;
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
      padding: 24px 26px;
      border: 1px solid var(--rule);
      background: color-mix(in srgb, var(--surface) 60%, transparent);
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

    .reader-body {
      font-family: 'Noto Serif SC', 'Inter', serif;
      font-size: 17px;
      line-height: 1.95;
      color: var(--ink);
    }
    .reader-body .para {
      margin: 0 0 1.1em;
    }
    .char {
      display: inline-block;
      transition: transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
      will-change: transform;
    }
    .reader-end {
      margin-top: 80px;
      text-align: center;
      color: var(--muted);
      font-size: 11px;
      letter-spacing: 0.4em;
    }

    /* =============== CONTACT =============== */
    .contact-page { padding: 120px 40px; max-width: 720px; margin: 0 auto; }
    .contact-page h1 {
      font-size: 56px;
      font-weight: 600;
      margin: 0 0 56px;
      letter-spacing: -0.02em;
      line-height: 1.1;
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
      .topbar { padding: 16px 20px; gap: 16px; }
      .topbar nav { gap: 18px; }
      .bio-hero { grid-template-columns: 1fr; gap: 40px; }
      .bio-portrait { max-width: 360px; }
      .bio-content h1 { font-size: 32px; }
      .cat-page h1 { font-size: 36px; }
      .reader { padding: 56px 24px 100px; }
    }
    @media (max-width: 600px) {
      .topbar nav a { display: none; }
      .topbar nav a.theme-toggle, .topbar nav .menu-btn { display: inline-flex; }
      .topbar.menu-open nav a { display: inline-flex; }
      .topbar.menu-open { flex-wrap: wrap; }
      .topbar.menu-open nav { width: 100%; flex-direction: column; align-items: flex-start; gap: 16px; padding: 16px 0; }
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
      const cats = (MANIFEST.categories || []).map(c =>
        `<a href="#/${c.id}" data-route="${c.id}">${escapeHtml(c.label)}</a>`
      ).join('');
      $nav.innerHTML = `
        <a href="#/" data-route="bio">Bio</a>
        ${cats}
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
      if (m) showRead(decodeURIComponent(m[1]));
      else {
        const tail = h.slice(2);
        if (!tail || tail === 'bio') showBio();
        else if (tail === 'contact') showContact();
        else {
          const cat = (MANIFEST.categories || []).find(c => c.id === tail);
          if (cat) showCategory(cat);
          else showBio();
        }
      }
      mountStaggers($view);
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

    window.addEventListener('hashchange', () => { window.scrollTo(0, 0); route(); });
    route();

    // ---- BIO ----
    function showBio() {
      setActiveNav('bio');
      document.title = (MANIFEST.site.title || '周未');
      const s = MANIFEST.site || {};
      const bioParas = (s.bio || []).map(p => `<p class="bio-para">${escapeHtml(p)}</p>`).join('');
      const eduRows = (s.education || []).map(e => `
        <div class="edu-year">${escapeHtml(e.year)}</div>
        <div class="edu-info">
          <div><span class="school">${escapeHtml(e.school)}</span><span class="where">${escapeHtml(e.where || '')}</span></div>
          <div class="detail">${escapeHtml(e.detail || '')}</div>
        </div>
      `).join('');
      const today = new Date();
      const expRows = (s.experience || []).map((e, idx) => {
        const isCurrent = idx === 0; // first/newest entry gets filled marker
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

      $view.innerHTML = `
        <div class="bio-page fade-stagger">
          <div class="bio-hero">
            <div class="bio-portrait ${photoClass}" ${photoStyle}></div>
            <div class="bio-content fade-stagger">
              <h1>${escapeHtml(s.title || '周未')}<span class="en">${escapeHtml(s.name_en || 'ZHOU WEI')}</span></h1>
              ${bioParas}
            </div>
          </div>
          ${eduRows ? `
          <section class="bio-section">
            <h2>Education · 教育</h2>
            <div class="edu-list">${eduRows}</div>
          </section>` : ''}
          ${expRows ? `
          <section class="bio-section">
            <h2>Experience · 实习经历</h2>
            <ol class="exp-list">${expRows}</ol>
          </section>` : ''}
          ${cats.length ? `
          <section class="bio-section">
            <h2>Selected Writing · 写作</h2>
            <div class="edu-list">
              ${cats.map(c => `
                <div class="edu-year"></div>
                <div class="edu-info">
                  <div><a href="#/${c.id}" class="school" style="text-decoration:underline;text-decoration-color:var(--rule);text-underline-offset:4px">${escapeHtml(c.label)}</a></div>
                  <div class="detail">${MANIFEST.works.filter(w => w.category === c.id).length} 篇</div>
                </div>
              `).join('')}
            </div>
          </section>` : ''}
        </div>
      `;
    }

    // ---- CATEGORY ----
    function showCategory(cat) {
      setActiveNav(cat.id);
      document.title = cat.label + ' · ' + (MANIFEST.site.title || '周未');
      const items = MANIFEST.works.filter(w => w.category === cat.id);
      if (!items.length) {
        $view.innerHTML = `<div class="cat-page fade-stagger">
          <h1>${escapeHtml(cat.label)}</h1>
          <p style="color:var(--muted);font-style:italic;margin-top:24px">尚无作品</p>
        </div>`;
        return;
      }

      const cardsHTML = items.map((w, i) => {
        const bg = w.cover
          ? `background-image:url('${w.cover}')`
          : `background: linear-gradient(135deg, ${w.color || '#2a2a2a'}, ${shadeColor(w.color || '#2a2a2a', -30)})`;
        return `<a class="cf-card" data-i="${i}" href="#/read/${encodeURIComponent(w.id)}" aria-label="${escapeHtml(w.title)}">
          <div class="cf-cover" style="${bg}"></div>
        </a>`;
      }).join('');

      const dotsHTML = items.map((_, i) => `<button class="cf-dot" data-i="${i}" aria-label="第 ${i+1} 篇"></button>`).join('');

      $view.innerHTML = `
        <div class="cat-page fade-stagger">
          <h1>${escapeHtml(cat.label)}</h1>
          <p class="cat-sub">${items.length} pieces · hover or use ← →</p>
          <div class="coverflow">
            <div class="cf-stage" id="cf-stage">
              <div class="cf-track" id="cf-track">${cardsHTML}</div>
            </div>
            <div class="cf-meta" id="cf-meta">
              <h2 id="cf-title"></h2>
              <p class="year" id="cf-year"></p>
              <p class="desc" id="cf-desc"></p>
              <a class="read-link" id="cf-link" href="#">Read piece →</a>
            </div>
            <div class="cf-dots">${dotsHTML}</div>
          </div>
        </div>
      `;

      const $stage = document.getElementById('cf-stage');
      const $meta = document.getElementById('cf-meta');
      const $title = document.getElementById('cf-title');
      const $year = document.getElementById('cf-year');
      const $desc = document.getElementById('cf-desc');
      const $link = document.getElementById('cf-link');
      const cards = [...document.querySelectorAll('.cf-card')];
      const dots = [...document.querySelectorAll('.cf-dot')];

      let active = 0;
      let metaTimer = null;

      function layout(i) {
        if (i < 0) i = 0;
        if (i >= items.length) i = items.length - 1;
        if (i === active && cards[i]?.classList.contains('active')) return;
        active = i;
        cards.forEach((card, j) => {
          const o = j - i;
          const abs = Math.abs(o);
          const sign = Math.sign(o);
          let x, z, ry, zi;
          if (abs === 0) {
            x = 0; z = 80; ry = 0; zi = 100;
          } else if (abs === 1) {
            x = sign * 180; z = -10; ry = sign * 42; zi = 90;
          } else if (abs === 2) {
            x = sign * 250; z = -70; ry = sign * 50; zi = 80;
          } else {
            x = sign * (290 + (abs - 3) * 30); z = -130 - (abs - 3) * 30; ry = sign * 56; zi = 80 - abs;
          }
          card.style.transform = `translate3d(${x}px, 0, ${z}px) rotateY(${ry}deg)`;
          card.style.zIndex = String(zi);
          card.classList.toggle('active', j === i);
        });
        dots.forEach((d, j) => d.classList.toggle('active', j === i));

        // Crossfade meta
        const w = items[i];
        $meta.classList.add('swap');
        clearTimeout(metaTimer);
        metaTimer = setTimeout(() => {
          $title.textContent = w.title;
          $year.textContent = w.year || '';
          $desc.textContent = w.subtitle || '';
          $link.href = '#/read/' + encodeURIComponent(w.id);
          requestAnimationFrame(() => $meta.classList.remove('swap'));
        }, 160);
      }

      cards.forEach((c, i) => {
        c.addEventListener('mouseenter', () => layout(i));
        c.addEventListener('focus', () => layout(i));
        c.addEventListener('click', (e) => {
          // If not yet active, intercept first click to bring to center
          if (active !== i) { e.preventDefault(); layout(i); }
        });
      });
      dots.forEach((d, i) => d.addEventListener('click', () => layout(i)));

      // Keyboard arrows when stage in focus area
      function onKey(e) {
        if (e.key === 'ArrowLeft')  { e.preventDefault(); layout(active - 1); }
        if (e.key === 'ArrowRight') { e.preventDefault(); layout(active + 1); }
      }
      $stage.tabIndex = 0;
      $stage.addEventListener('keydown', onKey);

      // Initial layout
      layout(0);
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

    // ---- CONTACT ----
    function showContact() {
      setActiveNav('contact');
      document.title = 'Contact · ' + (MANIFEST.site.title || '周未');
      const c = MANIFEST.site.contact || {};
      const rows = Object.entries(c).map(([k, v]) => `
        <div class="contact-row">
          <div class="label">${escapeHtml(k)}</div>
          <div class="value" data-copy="${escapeHtml(v)}">${escapeHtml(v)}</div>
        </div>
      `).join('');
      $view.innerHTML = `
        <div class="contact-page fade-stagger">
          <h1>Get in touch.</h1>
          <div class="contact-list fade-stagger">${rows}</div>
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
        <article class="reader fade-stagger">
          <a class="back" href="#/${work.category || ''}">← back</a>
          ${cat ? `<div class="cat-tag">${escapeHtml(cat.label)}</div>` : ''}
          <h1 class="headline">${escapeHtml(work.title)}</h1>
          ${showLede ? `<p class="lede">${escapeHtml(work.subtitle)}</p>` : ''}
          <p class="byline">${escapeHtml(bylineText)}</p>
          ${paperMeta}
          <div class="reader-body" id="reader-body">
            ${paragraphs.map(p => `<p class="para">${charsToSpans(p)}</p>`).join('')}
          </div>
          <div class="reader-end">— Fin —</div>
        </article>
      `;
      requestAnimationFrame(cacheCharPositions);
    }

    function charsToSpans(text) {
      return Array.from(text).map(c => {
        if (/\s|　/.test(c)) return escapeHtml(c);
        return `<span class="char">${escapeHtml(c)}</span>`;
      }).join('');
    }

    // ---- mouse dodge ----
    let mouseX = -99999, mouseY = -99999;
    let charCache = [];
    let rafScheduled = false;
    const DODGE_RADIUS = 95;
    const DODGE_MAX = 16;

    function cacheCharPositions() {
      charCache = [];
      const els = document.querySelectorAll('.reader-body .char');
      const sx = window.scrollX, sy = window.scrollY;
      for (const el of els) {
        const r = el.getBoundingClientRect();
        charCache.push({ el, cx: r.left + r.width/2 + sx, cy: r.top + r.height/2 + sy, dodged: false });
      }
      scheduleDodge();
    }

    function scheduleDodge() {
      if (rafScheduled) return;
      rafScheduled = true;
      requestAnimationFrame(updateDodge);
    }

    function updateDodge() {
      rafScheduled = false;
      if (!charCache.length) return;
      const r2 = DODGE_RADIUS * DODGE_RADIUS;
      const minY = window.scrollY - DODGE_RADIUS;
      const maxY = window.scrollY + window.innerHeight + DODGE_RADIUS;
      for (const c of charCache) {
        if (c.cy < minY || c.cy > maxY) {
          if (c.dodged) { c.el.style.transform = ''; c.dodged = false; }
          continue;
        }
        const dx = c.cx - mouseX, dy = c.cy - mouseY;
        const d2 = dx*dx + dy*dy;
        if (d2 > r2) {
          if (c.dodged) { c.el.style.transform = ''; c.dodged = false; }
          continue;
        }
        const d = Math.sqrt(d2) || 0.001;
        const f = 1 - d / DODGE_RADIUS;
        const push = DODGE_MAX * f * f;
        c.el.style.transform = `translate(${(dx/d*push).toFixed(2)}px, ${(dy/d*push).toFixed(2)}px)`;
        c.dodged = true;
      }
    }

    window.addEventListener('mousemove', e => { mouseX = e.pageX; mouseY = e.pageY; scheduleDodge(); });
    window.addEventListener('mouseleave', () => { mouseX = mouseY = -99999; scheduleDodge(); });
    window.addEventListener('scroll', () => {
      const max = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      $progress.style.width = (window.scrollY / max * 100) + '%';
      scheduleDodge();
    }, { passive: true });

    let resizeTimer;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (document.querySelector('.reader-body')) cacheCharPositions();
      }, 120);
    });

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
