from __future__ import annotations

import datetime
from typing import Iterable, Optional

from oraculo.match import Match
from oraculo.models.poisson import PoissonConfig, PoissonModel

# Inicio del Mundial 2026: las predicciones se congelan a datos previos a esta fecha.
WC_CUTOFF = datetime.date(2026, 6, 11)

# Misma config calibrada que usa la app.
_DEFAULT = PoissonConfig(lr=0.03, home_adv=0.3, rho=-0.05)


def frozen_poisson(
    matches: Iterable[Match],
    *,
    cutoff: datetime.date = WC_CUTOFF,
    config: Optional[PoissonConfig] = None,
) -> PoissonModel:
    """Poisson entrenado SOLO con partidos anteriores al corte -> toda prediccion
    del Mundial es out-of-sample y determinista."""
    pre = [m for m in matches if m.date < cutoff]
    return PoissonModel(config or _DEFAULT).fit(pre)
