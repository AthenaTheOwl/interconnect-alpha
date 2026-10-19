import pytest

from interconnect_alpha.kaplan_meier import kaplan_meier


@pytest.mark.parametrize("durations,events", [([-1], [1]), ([float("nan")], [1]), ([float("inf")], [0]), ([1], [2]), ([1], [0.5]), ([10 ** 400], [1])])
def test_invalid_cohort_cannot_produce_a_survival_curve(durations, events):
    with pytest.raises(ValueError):
        kaplan_meier(durations, events)


@pytest.mark.parametrize("z", [0, -1, float("nan"), float("inf")])
def test_invalid_confidence_multiplier_is_rejected(z):
    with pytest.raises(ValueError):
        kaplan_meier([1], [1], z=z)
