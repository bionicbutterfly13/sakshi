# Security Policy

Sakshi is a metacognitive runtime library. The package core does not include a
web server, database driver, credential store, or network transport.

## Supported Versions

The project is in private alpha. Security fixes apply to the `main` branch
until a stable release policy is published.

## Reporting a Vulnerability

Please do not open a public issue for a vulnerability report.

Use GitHub's private vulnerability reporting flow when available, or email the
maintainer listed on the GitHub repository profile with:

- affected version or commit
- a minimal reproduction
- expected impact
- any known mitigation

Reports involving host adapters should identify which behavior is in Sakshi
itself and which behavior belongs to the host application.

## Scope

In scope:

- unsafe validation or state transitions in package core
- package dependency or build-chain issues
- behavior that violates documented protocol boundaries

Out of scope:

- vulnerabilities in downstream host applications
- issues requiring private host adapters
- claims about agent quality or cognitive performance
