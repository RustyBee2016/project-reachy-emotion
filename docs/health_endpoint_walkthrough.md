# Health endpoint dependency injection walkthrough

This guide explains, step by step, how the `/health` and `/ready` endpoints in `apps/api/app/routers/health.py` obtain filesystem paths through dependency injection and use them to verify the service state.

## 1) Declaring a dependency

```python
@router.get("/health", response_model=HealthCheckResponse)
async def health_check(
    request: Request,
    config: AppConfig = Depends(get_config)
) -> HealthCheckResponse:
```

- `@router.get` registers an HTTP **GET** endpoint under the router’s prefix (`/api/v1`).
- The function parameters include `config: AppConfig = Depends(get_config)`. This is a FastAPI **dependency** declaration: instead of building `AppConfig` manually, you ask FastAPI to call `get_config` for each request and inject its return value into `config`.
- The `Depends` wrapper is the signal to FastAPI’s dependency system. It says, “resolve this argument by running `get_config`.”

## 2) What `AppConfig` contains

`AppConfig` (defined in `apps/api/app/config.py`) holds already-parsed filesystem locations, each stored as a `pathlib.Path` object (e.g., `videos_root`, `temp_path`, `train_path`). Because `get_config` is executed per request (or cached per app lifecycle if configured that way), the route handler always receives ready-to-use `Path` objects instead of raw strings.

## 3) Using the injected paths

Inside the endpoint body, the injected `config` object is immediately used to reach the filesystem:

```python
if config.videos_root.exists() and config.videos_root.is_dir():
    checks["videos_root"] = {
        "status": "ok",
        "path": str(config.videos_root)
    }
```

- `config.videos_root` is a `Path` pointing to the root video directory on disk.
- Calling `.exists()` and `.is_dir()` performs real filesystem checks to confirm the directory is reachable.
- The resulting status and the actual path string are written into the `checks` dictionary that will be returned to the client.

## 4) Looping over required subdirectories

The endpoint gathers additional `Path` objects from the same `config` instance:

```python
required_dirs = {
    "temp": config.temp_path,
    "dataset_all": config.dataset_path,
    "train": config.train_path,
    "test": config.test_path,
    "thumbs": config.thumbs_path,
    "manifests": config.manifests_path,
}
```

It then iterates through these paths, counting how many exist and are directories:

```python
for name, path in required_dirs.items():
    if path.exists() and path.is_dir():
        dirs_ok += 1
```

The summary (`accessible` vs `total`) is placed in the JSON response so operators can see which storage locations are available.

## 5) Ready endpoint reuses the same dependency

The `/ready` endpoint also declares `config: AppConfig = Depends(get_config)` and simply calls `health_check`. That means readiness presently relies on the same path checks. Future readiness logic (e.g., database connectivity) can reuse the same dependency pattern: add new checks using values retrieved from `config` or other dependencies without hardcoding paths.

## Takeaway

Dependency injection keeps the endpoint function free of manual setup code: you declare **what you need** (`AppConfig`), FastAPI resolves it (`get_config`), and you consume its `Path` attributes to touch the filesystem. This separates configuration loading from request handling and makes the code easier to test and extend.
