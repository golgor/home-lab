# Pulumi Overview

External services that live outside the k3s cluster (databases, caches,
etc.) are managed as code using [Pulumi](https://www.pulumi.com/docs/).
The Pulumi project lives in `infrastructure/` and uses Python with the
`uv` toolchain.

## Project layout

```text
infrastructure/
  Pulumi.yaml          # Project metadata, runtime, shared config defaults
  Pulumi.dev.yaml      # Stack-specific config (passwords, overrides)
  pyproject.toml       # Python dependencies
  __main__.py          # Entry point — imports and instantiates components
  postgres/
    __init__.py        # Postgres ComponentResource
```

Pulumi discovers the project by looking for `Pulumi.yaml` in the current
directory. It then runs `__main__.py` using the Python runtime configured
in that file. The `uv` toolchain handles the virtual environment and
dependency installation automatically.

## Day-to-day commands

All commands are run from the `infrastructure/` directory.

```bash
cd infrastructure
pulumi preview         # dry-run — shows what would change
pulumi up              # apply changes
pulumi destroy         # tear down all resources
pulumi stack output    # show exported values
pulumi stack ls        # list stacks, * marks the active one
```

## Further reading

- [Pulumi concepts](https://www.pulumi.com/docs/iac/concepts/) — projects, stacks, resources, state
- [Python SDK reference](https://www.pulumi.com/docs/iac/languages-sdks/python/)
- [Docker provider](https://www.pulumi.com/registry/packages/docker/) — managing containers, networks, volumes
