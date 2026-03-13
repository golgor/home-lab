# Pulumi

Quick reference for patterns and gotchas discovered while building the
infrastructure layer.

## Resource ordering with `depends_on`

Pulumi runs resources in parallel by default. Use `depends_on` when a
resource must wait for another to be fully ready — not just created.

### Container → provider dependency

The PostgreSQL provider must not connect until the container is healthy:

```python
pg_config = PostgresqlConfig(
    "postgresql-config",
    host=postgres.host,
    port=postgres.port,
    superuser=postgres.username,
    superuser_password=postgres.password,
    opts=pulumi.ResourceOptions(depends_on=[postgres]),
)
```

Without this, a container replacement (e.g. image upgrade) causes the
provider to connect before PostgreSQL is accepting connections.

### Sequential grant chaining

PostgreSQL's system catalog does not handle concurrent DDL well. Running
multiple `GRANT` statements in parallel on the same database causes:

```
tuple concurrently updated
```

Fix: chain every grant so each waits for the previous one:

```python
def _chain_opts(prev: pulumi.Resource) -> pulumi.ResourceOptions:
    return pulumi.ResourceOptions(
        parent=self, provider=pg_config.provider, depends_on=[prev]
    )

ro_connect = postgresql.Grant(..., opts=_chain_opts(db))
ro_usage   = postgresql.Grant(..., opts=_chain_opts(ro_connect))
rw_connect = postgresql.Grant(..., opts=_chain_opts(ro_usage))
```

## Docker container readiness

`docker.Container` reports as "created" the moment the container process
starts — not when the application inside is ready. Set `wait=True` and
`wait_timeout` so Pulumi blocks until the container's healthcheck passes:

```python
docker.Container(
    ...,
    wait=True,
    wait_timeout=30,
    healthcheck=docker.ContainerHealthcheckArgs(
        tests=["CMD-SHELL", "pg_isready -U postgres"],
        interval="10s",
        timeout="5s",
        retries=5,
    ),
)
```

This ensures downstream resources (like the PostgreSQL provider) only
run after the database is actually accepting connections.

## Avoiding unnecessary container replacements

Docker has daemon-level defaults for log configuration. If you don't set
`log_driver` and `log_opts` explicitly, Pulumi sees the daemon defaults
in the live state but nothing in the desired state, causing a diff and
container replacement on every `pulumi up`.

Fix: pin the values explicitly to match what Docker would set anyway:

```python
docker.Container(
    ...,
    log_driver="json-file",
    log_opts={"max-file": "5", "max-size": "10m"},
)
```

!!! tip "Check with `docker inspect`"
    Run `docker inspect <container> | jq '.[0].HostConfig.LogConfig'`
    to see the effective log configuration and match it in your Pulumi
    code.

## DefaultPrivileges owner scoping

`postgresql.DefaultPrivileges` only applies to objects created by the
specified `owner`. If you create a table as the `postgres` superuser,
the readonly/readwrite roles will **not** have access — you must grant
explicitly or create the table as the service account user.

## Local state backend

State is stored locally (`~/.pulumi/`). There is no remote backend.

```bash
pulumi login --local    # one-time setup
```

!!! warning "Back up your state"
    Losing `~/.pulumi/` means Pulumi loses track of all managed
    resources. Back it up or consider migrating to a remote backend
    (S3, GCS, Pulumi Cloud) if the project grows.

### What happens if you lose state

Pulumi does **not** auto-detect or import existing resources. With a
blank state, `pulumi up` tries to create everything from scratch:

- **Docker**: container and network fail with name conflicts. The volume
  silently reuses the existing one (data survives).
- **PostgreSQL**: `CREATE ROLE` / `CREATE DATABASE` fail with "already
  exists" errors.

Recovery paths:

1. **`pulumi import`** — import each resource by provider ID. Tedious
   with many resources (grants, default privileges, etc.):

    ```bash
    pulumi import docker:index/container:Container postgres <container-id>
    pulumi import postgresql:index/role:Role readonly readonly
    ```

2. **Recreate from scratch** — tear down manually (`docker rm`,
   `DROP ROLE/DATABASE` in psql), then `pulumi up`. The Docker volume
   is retained, so data survives.

!!! note "Secrets are passphrase-encrypted"
    The `PULUMI_CONFIG_PASSPHRASE` encrypts secret values (passwords)
    in the state file with AES-256-GCM. Non-secret properties (resource
    names, IDs, ports) remain plaintext.
