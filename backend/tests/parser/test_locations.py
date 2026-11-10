from ntip.parser.locations import ExtractedLocation, extract_locations


def only(text: str) -> ExtractedLocation:
    [location] = extract_locations(text)
    return location


def test_numbered_address_with_unit_before_it() -> None:
    text = "My father is not breathing. We're in apartment 4B at 12 Oak Street."
    location = only(text)
    assert location.kind == "numbered"
    assert location.raw_text(text) == "apartment 4B at 12 Oak Street"
    assert location.civic_address.house_number == "12"
    assert location.civic_address.street == "Oak Street"
    assert location.civic_address.unit == "4B"
    assert location.missing_fields == ["locality", "region"]


def test_numbered_address_with_unit_after_it_and_postcode() -> None:
    text = "Send help to 2210 West Ridgeway Boulevard apartment 4B, 60614."
    location = only(text)
    assert location.civic_address.street == "West Ridgeway Boulevard"
    assert location.civic_address.unit == "4B"
    assert location.civic_address.postal_code == "60614"


def test_unit_in_another_sentence_is_not_attached() -> None:
    text = "We live at 12 Oak Street. Room 5 at the school is empty."
    assert extract_locations(text)[0].civic_address.unit is None


def test_spanish_street_order() -> None:
    text = "Mi esposo no está respirando en la Calle Pino 789."
    location = only(text)
    assert (location.civic_address.street, location.civic_address.house_number) == (
        "Calle Pino",
        "789",
    )


def test_intersection() -> None:
    location = only("Someone was shot with a gun near 5th and Oak.")
    assert location.kind == "intersection"
    assert location.civic_address.street == "5th & Oak"
    assert "house_number" not in location.missing_fields


def test_corner_phrase_is_part_of_the_intersection() -> None:
    text = "Crash at the corner of Main Street and Elm Avenue."
    assert only(text).raw_text(text) == "corner of Main Street and Elm Avenue"


def test_conjunctions_that_are_not_streets() -> None:
    assert extract_locations("He is bleeding and he is not breathing.") == []


def test_route_reference_and_landmark_are_both_kept() -> None:
    route, landmark = extract_locations("There's been a crash on Route 9 near the old overpass.")
    assert (route.kind, landmark.kind) == ("route", "landmark")
    assert "house_number" in route.missing_fields


def test_street_without_number() -> None:
    location = only("Someone has been shot near 5th street.")
    assert location.kind == "street"
    assert location.civic_address.street == "5th street"
    assert location.missing_fields == ["house_number", "locality", "region"]


def test_landmark_lacks_street_and_number() -> None:
    location = only("There is a suspicious person near the Riverside park.")
    assert location.kind == "landmark"
    assert location.civic_address.landmark == "the Riverside park"
    assert {"street", "house_number"} <= set(location.missing_fields)


def test_every_mention_is_kept_in_order() -> None:
    text = "I'm at 123 Main Street. Sorry, I mean 321 Main Street."
    assert [loc.civic_address.house_number for loc in extract_locations(text)] == ["123", "321"]


def test_no_location() -> None:
    assert (
        extract_locations("Someone is hurt somewhere near here. I do not know the address.") == []
    )


def test_counts_are_not_addresses() -> None:
    assert extract_locations("There are 4 people hurt.") == []
