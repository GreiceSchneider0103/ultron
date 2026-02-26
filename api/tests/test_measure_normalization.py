from api.src.utils.measurements import parse_length_to_cm


def test_measure_normalization_variants():
    assert parse_length_to_cm("2,30m") == 230.0
    assert parse_length_to_cm("230 cm") == 230.0
    assert parse_length_to_cm("2.3 m") == 230.0
