import pulumi

from postgres import Postgres
from postgresql_config import PostgresqlConfig, PostgresqlServiceAccount, PostgresqlUser

postgres = Postgres("postgres")

pg_config = PostgresqlConfig(
    "postgresql-config",
    host=postgres.host,
    port=postgres.port,
    superuser=postgres.username,
    superuser_password=postgres.password,
    sslmode="disable",
)

human_users = [
    PostgresqlUser("robert", role="readwrite", pg_config=pg_config),
    PostgresqlUser("anna", role="readonly", pg_config=pg_config),
]

service_accounts = [
    PostgresqlServiceAccount(name, pg_config=pg_config) for name in ["authentik", "homarr"]
]

for user in human_users:
    pulumi.export(f"{user.username}_password", user.password)
for sa in service_accounts:
    pulumi.export(f"{sa.name}_password", sa.password)
