# Config and Secrets

Pulumi config is set per-stack. Plain values are stored in cleartext,
secrets are encrypted.

## Setting config

```bash
# Set a plain value (stored in Pulumi.<stack>.yaml)
pulumi config set postgres:port 5433

# Set an encrypted secret
pulumi config set --secret postgres:password <value>
```

## Where config lives

Config is resolved from two files, with stack config taking priority:

| File | Scope | Purpose |
| --- | --- | --- |
| `Pulumi.yaml` | All stacks | Shared defaults under the `config:` key |
| `Pulumi.<stack>.yaml` | One stack | Per-stack overrides and secrets |

Both files are safe to commit — secrets are encrypted with a passphrase
(local backend) or per-stack key (Pulumi Cloud).

## Reading config in Python

```python
config = pulumi.Config("postgres")

# Plain value with a fallback
version = config.get("version") or "18"

# Integer value
port = config.get_int("port") or 5432

# Secret — fails with a clear error if missing
password = config.require_secret("password")
```

The namespace (`"postgres"`) matches the prefix in the YAML config keys
(`postgres:version`, `postgres:password`, etc.).

## Adding config for a new component

1. Add shared defaults to `Pulumi.yaml`:

    ```yaml
    config:
      redis:version:
        value: "7"
    ```

2. Set stack-specific secrets:

    ```bash
    pulumi config set --secret redis:password <value>
    ```

For more details, see
[Pulumi configuration and secrets](https://www.pulumi.com/docs/iac/concepts/config/).
