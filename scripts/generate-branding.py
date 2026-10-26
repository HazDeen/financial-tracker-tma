#!/usr/bin/env python3
"""Generate web and Android vector marks from branding/mark.json (standard library only)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
mark = json.loads((ROOT / 'branding/mark.json').read_text())
paths = ''.join(f'<path d="{p["d"]}" stroke="{p["stroke"]}" stroke-width="{p["width"]}" stroke-linecap="round" stroke-linejoin="round"/>' for p in mark['paths'])
svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96" viewBox="0 0 96 96" fill="none"><rect width="96" height="96" rx="25" fill="{mark["background"]}"/>{paths}</svg>\n'
for name in ['branding/logo.svg', 'frontend/public/brand-mark.svg', 'frontend/public/favicon.svg']:
    (ROOT / name).write_text(svg)

res = ROOT / 'android/app/src/main/res'

def vector(viewport, content):
    return f'<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="{viewport}dp" android:height="{viewport}dp" android:viewportWidth="{viewport}" android:viewportHeight="{viewport}">{content}</vector>\n'

def android_paths(monochrome=False):
    return ''.join(f'<path android:pathData="{p["d"]}" android:fillColor="#00000000" android:strokeColor="{p["stroke"] if not monochrome else "#FFFFFF"}" android:strokeWidth="{p["width"]}" android:strokeLineCap="round" android:strokeLineJoin="round"/>' for p in mark['paths'])

(res / 'drawable/ic_finance.xml').write_text(vector(96, f'<path android:fillColor="{mark["background"]}" android:pathData="M25 0H71Q96 0 96 25V71Q96 96 71 96H25Q0 96 0 71V25Q0 0 25 0Z"/>' + android_paths()))
# Keep the complete mark within the adaptive icon's central safe region.
for suffix, mono in [('foreground', False), ('monochrome', True)]:
    (res / f'drawable/ic_finance_{suffix}.xml').write_text(vector(108, '<group android:translateX="6" android:translateY="6">' + android_paths(mono) + '</group>'))
(res / 'values/brand.xml').write_text(f'<resources><color name="brand_blue">{mark["background"]}</color></resources>\n')
for folder, monochrome in [('mipmap-anydpi-v26', ''), ('mipmap-anydpi-v33', '<monochrome android:drawable="@drawable/ic_finance_monochrome"/>')]:
    (res / folder).mkdir(exist_ok=True)
    (res / folder / 'ic_launcher.xml').write_text('<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android"><background android:drawable="@color/brand_blue"/><foreground android:drawable="@drawable/ic_finance_foreground"/>' + monochrome + '</adaptive-icon>\n')
print('Web and Android vector logos generated from branding/mark.json')
