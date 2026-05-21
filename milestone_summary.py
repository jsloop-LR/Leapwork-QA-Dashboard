#!/usr/bin/env python3
"""
netFLEX Milestone Summary Generator
Usage: python3 milestone_summary.py 5.4.0
Generates a grouped HTML report of ALL issues (open + closed) for a milestone.
"""

import json
import subprocess
import sys
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import defaultdict

REPO = "lightriversoftware/netflex"

def run_gh(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        return None
    return result.stdout

def fetch_milestone_number(milestone_title):
    output = run_gh(f'gh api repos/{REPO}/milestones --jq \'.[] | select(.title == "{milestone_title}") | .number\'')
    if not output or not output.strip():
        print(f"Milestone '{milestone_title}' not found.")
        sys.exit(1)
    return output.strip()

def fetch_issues(milestone_title):
    print(f"Fetching all issues for milestone: {milestone_title}...")
    cmd = f'gh issue list --repo {REPO} --milestone "{milestone_title}" --state all --limit 1000 --json number,title,state,labels,assignees,createdAt,url'
    output = run_gh(cmd)
    if not output:
        return []
    issues = json.loads(output)
    print(f"Found {len(issues)} issues.")
    return issues

def categorize(issues):
    groups = defaultdict(list)
    for i in issues:
        t = i['title'].lower()
        if 'nokia' in t or '1830' in t:
            groups['Nokia 1830'].append(i)
        elif 'infinera' in t or 'gx' in t or 'dtn' in t or 'otdr' in t:
            groups['Infinera'].append(i)
        elif 'ciena' in t or '6500' in t or 'ome' in t:
            groups['Ciena 6500'].append(i)
        elif 'att' in t or 'cem' in t or 'royal' in t or 'uvn' in t or 'epm' in t or 'cnm' in t:
            groups['ATT / CEM'].append(i)
        elif any(k in t for k in ['praetorian','penetrat','rce','injection','lockout','suid','cleartext','privilege escalat','brute']):
            groups['Security / Pen Test'].append(i)
        elif 'rdb' in t:
            groups['RDB Enhancements'].append(i)
        elif '[qa]' in t:
            groups['QA'].append(i)
        elif '[doc]' in t or 'document' in t or 'release note' in t:
            groups['Documentation'].append(i)
        elif 'charter' in t:
            groups['Charter'].append(i)
        elif 'lumen' in t:
            groups['Lumen'].append(i)
        elif 'disa' in t:
            groups['DISA'].append(i)
        elif 'fujitsu' in t or '1finity' in t:
            groups['Fujitsu'].append(i)
        elif 'huawei' in t:
            groups['Huawei'].append(i)
        else:
            groups['Core / DEV'].append(i)
    return groups

def generate_html(milestone_title, issues, groups):
    open_total = sum(1 for i in issues if i['state'].lower() == 'open')
    closed_total = sum(1 for i in issues if i['state'].lower() == 'closed')
    now = datetime.now(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d %H:%M %Z')

    # Build summary table rows
    summary_rows = ''
    for group, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        open_c = sum(1 for i in items if i['state'].lower() == 'open')
        closed_c = sum(1 for i in items if i['state'].lower() == 'closed')
        pct = int((closed_c / len(items)) * 100) if items else 0
        summary_rows += f'''
        <tr onclick="showGroup('{group}')" style="cursor:pointer">
            <td><strong>{group}</strong></td>
            <td style="text-align:center">{len(items)}</td>
            <td style="text-align:center; color:#e74c3c"><strong>{open_c}</strong></td>
            <td style="text-align:center; color:#27ae60"><strong>{closed_c}</strong></td>
            <td>
                <div style="background:#eee;border-radius:4px;height:18px;width:100%">
                    <div style="background:#27ae60;height:18px;border-radius:4px;width:{pct}%"></div>
                </div>
                <span style="font-size:11px">{pct}% done</span>
            </td>
        </tr>'''

    # Build detail sections
    detail_sections = ''
    for group, items in sorted(groups.items(), key=lambda x: -len(x[1])):
        open_c = sum(1 for i in items if i['state'].lower() == 'open')
        closed_c = sum(1 for i in items if i['state'].lower() == 'closed')
        rows = ''
        for i in sorted(items, key=lambda x: x['number']):
            state = i['state'].upper()
            state_color = '#27ae60' if state == 'CLOSED' else '#e74c3c'
            state_bg = '#d5f5e3' if state == 'CLOSED' else '#fde8e8'
            assignees = ', '.join(a['login'] for a in i['assignees']) or 'unassigned'
            labels = ', '.join(l['name'] for l in i['labels'])
            rows += f'''
            <tr>
                <td><a href="{i['url']}" target="_blank" style="color:#2980b9;text-decoration:none">#{i['number']}</a></td>
                <td>{i['title']}</td>
                <td><span style="background:{state_bg};color:{state_color};padding:2px 8px;border-radius:4px;font-size:12px;font-weight:bold">{state}</span></td>
                <td style="font-size:12px;color:#666">{assignees}</td>
                <td style="font-size:11px;color:#999">{labels}</td>
            </tr>'''

        safe_group = group.replace('/', '-').replace(' ', '_')
        detail_sections += f'''
        <div id="group-{safe_group}" class="group-section" style="display:none">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:15px">
                <h2 style="color:#2c3e50;margin:0">{group} <span style="font-size:16px;color:#666">({len(items)} issues)</span></h2>
                <div>
                    <span style="background:#fde8e8;color:#e74c3c;padding:4px 12px;border-radius:4px;margin-right:8px">{open_c} Open</span>
                    <span style="background:#d5f5e3;color:#27ae60;padding:4px 12px;border-radius:4px">{closed_c} Closed</span>
                </div>
            </div>
            <table style="width:100%;border-collapse:collapse;background:white;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.1)">
                <thead>
                    <tr style="background:#2c3e50;color:white">
                        <th style="padding:10px;text-align:left;width:60px">#</th>
                        <th style="padding:10px;text-align:left">Title</th>
                        <th style="padding:10px;text-align:left;width:80px">State</th>
                        <th style="padding:10px;text-align:left;width:140px">Assignee</th>
                        <th style="padding:10px;text-align:left;width:160px">Labels</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <br>
            <button onclick="showSummary()" style="background:#2c3e50;color:white;border:none;padding:8px 20px;border-radius:4px;cursor:pointer">← Back to Summary</button>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>netFLEX {milestone_title} Milestone Summary</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#f0f2f5; margin:0; padding:20px; color:#333; }}
        .container {{ max-width:1200px; margin:0 auto; background:white; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.1); overflow:hidden; }}
        header {{ background:linear-gradient(135deg,#2c3e50,#3498db); color:white; padding:40px; text-align:center; }}
        header h1 {{ margin:0 0 10px; font-size:2.2em; }}
        .stats {{ display:flex; justify-content:center; gap:30px; margin:10px 0; }}
        .stat {{ text-align:center; }}
        .stat-num {{ font-size:2.5em; font-weight:bold; }}
        .stat-lbl {{ font-size:0.85em; opacity:0.85; }}
        .content {{ padding:30px; }}
        .summary-table {{ width:100%; border-collapse:collapse; margin-bottom:20px; }}
        .summary-table th {{ background:#2c3e50; color:white; padding:12px; text-align:left; }}
        .summary-table td {{ padding:10px 12px; border-bottom:1px solid #eee; }}
        .summary-table tr:hover td {{ background:#f8f9fa; }}
        .group-section tr:nth-child(even) {{ background:#f8f9fa; }}
        .group-section td {{ padding:10px 12px; border-bottom:1px solid #eee; vertical-align:top; }}
        .updated {{ text-align:center; color:rgba(255,255,255,0.8); font-size:13px; margin-top:8px; }}
    </style>
</head>
<body>
<div class="container">
    <header>
        <h1>netFLEX {milestone_title} Milestone</h1>
        <p style="margin:0;opacity:0.9">Complete Issue Summary — Open &amp; Closed</p>
        <div class="stats">
            <div class="stat"><div class="stat-num">{len(issues)}</div><div class="stat-lbl">Total</div></div>
            <div class="stat"><div class="stat-num" style="color:#ff6b6b">{open_total}</div><div class="stat-lbl">Open</div></div>
            <div class="stat"><div class="stat-num" style="color:#51cf66">{closed_total}</div><div class="stat-lbl">Closed</div></div>
        </div>
        <div class="updated">Generated: {now}</div>
    </header>

    <div class="content">
        <!-- Summary View -->
        <div id="summary-view">
            <p style="color:#666;margin-bottom:15px">Click any row to drill into that area.</p>
            <table class="summary-table">
                <thead>
                    <tr>
                        <th>Area</th>
                        <th style="text-align:center">Total</th>
                        <th style="text-align:center">Open</th>
                        <th style="text-align:center">Closed</th>
                        <th style="width:200px">Progress</th>
                    </tr>
                </thead>
                <tbody>{summary_rows}</tbody>
            </table>
        </div>

        <!-- Detail Views -->
        {detail_sections}
    </div>
</div>

<script>
function showGroup(group) {{
    document.getElementById('summary-view').style.display = 'none';
    document.querySelectorAll('.group-section').forEach(s => s.style.display = 'none');
    const safe = group.replace(/[/]/g, '-').replace(/ /g, '_');
    const el = document.getElementById('group-' + safe);
    if (el) el.style.display = 'block';
    window.scrollTo(0, 0);
}}
function showSummary() {{
    document.querySelectorAll('.group-section').forEach(s => s.style.display = 'none');
    document.getElementById('summary-view').style.display = 'block';
    window.scrollTo(0, 0);
}}
</script>
</body>
</html>'''
    return html

def main():
    milestone = sys.argv[1] if len(sys.argv) > 1 else '5.4.0'
    issues = fetch_issues(milestone)
    if not issues:
        print("No issues found.")
        return

    groups = categorize(issues)
    html = generate_html(milestone, issues, groups)

    outfile = f'/mnt/c/Users/JimmySloop/netFLEX_{milestone.replace(".", "_")}_Milestone_Summary.html'
    with open(outfile, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"✅ Saved: {outfile}")

    # Open in browser
    win_path = outfile.replace('/mnt/c/', 'C:\\').replace('/', '\\')
    subprocess.run(f'powershell.exe -Command "Start-Process \'{win_path}\'"', shell=True)

if __name__ == '__main__':
    main()
