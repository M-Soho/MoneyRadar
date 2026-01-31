# MoneyRadar Deployment Guide

## Quick Deploy to Production

### 1. Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://user:pass@host:5432/moneyradar"
export STRIPE_API_KEY="sk_live_your_key"
export STRIPE_WEBHOOK_SECRET="whsec_your_secret"
export SECRET_KEY="$(openssl rand -hex 32)"
```

### 2. Database Migration

```bash
# Initialize database
python -c "from monetization_engine.database import init_db; init_db()"

# Verify tables created
psql $DATABASE_URL -c "\dt"
```

### 3. Initial Sync

```bash
# Sync products and plans from Stripe
moneyradar sync-stripe

# Calculate baseline MRR
moneyradar calculate-mrr
```

### 4. Start API Server

Using Gunicorn (recommended):

```bash
pip install gunicorn
gunicorn monetization_engine.api.app:app \
  --workers 4 \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

Or using systemd:

```ini
# /etc/systemd/system/moneyradar.service
[Unit]
Description=MoneyRadar API
After=network.target

[Service]
User=www-data
WorkingDirectory=/app/MoneyRadar
Environment="PATH=/app/MoneyRadar/venv/bin"
EnvironmentFile=/app/MoneyRadar/.env
ExecStart=/app/MoneyRadar/venv/bin/gunicorn monetization_engine.api.app:app \
  --workers 4 \
  --bind 0.0.0.0:5000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable moneyradar
sudo systemctl start moneyradar
```

### 5. Configure Stripe Webhooks

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-domain.com/webhooks/stripe`
3. Select events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy webhook signing secret to `STRIPE_WEBHOOK_SECRET`

### 6. Set Up Cron Jobs

```bash
# Edit crontab
crontab -e
```

Add these jobs:

```cron
# Daily MRR snapshot at midnight
0 0 * * * cd /app/MoneyRadar && /app/MoneyRadar/venv/bin/moneyradar calculate-mrr

# Hourly Stripe sync
0 * * * * cd /app/MoneyRadar && /app/MoneyRadar/venv/bin/moneyradar sync-stripe

# Risk scan every 6 hours
0 */6 * * * cd /app/MoneyRadar && /app/MoneyRadar/venv/bin/moneyradar scan-risks

# Mismatch analysis daily at 8am
0 8 * * * cd /app/MoneyRadar && /app/MoneyRadar/venv/bin/moneyradar analyze-mismatches
```

### 7. Nginx Reverse Proxy (Optional)

```nginx
server {
    listen 80;
    server_name moneyradar.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Docker Deployment

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install -e .

CMD ["gunicorn", "monetization_engine.api.app:app", "--bind", "0.0.0.0:5000", "--workers", "4"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: moneyradar
      POSTGRES_USER: moneyradar
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  api:
    build: .
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://moneyradar:${DB_PASSWORD}@db:5432/moneyradar
      STRIPE_API_KEY: ${STRIPE_API_KEY}
      STRIPE_WEBHOOK_SECRET: ${STRIPE_WEBHOOK_SECRET}
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      - db

  scheduler:
    build: .
    command: >
      sh -c "
        while true; do
          sleep 3600 && moneyradar sync-stripe;
          sleep 18000 && moneyradar scan-risks;
          sleep 3600;
        done
      "
    environment:
      DATABASE_URL: postgresql://moneyradar:${DB_PASSWORD}@db:5432/moneyradar
      STRIPE_API_KEY: ${STRIPE_API_KEY}
    depends_on:
      - db

volumes:
  postgres_data:
```

Deploy:

```bash
docker-compose up -d
```

## Monitoring

### Health Check

```bash
curl http://localhost:5000/health
```

### Logs

```bash
# Systemd
sudo journalctl -u moneyradar -f

# Docker
docker-compose logs -f api
```

### Metrics to Monitor

- MRR trends (daily)
- Alert counts by severity
- API response times
- Stripe webhook delivery status

## Backup

### Database Backup

```bash
# PostgreSQL backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d).sql

# Automated daily backups
0 2 * * * pg_dump $DATABASE_URL | gzip > /backups/moneyradar_$(date +\%Y\%m\%d).sql.gz
```

## Security

1. **API Authentication** - Add authentication middleware if exposing publicly
2. **Webhook Validation** - Stripe signature verification is implemented
3. **Environment Variables** - Never commit `.env` to version control
4. **Database** - Use strong passwords, restrict network access
5. **HTTPS** - Always use SSL in production

## Troubleshooting

### Database Connection Issues

```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1"

# Check tables
python -c "from monetization_engine.database import engine; print(engine.table_names())"
```

### Stripe Sync Issues

```bash
# Check API key
stripe customers list --api-key $STRIPE_API_KEY

# Manual sync with verbose output
python -c "from monetization_engine.database import get_db; from monetization_engine.ingestion import StripeIngestion; db = next(get_db()); StripeIngestion(db).sync_products_and_plans()"
```

### No Alerts Generated

```bash
# Check subscriptions
moneyradar list-alerts

# Force risk scan
moneyradar scan-risks

# Check if usage data exists
psql $DATABASE_URL -c "SELECT COUNT(*) FROM usage_records"
```
