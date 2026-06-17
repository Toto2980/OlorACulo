from __future__ import annotations

# Equipos canónicos del Mundial 2026 (deben coincidir con data/wc2026.yaml).
_CANONICAL = [
    "Mexico", "South Africa", "South Korea", "Czech Republic",
    "Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland",
    "Brazil", "Morocco", "Haiti", "Scotland",
    "United States", "Paraguay", "Australia", "Turkey",
    "Germany", "Curaçao", "Ivory Coast", "Ecuador",
    "Netherlands", "Japan", "Sweden", "Tunisia",
    "Belgium", "Egypt", "Iran", "New Zealand",
    "Spain", "Cape Verde", "Saudi Arabia", "Uruguay",
    "France", "Senegal", "Iraq", "Norway",
    "Argentina", "Algeria", "Austria", "Jordan",
    "Portugal", "DR Congo", "Uzbekistan", "Colombia",
    "England", "Croatia", "Ghana", "Panama",
]

# Spellings de la API que difieren del canónico (CONFIRMADO con /competitions/WC/teams en Task 1).
# Solo 4 difieren; el resto coincide (South Korea, United States, Turkey, Ivory Coast, Curaçao ya OK).
_OVERRIDES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Cape Verde Islands": "Cape Verde",
    "Congo DR": "DR Congo",
    "Czechia": "Czech Republic",
}

# Mapa final: identidad para cada canónico + overrides de la API.
ALIASES: dict[str, str] = {name: name for name in _CANONICAL}
ALIASES.update(_OVERRIDES)


def to_canonical(api_name: str) -> str:
    return ALIASES.get(api_name, api_name)


# Spellings de API-Football (api-sports.io) que difieren del canónico. Best-effort:
# se valida cuando el usuario cargue su API key. Lo no listado cae a to_canonical/identidad.
_APIFOOTBALL_OVERRIDES = {
    "USA": "United States",
    "Korea Republic": "South Korea",
    "IR Iran": "Iran",
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Congo DR": "DR Congo",
    "DR Congo": "DR Congo",
    "Czechia": "Czech Republic",
    "Cape Verde Islands": "Cape Verde",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
}


def apifootball_to_canonical(name: str) -> str:
    """Nombre de equipo de API-Football -> canónico del dataset."""
    if name in _APIFOOTBALL_OVERRIDES:
        return _APIFOOTBALL_OVERRIDES[name]
    return ALIASES.get(name, name)
