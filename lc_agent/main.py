# lc_agent/main.py
import argparse


def main():
    parser = argparse.ArgumentParser(description="lc_agent - LangChain Agent with Web UI")
    parser.add_argument("--config", "-c", help="Path to config.jsonc")
    parser.add_argument("--host", default="127.0.0.1", help="Server host (default: 127.0.0.1)")
    parser.add_argument("--port", "-p", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--dotenv", help="Path to .env file")
    parser.add_argument("--desktop", action="store_true", help="Run in desktop window mode")
    parser.add_argument("--title", default=None, help="Desktop window title")
    args = parser.parse_args()

    from lc_agent.config.loader import load_config

    config = load_config(config_path=args.config, dotenv_path=args.dotenv)

    from lc_agent.app import LcAgentApp

    app = LcAgentApp(config, host=args.host, port=args.port)
    app.run(desktop=args.desktop, title=args.title)


if __name__ == "__main__":
    main()
