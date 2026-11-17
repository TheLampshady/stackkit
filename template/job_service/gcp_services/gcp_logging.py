import logging
import sys

logger = logging.getLogger(__name__)


class StructuredLogFormatter(logging.Formatter):
    """
    Formatter that outputs JSON-structured logs for Cloud Logging.

    Includes extra 'json_fields' if provided in the log record, which allows
    structured data to be indexed and searchable in Cloud Logging.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Get the base formatted message
        message = super().format(record)

        # If json_fields are provided, append them to the message
        json_fields = getattr(record, "json_fields", None)
        if json_fields:
            import json

            message = f"{message} | {json.dumps(json_fields)}"

        return message


def setup_logging(is_local: bool) -> None:
    """
    Configure logging for the application.

    In GCP environments, uses Cloud Logging with structured log support.
    In local environments, uses standard Python logging with INFO level.

    :param is_local: Whether the application is running locally.
    """
    root_logger = logging.getLogger()
    msg = "Logging Initialized: Local"

    # Initialize cloud logging
    if not is_local:
        try:
            from google.cloud import logging as cloud_logging

            client = cloud_logging.Client()
            # Setup cloud logging with structured log support
            client.setup_logging(log_level=logging.DEBUG)

            # Add a structured formatter to help with log parsing
            for handler in root_logger.handlers:
                handler.setFormatter(
                    StructuredLogFormatter(
                        fmt="%(levelname)s - %(name)s - %(message)s",
                    )
                )

            msg = "Cloud logging initialized with structured log support."
            root_logger.setLevel(logging.DEBUG)
        except ImportError:
            logger.error("Cloud Logging import failed: Using local logging")
            _setup_local_logging(root_logger)
        except Exception:
            logger.exception("Cloud Logging setup failed. Using local logging")
            _setup_local_logging(root_logger)
    else:
        _setup_local_logging(root_logger)

    logger.info(msg)


def _setup_local_logging(logger: logging.Logger) -> None:
    """
    Configure local logging with a standard format.

    :param logger: The logger to configure.
    """
    logger.setLevel(logging.INFO)

    # Only add handler if none exist
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
