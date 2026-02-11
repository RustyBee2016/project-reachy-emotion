# Tutorial 14: pyproject.toml Cleanup

> **Priority**: LOW — Project metadata hygiene
> **Time estimate**: 2-3 hours
> **Difficulty**: Easy
> **Prerequisites**: None

---

## Why This Matters

The `pyproject.toml` has several issues:
- Project name says `"reachy-local-08-3"` but codebase is 08.4.2
- Missing `python-dotenv` (used everywhere)
- Missing `pytest-asyncio` in dev dependencies
- No CLI entry points defined

---

## Changes to Make

Open `pyproject.toml` and apply these fixes:

### 1. Update Project Name and Version

Find:
```toml
name = "reachy-local-08-3"
```

Replace with:
```toml
name = "reachy-local-08-4-2"
version = "0.8.4.2"
```

### 2. Add Missing Dependencies

In the main `[project.dependencies]` section, add:
```toml
"python-dotenv>=1.0",
```

In the dev optional dependencies, add:
```toml
"pytest-asyncio>=0.23",
"facenet-pytorch>=2.5",
```

### 3. Add Entry Points

Add this section:
```toml
[project.scripts]
reachy-api = "apps.api.app.main:run"
reachy-train = "scripts.run_training:main"
```

### 4. Add Pytest Configuration

Add or update:
```toml
[tool.pytest.ini_options]
markers = [
    "unit: Pure logic tests with no external dependencies",
    "integration: Tests requiring database or API",
    "slow: Tests that take more than 30 seconds",
    "external: Tests requiring external services",
]
testpaths = ["tests"]
asyncio_mode = "auto"
```

### 5. Verify

```bash
pip install -e ".[dev,trainer]"
python -c "import dotenv; print('python-dotenv OK')"
```

---

## Checklist

- [ ] Project name updated to `reachy-local-08-4-2`
- [ ] `python-dotenv` added to dependencies
- [ ] `pytest-asyncio` added to dev dependencies
- [ ] Pytest markers configured
- [ ] `pip install -e ".[dev]"` succeeds
