"""Hermes Council plugin foundation."""


def register(ctx):
    """Register the plugin with Hermes."""
    for key, display_name, description in (
        ("hermes_council_member", "Council member", "Structured council member inference."),
        ("hermes_council_moderator", "Council moderator", "Structured council moderation inference."),
        ("hermes_council_verifier", "Council verifier", "Structured council verification inference."),
    ):
        ctx.register_auxiliary_task(
            key,
            display_name=display_name,
            description=description,
            defaults={"provider": "auto", "timeout": 120},
        )
