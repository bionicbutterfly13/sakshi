## Summary

<!-- What changed? -->

## Type

- [ ] Bug fix
- [ ] Feature
- [ ] Documentation
- [ ] Tests / CI
- [ ] Maintenance

## Boundary Checklist

- [ ] Package core stays free of host runtime imports.
- [ ] Runtime dependencies enter through protocols, DTOs, or constructor arguments.
- [ ] Public identifiers stay Sakshi-native.
- [ ] Host-specific behavior remains in adapters outside this package.
- [ ] README / INSPIRATION / docs are updated if public behavior changed.

## Verification

```bash
make PYTHON=python all
python -m pip install --dry-run .
python -m build
python -m twine check dist/*
```

## Notes

<!-- Remaining risks, follow-ups, or intentionally out-of-scope items. -->
