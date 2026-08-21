# Security policy

The local agent follows least privilege.

## Allowed automatically

- Read project files
- Create and edit files inside an approved workspace
- Run tests and development servers
- Read public web pages
- Inspect browser pages

## Approval required

- Sending messages or publishing content
- Installing software or packages outside the workspace
- Changing production systems
- Using credentials against a new service

## Never autonomous by default

- Financial transactions
- Destructive system operations
- Deleting user data outside the workspace
- Exposing secrets

Secrets belong in local environment variables or a secret manager, never in Git.
