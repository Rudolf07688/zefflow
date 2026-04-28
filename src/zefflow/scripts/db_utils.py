"""Utilities for creating and seeding the local Postgres instance with mock data."""

from datetime import datetime, timedelta
from typing import Optional

import sqlalchemy
import typer
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from zefflow.config import app_config
from zefflow.db.db_models import (
    AgentError,
    AgentResponse,
    Base,
    Conversation,
    DataSource,
    Message,
    QueryExecution,
    ToolCall,
    User,
)

cli = typer.Typer(help="Local Postgres seeding and inspection utility.")

# ---------------------------------------------------------------------------
# Engine helpers
# ---------------------------------------------------------------------------

def create_db_engine(db_url: str) -> sqlalchemy.engine.Engine:
    return sqlalchemy.create_engine(db_url, echo=False)


def create_tables(engine: sqlalchemy.engine.Engine) -> None:
    Base.metadata.create_all(engine)


def drop_tables(engine: sqlalchemy.engine.Engine) -> None:
    Base.metadata.drop_all(engine)


def _build_db_url(db_url: Optional[str] = None) -> str:
    if db_url:
        return db_url
    cfg = app_config.default_app_config
    return (
        f"postgresql+psycopg2://{cfg.postgres_user}:{cfg.postgres_password}"
        f"@{cfg.postgres_host}:{cfg.db_postgresdb_port}/{cfg.postgres_db}"
    )


# ---------------------------------------------------------------------------
# Mock data
# ---------------------------------------------------------------------------

def _dt(days_ago: float, hour: int = 9, minute: int = 0) -> datetime:
    base = datetime(2026, 4, 28) - timedelta(days=days_ago)
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def populate_mock_db(engine: sqlalchemy.engine.Engine) -> None:
    with Session(engine) as session:
        # ── Users ──────────────────────────────────────────────────────────
        alice = User(username="alice_analyst", email="alice@acme.com",
                     created_at=_dt(90), updated_at=_dt(90))
        bob = User(username="bob_senior", email="bob@acme.com",
                   created_at=_dt(85), updated_at=_dt(85))
        carol = User(username="carol_bi", email="carol@techcorp.com",
                     created_at=_dt(60), updated_at=_dt(60))
        session.add_all([alice, bob, carol])
        session.flush()

        # ── Data sources ───────────────────────────────────────────────────
        bq_sales = DataSource(
            user_id=alice.id, name="acme_bigquery_sales", source_type="bigquery",
            config={"project_id": "acme-data-prod", "dataset": "sales", "credentials_secret": "bq_acme_prod"},
            description="ACME production BigQuery dataset. Contains orders, line_items, products, regions.",
            created_at=_dt(88), updated_at=_dt(88),
        )
        pg_app = DataSource(
            user_id=alice.id, name="acme_rails_postgres", source_type="postgres",
            config={"host": "db.acme.internal", "port": 5432, "database": "acme_production", "credentials_secret": "pg_acme_prod"},
            description="Rails app Postgres. users, orders, subscriptions, audit_logs.",
            created_at=_dt(87), updated_at=_dt(87),
        )
        bq_analytics = DataSource(
            user_id=bob.id, name="acme_bigquery_analytics", source_type="bigquery",
            config={"project_id": "acme-data-prod", "dataset": "analytics", "credentials_secret": "bq_acme_prod"},
            description="Marketing analytics warehouse. sessions, events, funnels, attribution.",
            created_at=_dt(80), updated_at=_dt(80),
        )
        pg_staging = DataSource(
            user_id=bob.id, name="acme_rails_staging", source_type="postgres",
            config={"host": "db-staging.acme.internal", "port": 5432, "database": "acme_staging", "credentials_secret": "pg_acme_staging"},
            description="Staging Rails DB — safe for exploratory queries.",
            created_at=_dt(79), updated_at=_dt(79),
        )
        redshift_dw = DataSource(
            user_id=carol.id, name="techcorp_redshift", source_type="redshift",
            config={"host": "techcorp.us-east-1.redshift.amazonaws.com", "port": 5439, "database": "dwh", "credentials_secret": "rs_techcorp_prod"},
            description="TechCorp Redshift data warehouse. finance, hr, ops schemas.",
            created_at=_dt(55), updated_at=_dt(55),
        )
        session.add_all([bq_sales, pg_app, bq_analytics, pg_staging, redshift_dw])
        session.flush()

        # ── Conversations + messages + agent responses ─────────────────────
        # Conv 1: alice — monthly revenue by region
        conv1 = Conversation(user_id=alice.id, title="Monthly revenue breakdown by region",
                             created_at=_dt(5, 10), updated_at=_dt(5, 10, 45))
        session.add(conv1)
        session.flush()

        m1_user = Message(conversation_id=conv1.id, role="user",
                          content="Show me total revenue by region for the last 3 months, broken down by month.",
                          created_at=_dt(5, 10, 0))
        session.add(m1_user)
        session.flush()

        m1_assist = Message(
            conversation_id=conv1.id, role="assistant",
            content="I'll query the sales BigQuery dataset for monthly revenue by region. Let me fetch the schema first, then run the aggregation.",
            created_at=_dt(5, 10, 1),
        )
        session.add(m1_assist)
        session.flush()

        ar1 = AgentResponse(message_id=m1_assist.id, model="gemini-1.5-pro",
                            input_tokens=420, output_tokens=310, stop_reason="tool_use",
                            created_at=_dt(5, 10, 1))
        session.add(ar1)
        session.flush()

        tc1a = ToolCall(agent_response_id=ar1.id, tool_name="get_schema",
                        input={"data_source_id": bq_sales.id, "table": "orders"},
                        output={"columns": ["id", "region", "amount", "created_at"]},
                        status="success", duration_ms=210, created_at=_dt(5, 10, 1))
        session.add(tc1a)
        session.flush()

        tc1b = ToolCall(
            agent_response_id=ar1.id, tool_name="execute_sql",
            input={"data_source_id": bq_sales.id, "sql": (
                "SELECT DATE_TRUNC('month', created_at) AS month, region, SUM(amount) AS total_revenue "
                "FROM `acme-data-prod.sales.orders` "
                "WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 3 MONTH) "
                "GROUP BY 1, 2 ORDER BY 1 DESC, 3 DESC"
            )},
            output={"rows": [
                {"month": "2026-04-01", "region": "EMEA", "total_revenue": 1840220.50},
                {"month": "2026-04-01", "region": "AMER", "total_revenue": 2301450.00},
                {"month": "2026-03-01", "region": "EMEA", "total_revenue": 1705110.75},
                {"month": "2026-03-01", "region": "AMER", "total_revenue": 2198330.25},
                {"month": "2026-02-01", "region": "EMEA", "total_revenue": 1620900.00},
                {"month": "2026-02-01", "region": "AMER", "total_revenue": 2050780.00},
            ]},
            status="success", duration_ms=1850, created_at=_dt(5, 10, 2),
        )
        session.add(tc1b)
        session.flush()

        session.add(QueryExecution(
            tool_call_id=tc1b.id, data_source_id=bq_sales.id,
            sql_query=tc1b.input["sql"], row_count=6, duration_ms=1850, created_at=_dt(5, 10, 2),
        ))

        # Conv 2: bob — top customers last 30 days
        conv2 = Conversation(user_id=bob.id, title="Top customers by revenue — last 30 days",
                             created_at=_dt(3, 14), updated_at=_dt(3, 14, 30))
        session.add(conv2)
        session.flush()

        m2_user = Message(conversation_id=conv2.id, role="user",
                          content="Who are our top 10 customers by total spend in the last 30 days?",
                          created_at=_dt(3, 14, 0))
        session.add(m2_user)
        session.flush()

        m2_assist = Message(conversation_id=conv2.id, role="assistant",
                            content="Querying the analytics BigQuery dataset for top customers.",
                            created_at=_dt(3, 14, 1))
        session.add(m2_assist)
        session.flush()

        ar2 = AgentResponse(message_id=m2_assist.id, model="gemini-1.5-pro",
                            input_tokens=380, output_tokens=290, stop_reason="end_turn",
                            created_at=_dt(3, 14, 1))
        session.add(ar2)
        session.flush()

        tc2 = ToolCall(
            agent_response_id=ar2.id, tool_name="execute_sql",
            input={"data_source_id": bq_analytics.id, "sql": (
                "SELECT customer_id, customer_name, SUM(order_total) AS total_spend "
                "FROM `acme-data-prod.analytics.orders` "
                "WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) "
                "GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 10"
            )},
            output={"rows": [
                {"customer_id": 4821, "customer_name": "Globex Corp", "total_spend": 98450.00},
                {"customer_id": 1102, "customer_name": "Initech Ltd", "total_spend": 87320.50},
                {"customer_id": 3374, "customer_name": "Umbrella GmbH", "total_spend": 74100.25},
            ]},
            status="success", duration_ms=2100, created_at=_dt(3, 14, 1),
        )
        session.add(tc2)
        session.flush()

        session.add(QueryExecution(
            tool_call_id=tc2.id, data_source_id=bq_analytics.id,
            sql_query=tc2.input["sql"], row_count=10, duration_ms=2100, created_at=_dt(3, 14, 1),
        ))

        # Conv 3: alice — slow query diagnosis on Rails Postgres
        conv3 = Conversation(user_id=alice.id, title="Diagnose slow query on orders table",
                             created_at=_dt(2, 9), updated_at=_dt(2, 9, 20))
        session.add(conv3)
        session.flush()

        m3_user = Message(conversation_id=conv3.id, role="user",
                          content="Our `orders` query is timing out in production. Can you run EXPLAIN ANALYZE and suggest indexes?",
                          created_at=_dt(2, 9, 0))
        session.add(m3_user)
        session.flush()

        m3_assist = Message(conversation_id=conv3.id, role="assistant",
                            content="Running EXPLAIN ANALYZE on the query. One moment.",
                            created_at=_dt(2, 9, 1))
        session.add(m3_assist)
        session.flush()

        ar3 = AgentResponse(message_id=m3_assist.id, model="gemini-1.5-pro",
                            input_tokens=510, output_tokens=640, stop_reason="tool_use",
                            created_at=_dt(2, 9, 1))
        session.add(ar3)
        session.flush()

        tc3 = ToolCall(
            agent_response_id=ar3.id, tool_name="execute_sql",
            input={"data_source_id": pg_staging.id, "sql": (
                "EXPLAIN ANALYZE SELECT o.id, o.status, u.email "
                "FROM orders o JOIN users u ON u.id = o.user_id "
                "WHERE o.status = 'pending' AND o.created_at > NOW() - INTERVAL '7 days'"
            )},
            output={"plan": (
                "Seq Scan on orders (cost=0.00..184322.10 rows=24810 width=48) "
                "(actual time=0.042..4821.233 rows=24810 loops=1)  "
                "Filter: ((status = 'pending') AND (created_at > (now() - '7 days'::interval)))  "
                "Rows Removed by Filter: 2847391  "
                "Planning Time: 1.2 ms  Execution Time: 4954.3 ms"
            )},
            status="success", duration_ms=5100, created_at=_dt(2, 9, 2),
        )
        session.add(tc3)
        session.flush()

        session.add(QueryExecution(
            tool_call_id=tc3.id, data_source_id=pg_staging.id,
            sql_query=tc3.input["sql"], row_count=None, duration_ms=5100, created_at=_dt(2, 9, 2),
        ))

        # Conv 4: carol — failed query (permission error)
        conv4 = Conversation(user_id=carol.id, title="Finance schema headcount query",
                             created_at=_dt(1, 15), updated_at=_dt(1, 15, 10))
        session.add(conv4)
        session.flush()

        m4_user = Message(conversation_id=conv4.id, role="user",
                          content="Give me headcount by department from the finance schema.",
                          created_at=_dt(1, 15, 0))
        session.add(m4_user)
        session.flush()

        m4_assist = Message(conversation_id=conv4.id, role="assistant",
                            content="Attempting to query the finance schema in Redshift.",
                            created_at=_dt(1, 15, 1))
        session.add(m4_assist)
        session.flush()

        ar4 = AgentResponse(message_id=m4_assist.id, model="gemini-1.5-flash",
                            input_tokens=290, output_tokens=180, stop_reason="tool_use",
                            created_at=_dt(1, 15, 1))
        session.add(ar4)
        session.flush()

        tc4 = ToolCall(
            agent_response_id=ar4.id, tool_name="execute_sql",
            input={"data_source_id": redshift_dw.id,
                   "sql": "SELECT department, COUNT(*) AS headcount FROM finance.employees GROUP BY 1 ORDER BY 2 DESC"},
            output={"error": "permission denied for schema finance"},
            status="error", duration_ms=320, created_at=_dt(1, 15, 2),
        )
        session.add(tc4)
        session.flush()

        session.add(QueryExecution(
            tool_call_id=tc4.id, data_source_id=redshift_dw.id,
            sql_query=tc4.input["sql"], row_count=None, duration_ms=320,
            error_message="permission denied for schema finance", created_at=_dt(1, 15, 2),
        ))
        session.add(AgentError(
            conversation_id=conv4.id, agent_response_id=ar4.id,
            error_type="PermissionError",
            message="User carol_bi does not have SELECT on finance.employees in Redshift.",
            traceback=None, created_at=_dt(1, 15, 2),
        ))

        session.commit()


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

_DB_URL_OPTION = typer.Option(None, "--db-url", help="Override the database URL.")


@cli.command()
def reset(db_url: Optional[str] = _DB_URL_OPTION) -> None:
    """Drop and recreate all tables (schema only, no data)."""
    engine = create_db_engine(_build_db_url(db_url))
    typer.echo("Dropping all tables...")
    drop_tables(engine)
    typer.echo("Creating tables...")
    create_tables(engine)
    typer.secho("Done.", fg=typer.colors.GREEN)


@cli.command()
def populate(db_url: Optional[str] = _DB_URL_OPTION) -> None:
    """Create tables (if missing) and insert mock data."""
    engine = create_db_engine(_build_db_url(db_url))
    typer.echo("Creating tables (if not present)...")
    create_tables(engine)
    typer.echo("Inserting mock data...")
    populate_mock_db(engine)
    typer.secho("Done.", fg=typer.colors.GREEN)


@cli.command()
def sample(
    db_url: Optional[str] = _DB_URL_OPTION,
    rows: int = typer.Option(3, "--rows", "-n", help="Sample rows to show per table."),
) -> None:
    """Show table counts and a few sample rows — quick liveness check."""
    engine = create_db_engine(_build_db_url(db_url))
    inspector = inspect(engine)
    table_names = sorted(inspector.get_table_names())

    if not table_names:
        typer.secho("No tables found in the database.", fg=typer.colors.YELLOW)
        raise typer.Exit(1)

    with engine.connect() as conn:
        typer.secho(f"\n{'TABLE':<28} {'ROWS':>6}", bold=True)
        typer.echo("─" * 36)

        counts: dict[str, int] = {}
        for table in table_names:
            count = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar()
            counts[table] = count
            colour = typer.colors.GREEN if count else typer.colors.YELLOW
            typer.secho(f"{table:<28} {count:>6}", fg=colour)

        typer.echo()

        for table in table_names:
            typer.secho(f"── {table} (sample {min(rows, counts[table])} of {counts[table]}) ", bold=True)
            result = conn.execute(text(f'SELECT * FROM "{table}" LIMIT {rows}'))
            col_names = list(result.keys())
            sample_rows = result.fetchall()

            if not sample_rows:
                typer.secho("  (empty)", fg=typer.colors.YELLOW)
                typer.echo()
                continue

            # Column widths: cap long values for readability
            col_w = {c: max(len(c), 6) for c in col_names}
            for row in sample_rows:
                for c, v in zip(col_names, row):
                    col_w[c] = min(max(col_w[c], len(str(v))), 40)

            header = "  " + "  ".join(c.ljust(col_w[c]) for c in col_names)
            typer.secho(header, fg=typer.colors.BRIGHT_BLACK)
            typer.echo("  " + "  ".join("─" * col_w[c] for c in col_names))
            for row in sample_rows:
                line = "  " + "  ".join(str(v)[:col_w[c]].ljust(col_w[c]) for c, v in zip(col_names, row))
                typer.echo(line)
            typer.echo()


if __name__ == "__main__":
    cli()
