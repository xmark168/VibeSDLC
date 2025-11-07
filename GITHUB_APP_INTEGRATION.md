# GitHub App Integration - Implementation Guide

## Overview

GitHub App integration has been successfully implemented in VibeSDLC. This allows users to:
- Install the GitHub App on their GitHub account/organization
- Receive webhooks when the app is installed/uninstalled
- Link GitHub repositories to VibeSDLC projects
- Manage repository permissions through the GitHub App

## Database Schema

### New Table: `github_installations`

```sql
CREATE TABLE github_installations (
    id UUID PRIMARY KEY,
    installation_id INTEGER UNIQUE NOT NULL,
    account_login VARCHAR NOT NULL,
    account_type VARCHAR NOT NULL,  -- "User" or "Organization"
    repositories JSON,              -- Array of repository objects
    user_id UUID NOT NULL FOREIGN KEY,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
);
```

### Updated Table: `projects`

Added columns:
- `github_repository_id` (INTEGER, UNIQUE, NULLABLE)
- `github_repository_name` (VARCHAR, NULLABLE)
- `github_installation_id` (UUID, FOREIGN KEY, NULLABLE)

## Files Created/Modified

### Models (`services/ai-agent-service/app/models.py`)
- ✅ Added `GitHubAccountType` enum
- ✅ Added `GitHubInstallation` model
- ✅ Updated `Project` model with GitHub fields
- ✅ Updated `User` model with relationship to installations

### Schemas (`services/ai-agent-service/app/schemas.py`)
- ✅ `GitHubInstallationBase`, `GitHubInstallationCreate`, `GitHubInstallationUpdate`, `GitHubInstallationPublic`
- ✅ `GitHubRepository`, `GitHubRepositoriesPublic`
- ✅ `ProjectGitHubLink`, `ProjectGitHubUnlink`

### CRUD (`services/ai-agent-service/app/crud/github_installation.py`)
- ✅ `create_github_installation()`
- ✅ `get_github_installation()`
- ✅ `get_github_installation_by_installation_id()`
- ✅ `get_github_installations_by_user()`
- ✅ `count_github_installations_by_user()`
- ✅ `update_github_installation()`
- ✅ `delete_github_installation()`
- ✅ `delete_github_installation_by_installation_id()`

### Webhook Handler (`services/ai-agent-service/app/api/routes/github_webhook.py`)
- ✅ `POST /api/v1/github/webhook` - Main webhook endpoint
- ✅ Signature verification using HMAC-SHA256
- ✅ Event handlers:
  - `installation.created` - Save installation to database
  - `installation.deleted` - Remove installation from database
  - `installation_repositories.added` - Update repository list
  - `installation_repositories.removed` - Update repository list

### Repository Linking (`services/ai-agent-service/app/api/routes/github_repositories.py`)
- ✅ `GET /api/v1/github/repositories` - List available repositories
- ✅ `GET /api/v1/github/installations` - List user's installations
- ✅ `POST /api/v1/github/projects/{project_id}/link-repository` - Link repo to project
- ✅ `DELETE /api/v1/github/projects/{project_id}/unlink-repository` - Unlink repo from project

### Updated Services
- ✅ `services/ai-agent-service/app/api/service/github_app_client.py`
  - Added database session support
  - Added installation validation
  - Added revocation handling
  - Improved error logging

### Configuration
- ✅ Updated `services/ai-agent-service/app/core/config.py`
  - Added `GITHUB_APP_ID`
  - Added `GITHUB_APP_PRIVATE_KEY`
  - Added `GITHUB_WEBHOOK_SECRET`

### Database Migration
- ✅ Created `services/ai-agent-service/app/alembic/versions/add_github_integration.py`
  - Creates `github_installations` table
  - Adds GitHub columns to `projects` table
  - Includes rollback support

### API Router
- ✅ Updated `services/ai-agent-service/app/api/main.py`
  - Registered `github_webhook` router
  - Registered `github_repositories` router

## Setup Instructions

### 1. Create GitHub App

1. Go to https://github.com/settings/apps
2. Click "New GitHub App"
3. Fill in the form:
   - **App name**: VibeSDLC
   - **Homepage URL**: https://your-domain.com
   - **Webhook URL**: https://your-domain.com/api/v1/github/webhook
   - **Webhook secret**: Generate a random secret (save this!)
   - **Permissions**:
     - Repository: Read access to code, issues, pull requests
     - Organization: Read access to members
   - **Events**: Select "Installation" and "Installation repositories"

4. Generate a private key and save it

### 2. Configure Environment Variables

Update `.env` file:

```bash
GITHUB_APP_ID=your-app-id
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----
GITHUB_WEBHOOK_SECRET=your-webhook-secret
```

### 3. Run Database Migration

```bash
cd services/ai-agent-service
alembic upgrade head
```

### 4. Restart Backend

```bash
cd services/ai-agent-service
uv run uvicorn app.main:app --reload --port 8001
```

## API Endpoints

### Webhook
- `POST /api/v1/github/webhook` - Receive GitHub events (no auth required)

### Installations
- `GET /api/v1/github/installations` - List user's GitHub App installations
  - Query params: `skip`, `limit`
  - Returns: List of installations with repository counts

### Repositories
- `GET /api/v1/github/repositories` - List available repositories
  - Query params: `installation_id` (optional), `skip`, `limit`
  - Returns: List of repositories

### Project Linking
- `POST /api/v1/github/projects/{project_id}/link-repository` - Link repository to project
  - Body: `{ "github_repository_id": int, "github_repository_name": str, "github_installation_id": UUID }`
  - Returns: Updated project

- `DELETE /api/v1/github/projects/{project_id}/unlink-repository` - Unlink repository
  - Returns: Updated project

## Testing

### 1. Test Webhook Signature Verification

```bash
curl -X POST http://localhost:8001/api/v1/github/webhook \
  -H "X-GitHub-Event: installation" \
  -H "X-Hub-Signature-256: sha256=invalid" \
  -H "Content-Type: application/json" \
  -d '{"action": "created", "installation": {"id": 123}}'
```

Expected: 401 Unauthorized

### 2. Test Installation Creation

Use GitHub App's test webhook feature or simulate with:

```bash
# Generate valid signature
python3 -c "
import hmac, hashlib, json
secret = 'your-webhook-secret'
payload = json.dumps({'action': 'created', 'installation': {'id': 123, 'account': {'login': 'test', 'type': 'User'}}, 'repositories': []})
sig = 'sha256=' + hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
print(sig)
"

curl -X POST http://localhost:8001/api/v1/github/webhook \
  -H "X-GitHub-Event: installation" \
  -H "X-Hub-Signature-256: sha256=<generated-signature>" \
  -H "Content-Type: application/json" \
  -d '<payload>'
```

### 3. Test Repository Listing

```bash
curl -X GET http://localhost:8001/api/v1/github/repositories \
  -H "Authorization: Bearer <access-token>"
```

### 4. Test Project Linking

```bash
curl -X POST http://localhost:8001/api/v1/github/projects/<project-id>/link-repository \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "github_repository_id": 123456,
    "github_repository_name": "owner/repo",
    "github_installation_id": "<installation-uuid>"
  }'
```

## Error Handling

### Installation Revoked
- When GitHub App is uninstalled, webhook triggers `installation.deleted`
- Installation record is deleted from database
- Projects linked to that installation will have `github_installation_id` set to NULL

### Invalid Webhook Signature
- Returns 401 Unauthorized
- Check `GITHUB_WEBHOOK_SECRET` configuration

### Installation Not Found
- Returns 404 Not Found
- Verify installation exists in database

## Security Considerations

1. **Webhook Signature Verification**: All webhooks are verified using HMAC-SHA256
2. **User Authorization**: All endpoints require authentication
3. **Ownership Validation**: Users can only access their own installations and projects
4. **Installation Validation**: GitHubAppClient validates installation exists before fetching tokens
5. **Token Expiration**: Installation tokens are automatically refreshed (1-hour expiry)

## Next Steps

1. ✅ Test webhook integration with GitHub
2. ✅ Test repository listing and linking
3. ✅ Implement GitHub Actions integration (optional)
4. ✅ Add repository sync functionality (optional)
5. ✅ Add pull request tracking (optional)

