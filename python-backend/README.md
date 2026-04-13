# PPT Studio Python Backend

Minimal FastAPI sidecar skeleton for `Phase 1 -> 1.2`.

## Requirements

- Python 3.12+
- `uv`

## Install dependencies

```bash
uv sync
```

## Run the backend

```bash
uv run fastapi dev app/main.py --port 18922
```

## Health check

```bash
curl http://127.0.0.1:18922/health
```

Expected response:

```json
{"status":"ok","version":"0.1.0"}
```

## Supported environment variables

- `PPT_STUDIO_ENV`: runtime environment, defaults to `development`
- `PPT_STUDIO_HOST`: bind host, defaults to `127.0.0.1`
- `PPT_STUDIO_PORT`: default backend port, defaults to `18922`
- `PPT_STUDIO_DATA_DIR`: backend data directory, defaults to `python-backend/data`
