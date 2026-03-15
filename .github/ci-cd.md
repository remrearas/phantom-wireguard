# CI/CD

| Workflow                                        | Trigger                                                               | Runner                     | Output                     |
|-------------------------------------------------|-----------------------------------------------------------------------|----------------------------|----------------------------|
| `auto-close-pr.yml`                             | pull_request_target (opened)                                          | ubuntu-latest              | Close unauthorized PRs     |
| `deploy-phantom-docs.yml`                       | `documentation/**` push, manual                                       | ubuntu-latest, self-hosted | Cloudflare Pages           |
| `deploy-phantom-install.yml`                    | `tools/phantom-install/**` push, manual                               | self-hosted                | Cloudflare Worker          |
| `deploy-phantom-www.yml`                        | `tools/phantom-www/**` push, manual                                   | ubuntu-latest, self-hosted | Cloudflare Pages           |
| `generate-api-recordings.yml`                   | `tools/recording-utilities/recording_automations_api/**` push, manual | ubuntu-latest              | Recording GIFs             |
| `generate-cli-recordings.yml`                   | `tools/recording-utilities/phantom-recorder/**` push, manual          | ubuntu-latest              | Recording GIFs             |
| `integration-workflow.yml`                      | push (main, paths-ignore), manual                                     | workflow_call              | Test reports               |
| `phantom-asset-generator-workflow.yml`          | manual, workflow_call                                                 | ubuntu-latest              | Generated assets           |
| `phantom-wizard-hidden-deployment-workflow.yml` | `tools/phantom-deployment-wizard/**` push, manual                     | ubuntu-latest              | Signed package deploy      |
| `release-workflow.yml`                          | manual (version_id)                                                   | ubuntu-latest              | GitHub Release             |
| `test-development-integration.yml`              | manual, workflow_call                                                 | ubuntu-latest, self-hosted | Coverage reports, CF Pages |
| `test-production-integration.yml`               | manual, workflow_call                                                 | ubuntu-latest, self-hosted | Test reports, CF Pages     |