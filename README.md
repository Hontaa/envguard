<p align="center">
  <img src="envguard_banner.svg" alt="envguard banner" width="100%"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11-3776ab?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/license-MIT-2ea043?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/tests-7%20passed-2ea043?style=for-the-badge"/>
  <img src="https://img.shields.io/github/actions/workflow/status/Hontaa/envguard/ci.yml?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/API-FastAPI-58a6ff?style=for-the-badge"/>
</p>

<h1 align="center">envguard</h1>
<p align="center"><b>Python-native validator for <code>.env</code> / config files.</b><br/>
Catch misconfig and secret leaks <b>before</b> they hit production.</p>

---

## Why

`python-dotenv` only *loads* env files — it won't tell you `API_URL` is missing or
`PORT` is `"abc"`. `dotenv-linter` is a great Rust CLI, but there is **no Python
library + no hosted service** combining schema validation, secret-leak scanning,
and drift history. **envguard** does all three, self-hostable in 30 seconds.

## Install

```bash
# from git (not yet on PyPI)
pip install git+https://github.com/Hontaa/envguard.git
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
print(result.ok)          # False
for e in result.errors:
    print(e.key, e.message)

print(find_leaks(env))    # [('AWS_KEY', 'AWS_ACCESS_KEY')]
```

### Drift (staging vs prod)

```python
staging = parse_env("A=1\nB=2")
prod    = parse_env("A=1\nB=9\nC=3")
print(diff_envs(staging, prod))
# {'added': {'C': '3'}, 'removed': {}, 'changed': {'B': ('2', '9')}}
```

## CLI

```bash
envguard check .env --schema schema.json     # schema validation
envguard scan  .env                          # secret-leak scan
envguard diff  staging.env prod.env          # drift between environments
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

Example response (`POST /v1/validate`):

```json
{
  "ok": false,
  "errors": [
    {"key": "API_URL", "message": "must be a valid URL"},
    {"key": "PORT", "message": "expected int, got 'abc'"}
  ]
}
```

## Paid layer (hosted SaaS)

The open core is MIT. The hosted dashboard adds, behind an API key:

- team alerting when a secret leaks into a pushed `.env`
- historical drift timeline across environments
- CI integration (fail the build on new `unknown` keys)

Self-host the API above, or use the managed service (link in releases).

## License

MIT
