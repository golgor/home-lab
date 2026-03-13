from typing import Literal

import pulumi
import pulumi_postgresql as postgresql
import pulumi_random as random


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
            sslmode="disable",
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

        self.username = username
        child_opts = pulumi.ResourceOptions(parent=self)
        pg_opts = pulumi.ResourceOptions(parent=self, provider=pg_config.provider)

        pw = random.RandomPassword(
            f"{username}-password",
            length=32,
            special=False,
            opts=child_opts,
        )

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

        pw = random.RandomPassword(
            f"{name}-password",
            length=32,
            special=False,
            opts=child_opts,
        )

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
        # Each grant depends on the previous one.
        prev: pulumi.Resource = db

        for grant_name, role, obj_type, schema, privileges in [
            ("ro-connect", pg_config.readonly_role, "database", None, ["CONNECT"]),
            ("ro-usage", pg_config.readonly_role, "schema", "public", ["USAGE"]),
            ("rw-connect", pg_config.readwrite_role, "database", None, ["CONNECT"]),
            (
                "rw-usage",
                pg_config.readwrite_role,
                "schema",
                "public",
                ["USAGE", "CREATE"],
            ),
        ]:
            kwargs = {
                "role": role.name,
                "database": db.name,
                "object_type": obj_type,
                "privileges": privileges,
            }
            if schema:
                kwargs["schema"] = schema
            grant = postgresql.Grant(
                f"{name}-{grant_name}",
                **kwargs,
                opts=pulumi.ResourceOptions(
                    parent=self, provider=pg_config.provider, depends_on=[prev]
                ),
            )
            prev = grant

        for grant_name, role, obj_type, privileges in [
            ("ro-tables", pg_config.readonly_role, "table", ["SELECT"]),
            (
                "ro-sequences",
                pg_config.readonly_role,
                "sequence",
                ["SELECT", "USAGE"],
            ),
            (
                "rw-tables",
                pg_config.readwrite_role,
                "table",
                ["SELECT", "INSERT", "UPDATE", "DELETE"],
            ),
            (
                "rw-sequences",
                pg_config.readwrite_role,
                "sequence",
                ["SELECT", "USAGE", "UPDATE"],
            ),
        ]:
            default_priv = postgresql.DefaultPrivileges(
                f"{name}-{grant_name}",
                role=role.name,
                database=db.name,
                schema="public",
                owner=user.name,
                object_type=obj_type,
                privileges=privileges,
                opts=pulumi.ResourceOptions(
                    parent=self, provider=pg_config.provider, depends_on=[prev]
                ),
            )
            prev = default_priv

        self.password = pw.result

        self.register_outputs({"password": self.password})
