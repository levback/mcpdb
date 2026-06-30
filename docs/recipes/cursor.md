# Recipe: Cursor

Add this MCP server block in `mcp.json`:

```json
{
  "mcpServers": {
    "mcpdb": {
      "command": "uv",
      "args": [
        "run",
        "python",
        "-m",
        "mcpdb.cli",
        "serve",
        "--transport",
        "stdio",
        "--config",
        "examples/01-minimal/mcpdb.yaml"
      ]
    }
  }
}
```
