"""Candidate strategies: authenticated WhatsApp selectors require live validation.

Override these keys in config.json's selectors object after --debug-ui inspection.
No generated class names, menu actions, composer actions, or message modifications.
"""
DEFAULTS = {
    "sidebar": "#side",
    "main": "#main",
    "search": '[role="textbox"][contenteditable="true"], input[placeholder*="Search" i], [contenteditable="true"][data-tab="3"]',
    "chat_titles": "[title]",
    "header_titles": "header [title]",
    "message": "[data-id]",
    "filename": "[title], [download], span, a",
    "download": 'button[aria-label*="download" i], [role="button"][aria-label*="download" i], [title*="download" i], [data-icon="download"], [data-icon="document-download"], a[download]',
    "document": '[data-icon*="document"], [data-icon*="file"], [data-testid*="document"]',
}


def selectors(overrides):
    unknown = set(overrides) - set(DEFAULTS)
    if unknown:
        raise ValueError(f"Unknown selector keys: {sorted(unknown)}")
    if any(not isinstance(v, str) or not v.strip() for v in overrides.values()):
        raise ValueError("Selector overrides must be nonempty CSS selector strings")
    return DEFAULTS | overrides
