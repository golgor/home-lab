# ComponentResource Pattern

Each infrastructure component is a Python package that exports a
[ComponentResource](https://www.pulumi.com/docs/iac/concepts/resources/components/)
class. This groups related resources under a single logical parent in
the Pulumi state tree.

## The pattern

```python
import pulumi
import pulumi_docker as docker


class MyService(pulumi.ComponentResource):
    def __init__(self, name: str, opts: pulumi.ResourceOptions | None = None):
        super().__init__("homelab:infrastructure:MyService", name, None, opts)

        # All child resources use this to set their parent
        child_opts = pulumi.ResourceOptions(parent=self)

        # Create resources as children
        container = docker.Container(
            name,
            # ... container config ...
            opts=child_opts,
        )

        # Expose outputs
        self.container_id = container.id

        # Register outputs so they appear in `pulumi stack output`
        self.register_outputs({"container_id": self.container_id})
```

Key points:

- **`super().__init__`** — the first argument is the component's type
  token (`pkg:module:Class`). Must be globally unique.
- **`child_opts`** — passing `parent=self` nests child resources under
  the component in the Pulumi state tree.
- **`register_outputs`** — declares what the component exposes. These
  show up in `pulumi stack output` and can be referenced by other
  components.

## Entry point

The `__main__.py` file imports and instantiates components:

```python
from postgres import Postgres
from postgresql_config import PostgresqlConfig, PostgresqlServiceAccount, PostgresqlUser

postgres = Postgres("postgres")

pg_config = PostgresqlConfig(
    "postgresql-config",
    host=postgres.host,
    port=postgres.port,
    superuser=postgres.username,
    superuser_password=postgres.password,
    opts=pulumi.ResourceOptions(depends_on=[postgres]),
)

human_users = [
    PostgresqlUser("robert", role="readwrite", pg_config=pg_config),
    PostgresqlUser("anna", role="readonly", pg_config=pg_config),
]

service_accounts = [
    PostgresqlServiceAccount(name, pg_config=pg_config) for name in ["authentik"]
]
```

`pulumi up` then shows a tree like:

```text
+ homelab:infrastructure:Postgres              postgres
  + docker:index:Network                       postgres-net
  + docker:index:Volume                        postgres-data
  + docker:index:Container                     postgres
+ homelab:infrastructure:PostgresqlConfig      postgresql-config
  + postgresql:index:Role                      readonly
  + postgresql:index:Role                      readwrite
+ homelab:infrastructure:PostgresqlUser        robert
+ homelab:infrastructure:PostgresqlUser        anna
+ homelab:infrastructure:PostgresqlServiceAccount  authentik
  + postgresql:index:Database                  authentik
  + postgresql:index:Grant                     authentik-ro-connect
  ...
```

## Database management

The `postgresql_config` package manages everything inside PostgreSQL:
roles, human users, service accounts, databases, and grants. It uses
three component classes:

- **`PostgresqlConfig`** — creates the PostgreSQL provider and two
  shared roles (`readonly`, `readwrite`).
- **`PostgresqlUser`** — a human user with a generated password and
  membership in one of the shared roles.
- **`PostgresqlServiceAccount`** — an application user with its own
  database (owned by the user) and grants/default privileges for both
  shared roles.

### Adding a new service account

Append the name to the list in `__main__.py`:

```python
service_accounts = [
    PostgresqlServiceAccount(name, pg_config=pg_config)
    for name in ["authentik", "grafana"]  # add here
]
```

This creates the `grafana` user, `grafana` database, and all
grants/default privileges automatically.

### Adding a new human user

```python
human_users = [
    PostgresqlUser("robert", role="readwrite", pg_config=pg_config),
    PostgresqlUser("anna", role="readonly", pg_config=pg_config),
    PostgresqlUser("erik", role="readonly", pg_config=pg_config),  # new
]
```

### Retrieving passwords

Passwords are auto-generated and stored in Pulumi state:

```bash
pulumi stack output --show-secrets authentik_password
pulumi stack output --show-secrets robert_password
```

### Gotchas

- Grants are chained sequentially (`depends_on`) to avoid PostgreSQL
  catalog concurrency errors during `pulumi up`.
- `DefaultPrivileges` are scoped per owner — they only apply to objects
  created by the service account user, not by the superuser.
- The `PostgresqlConfig` depends on the `Postgres` container
  (`depends_on=[postgres]`), and the container uses `wait=True` to
  ensure PostgreSQL is accepting connections before grants are attempted.

## Adding a new component

1. Create a new package directory:

    ```bash
    mkdir infrastructure/redis
    ```

2. Create `infrastructure/redis/__init__.py` with a ComponentResource
   class following the pattern above.

3. Add the dependency to `pyproject.toml` if the component needs a new
   Pulumi provider:

    ```bash
    cd infrastructure
    uv add pulumi-redis
    ```

4. Add config defaults to `Pulumi.yaml`:

    ```yaml
    config:
      redis:version:
        value: "7"
    ```

5. Import and instantiate in `__main__.py`:

    ```python
    from postgres import Postgres
    from redis import Redis

    postgres = Postgres("postgres")
    redis = Redis("redis")
    ```

6. Set any secrets for the active stack:

    ```bash
    pulumi config set --secret redis:password <value>
    ```

7. Deploy:

    ```bash
    pulumi preview   # verify
    pulumi up        # apply
    ```
