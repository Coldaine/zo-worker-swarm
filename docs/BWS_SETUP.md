# Bitwarden Secrets Manager Setup Guide

This guide walks you through setting up Bitwarden Secrets Manager (BWS) to automatically manage API keys for zo-worker-swarm.

## Why Use BWS?

✅ **Automatic Secret Injection** - No need to manually set environment variables
✅ **Secure Storage** - API keys encrypted in Bitwarden vault
✅ **Easy Rotation** - Update secrets in one place, automatically available everywhere
✅ **No Files** - Secrets never written to disk
✅ **Team Sharing** - Share secrets securely with machine accounts

---

## Prerequisites

1. **Bitwarden Account** - Free personal or organization account
2. **Bitwarden Secrets Manager Access** - Free tier includes:
   - 2 users
   - 3 machine accounts
   - Unlimited secrets

---

## Step 1: Sign Up for Secrets Manager

1. Go to https://bitwarden.com/products/secrets-manager/
2. Click "Get Started" or log into your existing Bitwarden account
3. Navigate to **Secrets Manager** in the web vault
4. Accept the free trial or free tier

---

## Step 2: Create a Project

Projects organize related secrets. We'll create one for zo-worker-swarm.

1. In the Bitwarden web vault, go to **Secrets Manager** → **Projects**
2. Click **New Project**
3. Name it: `zo-worker-swarm` or `AI-API-Keys`
4. Click **Save**
5. **Copy the Project ID** (you'll need this later)

---

## Step 3: Add Secrets

Add your API keys as secrets in the project:

### Required Secrets

Create the following secrets with **exact names** (case-sensitive):

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `ZAI_API_KEY` | Z.ai API key | `2c21c2ee...` |
| `XAI_API_KEY` | X.AI (Grok) API key | `xai-LEQat...` |
| `OPENROUTER_API_KEY` | OpenRouter API key | `sk-or-v1-...` |

### Optional Secrets

If using additional models, add these:

| Secret Name | Description |
|-------------|-------------|
| `GEMINI_API_KEY` | Google Gemini API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `CEREBRAS_API_KEY` | Cerebras API key |

### How to Add Secrets

1. Go to **Secrets Manager** → **Secrets**
2. Click **New Secret**
3. Fill in:
   - **Name**: Exact secret name from table above (e.g., `ZAI_API_KEY`)
   - **Value**: Your actual API key
   - **Project**: Select your `zo-worker-swarm` project
4. Click **Save**
5. Repeat for all API keys

---

## Step 4: Create a Machine Account

Machine accounts are service accounts that can access secrets programmatically.

1. Go to **Secrets Manager** → **Machine Accounts**
2. Click **New Machine Account**
3. Name it: `zo-worker-swarm-machine` or `local-dev-machine`
4. Click **Save**

---

## Step 5: Grant Machine Account Access

Give the machine account permission to read your secrets:

1. Go to **Secrets Manager** → **Projects**
2. Click on your `zo-worker-swarm` project
3. Go to the **Machine Accounts** tab
4. Click **Add Machine Account**
5. Select your machine account
6. Set permission to **Read** (or **Read/Write** if you want to update secrets)
7. Click **Save**

---

## Step 6: Generate Access Token

This token authenticates the machine account:

1. Go to **Secrets Manager** → **Machine Accounts**
2. Click on your machine account
3. Click **Access Tokens** tab
4. Click **New Access Token**
5. **Copy the token** - You'll only see this once!
6. Store it securely (see below)

### Secure Token Storage

**Option A: Environment Variable (Quick)**
```bash
export BWS_ACCESS_TOKEN="your-token-here"
```

**Option B: Shell Profile (Persistent - Linux/macOS)**

Add to `~/.bashrc` or `~/.zshrc`:
```bash
export BWS_ACCESS_TOKEN="your-bws-token-here"
```

Then reload: `source ~/.bashrc`

**Option C: Shell Profile (Persistent - Windows)**

Add to PowerShell profile:
```powershell
$env:BWS_ACCESS_TOKEN = "your-bws-token-here"
```

**Option D: Keychain (Most Secure - macOS)**
```bash
# Store token
security add-generic-password -a "${USER}" -s bws_token -w "your-token-here"

# Add to ~/.zshrc
export BWS_ACCESS_TOKEN=$(security find-generic-password -a "${USER}" -s bws_token -w)
```

**Option E: Secret Tool (Most Secure - Linux)**
```bash
# Store token
secret-tool store --label='BWS Token' service bws user $USER

# Add to ~/.bashrc
export BWS_ACCESS_TOKEN=$(secret-tool lookup service bws user $USER)
```

---

## Step 7: Install Python SDK

```bash
cd E:\_projectsGithub\zo-worker-swarm
pip install -r requirements.txt
```

This installs `bitwarden-sdk` along with other dependencies.

---

## Step 8: Test the Integration

### Test 1: List Available Secrets

```bash
cd E:\_projectsGithub\zo-worker-swarm
python src/secrets_manager.py
```

**Expected output:**
```
✅ Connected to Bitwarden Secrets Manager
📦 Available secrets in BWS:
──────────────────────────────────────────────────────────
  • ZAI_API_KEY (Project: xxx-xxx-xxx)
    ID: secret-id-1
  • XAI_API_KEY (Project: xxx-xxx-xxx)
    ID: secret-id-2
  • OPENROUTER_API_KEY (Project: xxx-xxx-xxx)
    ID: secret-id-3
```

### Test 2: Run with Secrets

```bash
python scripts/run.py start-ccr
```

**Expected output:**
```
✅ Connected to Bitwarden Secrets Manager
✅ Injected 3 secrets into environment
🚀 Starting all CCR instances...
...
```

---

## Usage

Once configured, secrets are automatically loaded!

### Normal Usage

```bash
# No need to manually set API keys!
python scripts/run.py start-ccr
python scripts/run.py execute tasks/example_zo_tasks.yaml
```

### Manual Override

You can still override with environment variables:
```bash
export XAI_API_KEY="temporary-key-for-testing"
python scripts/run.py start-ccr
```

Environment variables take precedence over BWS secrets.

---

## Troubleshooting

### ⚠️ "BWS_ACCESS_TOKEN not set"

**Problem**: Token not in environment
**Solution**: Set `BWS_ACCESS_TOKEN` environment variable (see Step 6)

### ❌ "Failed to initialize Bitwarden SDK"

**Problem**: `bitwarden-sdk` not installed
**Solution**: `pip install bitwarden-sdk`

### ⚠️ "Secret 'ZAI_API_KEY' not found"

**Problem**: Secret doesn't exist in BWS or machine account lacks access
**Solutions**:
1. Verify secret exists in web vault
2. Check secret name is exact match (case-sensitive)
3. Verify machine account has access to the project
4. Run `python src/secrets_manager.py` to list available secrets

### ❌ "Unauthorized"

**Problem**: Invalid or expired access token
**Solutions**:
1. Regenerate access token in web vault
2. Update `BWS_ACCESS_TOKEN` environment variable
3. Verify token has no extra spaces or quotes

### ⚠️ Fallback to Environment Variables

If BWS fails, the system automatically falls back to environment variables:
```bash
export ZAI_API_KEY="your-key"
export XAI_API_KEY="your-key"
export OPENROUTER_API_KEY="your-key"
python scripts/run.py start-ccr
```

---

## Security Best Practices

✅ **Never commit BWS_ACCESS_TOKEN** - Add to `.gitignore`
✅ **Use keychain/secret-tool** - Don't store tokens in plain text
✅ **Rotate tokens regularly** - Generate new tokens periodically
✅ **Scope machine accounts** - Only grant access to necessary projects
✅ **Use Read-only access** - Unless you need to update secrets programmatically
✅ **Enable 2FA** - Protect your Bitwarden master account

❌ **Don't share access tokens** - Each machine/dev should have their own
❌ **Don't echo secrets** - They'll appear in logs and shell history
❌ **Don't commit .env files** - Even with BWS, keep .env in .gitignore

---

## Advanced: Multiple Environments

For dev/staging/prod environments, use separate projects:

```bash
# Store tokens
export BWS_DEV_TOKEN="dev-token"
export BWS_PROD_TOKEN="prod-token"

# Dev
BWS_ACCESS_TOKEN=$BWS_DEV_TOKEN python scripts/run.py start-ccr

# Prod
BWS_ACCESS_TOKEN=$BWS_PROD_TOKEN python scripts/run.py start-ccr
```

Or use project IDs:
```bash
export BWS_PROJECT_ID="dev-project-id"
python scripts/run.py start-ccr
```

---

## Need Help?

- **Bitwarden Docs**: https://bitwarden.com/help/secrets-manager-quick-start/
- **SDK Documentation**: https://github.com/bitwarden/sdk-sm/tree/main/languages/python
- **zo-worker-swarm Issues**: https://github.com/Coldaine/zo-worker-swarm/issues

---

## Summary

1. ✅ Create BWS project
2. ✅ Add API key secrets
3. ✅ Create machine account
4. ✅ Generate access token
5. ✅ Set `BWS_ACCESS_TOKEN` environment variable
6. ✅ Run `python scripts/run.py start-ccr`

**That's it!** Your API keys are now automatically managed by Bitwarden Secrets Manager. 🎉
