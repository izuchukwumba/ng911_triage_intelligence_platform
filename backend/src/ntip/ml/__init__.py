"""Machine-learning extraction layer (design v1.2, section 3A).

Models only ever propose candidates. They are verified against the source,
fused with the rules baseline under an explicit mode, and can always be
turned off without affecting the rest of the platform.
"""
