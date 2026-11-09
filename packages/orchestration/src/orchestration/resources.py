"""Resources: the connections the assets use, configured in one place.

The connection strings come from environment variables: the `.env` file on your computer and the
repository secrets in GitHub Actions. Dagster never shows their value in its web panel.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import dagster as dg
import psycopg
from pipelines.neon import connect


class NeonResource(dg.ConfigurableResource):
    """A connection to the Neon database. Use it as `with neon.connect() as connection:`."""

    url: str

    @contextmanager
    def connect(self) -> Iterator[psycopg.Connection]:
        with connect(self.url) as connection:
            yield connection


# Two users: the update writes; the quality checks only need to read
neon_writer = NeonResource(url=dg.EnvVar("DATABASE_URL"))
neon_reader = NeonResource(url=dg.EnvVar("READONLY_DATABASE_URL"))
