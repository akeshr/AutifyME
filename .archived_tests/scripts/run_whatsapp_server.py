"""Operational helpers for the WhatsApp webhook stack.

We expose two entrypoints so operators can spin up the FastAPI webhook and an
ngrok tunnel without hand-crafted shell steps. Keeping this scripted guarantees
alignment with our Architecture-First practice of reproducible environments.
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

LOG = logging.getLogger(__name__)


def _load_env() -> None:
    """Load environment variables from the project root .env."""
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        LOG.warning(".env file not found at %s; relying on ambient variables", env_path)
    load_dotenv(env_path)


def run_server(host: str, port: int) -> None:
    """Run the WhatsApp webhook FastAPI app with uvicorn."""
    _load_env()

    LOG.info("Starting WhatsApp webhook server on %s:%s", host, port)
    uvicorn.run(
        "autifyme_agents.entrypoints.whatsapp_webhook:app",
        host=host,
        port=port,
        reload=True,
        reload_dirs=["."],
    )


def _run_subprocess(cmd: Iterable[str]) -> None:
    LOG.info("Launching: %s", " ".join(cmd))
    try:
        subprocess.run(list(cmd), check=True)
    except FileNotFoundError as exc:  # pragma: no cover - operational failure
        raise RuntimeError(
            "Executable not found. Ensure the tool is installed and on PATH."
        ) from exc


def start_ngrok(port: int, domain: str | None) -> None:
    """Start an ngrok tunnel for the given local port."""
    _load_env()

    cmd: list[str] = ["ngrok", "http", str(port)]
    if domain:
        cmd.extend(["--domain", domain])

    _run_subprocess(cmd)


def start_cloudflare_tunnel(port: int, hostname: str | None) -> None:
    """Start a Cloudflare quick tunnel for the given local port."""
    _load_env()

    cmd: list[str] = [
        "cloudflared",
        "tunnel",
        "--url",
        f"http://localhost:{port}",
    ]
    if hostname:
        cmd.extend(["--hostname", hostname])

    _run_subprocess(cmd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WhatsApp webhook tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve_parser = subparsers.add_parser("serve", help="Run the FastAPI webhook server")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Bind address for uvicorn")
    serve_parser.add_argument("--port", type=int, default=8000, help="Bind port for uvicorn")

    ngrok_parser = subparsers.add_parser("ngrok", help="Start an ngrok tunnel")
    ngrok_parser.add_argument("--port", type=int, default=8000, help="Local port to expose")
    ngrok_parser.add_argument(
        "--domain",
        default=None,
        help="Reserved ngrok domain (optional; requires paid plan)",
    )

    cf_parser = subparsers.add_parser(
        "cloudflare", help="Start a Cloudflare quick tunnel"
    )
    cf_parser.add_argument("--port", type=int, default=8000, help="Local port to expose")
    cf_parser.add_argument(
        "--hostname",
        default=None,
        help="Custom hostname (requires named tunnel)",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    if args.command == "serve":
        run_server(args.host, args.port)
    elif args.command == "ngrok":
        start_ngrok(args.port, args.domain)
    elif args.command == "cloudflare":
        start_cloudflare_tunnel(args.port, args.hostname)
    else:  # pragma: no cover - argparse prevents this
        parser.error(f"Unknown command: {args.command}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
