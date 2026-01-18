"""
Main entry point for the Fronius Dual MPPT to HA MQTT Bridge application.

This module provides the command-line interface and argument parsing for the application.
"""

import argparse
import logging
import os
import sys

from .config import Config, ConfigValidationError
from .controller import FroniusBridgeController

logger = logging.getLogger(__name__)


def setup_logging(log_level: str) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> int:
    """
    Main entry point for the Fronius Dual MPPT to HA MQTT Bridge.

    Parses command-line arguments, loads configuration, and starts the controller.

    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Fronius Dual MPPT to HA MQTT Bridge for Home Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Use config.yaml in current directory
  %(prog)s --config /path/to/config.yaml  # Use custom config file
        """,
    )

    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_config = os.path.join(script_dir, "config.yaml")

    parser.add_argument(
        "--config",
        type=str,
        default=default_config,
        help=f"Path to configuration file (default: {default_config})",
    )

    args = parser.parse_args()

    # Verify config file exists
    if not os.path.exists(args.config):
        print(f"Error: Configuration file not found: {args.config}", file=sys.stderr)
        return 1

    # Load and validate configuration
    try:
        config = Config(args.config)
        print(f"Using configuration file: {args.config}")
    except (FileNotFoundError, ConfigValidationError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        return 1

    # Setup logging
    setup_logging(config.log_level)
    logger.info("Fronius Dual MPPT to HA MQTT Bridge starting")

    # Create and run controller
    controller = FroniusBridgeController(config)

    try:
        controller.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, cleaning up...")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
