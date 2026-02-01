# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via:

1. **GitHub Security Advisories** (preferred)
   - Go to https://github.com/M-Soho/MoneyRadar/security/advisories
   - Click "Report a vulnerability"

2. **Email** (if GitHub is unavailable)
   - Create a private GitHub issue with subject "SECURITY"

### What to Include

Please include:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)
- Your contact information

### Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 1 week
- **Fix Timeline**: Depends on severity
  - Critical: Within 7 days
  - High: Within 30 days
  - Medium: Within 90 days
  - Low: Next release

## Security Best Practices

### For Users

1. **Never commit `.env` files** - Use `.env.example` as template
2. **Rotate secrets regularly** - Change `STRIPE_WEBHOOK_SECRET` quarterly
3. **Use strong SECRET_KEY** - Generate with `openssl rand -base64 32`
4. **Verify webhook signatures** - Always required in production
5. **Use HTTPS** - Required for webhook endpoints
6. **Limit API access** - Add authentication to API endpoints
7. **Regular backups** - Daily PostgreSQL backups
8. **Keep dependencies updated** - Run `pip install -U -r requirements.txt`

### Environment Variables

These should NEVER be committed:
- `STRIPE_API_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `SECRET_KEY`
- `DATABASE_URL` (with credentials)

### Webhook Security

1. Always verify Stripe webhook signatures in production
2. Use HTTPS endpoints only
3. Implement rate limiting
4. Log all webhook events for audit trail

### Database Security

1. Use strong passwords for PostgreSQL
2. Restrict database access by IP
3. Enable SSL for database connections
4. Regular automated backups
5. Encrypt backups at rest

## Known Security Considerations

1. **API Authentication**: Currently no auth on API endpoints - add before production
2. **Rate Limiting**: Not implemented - vulnerable to abuse
3. **Input Validation**: Limited - sanitize all user inputs
4. **SQL Injection**: Protected by SQLAlchemy ORM, but verify custom queries

## Security Updates

Security updates will be released as patch versions (e.g., 1.0.1).

Subscribe to releases to be notified: https://github.com/M-Soho/MoneyRadar/releases

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine affected versions
2. Audit code to find similar problems
3. Prepare fixes for all supported versions
4. Release new versions as soon as possible
5. Publicly disclose the issue after fix is deployed

## Contact

For security concerns, use GitHub Security Advisories or create a private issue.

**Do not use public issues, discussions, or social media for security reports.**
