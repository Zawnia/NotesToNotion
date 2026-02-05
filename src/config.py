"""Configuration management for NotesToNotion."""

from dataclasses import dataclass
from typing import Literal


@dataclass
class GeminiConfig:
    """Configuration for Gemini API.

    Attributes:
        model: Gemini model name to use.
        upload_timeout: Maximum time in seconds to wait for file processing.
        poll_interval: Time in seconds between file status checks.
        max_file_size_mb: Maximum PDF file size in megabytes.
    """

    model: str = "gemini-2.0-flash"
    upload_timeout: int = 120
    poll_interval: float = 2.0
    max_file_size_mb: int = 50


@dataclass
class NotionConfig:
    """Configuration for Notion API.

    Attributes:
        block_limit: Maximum characters per Notion block.
        max_retries: Maximum number of retry attempts for API calls.
        base_delay: Initial delay in seconds for exponential backoff.
        max_delay: Maximum delay in seconds between retries.
    """

    block_limit: int = 2000
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0


@dataclass
class AppConfig:
    """Global application configuration.

    Attributes:
        gemini: Gemini API configuration.
        notion: Notion API configuration.
        backup_dir: Directory for local backups.
        log_level: Logging verbosity level.
    """

    gemini: GeminiConfig
    notion: NotionConfig
    backup_dir: str = "backups"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    @classmethod
    def default(cls) -> "AppConfig":
        """Create configuration with default values.

        Returns:
            AppConfig instance with default settings.
        """
        return cls(
            gemini=GeminiConfig(),
            notion=NotionConfig(),
        )

    @classmethod
    def for_testing(cls) -> "AppConfig":
        """Create configuration optimized for testing.

        Returns:
            AppConfig with shorter timeouts and faster retries.
        """
        return cls(
            gemini=GeminiConfig(
                upload_timeout=10,
                poll_interval=0.5,
            ),
            notion=NotionConfig(
                max_retries=2,
                base_delay=0.1,
                max_delay=1.0,
            ),
            backup_dir="test_backups",
        )
