# MoneyRadar UI/UX Quick Start Guide

## Overview

MoneyRadar now includes a modern React-based web UI for visualizing revenue intelligence, alongside the powerful CLI interface.

## What's Included

### 🎨 Web UI Features

- **Interactive Dashboard** - Real-time MRR tracking, alerts overview, and trend visualization
- **Revenue Analytics** - Detailed MRR trends with component breakdown (new, expansion, contraction, churn)
- **Alerts Management** - Monitor and resolve revenue signals with one-click actions
- **Usage Mismatches** - Identify upgrade opportunities and potential downgrades
- **Customer Scoring** - Analyze expansion readiness with actionable recommendations
- **Experiment Tracking** - Create, manage, and track pricing experiments

### 🛠️ Tech Stack

- **Frontend:** React 18, Vite, Tailwind CSS, Recharts
- **Backend:** Flask API with CORS support
- **Development:** Hot reload, proxy configuration, responsive design

## Installation

### 1. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 2. Install Flask CORS Package

```bash
pip install flask-cors
```

Already included in `requirements.txt`.

## Running the Application

### Quick Start (Recommended)

Use the startup script to launch both API and UI:

**Linux/Mac:**
```bash
./start-dev.sh
```

**Windows:**
```powershell
.\start-dev.ps1
```

**Or use Make:**
```bash
make dev
```

This will start:
- API server on http://localhost:5000
- Web UI on http://localhost:3000

### Manual Start

**Terminal 1 - API Server:**
```bash
python -m monetization_engine.api.app
# or
make dev-api
```

**Terminal 2 - Web UI:**
```bash
cd frontend
npm run dev
# or
make dev-ui
```

## Project Structure

```
MoneyRadar/
├── frontend/                # React web application
│   ├── src/
│   │   ├── api/            # API client
│   │   ├── components/     # Reusable UI components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── pages/          # Page components
│   │   ├── App.jsx         # Main app with routing
│   │   └── main.jsx        # Entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── monetization_engine/
│   └── api/
│       └── app.py          # Flask API with CORS
├── start-dev.sh            # Linux/Mac startup script
├── start-dev.ps1           # Windows startup script
└── Makefile                # Enhanced with UI commands
```

## Development Workflow

### Daily Use

1. **Start the application:**
   ```bash
   make dev
   ```

2. **Access the web UI:**
   - Open http://localhost:3000
   - Navigate using the top menu

3. **Check the dashboard:**
   - View current MRR and trends
   - Review active alerts
   - Monitor revenue movements

### Making Changes

**Frontend Development:**
- Edit files in `frontend/src/`
- Hot reload automatically updates the browser
- Use browser DevTools for debugging

**Backend Development:**
- Edit API routes in `monetization_engine/api/routes/`
- Restart the API server to see changes
- Check console logs for errors

### Building for Production

```bash
# Build optimized frontend
cd frontend
npm run build

# Preview production build
npm run preview
```

Built files will be in `frontend/dist/`.

## API Integration

The frontend communicates with the Flask API via:

1. **Development Proxy:** Vite proxies `/api` requests to `http://localhost:5000`
2. **CORS Configuration:** Flask API allows requests from `localhost:3000`
3. **API Client:** `src/api/client.js` provides typed methods for all endpoints

### Available API Endpoints

All endpoints are accessible via the API client:

```javascript
import { api } from './api/client'

// Revenue
api.getMRR({ days: 30 })
api.getMRRSnapshots({ days: 90 })

// Alerts
api.getAlerts({ status: 'active' })
api.resolveAlert(alertId, notes)
api.scanAlerts()

// Analysis
api.getMismatches({ min_severity: 0.7 })

// Customers
api.getCustomerScore(customerId)

// Experiments
api.getExperiments()
api.createExperiment(data)
api.startExperiment(id)
api.completeExperiment(id, results)

// Admin
api.syncStripe()
api.calculateMRRSnapshot(date)
```

## Customization

### Styling

The UI uses Tailwind CSS with a custom theme:

**Colors:**
- Primary: Blue (`#0EA5E9`)
- Success: Green
- Warning: Yellow
- Danger: Red

**Dark Mode:**
- Fully supported
- Automatic based on system preferences

**Customizing:**
Edit `frontend/tailwind.config.js` to change colors, spacing, etc.

### Components

Reusable components are in `frontend/src/components/`:

- `Layout.jsx` - Main layout with navigation
- `Card.jsx` - Content card wrapper
- `StatCard.jsx` - Metric display card
- `LoadingSpinner.jsx` - Loading indicator
- `ErrorMessage.jsx` - Error display

## Troubleshooting

### Frontend won't start

```bash
# Clear and reinstall dependencies
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### API connection errors

1. Ensure API is running on port 5000
2. Check CORS configuration in `monetization_engine/api/app.py`
3. Verify proxy settings in `frontend/vite.config.js`

### CORS errors

The API should have flask-cors configured. If issues persist:

```bash
pip install --upgrade flask-cors
```

Check the CORS configuration in `app.py`:
```python
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:3000"],
        ...
    }
})
```

### Database not initialized

```bash
python init_db.py
```

## Next Steps

1. **Explore the UI:**
   - Navigate through all pages
   - Try creating an experiment
   - Scan for alerts

2. **Connect Real Data:**
   - Configure Stripe credentials in `.env`
   - Run `moneyradar sync-stripe`
   - Calculate MRR snapshots

3. **Customize:**
   - Adjust color theme
   - Modify dashboard widgets
   - Add new pages or features

## Support

- **Documentation:** See main [README.md](../README.md) and [USAGE.md](../USAGE.md)
- **Frontend Docs:** [frontend/README.md](../frontend/README.md)
- **Architecture:** [ARCHITECTURE.md](../ARCHITECTURE.md)

---

**Built with ❤️ for solo SaaS founders**
