"""CLI: `uv run seed-db` — initialises the DB and seeds it with mock data."""
import typer
from rich.console import Console

from agent_workflows.data_generation import (
    Customer,
    MockDataFactory,
    Order,
    Product,
    seed_table,
)
from agent_workflows.db import init_db

app = typer.Typer(add_completion=False, help="Seed the demo DB with LLM-generated data.")
console = Console()


@app.command()
def main(
    customers: int = typer.Option(20, help="Customers to generate."),
    products: int = typer.Option(10, help="Products to generate."),
    orders: int = typer.Option(40, help="Orders to generate."),
    context: str = typer.Option(
        "B2B SaaS company in the UK, 2025",
        help="Free-text hint to bias data generation.",
    ),
) -> None:
    console.print("[cyan]Initialising DB schema...[/cyan]")
    init_db()

    factory = MockDataFactory()

    console.print(f"[cyan]Generating {customers} customers...[/cyan]")
    customer_rows = factory.generate(Customer, n=customers, context=context)
    seed_table("customers", customer_rows)

    console.print(f"[cyan]Generating {products} products...[/cyan]")
    product_rows = factory.generate(Product, n=products, context=context)
    seed_table("products", product_rows)

    console.print(f"[cyan]Generating {orders} orders...[/cyan]")
    order_context = (
        f"{context}. customer_ids range 1-{customers}, product_ids range 1-{products}."
    )
    order_rows = factory.generate(Order, n=orders, context=order_context)
    seed_table("orders", order_rows)

    console.print("[green]Seed complete.[/green]")


if __name__ == "__main__":
    app()
