# 12 - Deployment

## Overview
Docker multi-arch build, GitHub Actions CI/CD pipeline ve Home Assistant Add-on repository yayınlama.

## Workflow Type
**feature** - CI/CD ve deployment

## Task Scope
Build pipeline, container registry ve add-on repository.

### GitHub Actions Workflows
```yaml
# .github/workflows/build.yml
name: Build
on:
  push:
    branches: [main]
  pull_request:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker build .
      - name: Run tests
        run: pytest
      - name: Security scan
        uses: aquasecurity/trivy-action@master
```

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags: ['v*']

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - name: Build multi-arch
        uses: docker/build-push-action@v5
        with:
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.ref_name }}
```

### Add-on Repository Structure
```
repository/
├── smart_motion_detector/
│   ├── config.yaml
│   ├── CHANGELOG.md
│   ├── DOCS.md
│   ├── icon.png
│   └── logo.png
└── repository.yaml
```

### repository.yaml
```yaml
name: Smart Motion Detector Repository
url: https://github.com/repo/ha-addons
maintainer: Developer Name
```

## Requirements
1. Multi-arch Docker build (amd64, arm64)
2. GitHub Actions workflows
3. GHCR image push
4. Add-on repository setup
5. Semantic versioning
6. Security scanning

## Files to Modify
- `Dockerfile` - Multi-arch optimizasyonu

## Files to Reference
- `config.yaml`
- `requirements.txt`

## Success Criteria
- [ ] Docker build başarılı (amd64 + aarch64)
- [ ] GitHub Actions çalışıyor
- [ ] Image GHCR'da yayınlandı
- [ ] Add-on repo oluşturuldu
- [ ] Version tagging çalışıyor
- [ ] Security scan geçiyor

## QA Acceptance Criteria
- CI pipeline tüm adımları geçmeli
- Multi-arch image çalışmalı
- Add-on HA'dan yüklenebilmeli

## Dependencies
- 08-main-app
- 09-testing
- 10-ha-integration

## Notes
- GitHub Container Registry kullanılacak
- Dependabot eklenebilir
- Release notes otomatik oluşturulabilir
