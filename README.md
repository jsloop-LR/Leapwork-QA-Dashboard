# 🧪 Leapwork QA Dashboard

Automated dashboard for tracking QA issues in the netFLEX project using Leapwork testing framework.

## 🌐 Live Dashboard

**View the dashboard:** https://jsloop-lr.github.io/Leapwork-QA-Dashboard/

## 📊 Features

- **Real-time Issue Tracking**: Automatically fetches QA issues from GitHub
- **Interactive Charts**: Visual representation of issue status and trends
- **Detailed Issue Lists**: Browse open, closed, and all QA issues
- **Clickable Links**: Direct links to each issue on GitHub
- **Auto-Updated**: Dashboard refreshes automatically every 30 minutes

## 🔄 Automatic Updates

This dashboard updates automatically using GitHub Actions:
- **Schedule**: Every 30 minutes
- **Manual Trigger**: Can be triggered manually from the Actions tab
- **Auto-commit**: Changes are automatically committed to the repository

## 📈 What's Tracked

- Total QA issues
- Open vs Closed issues
- Historical trends (last 12 months)
- Issue details with direct GitHub links

## 🛠️ How It Works

1. GitHub Actions runs `generate_dashboard.py` every 30 minutes
2. Script fetches all QA issues from lightriversoftware organization
3. Generates an interactive HTML dashboard with charts
4. Commits the updated dashboard to the repository
5. GitHub Pages serves the latest version at the live URL

## 📝 Note

Yellow-highlighted rows in the dashboard indicate test issues from the workflow-testing repository.

---

*Last manual update: 2025-12-08*
*Automated by GitHub Actions*
