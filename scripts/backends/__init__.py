"""Registered Spiral Oracle backends."""

from . import four_pillars, iching, symbolic_prompt, tarot, western_astrology


BACKENDS = {
    iching.BACKEND_ID: iching,
    tarot.BACKEND_ID: tarot,
    western_astrology.BACKEND_ID: western_astrology,
    four_pillars.BACKEND_ID: four_pillars,
    symbolic_prompt.BACKEND_ID: symbolic_prompt,
}
