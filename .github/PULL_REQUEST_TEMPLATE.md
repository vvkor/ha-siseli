## Summary

- describe the user-facing change
- note any SDK dependency or release impact

## Validation

- [ ] `ruff check custom_components/`
- [ ] `python -m pytest tests/ --tb=short -q`
- [ ] README / changelog / roadmap updated when needed

## Checklist

- [ ] coordinator remains the only runtime data path
- [ ] no secrets added to code, docs, tests, or logs
- [ ] Home Assistant and HACS compatibility considered
