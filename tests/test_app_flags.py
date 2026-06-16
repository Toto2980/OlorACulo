from app.flags import display_name, with_flag


def test_display_name_traduce_los_que_difieren():
    assert display_name("Brazil") == "Brasil"
    assert display_name("Spain") == "España"
    assert display_name("Germany") == "Alemania"
    assert display_name("England") == "Inglaterra"
    assert display_name("Netherlands") == "Países Bajos"


def test_display_name_deja_intactos_los_que_coinciden():
    assert display_name("Argentina") == "Argentina"
    assert display_name("Colombia") == "Colombia"


def test_display_name_equipo_desconocido_se_devuelve_igual():
    assert display_name("Wakanda") == "Wakanda"


def test_with_flag_usa_nombre_en_espanol():
    assert with_flag("Brazil") == "🇧🇷 Brasil"
    assert with_flag("Argentina") == "🇦🇷 Argentina"
    assert with_flag("Wakanda") == "⚽ Wakanda"
