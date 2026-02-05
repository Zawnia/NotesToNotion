"""Custom exceptions for NotesToNotion."""


class NotesToNotionError(Exception):
    """Base exception for NotesToNotion.

    All custom exceptions in this module inherit from this base class.
    """

    pass


class PDFValidationError(NotesToNotionError):
    """Raised when PDF file validation fails.

    Examples:
        - File is not a PDF
        - File is too large
        - File is corrupted
    """

    pass


class TranscriptionError(NotesToNotionError):
    """Raised when Gemini transcription fails.

    Examples:
        - Gemini API timeout
        - File processing failed
        - Empty transcription result
    """

    pass


class NotionError(NotesToNotionError):
    """Raised when Notion API interaction fails.

    Examples:
        - Authentication error
        - Page creation failed
        - Invalid database ID
    """

    pass
