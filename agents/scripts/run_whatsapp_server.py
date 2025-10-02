"""Run the WhatsApp webhook server with uvicorn."""

from __future__ import annotations

import uvicorn
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    uvicorn.run(
        "autifyme_agents.entrypoints.whatsapp_webhook:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["."],
    )


if __name__ == "__main__":
    main()
