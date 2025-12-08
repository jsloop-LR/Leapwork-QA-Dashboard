# 🧪 Leapwork QA Dashboard

Automated dashboard for tracking QA issues in the netFLEX project using Leapwork testing framework.

## 🌐 Live Dashboard

**View the dashboard:** https://jsloop-LR.github.io/leapwork-qa-dashboard/

## 📊 Features

- **Real-time Issue Tracking**: Automatically fetches QA issues from GitHub
- **Interactive Charts**: Visual representation of issue status and trends
- **Detailed Issue Lists**: Browse open, closed, and all QA issues
- **Clickable Links**: Direct links to each issue on GitHub
- **Auto-Updated Daily**: Dashboard refreshes automatically at 8 AM UTC every day

## 🔄 Automatic Updates

This dashboard updates automatically using GitHub Actions:
- **Schedule**: Daily at 8:00 AM UTC
- **Manual Trigger**: Can be triggered manually from the Actions tab
- **Auto-commit**: Changes are automatically committed to the repository

## 📈 What's Tracked

- Total QA issues
- Open vs Closed issues
- Production issues (netflex repo only)
- Historical trends (last 12 months)
- Issue details with direct GitHub links

## 🛠️ How It Works

1. GitHub Actions runs `generate_dashboard.py` daily
2. Script fetches all QA issues from lightriversoftware organization
3. Generates an interactive HTML dashboard with charts
4. Commits the updated dashboard to the repository
5. GitHub Pages serves the latest version at the live URL

## 📝 Note

Yellow-highlighted rows in the dashboard indicate test issues from the workflow-testing repository.

---

*Last manual update: 2025-12-08*
*Automated by GitHub Actions*
