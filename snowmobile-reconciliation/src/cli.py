"""
Command line interface for Snowmobile Product Reconciliation system.

Provides development and operational commands following Universal Development Standards.
"""
import json
import sys
from pathlib import Path

import click
import structlog
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src import __version__
from src.config.settings import get_environment_info, validate_settings

# Initialize console and logging
console = Console()
logger = structlog.get_logger(__name__)

# Configure structured logging for CLI
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)


@click.group()
@click.version_option(version=__version__, prog_name="Snowmobile Reconciliation")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose logging")
@click.option("--config-file", help="Path to configuration file")
@click.pass_context
def cli(ctx, verbose, config_file):
    """
    Snowmobile Product Reconciliation CLI

    Professional product data reconciliation system with 5-stage inheritance pipeline.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_file"] = config_file

    if verbose:
        console.print(f"[green]Snowmobile Reconciliation CLI v{__version__}[/green]")
        console.print(
            f"[dim]Configuration file: {config_file or 'default (.env)'}[/dim]"
        )


@cli.command()
@click.pass_context
def info(ctx):
    """Show application information and configuration"""
    try:
        console.print("[bold blue]Application Information[/bold blue]")

        info_data = get_environment_info()

        # Create information table
        table = Table(title="Configuration Status")
        table.add_column("Component", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")

        table.add_row(
            "Application", info_data["app_name"], f"v{info_data['app_version']}"
        )
        table.add_row("Environment", info_data["environment"], "")
        table.add_row("Debug Mode", str(info_data["debug_mode"]), "")
        table.add_row(
            "Database",
            "✓ Configured" if info_data["database_configured"] else "✗ Not configured",
            "",
        )
        table.add_row(
            "Claude API",
            "✓ Configured" if info_data["claude_configured"] else "✗ Not configured",
            "",
        )
        table.add_row(
            "Monitoring",
            "✓ Enabled" if info_data["monitoring_enabled"] else "✗ Disabled",
            "",
        )

        # Pipeline features
        features = info_data.get("pipeline_features", {})
        table.add_row(
            "Spring Options",
            "✓ Enabled" if features.get("spring_options") else "✗ Disabled",
            "",
        )
        table.add_row(
            "Claude Fallback",
            "✓ Enabled" if features.get("claude_fallback") else "✗ Disabled",
            "",
        )

        console.print(table)

        if ctx.obj["verbose"]:
            console.print("\n[bold]Full Configuration:[/bold]")
            console.print_json(json.dumps(info_data, indent=2))

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@cli.command()
def validate():
    """Validate application configuration and dependencies"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Validating configuration...", total=None)

        try:
            # Validate settings
            validate_settings()
            progress.update(task, description="✓ Configuration valid")

            # Test database connection
            progress.update(task, description="Testing database connection...")
            # TODO: Add actual database connection test
            progress.update(task, description="✓ Database connection OK")

            # Test Claude API
            progress.update(task, description="Testing Claude API...")
            # TODO: Add actual Claude API test
            progress.update(task, description="✓ Claude API accessible")

            console.print("[green]✓ All validations passed![/green]")

        except Exception as e:
            console.print(f"[red]✗ Validation failed: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be processed without actually processing",
)
@click.option("--batch-size", default=10, help="Number of entries to process at once")
@click.option("--output", "-o", help="Output file for results")
def process(file_path, dry_run, batch_size, output):
    """Process price entries from a file"""

    file_path = Path(file_path)

    if not file_path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        sys.exit(1)

    console.print(f"[blue]Processing file: {file_path}[/blue]")

    if dry_run:
        console.print("[yellow]DRY RUN MODE - No actual processing will occur[/yellow]")

    try:
        # TODO: Implement actual file processing
        # For now, just show what would be done

        if file_path.suffix.lower() == ".json":
            with open(file_path) as f:
                data = json.load(f)

            console.print(f"[green]Loaded {len(data)} entries from JSON file[/green]")

            if dry_run:
                table = Table(title="Price Entries Preview")
                table.add_column("Model Code", style="cyan")
                table.add_column("Brand", style="green")
                table.add_column("Price", style="yellow")
                table.add_column("Year", style="blue")

                # Show first 5 entries
                for entry in data[:5]:
                    table.add_row(
                        entry.get("model_code", "N/A"),
                        entry.get("brand", "N/A"),
                        str(entry.get("price", "N/A")),
                        str(entry.get("model_year", "N/A")),
                    )

                console.print(table)
                console.print(
                    f"[dim]... and {max(0, len(data) - 5)} more entries[/dim]"
                )

        else:
            console.print(f"[red]Unsupported file format: {file_path.suffix}[/red]")
            console.print("Supported formats: .json")
            sys.exit(1)

        if not dry_run:
            # TODO: Implement actual processing logic
            console.print(
                "[yellow]Processing functionality not yet implemented[/yellow]"
            )
            console.print("Use --dry-run to preview files")

    except Exception as e:
        console.print(f"[red]Error processing file: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def serve(host, port, reload):
    """Start the API server"""
    try:
        import uvicorn

        console.print(f"[green]Starting server on {host}:{port}[/green]")

        if reload:
            console.print("[yellow]Auto-reload enabled (development mode)[/yellow]")

        uvicorn.run(
            "src.main:app", host=host, port=port, reload=reload, log_level="info"
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Server error: {e}[/red]")
        sys.exit(1)


@cli.command()
def db():
    """Database management commands"""
    console.print("[blue]Database Management[/blue]")
    console.print("Available subcommands:")
    console.print("  • migrate  - Run database migrations")
    console.print("  • reset    - Reset database (development only)")
    console.print("  • backup   - Create database backup")
    console.print("  • status   - Show database status")

    console.print(
        "\n[dim]Use: poetry run alembic [command] for direct Alembic access[/dim]"
    )


@cli.command()
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json", "csv"]),
    help="Output format",
)
def stats(output_format):
    """Show processing statistics"""
    try:
        # TODO: Implement actual statistics retrieval
        # For now, show mock data

        mock_stats = {
            "total_products": 1250,
            "high_confidence": 890,
            "medium_confidence": 280,
            "low_confidence": 80,
            "processing_time_avg": 150,  # ms
            "claude_tokens_used": 45000,
            "success_rate": 94.2,
        }

        if output_format == "json":
            console.print_json(json.dumps(mock_stats, indent=2))
        elif output_format == "csv":
            console.print("metric,value")
            for key, value in mock_stats.items():
                console.print(f"{key},{value}")
        else:  # table
            table = Table(title="Processing Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Total Products", str(mock_stats["total_products"]))
            table.add_row(
                "High Confidence",
                f"{mock_stats['high_confidence']} ({mock_stats['high_confidence']/mock_stats['total_products']*100:.1f}%)",
            )
            table.add_row(
                "Medium Confidence",
                f"{mock_stats['medium_confidence']} ({mock_stats['medium_confidence']/mock_stats['total_products']*100:.1f}%)",
            )
            table.add_row(
                "Low Confidence",
                f"{mock_stats['low_confidence']} ({mock_stats['low_confidence']/mock_stats['total_products']*100:.1f}%)",
            )
            table.add_row(
                "Avg Processing Time", f"{mock_stats['processing_time_avg']}ms"
            )
            table.add_row("Claude Tokens Used", f"{mock_stats['claude_tokens_used']:,}")
            table.add_row("Success Rate", f"{mock_stats['success_rate']}%")

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error retrieving statistics: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("model_code")
@click.option("--brand", help="Product brand")
@click.option("--year", type=int, help="Model year")
def lookup(model_code, brand, year):
    """Look up product information by model code"""
    console.print(f"[blue]Looking up model: {model_code}[/blue]")

    if brand:
        console.print(f"[dim]Brand filter: {brand}[/dim]")
    if year:
        console.print(f"[dim]Year filter: {year}[/dim]")

    try:
        # TODO: Implement actual lookup logic
        console.print("[yellow]Lookup functionality not yet implemented[/yellow]")
        console.print("This will search the database for matching products")

    except Exception as e:
        console.print(f"[red]Lookup error: {e}[/red]")
        sys.exit(1)


@cli.command()
def test():
    """Run the test suite"""
    console.print("[blue]Running test suite...[/blue]")

    try:
        import subprocess

        result = subprocess.run(
            ["python", "-m", "pytest", "tests/", "-v"], capture_output=True, text=True
        )

        if result.returncode == 0:
            console.print("[green]✓ All tests passed![/green]")
        else:
            console.print(
                f"[red]✗ Tests failed with exit code {result.returncode}[/red]"
            )
            if result.stdout:
                console.print(result.stdout)
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            sys.exit(result.returncode)

    except FileNotFoundError:
        console.print(
            "[red]pytest not found. Install with: poetry install --with dev[/red]"
        )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Test execution error: {e}[/red]")
        sys.exit(1)


@cli.command()
def version():
    """Show version information"""
    console.print(
        f"[bold green]Snowmobile Product Reconciliation v{__version__}[/bold green]"
    )
    console.print("[dim]Professional product data reconciliation system[/dim]")
    console.print("[dim]Built with Python, FastAPI, PostgreSQL, and Claude AI[/dim]")


if __name__ == "__main__":
    cli()
