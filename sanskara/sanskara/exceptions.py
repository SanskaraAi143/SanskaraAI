"""Custom exceptions for the Sanskara application."""

class WeddingNotActiveError(Exception):
    """Raised when an operation is attempted on a wedding that is not in 'active' status."""
    pass
