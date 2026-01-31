"""
Template Service - renders email templates using Jinja2.

Provides templated email rendering for disaster notifications with
custom filters for severity colors and datetime formatting.
"""

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from src.config import config
from src.models import NGO, Disaster


def _severity_color(severity: str) -> str:
    """
    Map severity level to CSS class suffix.

    Args:
        severity: The severity level (critical, high, medium, low)

    Returns:
        CSS class suffix for the severity badge.
    """
    severity_lower = str(severity).lower()
    if severity_lower in ("critical", "high", "medium", "low"):
        return severity_lower
    return "medium"


def _format_datetime(dt: datetime | None, fmt: str = "%Y-%m-%d %H:%M UTC") -> str:
    """
    Format a datetime object for display.

    Args:
        dt: The datetime to format (can be None)
        fmt: strftime format string

    Returns:
        Formatted datetime string or "N/A" if None.
    """
    if dt is None:
        return "N/A"
    return dt.strftime(fmt)


class TemplateService:
    """Service for rendering Jinja2 email templates."""

    def __init__(self, template_dir: str | None = None):
        """
        Initialize the template service.

        Args:
            template_dir: Path to templates directory. Defaults to config.template_dir.
        """
        self._template_dir = Path(template_dir or config.template_dir)

        self._env = Environment(
            loader=FileSystemLoader(self._template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom filters
        self._env.filters["severity_color"] = _severity_color
        self._env.filters["format_datetime"] = _format_datetime

    def render_disaster_alert(self, ngo: NGO, disaster: Disaster) -> str:
        """
        Render a disaster alert email for an NGO.

        Args:
            ngo: The NGO receiving the notification
            disaster: The disaster to notify about

        Returns:
            Rendered HTML string for the email body.
        """
        template = self._env.get_template("disaster_alert.html")

        # Convert models to dicts for template access
        ngo_data = ngo.model_dump()
        disaster_data = disaster.model_dump()

        return template.render(
            ngo=ngo_data,
            disaster=disaster_data,
        )

    def render_template(self, template_name: str, **context) -> str:
        """
        Render an arbitrary template with context.

        Args:
            template_name: Name of the template file
            **context: Template context variables

        Returns:
            Rendered HTML string.
        """
        template = self._env.get_template(template_name)
        return template.render(**context)
