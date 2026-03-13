import pulumi
import pulumi_docker as docker


class Postgres(pulumi.ComponentResource):
    """PostgreSQL database running as a Docker container."""

    container_id: pulumi.Output[str]
    host: str
    port: int
    database: str
    username: str
    password: pulumi.Output[str]

    def __init__(self, name: str, opts: pulumi.ResourceOptions | None = None):
        super().__init__("homelab:infrastructure:Postgres", name, None, opts)

        config = pulumi.Config("postgres")
        version = config.get("version") or "18"
        self.port = config.get_int("port") or 5432
        self.database = config.get("database") or "postgres"
        self.username = config.get("username") or "postgres"
        self.password = config.require_secret("password")
        self.host = "localhost"

        child_opts = pulumi.ResourceOptions(parent=self)

        network = docker.Network(
            f"{name}-net",
            name=f"{name}-net",
            opts=child_opts,
        )

        volume = docker.Volume(
            f"{name}-data",
            name=f"{name}-data",
            opts=pulumi.ResourceOptions(parent=self, retain_on_delete=True),
        )

        container = docker.Container(
            name,
            name=name,
            image=f"postgres:{version}",
            networks_advanced=[docker.ContainerNetworksAdvancedArgs(name=network.name)],
            ports=[
                docker.ContainerPortArgs(
                    internal=5432,
                    external=self.port,
                    ip="0.0.0.0",
                )
            ],
            volumes=[
                docker.ContainerVolumeArgs(
                    volume_name=volume.name,
                    container_path="/var/lib/postgresql",
                )
            ],
            envs=[
                pulumi.Output.concat("POSTGRES_DB=", self.database),
                pulumi.Output.concat("POSTGRES_USER=", self.username),
                pulumi.Output.concat("POSTGRES_PASSWORD=", self.password),
            ],
            log_driver="json-file",
            restart="unless-stopped",
            wait=True,
            wait_timeout=30,
            healthcheck=docker.ContainerHealthcheckArgs(
                tests=["CMD-SHELL", f"pg_isready -U {self.username}"],
                interval="10s",
                timeout="5s",
                retries=5,
            ),
            opts=child_opts,
        )

        self.container_id = container.id

        self.register_outputs(
            {
                "container_id": self.container_id,
                "host": self.host,
                "port": self.port,
                "database": self.database,
                "username": self.username,
            }
        )
