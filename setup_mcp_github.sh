#!/bin/bash
# ============================================================
#  GitHub MCP Server Setup — Panaversity AI Employee
#  Reads token from .env.github and registers with Claude Code
# ============================================================

ENV_FILE="$(dirname "$0")/.env.github"

echo ""
echo "  GitHub MCP Server Setup"
echo "  ───────────────────────"

# Load token from .env.github
if [ ! -f "$ENV_FILE" ]; then
  echo "  ERROR: .env.github not found at $ENV_FILE"
  exit 1
fi

source "$ENV_FILE"

if [ -z "$GITHUB_PERSONAL_ACCESS_TOKEN" ] || [ "$GITHUB_PERSONAL_ACCESS_TOKEN" = "paste_your_token_here" ]; then
  echo "  ERROR: Token not set in .env.github"
  echo "  Edit .env.github and replace 'paste_your_token_here' with your real GitHub PAT"
  echo ""
  echo "  Create a token at: https://github.com/settings/tokens"
  echo "  Required scopes: repo, read:user, read:org"
  exit 1
fi

echo "  Token found. Registering GitHub MCP server with Claude Code..."
echo ""

# Remove existing github MCP if present (clean re-register)
claude mcp remove github 2>/dev/null && echo "  Removed existing github MCP entry."

# Register the GitHub MCP server (user scope — available across all projects)
claude mcp add github \
  --scope user \
  -e GITHUB_PERSONAL_ACCESS_TOKEN="$GITHUB_PERSONAL_ACCESS_TOKEN" \
  -- npx -y @modelcontextprotocol/server-github

if [ $? -eq 0 ]; then
  echo ""
  echo "  SUCCESS: GitHub MCP server registered."
  echo ""
  echo "  Next steps:"
  echo "  1. Restart Claude Code (close and reopen)"
  echo "  2. Run: claude mcp list  — to verify"
  echo "  3. Claude can now create issues, PRs, push files via MCP"
else
  echo ""
  echo "  ERROR: Registration failed. Check token scopes and try again."
  exit 1
fi
