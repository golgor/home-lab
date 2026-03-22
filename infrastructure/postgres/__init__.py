import pulumi


class Postgres(pulumi.ComponentResource):
    """Remote PostgreSQL instance. Holds connection details only — provisioning
    of the server itself is handled by Ansible."""

    host: str
    port: int
    database: str
    username: str
    password: pulumi.Output[str]

    def __init__(self, name: str, opts: pulumi.ResourceOptions | None = None):
        super().__init__("homelab:infrastructure:Postgres", name, None, opts)

        config = pulumi.Config("postgres")
        self.host = config.get("host") or "10.0.0.110"
        self.port = config.get_int("port") or 5432
        self.database = config.get("database") or "postgres"
        self.username = config.get("username") or "postgres"
        self.password = config.require_secret("password")

        self.register_outputs(
            {
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "username": self.username,
            }
        )
