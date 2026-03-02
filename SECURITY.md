# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability in Ira, please report it responsibly.

### How to Report

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please email security concerns to: **security@machinecraft.in**

Include the following information:
- Type of vulnerability (e.g., authentication bypass, injection, data exposure)
- Location of the affected code (file path, function name)
- Steps to reproduce the issue
- Potential impact assessment
- Any suggested fixes (optional)

### What to Expect

1. **Acknowledgment**: We will acknowledge receipt within 48 hours
2. **Assessment**: We will assess the vulnerability within 7 days
3. **Resolution**: Critical issues will be addressed within 30 days
4. **Disclosure**: We will coordinate public disclosure timing with you

### Scope

The following are in scope:
- Authentication and authorization issues
- Data exposure vulnerabilities
- Injection vulnerabilities (SQL, command, etc.)
- API security issues
- Credential/secret exposure
- Memory safety issues

The following are **out of scope**:
- Social engineering attacks
- Physical security issues
- Issues in third-party dependencies (report to the maintainer)
- Issues requiring physical access to hardware

## Security Best Practices

When deploying Ira, follow these guidelines:

### Environment Variables

- Never commit `.env` files to version control
- Use a secrets manager in production (e.g., AWS Secrets Manager, HashiCorp Vault)
- Rotate API keys regularly
- Use separate credentials for development and production

### Network Security

- Run Qdrant and PostgreSQL on private networks
- Use TLS for all external connections
- Implement rate limiting for API endpoints
- Use firewall rules to restrict database access

### Authentication

- Use strong, unique API keys
- Implement token rotation
- For Telegram: Only allow authorized chat IDs
- For Email: Use OAuth 2.0, not password authentication

### Data Protection

- Encrypt sensitive data at rest
- Implement access logging
- Regular backup with encryption
- Data retention policies

### Monitoring

- Enable audit logging
- Monitor for unusual access patterns
- Set up alerts for failed authentication attempts
- Regular security audits

## Dependency Security

We use the following tools to monitor dependency security:

```bash
# Check for known vulnerabilities
pip install safety
safety check

# Run security linter
pip install bandit
bandit -r openclaw/agents/ira/
```

## Security Updates

Security updates will be released as patch versions (e.g., 1.0.1, 1.0.2). 

Subscribe to GitHub releases to be notified of security updates.

---

Thank you for helping keep Ira and its users safe!
