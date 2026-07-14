# envguard

Python-native validator for `.env` / config files. Catch misconfig and
secret leaks **before** they hit production.

> Free OSS core (this repo) + optional hosted dashboard (team alerts,
> secret-leak history, staging↔prod drift tracking) — see *Paid layer*.

## Why

`python-dotenv` only *loads* env files — it does not tell you that
`API_URL` is missing or that `PORT` is `"abc"`. `dotenv-linter` is a
great Rust CLI but there is **no Python library + no hosted service**
that combines schema validation, secret-leak scanning, and drift history.
envguard does all three, and you can self-host the API in 30 seconds.

## Install

```bash
pip install envguard
```

## Quick start

```python
from envguard import parse_env, validate, find_leaks, diff_envs

text = "API_URL=not-a-url\nPORT=abc\nAWS_KEY=AKIAIOSFODNN7EXAMPLE"
env = parse_env(text)

schema = {
    "API_URL": {"required": True, "type": "url"},
    "PORT":    {"required": True, "type": "int"},
}
result = validate(env, schema)
print(result.ok)            # False
for e in result.errors:
    print(e.key, e.message) # API_URL expected url...; PORT expected int...

print(find_leaks(env))      # [('AWS_KEY', 'AWS_ACCESS_KEY')]
```

### Drift detection (staging vs prod)

```python
staging = parse_env("A=1\nB=2")
prod    = parse_env("A=1\nB=9\nC=3")
print(diff_envs(staging, prod))
# {'added': {'C': '3'}, 'removed': {}, 'changed': {'B': ('2', '9')}}
```

## CLI

```bash
envguard check .env --schema schema.json
envguard scan .env
envguard diff staging.env prod.env
```

## API (self-hosted)

```bash
ENVGUARD_KEYS=sk_demo uvicorn api_server:app --port 8000
```

| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /v1/validate` | none (open core) | schema validation |
| `POST /v1/scan` | API key | secret-leak scan |
| `POST /v1/drift` | API key | snapshot + compare, stores history |

## Paid layer (hosted SaaS)

The open core is MIT. The hosted dashboard adds, behind an API key:

- team alerting when a secret leaks into a pushed `.env`
- historical drift timeline across environments
- CI integration (fail the build on new `unknown` keys)

Self-host the API above, or use the managed service (link in releases).

## License

MIT
