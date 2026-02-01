# MoneyRadar Frontend

Modern React-based UI for the MoneyRadar revenue intelligence platform.

## Features

- 📊 **Interactive Dashboard** - Real-time MRR tracking and key metrics
- 💰 **Revenue Analytics** - Detailed MRR trends and movement analysis
- ⚠️ **Alerts Management** - Monitor and resolve revenue signals
- 🎯 **Mismatch Detection** - Identify upgrade and downgrade opportunities
- 👥 **Customer Scoring** - Expansion readiness analysis
- 🧪 **Experiment Tracking** - Track pricing changes and their impact

## Tech Stack

- **React 18** - Modern UI library
- **Vite** - Fast build tool and dev server
- **React Router** - Client-side routing
- **Tailwind CSS** - Utility-first styling
- **Recharts** - Data visualization
- **date-fns** - Date formatting

## Development

### Prerequisites

- Node.js 18+ and npm
- MoneyRadar API running on http://localhost:5000

### Install Dependencies

```bash
npm install
```

### Start Development Server

```bash
npm run dev
```

The app will be available at http://localhost:3000

### Build for Production

```bash
npm run build
```

Built files will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client and integration
│   │   └── client.js     # API request methods
│   ├── components/       # Reusable UI components
│   │   ├── Layout.jsx
│   │   ├── Card.jsx
│   │   ├── StatCard.jsx
│   │   ├── LoadingSpinner.jsx
│   │   └── ErrorMessage.jsx
│   ├── hooks/            # Custom React hooks
│   │   └── useApi.js     # API data fetching hook
│   ├── pages/            # Page components
│   │   ├── Dashboard.jsx
│   │   ├── Revenue.jsx
│   │   ├── Alerts.jsx
│   │   ├── Mismatches.jsx
│   │   ├── Customers.jsx
│   │   └── Experiments.jsx
│   ├── App.jsx           # Main app component with routes
│   ├── main.jsx          # App entry point
│   └── index.css         # Global styles
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
└── README.md
```

## API Integration

The frontend connects to the MoneyRadar API via the `api/client.js` module. The Vite dev server proxies API requests to avoid CORS issues.

All API endpoints are configured in `src/api/client.js`:
- Revenue endpoints (`/api/revenue/*`)
- Alert endpoints (`/api/alerts/*`)
- Analysis endpoints (`/api/analysis/*`)
- Customer endpoints (`/api/customers/*`)
- Experiment endpoints (`/api/experiments/*`)
- Admin endpoints (`/api/admin/*`)

## Environment Variables

Create a `.env.local` file for local development:

```bash
VITE_API_URL=http://localhost:5000/api
```

## Features by Page

### Dashboard
- Current MRR with trend
- Active alerts count
- New and churned revenue
- MRR trend chart
- Recent alerts list

### Revenue Analytics
- Historical MRR trends
- Revenue movement breakdown (new, expansion, contraction, churn)
- Component analysis over time
- Time range filtering

### Alerts Management
- Active/resolved alert filtering
- Alert severity indicators
- One-click resolution
- Alert scanning
- Detailed alert metadata

### Usage Mismatches
- Upgrade opportunities
- Potential downgrades
- Severity-based filtering
- Usage ratio analysis

### Customer Scoring
- Expansion readiness scores
- Score factor breakdown
- Actionable recommendations
- Score interpretation guide

### Pricing Experiments
- Create and track experiments
- Start/complete workflows
- MRR impact tracking
- Experiment history

## Styling

The app uses Tailwind CSS with a custom theme. Key design tokens:
- Primary color: Blue (#0EA5E9)
- Dark mode support
- Responsive grid layouts
- Custom component classes (card, btn, badge)

## License

MIT - See LICENSE file in project root
