# Recipe: Claude Desktop

Use stdio transport for local execution.

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
