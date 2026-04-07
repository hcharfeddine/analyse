"""
Custom exception classes for the academic paper scraper.

This module defines a hierarchy of exceptions used throughout the application
to handle specific error conditions.
"""


class ScraperException(Exception):
    """Base exception for all scraper-related errors."""
    pass


class APIException(ScraperException):
    """Exception raised when an API request fails."""
    pass


class ExportException(ScraperException):
    """Exception raised when data export fails."""
    pass


class ValidationException(ScraperException):
    """Exception raised when data validation fails."""
    pass
