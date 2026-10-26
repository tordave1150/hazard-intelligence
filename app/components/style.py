"""
Shared style injection for pages that don't use the forecast page's
inline CSS (e.g. historical.py).

Task 2: Delegates to the centralized theme.apply_theme() to keep
all pages consistent with the Sky Palette light design.
"""

from theme import apply_theme


def inject_custom_css():
    """Inject the Sky Palette light theme CSS.

    Delegates to theme.apply_theme() for consistency across all pages.
    """
    apply_theme()
