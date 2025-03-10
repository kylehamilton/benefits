import pytest

from benefits.eligibility.analytics import EligibilityEvent, ReturnedEligibilityEvent


@pytest.mark.django_db
def test_EligibilityEvent_overwrites_event_eligibility_types(app_request, mocker):
    key, type1, type2 = "eligibility_types", "type1", "type2"
    mocker.patch("benefits.core.analytics.session.eligibility", return_value=[type1])
    mocker.patch("benefits.core.analytics.EligibilityType.get_names", return_value=[type1])

    event = EligibilityEvent(app_request, "event_type", [type2])

    # event_properties should have been overwritten
    assert key in event.event_properties
    assert type2 in event.event_properties[key]
    assert type1 not in event.event_properties[key]

    # user_properties should not have been overwritten
    assert key in event.user_properties
    assert type1 in event.user_properties[key]
    assert type2 not in event.user_properties[key]


@pytest.mark.django_db
def test_ReturnedEligibilityEvent_success_overwrites_user_eligibility_types(app_request, mocker):
    key, type1, type2 = "eligibility_types", "type1", "type2"
    mocker.patch("benefits.core.analytics.session.eligibility", return_value=[type1])
    mocker.patch("benefits.core.analytics.EligibilityType.get_names", return_value=[type1])

    event = ReturnedEligibilityEvent(app_request, eligibility_types=[type2], status="success")

    # user_properties should have been overwritten
    assert key in event.user_properties
    assert type1 not in event.user_properties[key]
    assert type2 in event.user_properties[key]
