# Usage Guide - MoneyRadar

## Daily Workflow

### Morning Routine (5 minutes)

1. **Check Critical Alerts**
   ```bash
   moneyradar list-alerts
   ```
   Review any critical revenue risks that appeared overnight.

2. **Review MRR**
   ```bash
   moneyradar calculate-mrr
   ```
   See yesterday's MRR movements - new, expansion, churn.

3. **Scan for New Risks**
   ```bash
   moneyradar scan-risks
   ```
   Surface any new warning signs.

### Weekly Review (15 minutes)

1. **Analyze Mismatches**
   ```bash
   moneyradar analyze-mismatches
   ```
   
   Focus on:
   - Top 3 upgrade candidates - reach out personally
   - Overpriced customers - consider plan adjustments
   
2. **Score Expansion Candidates**
   ```bash
   # For each high-value customer
   moneyradar score-customer cus_ABC123
   ```
   
   Categories:
   - `safe_to_upsell` - Green light for outreach
   - `do_not_touch` - Leave alone
   - `likely_to_churn` - Retention focus

3. **Review Running Experiments**
   ```bash
   moneyradar experiment list
   moneyradar experiment analyze <id>
   ```

## Common Scenarios

### Scenario 1: Customer Hitting Limits

**Signal:** Alert for high usage (>80%)

**Action:**
```bash
# 1. Check their score
moneyradar score-customer cus_XYZ

# 2. Review their usage
curl http://localhost:5000/api/customers/cus_XYZ/score
```

**If score > 70:**
- Reach out with upgrade offer
- Highlight value they're getting
- Show them how limits are impacting them

**If score < 40:**
- Investigate why heavy usage but low score
- May have support issues or churn risk
- Fix issues before attempting upsell

### Scenario 2: MRR Declining

**Signal:** Critical alert for MRR decline

**Action:**
```bash
# Get detailed breakdown
curl http://localhost:5000/api/revenue/snapshots?days=30
```

**Analyze:**
- Is churn increasing? (churned_mrr)
- Is new MRR slowing? (new_mrr)
- Are downgrades happening? (contraction_mrr)

**Response:**
- High churn → Review exit surveys, fix retention
- Low new MRR → Check conversion funnel
- Downgrades → Investigate pricing perception

### Scenario 3: Testing Price Change

**Goal:** Increase Pro plan from $49 to $59

**Process:**
```bash
# 1. Create experiment
moneyradar experiment create \
  --name "Pro Price Test" \
  --hypothesis "20% increase won't hurt conversion" \
  --change "Pro: $49 → $59" \
  --metric conversion_rate

# 2. Start (calculates baseline)
moneyradar experiment start <id>

# 3. Implement price change in Stripe
# (for variant group or all new customers)

# 4. Monitor weekly
moneyradar experiment analyze <id>

# 5. After 30-60 days, record result
curl -X POST http://localhost:5000/api/experiments/<id>/complete \
  -H "Content-Type: application/json" \
  -d '{
    "actual_value": 0.18,
    "outcome": "Success - conversion dropped 2% but ARPU increased 15%"
  }'
```

### Scenario 4: Plan Might Be Mispriced

**Signal:** Many customers on same plan showing similar mismatch

**Action:**
```bash
# Check for systemic issues
curl http://localhost:5000/api/analysis/feature-pricing
```

**If >60% of plan users are heavy users:**
- Limits too restrictive
- Create higher tier OR
- Raise limits and price

**If >60% of plan users are light users:**
- Limits too generous
- Lower price OR
- Lower limits OR
- Market to different segment

### Scenario 5: Payment Failures

**Signal:** Payment retry alert

**Action:**
```bash
# List payment issues
moneyradar list-alerts | grep PAYMENT
```

**Triage by attempt count:**
- Attempt 1-2: Automatic email (Stripe handles)
- Attempt 3+: Personal outreach required
- Valuable customers: Immediate contact

## Integration with OPSP

If you're using OPSP (your main operational system):

1. **Forward Critical Alerts**
   ```python
   # In your cron job
   import requests
   
   # Get critical alerts
   alerts = requests.get('http://localhost:5000/api/alerts?severity=critical')
   
   # Forward to OPSP
   for alert in alerts.json()['alerts']:
       requests.post(
           f"{OPSP_URL}/tasks",
           json={
               "title": alert['title'],
               "description": alert['description'],
               "priority": "high",
               "source": "MoneyRadar"
           }
       )
   ```

2. **Dashboard Widget**
   Embed MRR chart in OPSP dashboard:
   ```html
   <iframe src="http://localhost:5000/api/revenue/snapshots?days=30"></iframe>
   ```

## API Integration Examples

### Get Upgrade Candidates for Email Campaign

```python
import requests

# Get mismatches
response = requests.get('http://localhost:5000/api/analysis/mismatches')
data = response.json()

upgrade_candidates = data['upgrade_candidates']

for customer in upgrade_candidates:
    if customer['utilization'] > 0.8:  # Over 80% usage
        # Add to email campaign
        print(f"Email {customer['customer_id']} about upgrade")
        print(f"  Current: {customer['plan_name']} (${customer['mrr']}/mo)")
        print(f"  Usage: {customer['utilization']*100:.1f}%")
```

### Build Custom Dashboard

```python
import requests
from datetime import datetime, timedelta

# Get 30-day MRR trend
snapshots = requests.get(
    'http://localhost:5000/api/revenue/snapshots?days=30'
).json()['snapshots']

# Get current alerts
alerts = requests.get('http://localhost:5000/api/alerts').json()['alerts']

# Build dashboard data
dashboard = {
    'current_mrr': snapshots[0]['total_mrr'],
    'mrr_trend': [s['total_mrr'] for s in snapshots],
    'critical_alerts': len([a for a in alerts if a['severity'] == 'critical']),
    'opportunities': len([a for a in alerts if a['type'] == 'usage_mismatch_high'])
}
```

### Automated Weekly Report

```python
from datetime import datetime
import requests

def weekly_revenue_report():
    # Get data
    mrr = requests.get('http://localhost:5000/api/revenue/mrr').json()
    mismatches = requests.get('http://localhost:5000/api/analysis/mismatches').json()
    alerts = requests.get('http://localhost:5000/api/alerts').json()
    
    # Format report
    report = f"""
    Weekly Revenue Intelligence Report
    {datetime.now().strftime('%Y-%m-%d')}
    
    📊 Current MRR: ${mrr['current_mrr']:,.2f}
    📈 New MRR: ${mrr['latest_snapshot']['new_mrr']:,.2f}
    📉 Churned MRR: ${mrr['latest_snapshot']['churned_mrr']:,.2f}
    
    🎯 Opportunities:
    - {len(mismatches['upgrade_candidates'])} upgrade candidates
    - Potential additional MRR: $XXX
    
    ⚠️  Risks:
    - {len([a for a in alerts['alerts'] if a['severity'] == 'critical'])} critical alerts
    - Require immediate attention
    
    💡 Top Action Items:
    1. Contact top 3 upgrade candidates
    2. Investigate critical payment failures
    3. Review declining usage customers
    """
    
    # Send via email or Slack
    return report

# Run weekly
if __name__ == '__main__':
    print(weekly_revenue_report())
```

## Best Practices

1. **Act on Signals, Don't Just Monitor**
   - Every upgrade candidate should get outreach
   - Every critical alert needs action
   
2. **Document Experiment Outcomes**
   - Prevents repeating failed experiments
   - Builds institutional knowledge
   
3. **Score Before Selling**
   - Don't upsell "likely to churn" customers
   - Fix issues first
   
4. **Regular Cadence**
   - Daily: Check critical alerts
   - Weekly: Review opportunities
   - Monthly: Analyze experiments
   
5. **Keep It Simple**
   - This is not BI software
   - Focus on actionable insights
   - Ignore vanity metrics

## Metrics That Matter

**Track Weekly:**
- Upgrade candidate conversion rate
- Average time from alert to action
- Experiment win rate

**Ignore:**
- Total customer count (use Stripe)
- Detailed funnel analytics (use analytics tool)
- Session data (not revenue-related)

## Getting Help

1. Check logs: `journalctl -u moneyradar -f`
2. Verify database: `psql $DATABASE_URL`
3. Test API: `curl http://localhost:5000/health`
4. Review Stripe events: Stripe Dashboard → Events
