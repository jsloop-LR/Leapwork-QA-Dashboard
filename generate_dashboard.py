#!/usr/bin/env python3
"""
Issues Dashboard Generator
Fetches issues from GitHub and generates an interactive HTML dashboard
Includes historical data from pre-GitHub Monday.com export CSV
"""

import json
import subprocess
import re
import csv
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict

# Path to the historical CSV export from Monday.com
HISTORICAL_CSV_PATH = '/mnt/c/Users/JimmySloop/Downloads/Regression_Test_Result_Failures.csv'

def run_gh_command(cmd):
    """Run a gh CLI command and return the output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"Error: {result.stderr}")
        return None
    return result.stdout

def extract_software_release(body):
    """Extract Software Release Detected from issue body"""
    if not body:
        return 'Not specified'

    # Look for "Software Release Detected" field
    match = re.search(r'Software Release Detected[:\s]*([^\n]+)', body, re.IGNORECASE)
    if match:
        release = match.group(1).strip()
        # Clean up common variations
        if release.lower() in ['none', 'n/a', '']:
            return 'Not specified'
        return release
    return 'Not specified'

def normalize_release(rel):
    """Normalize release strings to a sortable format"""
    rel = rel.strip().strip('"').strip()
    if not rel or rel in ('Release', 'Post/Pre GA', 'Not specified'):
        return None
    # Map old-style (4.x.x) and new-style (50, 51.1, etc.)
    rel = rel.replace('v', '').replace('V', '')
    return rel

def sort_release_key(rel):
    """Sort releases chronologically by parsing version numbers"""
    try:
        parts = rel.replace('-', '.').split('.')
        return tuple(int(p) for p in parts[:3] + [0]*(3-len(parts[:3])))
    except:
        return (999, 0, 0)

def load_historical_csv():
    """Load and parse historical issue data from Monday.com CSV export"""
    if not os.path.exists(HISTORICAL_CSV_PATH):
        print(f"Warning: Historical CSV not found at {HISTORICAL_CSV_PATH}")
        return []

    print(f"Loading historical data from CSV...")
    records = []
    skip_patterns = ['Regression Test Result Failures', 'Name,MR,Release',
                     'Problem Identified MR Entered', 'This spreadsheet']

    with open(HISTORICAL_CSV_PATH, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Skip header/section rows
            if any(p in line for p in skip_patterns):
                continue

            parts = line.split(',')
            if len(parts) < 5:
                continue

            name     = parts[0].strip().strip('"')
            mr       = parts[1].strip().strip('"')
            release  = parts[2].strip().strip('"')
            timing   = parts[3].strip().strip('"')   # Pre GA / Post GA
            status   = parts[4].strip().strip('"')
            found_by = parts[5].strip().strip('"') if len(parts) > 5 else ''

            # Skip rows that are clearly headers or section labels
            if name in ('Name', '') or release in ('Release', ''):
                continue
            if status not in ('MR Resolved', 'Working on it'):
                continue

            rel_norm = normalize_release(release)
            if not rel_norm:
                continue

            records.append({
                'name':     name,
                'mr':       mr,
                'release':  rel_norm,
                'timing':   timing,   # 'Pre GA' or 'Post GA'
                'status':   status,
                'found_by': found_by  # 'Leapwork' or 'Manual'
            })

    print(f"Loaded {len(records)} historical records")
    return records

def fetch_issues():
    """Fetch all issues matching your search criteria"""
    print("Fetching issues from GitHub...")
    cmd = 'gh issue list --repo lightriversoftware/netflex --state all --search "[QA] LW" --limit 2000 --json number,title,state,createdAt,updatedAt,labels,url,body'
    output = run_gh_command(cmd)

    if not output:
        return []

    issues = json.loads(output)

    # Safety filter — ensure title actually contains both QA and LW
    filtered_issues = [issue for issue in issues if 'LW' in issue['title'] and 'QA' in issue['title']]

    print(f"Found {len(filtered_issues)} issues")
    return filtered_issues

def generate_html(issues, historical=[]):
    """Generate the HTML dashboard"""

    # Calculate statistics
    open_issues = [i for i in issues if i['state'].lower() == 'open']
    closed_issues = [i for i in issues if i['state'].lower() == 'closed']

    # Issues over time
    issues_by_month = defaultdict(int)
    for issue in issues:
        date = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00'))
        month_key = date.strftime('%Y-%m')
        issues_by_month[month_key] += 1

    sorted_months = sorted(issues_by_month.items())[-12:]  # Last 12 months

    # Extract software releases and count
    releases = []
    for issue in issues:
        release = extract_software_release(issue.get('body', ''))
        releases.append(release)

    release_counts = Counter(releases)
    # Sort by count (descending) and then by release name
    sorted_releases = sorted(release_counts.items(), key=lambda x: (-x[1], x[0]))
    release_labels = [r[0] for r in sorted_releases]
    release_counts_list = [r[1] for r in sorted_releases]

    # ── Historical data processing ──
    hist_by_release   = defaultdict(int)
    hist_pre_ga       = defaultdict(int)
    hist_post_ga      = defaultdict(int)
    hist_leapwork     = defaultdict(int)
    hist_manual       = defaultdict(int)
    hist_total_lw     = 0
    hist_total_manual = 0
    hist_total_pre    = 0
    hist_total_post   = 0

    for rec in historical:
        rel = rec['release']
        hist_by_release[rel] += 1
        if rec['timing'] == 'Pre GA':
            hist_pre_ga[rel] += 1
            hist_total_pre += 1
        elif rec['timing'] == 'Post GA':
            hist_post_ga[rel] += 1
            hist_total_post += 1
        if rec['found_by'] == 'Leapwork':
            hist_leapwork[rel] += 1
            hist_total_lw += 1
        elif rec['found_by'] == 'Manual':
            hist_manual[rel] += 1
            hist_total_manual += 1

    # Combined defects per release (CSV history + GitHub live)
    combined_releases = set(hist_by_release.keys())
    for r in release_labels:
        combined_releases.add(r)
    sorted_combined = sorted(combined_releases, key=sort_release_key)

    combined_hist_counts  = [hist_by_release.get(r, 0) for r in sorted_combined]
    combined_github_counts = [release_counts.get(r, 0) for r in sorted_combined]

    # Pre/Post GA per release (sorted chronologically)
    hist_releases_sorted = sorted(hist_by_release.keys(), key=sort_release_key)
    pre_ga_counts  = [hist_pre_ga.get(r, 0)  for r in hist_releases_sorted]
    post_ga_counts = [hist_post_ga.get(r, 0) for r in hist_releases_sorted]
    lw_counts      = [hist_leapwork.get(r, 0) for r in hist_releases_sorted]
    manual_counts  = [hist_manual.get(r, 0)   for r in hist_releases_sorted]

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Issues Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .update-time {{
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
        }}
        .stats {{
            display: flex;
            justify-content: space-around;
            margin: 30px 0;
            flex-wrap: wrap;
        }}
        .stat-box {{
            text-align: center;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 8px;
            min-width: 150px;
            margin: 10px;
            cursor: pointer;
            transition: transform 0.2s;
        }}
        .stat-box:hover {{
            transform: scale(1.05);
        }}
        .stat-number {{
            font-size: 48px;
            font-weight: bold;
        }}
        .stat-label {{
            font-size: 16px;
            margin-top: 10px;
        }}
        .chart-container {{
            margin: 40px 0;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
        }}
        .chart-box {{
            width: 45%;
            min-width: 400px;
            margin: 20px 0;
        }}
        .chart-box-full {{
            width: 90%;
            min-width: 400px;
            margin: 20px auto;
        }}
        canvas {{
            max-height: 400px;
        }}
        h2 {{
            color: #555;
            margin-top: 40px;
        }}
        .issues-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
        }}
        .issues-table th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
            cursor: pointer;
            user-select: none;
            position: relative;
        }}
        .issues-table th:hover {{
            background: linear-gradient(135deg, #7889f5 0%, #8757b3 100%);
        }}
        .issues-table th::after {{
            content: ' ↕';
            opacity: 0.3;
            font-size: 12px;
        }}
        .issues-table th.sort-asc::after {{
            content: ' ↑';
            opacity: 1;
        }}
        .issues-table th.sort-desc::after {{
            content: ' ↓';
            opacity: 1;
        }}
        .issues-table td {{
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }}
        .issues-table tr:hover {{
            background-color: #f5f5f5;
        }}
        .issue-link {{
            color: #667eea;
            text-decoration: none;
            font-weight: bold;
        }}
        .issue-link:hover {{
            text-decoration: underline;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }}
        .badge-open {{
            background-color: #28a745;
            color: white;
        }}
        .badge-closed {{
            background-color: #6c757d;
            color: white;
        }}
        .badge-repo {{
            background-color: #007bff;
            color: white;
        }}
        .section {{
            margin: 40px 0;
            display: none;
        }}
        .section.active {{
            display: block;
        }}
        .nav-buttons {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 30px 0;
            flex-wrap: wrap;
        }}
        .nav-button {{
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            transition: transform 0.2s;
        }}
        .nav-button:hover {{
            transform: scale(1.05);
        }}
        .nav-button.active {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        /* Back to Top Button */
        .back-to-top {{
            position: fixed;
            bottom: 40px;
            right: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            font-size: 24px;
            display: none;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            transition: all 0.3s ease;
            z-index: 1000;
        }}
        .back-to-top:hover {{
            transform: scale(1.1);
            box-shadow: 0 6px 16px rgba(0,0,0,0.4);
        }}
        .back-to-top.visible {{
            display: flex;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Issues Dashboard</h1>
        <p style="text-align: center; color: #666;">Automated Issue Tracking</p>
        <div class="update-time">Last updated: {datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M %Z')}</div>

        <div class="stats">
            <div class="stat-box" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);" onclick="showSection('all')">
                <div class="stat-number">{len(issues)}</div>
                <div class="stat-label">Total Issues</div>
            </div>
            <div class="stat-box" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);" onclick="showSection('open')">
                <div class="stat-number">{len(open_issues)}</div>
                <div class="stat-label">Open Issues</div>
            </div>
            <div class="stat-box" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);" onclick="showSection('closed')">
                <div class="stat-number">{len(closed_issues)}</div>
                <div class="stat-label">Closed Issues</div>
            </div>
        </div>

        <div class="nav-buttons">
            <button class="nav-button active" onclick="showSection('charts')">Charts</button>
            <button class="nav-button" onclick="showSection('historical')">Historical Trends</button>
            <button class="nav-button" onclick="showSection('open')">Open Issues</button>
            <button class="nav-button" onclick="showSection('closed')">Closed Issues</button>
            <button class="nav-button" onclick="showSection('all')">All Issues</button>
            <button class="nav-button" id="release-nav-button" onclick="showSection('release')" style="display:none;">Release Issues</button>
        </div>

        <!-- Charts Section -->
        <div id="charts-section" class="section active">
            <div class="chart-container">
                <div class="chart-box">
                    <h2>Issues by Status</h2>
                    <canvas id="statusChart"></canvas>
                </div>
                <div class="chart-box">
                    <h2>Issues Over Time (Last 12 Months)</h2>
                    <canvas id="timeChart"></canvas>
                </div>
            </div>
            <div class="chart-box-full">
                <h2>Issues by Software Release</h2>
                <p style="text-align: center; color: #666; font-size: 14px; margin-top: 10px;">Click on any bar to view issues for that release</p>
                <canvas id="releaseChart"></canvas>
            </div>
        </div>

        <!-- Historical Trends Section -->
        <div id="historical-section" class="section">
            <p style="text-align:center;color:#666;font-size:14px;margin-bottom:10px;">
                Historical data from {len(historical):,} issues spanning v4.2.0 → 54.0 (pre-GitHub era + GitHub era combined)
            </p>
            <div class="chart-container">
                <div class="chart-box">
                    <h2>Detection Method — Overall</h2>
                    <canvas id="detectionPieChart"></canvas>
                </div>
                <div class="chart-box">
                    <h2>Pre GA vs Post GA — Overall</h2>
                    <canvas id="timingPieChart"></canvas>
                </div>
            </div>
            <div class="chart-box-full">
                <h2>Defects per Release — All Time (Historical + Live GitHub)</h2>
                <p style="text-align:center;color:#666;font-size:13px;">Blue = pre-GitHub CSV history &nbsp;|&nbsp; Orange = live GitHub issues</p>
                <canvas id="combinedReleaseChart"></canvas>
            </div>
            <div class="chart-box-full">
                <h2>Pre GA vs Post GA by Release</h2>
                <canvas id="prePostChart"></canvas>
            </div>
            <div class="chart-box-full">
                <h2>Leapwork vs Manual Detection by Release</h2>
                <canvas id="detectionChart"></canvas>
            </div>
        </div>

        <!-- Release Filtered Issues Section -->
        <div id="release-section" class="section">
            <h2 id="release-section-title">Issues for Release</h2>
            <table class="issues-table" id="release-table">
                <thead>
                    <tr>
                        <th data-sort="number" onclick="sortTable('release-table', 'number')">#</th>
                        <th data-sort="title" onclick="sortTable('release-table', 'title')">Title</th>
                        <th data-sort="status" onclick="sortTable('release-table', 'status')">Status</th>
                        <th data-sort="created" onclick="sortTable('release-table', 'created')">Created</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody id="release-issues-tbody">
                </tbody>
            </table>
        </div>

        <!-- Open Issues Section -->
        <div id="open-section" class="section">
            <h2>Open Issues ({len(open_issues)})</h2>
            <table class="issues-table" id="open-table">
                <thead>
                    <tr>
                        <th data-sort="number" onclick="sortTable('open-table', 'number')">#</th>
                        <th data-sort="title" onclick="sortTable('open-table', 'title')">Title</th>
                        <th data-sort="release" onclick="sortTable('open-table', 'release')">Release</th>
                        <th data-sort="created" onclick="sortTable('open-table', 'created')">Created</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Add open issues
    for issue in sorted(open_issues, key=lambda x: x['number'], reverse=True):
        created = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
        release = extract_software_release(issue.get('body', ''))

        html += f"""                    <tr>
                        <td><span class="badge badge-open">{issue['number']}</span></td>
                        <td>{issue['title']}</td>
                        <td>{release}</td>
                        <td>{created}</td>
                        <td><a href="{issue['url']}" target="_blank" class="issue-link">View Issue →</a></td>
                    </tr>
"""

    html += """                </tbody>
            </table>
        </div>

        <!-- Closed Issues Section -->
        <div id="closed-section" class="section">
            <h2>Closed Issues (""" + str(len(closed_issues)) + """)</h2>
            <table class="issues-table" id="closed-table">
                <thead>
                    <tr>
                        <th data-sort="number" onclick="sortTable('closed-table', 'number')">#</th>
                        <th data-sort="title" onclick="sortTable('closed-table', 'title')">Title</th>
                        <th data-sort="release" onclick="sortTable('closed-table', 'release')">Release</th>
                        <th data-sort="created" onclick="sortTable('closed-table', 'created')">Created</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Add closed issues
    for issue in sorted(closed_issues, key=lambda x: x['number'], reverse=True):
        created = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
        release = extract_software_release(issue.get('body', ''))

        html += f"""                    <tr>
                        <td><span class="badge badge-closed">{issue['number']}</span></td>
                        <td>{issue['title']}</td>
                        <td>{release}</td>
                        <td>{created}</td>
                        <td><a href="{issue['url']}" target="_blank" class="issue-link">View Issue →</a></td>
                    </tr>
"""

    html += """                </tbody>
            </table>
        </div>

        <!-- All Issues Section -->
        <div id="all-section" class="section">
            <h2>All Issues (""" + str(len(issues)) + """)</h2>
            <table class="issues-table" id="all-table">
                <thead>
                    <tr>
                        <th data-sort="number" onclick="sortTable('all-table', 'number')">#</th>
                        <th data-sort="title" onclick="sortTable('all-table', 'title')">Title</th>
                        <th data-sort="release" onclick="sortTable('all-table', 'release')">Release</th>
                        <th data-sort="status" onclick="sortTable('all-table', 'status')">Status</th>
                        <th data-sort="created" onclick="sortTable('all-table', 'created')">Created</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Add all issues
    for issue in sorted(issues, key=lambda x: x['number'], reverse=True):
        created = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
        status_badge = 'badge-open' if issue['state'].lower() == 'open' else 'badge-closed'
        status_text = issue['state'].upper()
        release = extract_software_release(issue.get('body', ''))

        html += f"""                    <tr>
                        <td><span class="badge {status_badge}">{issue['number']}</span></td>
                        <td>{issue['title']}</td>
                        <td>{release}</td>
                        <td><span class="badge {status_badge}">{status_text}</span></td>
                        <td>{created}</td>
                        <td><a href="{issue['url']}" target="_blank" class="issue-link">View Issue →</a></td>
                    </tr>
"""

    # Generate chart data
    month_labels = [m[0] for m in sorted_months]
    month_counts = [m[1] for m in sorted_months]

    # Prepare issues data for JavaScript
    issues_data = []
    for issue in issues:
        created = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
        status_badge = 'badge-open' if issue['state'].lower() == 'open' else 'badge-closed'
        status_text = issue['state'].upper()
        release = extract_software_release(issue.get('body', ''))
        issues_data.append({
            'number': issue['number'],
            'title': issue['title'],
            'release': release,
            'state': issue['state'],
            'created': created,
            'url': issue['url'],
            'status_badge': status_badge,
            'status_text': status_text
        })

    html += f"""                </tbody>
            </table>
        </div>
    </div>

    <!-- Back to Top Button -->
    <button class="back-to-top" id="backToTop" onclick="scrollToTop()" title="Back to top">
        ↑
    </button>

    <script>
        // All issues data
        const allIssues = {json.dumps(issues_data)};

        // Function to show issues for a specific release
        function showReleaseIssues(release) {{
            const filteredIssues = allIssues.filter(issue => issue.release === release);
            const tbody = document.getElementById('release-issues-tbody');
            const title = document.getElementById('release-section-title');
            const navButton = document.getElementById('release-nav-button');

            title.textContent = `Issues for Release: ${{release}} (${{filteredIssues.length}} issues)`;

            tbody.innerHTML = '';
            filteredIssues.sort((a, b) => b.number - a.number).forEach(issue => {{
                const row = `
                    <tr>
                        <td><span class="badge ${{issue.status_badge}}">${{issue.number}}</span></td>
                        <td>${{issue.title}}</td>
                        <td><span class="badge ${{issue.status_badge}}">${{issue.status_text}}</span></td>
                        <td>${{issue.created}}</td>
                        <td><a href="${{issue.url}}" target="_blank" class="issue-link">View Issue →</a></td>
                    </tr>
                `;
                tbody.innerHTML += row;
            }});

            // Show the release section and update navigation
            navButton.style.display = 'inline-block';
            navButton.textContent = `${{release}} (${{filteredIssues.length}})`;
            showSection('release');
        }}

        // Chart 1: Issues by Status (Pie Chart)
        const statusCtx = document.getElementById('statusChart').getContext('2d');
        new Chart(statusCtx, {{
            type: 'pie',
            data: {{
                labels: ['Open', 'Closed'],
                datasets: [{{
                    data: [{len(open_issues)}, {len(closed_issues)}],
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)'
                    ],
                    borderColor: [
                        'rgba(75, 192, 192, 1)',
                        'rgba(153, 102, 255, 1)'
                    ],
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            font: {{
                                size: 14
                            }}
                        }}
                    }},
                    title: {{
                        display: true,
                        text: 'Issues Distribution',
                        font: {{
                            size: 16
                        }}
                    }}
                }}
            }}
        }});

        // Chart 2: Issues Over Time (Bar Chart)
        const timeCtx = document.getElementById('timeChart').getContext('2d');
        new Chart(timeCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(month_labels)},
                datasets: [{{
                    label: 'New Issues',
                    data: {json.dumps(month_counts)},
                    backgroundColor: 'rgba(54, 162, 235, 0.8)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 2
                        }},
                        title: {{
                            display: true,
                            text: 'Number of Issues'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Month'
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: 'Issues Created Per Month',
                        font: {{
                            size: 16
                        }}
                    }}
                }}
            }}
        }});

        // Chart 3: Issues by Software Release (Bar Chart)
        const releaseCtx = document.getElementById('releaseChart').getContext('2d');
        new Chart(releaseCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(release_labels)},
                datasets: [{{
                    label: 'Issues',
                    data: {json.dumps(release_counts_list)},
                    backgroundColor: 'rgba(255, 159, 64, 0.8)',
                    borderColor: 'rgba(255, 159, 64, 1)',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 5
                        }},
                        title: {{
                            display: true,
                            text: 'Number of Issues'
                        }}
                    }},
                    x: {{
                        title: {{
                            display: true,
                            text: 'Software Release'
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    title: {{
                        display: true,
                        text: 'Issues by Software Release Detected',
                        font: {{
                            size: 16
                        }}
                    }}
                }},
                onClick: (event, activeElements) => {{
                    if (activeElements.length > 0) {{
                        const index = activeElements[0].index;
                        const release = {json.dumps(release_labels)}[index];
                        showReleaseIssues(release);
                    }}
                }}
            }}
        }});

        // ── Historical Charts ──

        // Detection Method Pie
        new Chart(document.getElementById('detectionPieChart').getContext('2d'), {{
            type: 'pie',
            data: {{
                labels: ['Leapwork', 'Manual', 'Not Specified'],
                datasets: [{{ data: [{hist_total_lw}, {hist_total_manual}, {len(historical) - hist_total_lw - hist_total_manual}],
                    backgroundColor: ['rgba(54,162,235,0.8)','rgba(255,159,64,0.8)','rgba(200,200,200,0.8)'],
                    borderWidth: 2 }}]
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }},
                title: {{ display: true, text: 'How Issues Were Found', font: {{ size: 15 }} }} }} }}
        }});

        // Pre/Post GA Pie
        new Chart(document.getElementById('timingPieChart').getContext('2d'), {{
            type: 'pie',
            data: {{
                labels: ['Pre GA', 'Post GA', 'Not Specified'],
                datasets: [{{ data: [{hist_total_pre}, {hist_total_post}, {len(historical) - hist_total_pre - hist_total_post}],
                    backgroundColor: ['rgba(75,192,192,0.8)','rgba(255,99,132,0.8)','rgba(200,200,200,0.8)'],
                    borderWidth: 2 }}]
            }},
            options: {{ responsive: true, plugins: {{ legend: {{ position: 'bottom' }},
                title: {{ display: true, text: 'When Issues Were Found', font: {{ size: 15 }} }} }} }}
        }});

        // Combined Defects per Release (stacked: CSV + GitHub)
        new Chart(document.getElementById('combinedReleaseChart').getContext('2d'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(sorted_combined)},
                datasets: [
                    {{ label: 'Historical (CSV)', data: {json.dumps(combined_hist_counts)},
                       backgroundColor: 'rgba(54,162,235,0.75)', borderColor: 'rgba(54,162,235,1)', borderWidth: 1 }},
                    {{ label: 'GitHub Live', data: {json.dumps(combined_github_counts)},
                       backgroundColor: 'rgba(255,159,64,0.75)', borderColor: 'rgba(255,159,64,1)', borderWidth: 1 }}
                ]
            }},
            options: {{ responsive: true, scales: {{
                x: {{ stacked: true, title: {{ display: true, text: 'Release' }} }},
                y: {{ stacked: true, beginAtZero: true, title: {{ display: true, text: 'Number of Issues' }} }}
            }}, plugins: {{ legend: {{ position: 'top' }} }} }}
        }});

        // Pre GA vs Post GA per Release
        new Chart(document.getElementById('prePostChart').getContext('2d'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(hist_releases_sorted)},
                datasets: [
                    {{ label: 'Pre GA',  data: {json.dumps(pre_ga_counts)},
                       backgroundColor: 'rgba(75,192,192,0.75)', borderColor: 'rgba(75,192,192,1)', borderWidth: 1 }},
                    {{ label: 'Post GA', data: {json.dumps(post_ga_counts)},
                       backgroundColor: 'rgba(255,99,132,0.75)', borderColor: 'rgba(255,99,132,1)', borderWidth: 1 }}
                ]
            }},
            options: {{ responsive: true, scales: {{
                x: {{ stacked: true, title: {{ display: true, text: 'Release' }} }},
                y: {{ stacked: true, beginAtZero: true, title: {{ display: true, text: 'Number of Issues' }} }}
            }}, plugins: {{ legend: {{ position: 'top' }} }} }}
        }});

        // Leapwork vs Manual per Release
        new Chart(document.getElementById('detectionChart').getContext('2d'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(hist_releases_sorted)},
                datasets: [
                    {{ label: 'Leapwork', data: {json.dumps(lw_counts)},
                       backgroundColor: 'rgba(54,162,235,0.75)', borderColor: 'rgba(54,162,235,1)', borderWidth: 1 }},
                    {{ label: 'Manual',   data: {json.dumps(manual_counts)},
                       backgroundColor: 'rgba(255,159,64,0.75)', borderColor: 'rgba(255,159,64,1)', borderWidth: 1 }}
                ]
            }},
            options: {{ responsive: true, scales: {{
                x: {{ stacked: true, title: {{ display: true, text: 'Release' }} }},
                y: {{ stacked: true, beginAtZero: true, title: {{ display: true, text: 'Number of Issues' }} }}
            }}, plugins: {{ legend: {{ position: 'top' }} }} }}
        }});

        // Section switching functionality
        function showSection(section) {{
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-button').forEach(btn => btn.classList.remove('active'));

            if (section === 'charts') {{
                document.getElementById('charts-section').classList.add('active');
                document.querySelectorAll('.nav-button')[0].classList.add('active');
            }} else if (section === 'historical') {{
                document.getElementById('historical-section').classList.add('active');
                document.querySelectorAll('.nav-button')[1].classList.add('active');
            }} else if (section === 'open') {{
                document.getElementById('open-section').classList.add('active');
                document.querySelectorAll('.nav-button')[2].classList.add('active');
            }} else if (section === 'closed') {{
                document.getElementById('closed-section').classList.add('active');
                document.querySelectorAll('.nav-button')[3].classList.add('active');
            }} else if (section === 'all') {{
                document.getElementById('all-section').classList.add('active');
                document.querySelectorAll('.nav-button')[4].classList.add('active');
            }} else if (section === 'release') {{
                document.getElementById('release-section').classList.add('active');
                document.getElementById('release-nav-button').classList.add('active');
            }}
        }}

        // Back to Top Button functionality
        window.addEventListener('scroll', function() {{
            const backToTopButton = document.getElementById('backToTop');
            if (window.pageYOffset > 300) {{
                backToTopButton.classList.add('visible');
            }} else {{
                backToTopButton.classList.remove('visible');
            }}
        }});

        function scrollToTop() {{
            window.scrollTo({{
                top: 0,
                behavior: 'smooth'
            }});
        }}

        // Table sorting functionality
        let sortStates = {{}};  // Track sort state for each table

        function sortTable(tableId, column) {{
            const table = document.getElementById(tableId);
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const th = table.querySelector(`th[data-sort="${{column}}"]`);

            // Initialize sort state for this table/column if not exists
            const key = `${{tableId}}-${{column}}`;
            if (!sortStates[key]) {{
                sortStates[key] = 'none';
            }}

            // Determine next sort direction
            let direction;
            if (sortStates[key] === 'none' || sortStates[key] === 'desc') {{
                direction = 'asc';
            }} else {{
                direction = 'desc';
            }}
            sortStates[key] = direction;

            // Clear all sort indicators in this table
            table.querySelectorAll('th').forEach(header => {{
                header.classList.remove('sort-asc', 'sort-desc');
            }});

            // Add sort indicator to clicked header
            th.classList.add(`sort-${{direction}}`);

            // Sort rows
            rows.sort((a, b) => {{
                let aVal, bVal;

                if (column === 'number') {{
                    // Extract number from badge
                    aVal = parseInt(a.cells[0].textContent.trim());
                    bVal = parseInt(b.cells[0].textContent.trim());
                }} else if (column === 'title') {{
                    // Get column index based on table structure
                    const colIndex = Array.from(th.parentElement.children).indexOf(th);
                    aVal = a.cells[colIndex].textContent.toLowerCase();
                    bVal = b.cells[colIndex].textContent.toLowerCase();
                }} else if (column === 'release') {{
                    const colIndex = Array.from(th.parentElement.children).indexOf(th);
                    aVal = a.cells[colIndex].textContent.toLowerCase();
                    bVal = b.cells[colIndex].textContent.toLowerCase();
                }} else if (column === 'status') {{
                    const colIndex = Array.from(th.parentElement.children).indexOf(th);
                    aVal = a.cells[colIndex].textContent.toLowerCase();
                    bVal = b.cells[colIndex].textContent.toLowerCase();
                }} else if (column === 'created') {{
                    const colIndex = Array.from(th.parentElement.children).indexOf(th);
                    aVal = a.cells[colIndex].textContent;
                    bVal = b.cells[colIndex].textContent;
                }}

                // Compare values
                if (aVal < bVal) return direction === 'asc' ? -1 : 1;
                if (aVal > bVal) return direction === 'asc' ? 1 : -1;
                return 0;
            }});

            // Re-append sorted rows
            rows.forEach(row => tbody.appendChild(row));
        }}
    </script>
</body>
</html>
"""

    return html

def main():
    """Main function"""
    print("Issues Dashboard Generator")
    print("=" * 50)

    # Load historical CSV data
    historical = load_historical_csv()

    # Fetch live GitHub issues
    issues = fetch_issues()

    if not issues:
        print("No issues found or error fetching data")
        return

    # Generate HTML
    print("Generating HTML dashboard...")
    html = generate_html(issues, historical)

    # Write to file
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print("✅ Dashboard generated successfully: index.html")
    print(f"   Total issues: {len(issues)}")
    print(f"   Open: {len([i for i in issues if i['state'].lower() == 'open'])}")
    print(f"   Closed: {len([i for i in issues if i['state'].lower() == 'closed'])}")

if __name__ == '__main__':
    main()
