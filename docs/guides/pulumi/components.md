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

postgres = Postgres("postgres")
```

`pulumi up` then shows a tree like:

```text
+ homelab:infrastructure:Postgres  postgres
  + docker:index:Network           postgres-net
  + docker:index:Volume            postgres-data
  + docker:index:Container         postgres
```

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
