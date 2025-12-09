#!/usr/bin/env python3
"""
Leapwork QA Dashboard Generator
Fetches QA issues from GitHub and generates an interactive HTML dashboard
"""

import json
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter, defaultdict

def run_gh_command(cmd):
    """Run a gh CLI command and return the output"""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {cmd}")
        print(f"Error: {result.stderr}")
        return None
    return result.stdout

def fetch_qa_issues():
    """Fetch all QA issues from lightriversoftware organization"""
    print("Fetching QA issues from GitHub...")
    cmd = 'gh search issues "org:lightriversoftware" --limit 500 --json number,title,state,createdAt,updatedAt,labels,url'
    output = run_gh_command(cmd)

    if not output:
        return []

    all_issues = json.loads(output)
    # Filter for QA issues only
    qa_issues = [issue for issue in all_issues if '[QA]' in issue['title']]

    print(f"Found {len(qa_issues)} QA issues")
    return qa_issues

def generate_html(qa_issues):
    """Generate the HTML dashboard"""

    # Calculate statistics
    open_issues = [i for i in qa_issues if i['state'] == 'open']
    closed_issues = [i for i in qa_issues if i['state'] == 'closed']

    # Separate by repository
    netflex_open = [i for i in open_issues if 'netflex/issues' in i['url'] and 'workflow-testing' not in i['url']]
    test_open = [i for i in open_issues if 'workflow-testing' in i['url']]

    # Issues over time
    issues_by_month = defaultdict(int)
    for issue in qa_issues:
        date = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00'))
        month_key = date.strftime('%Y-%m')
        issues_by_month[month_key] += 1

    sorted_months = sorted(issues_by_month.items())[-12:]  # Last 12 months

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Leapwork QA Dashboard - LightRiver netFLEX</title>
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
        .test-issue {{
            background-color: #fff3cd;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 Leapwork QA Dashboard</h1>
        <p style="text-align: center; color: #666;">LightRiver netFLEX - Automated Testing Results</p>
        <div class="update-time">Last updated: {datetime.now(ZoneInfo('America/New_York')).strftime('%Y-%m-%d %H:%M %Z')}</div>

        <div class="stats">
            <div class="stat-box" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);" onclick="showSection('all')">
                <div class="stat-number">{len(qa_issues)}</div>
                <div class="stat-label">Total QA Issues</div>
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
            <button class="nav-button" onclick="showSection('open')">Open Issues</button>
            <button class="nav-button" onclick="showSection('closed')">Closed Issues</button>
            <button class="nav-button" onclick="showSection('all')">All Issues</button>
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
        </div>

        <!-- Open Issues Section -->
        <div id="open-section" class="section">
            <h2>Open QA Issues ({len(open_issues)})</h2>
            <table class="issues-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Title</th>
                        <th>Repository</th>
                        <th>Created</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Add open issues
    for issue in sorted(open_issues, key=lambda x: x['number'], reverse=True):
        repo_name = 'netflex' if 'netflex/issues' in issue['url'] and 'workflow-testing' not in issue['url'] else 'workflow-testing'
        is_test = 'test-issue' if repo_name == 'workflow-testing' else ''
        created = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')

        html += f"""                    <tr class="{is_test}">
                        <td><span class="badge badge-open">{issue['number']}</span></td>
                        <td>{issue['title']}</td>
                        <td><span class="badge badge-repo">{repo_name}</span></td>
                        <td>{created}</td>
                        <td><a href="{issue['url']}" target="_blank" class="issue-link">View Issue →</a></td>
                    </tr>
"""

    html += """                </tbody>
            </table>
            <p style="color: #666; font-style: italic;">Note: Yellow highlighted rows are test issues from the workflow-testing repository</p>
        </div>

        <!-- Closed Issues Section -->
        <div id="closed-section" class="section">
            <h2>Closed QA Issues (""" + str(len(closed_issues)) + """)</h2>
            <table class="issues-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Title</th>
                        <th>Repository</th>
                        <th>Created</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Add closed issues
    for issue in sorted(closed_issues, key=lambda x: x['number'], reverse=True):
        repo_name = 'netflex' if 'netflex/issues' in issue['url'] and 'workflow-testing' not in issue['url'] else 'workflow-testing'
        created = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')

        html += f"""                    <tr>
                        <td><span class="badge badge-closed">{issue['number']}</span></td>
                        <td>{issue['title']}</td>
                        <td><span class="badge badge-repo">{repo_name}</span></td>
                        <td>{created}</td>
                        <td><a href="{issue['url']}" target="_blank" class="issue-link">View Issue →</a></td>
                    </tr>
"""

    html += """                </tbody>
            </table>
        </div>

        <!-- All Issues Section -->
        <div id="all-section" class="section">
            <h2>All QA Issues (""" + str(len(qa_issues)) + """)</h2>
            <table class="issues-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Title</th>
                        <th>Status</th>
                        <th>Repository</th>
                        <th>Created</th>
                        <th>Link</th>
                    </tr>
                </thead>
                <tbody>
"""

    # Add all issues
    for issue in sorted(qa_issues, key=lambda x: x['number'], reverse=True):
        repo_name = 'netflex' if 'netflex/issues' in issue['url'] and 'workflow-testing' not in issue['url'] else 'workflow-testing'
        is_test = 'test-issue' if repo_name == 'workflow-testing' and issue['state'] == 'open' else ''
        created = datetime.fromisoformat(issue['createdAt'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
        status_badge = 'badge-open' if issue['state'] == 'open' else 'badge-closed'
        status_text = issue['state'].upper()

        html += f"""                    <tr class="{is_test}">
                        <td><span class="badge {status_badge}">{issue['number']}</span></td>
                        <td>{issue['title']}</td>
                        <td><span class="badge {status_badge}">{status_text}</span></td>
                        <td><span class="badge badge-repo">{repo_name}</span></td>
                        <td>{created}</td>
                        <td><a href="{issue['url']}" target="_blank" class="issue-link">View Issue →</a></td>
                    </tr>
"""

    # Generate chart data
    month_labels = [m[0] for m in sorted_months]
    month_counts = [m[1] for m in sorted_months]

    html += f"""                </tbody>
            </table>
            <p style="color: #666; font-style: italic; margin-top: 20px;">Note: Yellow highlighted rows are test issues from the workflow-testing repository</p>
        </div>
    </div>

    <script>
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
                        text: 'QA Issues Distribution',
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
                    label: 'New QA Issues',
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
                        text: 'QA Issues Created Per Month',
                        font: {{
                            size: 16
                        }}
                    }}
                }}
            }}
        }});

        // Section switching functionality
        function showSection(section) {{
            document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
            document.querySelectorAll('.nav-button').forEach(btn => btn.classList.remove('active'));

            if (section === 'charts') {{
                document.getElementById('charts-section').classList.add('active');
                document.querySelectorAll('.nav-button')[0].classList.add('active');
            }} else if (section === 'open') {{
                document.getElementById('open-section').classList.add('active');
                document.querySelectorAll('.nav-button')[1].classList.add('active');
            }} else if (section === 'closed') {{
                document.getElementById('closed-section').classList.add('active');
                document.querySelectorAll('.nav-button')[2].classList.add('active');
            }} else if (section === 'all') {{
                document.getElementById('all-section').classList.add('active');
                document.querySelectorAll('.nav-button')[3].classList.add('active');
            }}
        }}
    </script>
</body>
</html>
"""

    return html

def main():
    """Main function"""
    print("Leapwork QA Dashboard Generator")
    print("=" * 50)

    # Fetch QA issues
    qa_issues = fetch_qa_issues()

    if not qa_issues:
        print("No QA issues found or error fetching data")
        return

    # Generate HTML
    print("Generating HTML dashboard...")
    html = generate_html(qa_issues)

    # Write to file
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)

    print("✅ Dashboard generated successfully: index.html")
    print(f"   Total issues: {len(qa_issues)}")
    print(f"   Open: {len([i for i in qa_issues if i['state'] == 'open'])}")
    print(f"   Closed: {len([i for i in qa_issues if i['state'] == 'closed'])}")

if __name__ == '__main__':
    main()
