from typing import Literal

import pulumi
import pulumi_postgresql as postgresql
import pulumi_random as random

_VALID_ROLES = ("readonly", "readwrite")


def _generate_password(
    name: str, opts: pulumi.ResourceOptions | None = None
) -> random.RandomPassword:
    return random.RandomPassword(
        f"{name}-password",
        length=32,
        special=False,
        opts=opts,
    )


class PostgresqlConfig(pulumi.ComponentResource):
    """Sets up the PostgreSQL provider and shared readonly/readwrite roles."""

    provider: postgresql.Provider
    readonly_role: postgresql.Role
    readwrite_role: postgresql.Role

    def __init__(
        self,
        name: str,
        host: str,
        port: int,
        superuser: str,
        superuser_password: pulumi.Output[str],
        sslmode: str = "require",
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("homelab:infrastructure:PostgresqlConfig", name, None, opts)

        child_opts = pulumi.ResourceOptions(parent=self)

        self.provider = postgresql.Provider(
            f"{name}-provider",
            host=host,
            port=port,
            username=superuser,
            password=superuser_password,
            sslmode=sslmode,
            opts=child_opts,
        )

        pg_opts = pulumi.ResourceOptions(parent=self, provider=self.provider)

        self.readonly_role = postgresql.Role(
            "readonly",
            name="readonly",
            login=False,
            opts=pg_opts,
        )

        self.readwrite_role = postgresql.Role(
            "readwrite",
            name="readwrite",
            login=False,
            opts=pg_opts,
        )

        self.register_outputs({})


class PostgresqlUser(pulumi.ComponentResource):
    """Human user with a generated password and membership in a shared role."""

    username: str
    password: pulumi.Output[str]

    def __init__(
        self,
        username: str,
        role: Literal["readonly", "readwrite"],
        pg_config: PostgresqlConfig,
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__("homelab:infrastructure:PostgresqlUser", username, None, opts)

        if role not in _VALID_ROLES:
            raise ValueError(f"role must be one of {_VALID_ROLES}, got {role!r}")

        self.username = username
        child_opts = pulumi.ResourceOptions(parent=self)
        pg_opts = pulumi.ResourceOptions(parent=self, provider=pg_config.provider)

        pw = _generate_password(username, opts=child_opts)

        parent_role = (
            pg_config.readonly_role if role == "readonly" else pg_config.readwrite_role
        )

        postgresql.Role(
            username,
            name=username,
            login=True,
            password=pw.result,
            roles=[parent_role.name],
            opts=pg_opts,
        )

        self.password = pw.result

        self.register_outputs({"password": self.password})


class PostgresqlServiceAccount(pulumi.ComponentResource):
    """Application service account with its own database and grants for shared roles."""

    name: str
    password: pulumi.Output[str]

    def __init__(
        self,
        name: str,
        pg_config: PostgresqlConfig,
        opts: pulumi.ResourceOptions | None = None,
    ):
        super().__init__(
            "homelab:infrastructure:PostgresqlServiceAccount", name, None, opts
        )

        self.name = name
        child_opts = pulumi.ResourceOptions(parent=self)
        pg_opts = pulumi.ResourceOptions(parent=self, provider=pg_config.provider)

        pw = _generate_password(name, opts=child_opts)

        user = postgresql.Role(
            name,
            name=name,
            login=True,
            password=pw.result,
            opts=pg_opts,
        )

        db = postgresql.Database(
            name,
            name=name,
            owner=user.name,
            opts=pg_opts,
        )

        # Chain grants sequentially to avoid PostgreSQL catalog concurrency errors.
        def _chain_opts(prev: pulumi.Resource) -> pulumi.ResourceOptions:
            return pulumi.ResourceOptions(
                parent=self, provider=pg_config.provider, depends_on=[prev]
            )

        ro_connect = postgresql.Grant(
            f"{name}-ro-connect",
            role=pg_config.readonly_role.name,
            database=db.name,
            object_type="database",
            privileges=["CONNECT"],
            opts=_chain_opts(db),
        )

        ro_usage = postgresql.Grant(
            f"{name}-ro-usage",
            role=pg_config.readonly_role.name,
            database=db.name,
            schema="public",
            object_type="schema",
            privileges=["USAGE"],
            opts=_chain_opts(ro_connect),
        )

        rw_connect = postgresql.Grant(
            f"{name}-rw-connect",
            role=pg_config.readwrite_role.name,
            database=db.name,
            object_type="database",
            privileges=["CONNECT"],
            opts=_chain_opts(ro_usage),
        )

        rw_usage = postgresql.Grant(
            f"{name}-rw-usage",
            role=pg_config.readwrite_role.name,
            database=db.name,
            schema="public",
            object_type="schema",
            privileges=["USAGE", "CREATE"],
            opts=_chain_opts(rw_connect),
        )

        ro_tables = postgresql.DefaultPrivileges(
            f"{name}-ro-tables",
            role=pg_config.readonly_role.name,
            database=db.name,
            schema="public",
            owner=user.name,
            object_type="table",
            privileges=["SELECT"],
            opts=_chain_opts(rw_usage),
        )

        ro_sequences = postgresql.DefaultPrivileges(
            f"{name}-ro-sequences",
            role=pg_config.readonly_role.name,
            database=db.name,
            schema="public",
            owner=user.name,
            object_type="sequence",
            privileges=["SELECT", "USAGE"],
            opts=_chain_opts(ro_tables),
        )

        rw_tables = postgresql.DefaultPrivileges(
            f"{name}-rw-tables",
            role=pg_config.readwrite_role.name,
            database=db.name,
            schema="public",
            owner=user.name,
            object_type="table",
            privileges=["SELECT", "INSERT", "UPDATE", "DELETE"],
            opts=_chain_opts(ro_sequences),
        )

        postgresql.DefaultPrivileges(
            f"{name}-rw-sequences",
            role=pg_config.readwrite_role.name,
            database=db.name,
            schema="public",
            owner=user.name,
            object_type="sequence",
            privileges=["SELECT", "USAGE", "UPDATE"],
            opts=_chain_opts(rw_tables),
        )

        self.password = pw.result

        self.register_outputs({"password": self.password})
