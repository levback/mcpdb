# Recipe: LangChain integration

This example shows a lightweight client call to MCP HTTP transport.

```python
import httpx

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "db_query",
        "arguments": {
            "profile": "main",
            "query": "SELECT 1 as ok",
            "params": {}
        }
    }
}

response = httpx.post("http://127.0.0.1:8080/mcp", json=payload, timeout=10.0)
response.raise_for_status()
print(response.json())
```

Use bearer auth headers in production. # OWASP A01
