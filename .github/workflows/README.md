# GitHub Actions Workflows

## Docker Image CI/CD

### Setup Instructions

#### 1. Create Docker Hub Access Token
1. Go to https://hub.docker.com/settings/security
2. Click "New Access Token"
3. Name: `github-actions-jerp`
4. Access permissions: Read, Write, Delete
5. Copy the generated token (you won't see it again!)

#### 2. Add Secrets to GitHub Repository
1. Go to repository Settings → Secrets and variables → Actions
2. Add two secrets:
   - Name: `DOCKERHUB_USERNAME`
     Value: Your Docker Hub username (e.g., `juliocesarmendeztobar`)
   
   - Name: `DOCKERHUB_TOKEN`
     Value: The access token from step 1

#### 3. Verify Workflow
- Push to `main` branch or create a PR
- Check Actions tab to see the workflow run
- Verify images appear at https://hub.docker.com/r/juliocesarmendeztobar/jerp-backend

### Image Tagging Strategy

The workflow automatically creates multiple tags:

- `latest` - Latest commit on main branch
- `main-abc1234` - Branch name + short SHA
- `pr-123` - Pull request number (for PRs)
- `sha-abc1234567890...` - Full commit SHA

### Using Published Images

Update `docker-compose.yml` to use published images:

```yaml
services:
  backend:
    image: juliocesarmendeztobar/jerp-backend:latest
    # Remove or comment out the build section
    # build:
    #   context: .
    #   dockerfile: Dockerfile
```

Then deploy with:
```bash
docker-compose pull
docker-compose up -d
```
