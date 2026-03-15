# CI/CD

## Workflows

| Workflow                                        | Trigger                                                   | Runner                     | Output                                |
|-------------------------------------------------|-----------------------------------------------------------|----------------------------|---------------------------------------|
| `integration-workflow.yml`                      | `phantom/**` push (retro), manual                         | workflow_call              | Test reports                          |
| `test-development-integration.yml`              | manual, workflow_call                                     | ubuntu-latest              | Test artifacts                        |
| `test-production-integration.yml`               | manual, workflow_call                                     | ubuntu-latest              | Test artifacts                        |
| `release-workflow.yml`                          | manual (version_id)                                       | ubuntu-latest              | GitHub Release (core-v*)              |
| `deploy-phantom-docs.yml`                       | `documentation/**` push (retro), manual                   | ubuntu-latest, self-hosted | Cloudflare Pages (phantom-docs-retro) |
| `deploy-phantom-www.yml`                        | `tools/phantom-www/**` push (retro), manual               | ubuntu-latest, self-hosted | Cloudflare Pages (phantom-www-retro)  |
| `deploy-phantom-install.yml`                    | `tools/phantom-install/**` push (retro), manual           | self-hosted                | Cloudflare Worker                     |
| `phantom-wizard-hidden-deployment-workflow.yml` | `tools/phantom-deployment-wizard/**` push (retro), manual | ubuntu-latest              | Signed package deploy                 |
| `mac-build.yml`                                 | `tools/client-applications/mac/**` push (retro)           | macos-26                   | Build validation                      |
| `mac-deploy-dmg.yml`                            | `dmg-v*` tag, workflow_call                               | macos-26                   | Signed DMG artifact                   |
| `mac-release.yml`                               | `mac-v*` tag                                              | ubuntu-latest + macos-26   | GitHub Release (mac-v*)               |

## Branch Strategy

All workflows run on the `retro` branch. Tag-triggered workflows (`mac-v*`, `dmg-v*`, `core-v*`) are branch-agnostic and triggered manually.

## Deployment Targets

| Service | Project | Domain |
|---------|---------|--------|
| Docs | `phantom-docs-retro` | retro-docs.phantom.tc |
| WWW | `phantom-www-retro` | retro.phantom.tc |
| Install | Cloudflare Worker | install.phantom.tc |

## Test Reports

Test artifacts are uploaded to GitHub Actions (90-day retention). Cloudflare Pages deployment for test reports has been removed.
