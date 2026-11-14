"""Validate PDFminer before the lazy parser imports its private interfaces."""

from importlib.metadata import PackageNotFoundError, version

SUPPORTED_PDFMINER = "20260107"


def pdfminer_compatibility_error() -> str | None:
    """Return an actionable diagnostic for an unqualified PDFminer installation."""
    try:
        installed = version("pdfminer.six")
    except PackageNotFoundError:
        installed = "not installed"
    if installed == SUPPORTED_PDFMINER:
        return None
    return (
        f"PDF instrumentation requires pdfminer.six=={SUPPORTED_PDFMINER}; found {installed}. "
        "Reinstall PolyFile's declared dependencies or upgrade PolyFile to an adapter "
        "qualified for your PDFminer release."
    )
