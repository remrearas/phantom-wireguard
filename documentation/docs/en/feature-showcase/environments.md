# Test Environments

Environments used for recordings and tests in this section.

## DigitalOcean Recording Environment

Real-world test environment used for scenarios requiring multiple servers.

**Workflow:** [setup-recording-environment.yml](https://github.com/ARAS-Workspace/phantom-wg/blob/main/.github/retired/setup-recording-environment.yml)

### Environment Structure

| Droplet  | Role                                       |
|----------|--------------------------------------------|
| `master` | Main recording machine (asciinema)         |
| `server` | Phantom-WG server                          |
| `client` | Client machine                             |
| `exit`   | Multihop exit point                        |

All droplets are located in the same VPC and communicate over private IPs.

### Use Cases

Recordings captured in this environment:

- **Multihop VPN** - Client → Server → Exit configuration
- **Ghost Mode** - Hidden tunnel setup and verification
- **Installation** - Fresh installation scenarios

### Running

1. Trigger the workflow from GitHub Actions
2. Specify a session name (e.g., `ghost-recording`)
3. Get IP addresses and setup commands when workflow completes
4. SSH into master and apply the recording scenario

### Scenario Files

Recording scenarios: `tools/recording-utilities/recording_environment/scenarios/`

| File                  | Description                      |
|-----------------------|----------------------------------|
| `installation.md`     | Fresh installation steps         |
| `multihop_compact.md` | Multihop VPN setup steps         |
| `ghost_compact.md`    | Ghost Mode setup steps           |

These scenarios contain step-by-step instructions suitable for real-world usage.

---

## GitHub Actions Test Environments

CI/CD environments used for automated testing and recording.

### Integration Tests

| Workflow                                                                                                                                      | Description                           |
|-----------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| [test-development-integration.yml](https://github.com/ARAS-Workspace/phantom-wg/blob/main/.github/workflows/test-development-integration.yml) | Development tests in Docker container |
| [test-production-integration.yml](https://github.com/ARAS-Workspace/phantom-wg/blob/main/.github/workflows/test-production-integration.yml)   | Production tests on real installation |

### Recording Generation

[![Generate CLI Recordings](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/generate-cli-recordings.yml/badge.svg)](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/generate-cli-recordings.yml)
[![Generate API Recordings](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/generate-api-recordings.yml/badge.svg)](https://github.com/ARAS-Workspace/phantom-wg/actions/workflows/generate-api-recordings.yml)

| Workflow                                                                                                                            | Description                |
|-------------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| [generate-api-recordings.yml](https://github.com/ARAS-Workspace/phantom-wg/blob/main/.github/workflows/generate-api-recordings.yml) | API command recordings     |
| [generate-cli-recordings.yml](https://github.com/ARAS-Workspace/phantom-wg/blob/main/.github/workflows/generate-cli-recordings.yml) | Interactive CLI recordings |

These workflows are manually triggered via `workflow_dispatch` and results are automatically committed to documentation.

---

## Environment Comparison

| Feature                    | DigitalOcean         | GitHub Actions       |
|----------------------------|----------------------|----------------------|
| Multi-server support       | Yes                  | No                   |
| Real network traffic       | Yes                  | Limited              |
| Cost                       | Per usage            | Free                 |
| Automated recording        | Manual               | Automatic            |
| Use case                   | Complex scenarios    | Single operations    |

