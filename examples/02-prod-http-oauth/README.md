# Example 02: HTTP + OAuth

## Run

```bash
docker compose up --build
```

## Generate local keypair

```bash
openssl genrsa -out jwt-private.pem 2048
openssl rsa -in jwt-private.pem -pubout -out jwt-public.pem
```

This stack demonstrates HTTP transport with bearer-token validation and explicit policy files.
