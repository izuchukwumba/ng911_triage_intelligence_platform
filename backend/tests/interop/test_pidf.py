"""Reading PIDF-LO safely: civic addresses and points, nothing guessed."""

import pytest

from ntip.interop.eido.pidf import UnreadablePidf, parse_pidf_lo

NS = (
    'xmlns="urn:ietf:params:xml:ns:pidf" xmlns:gp="urn:ietf:params:xml:ns:pidf:geopriv10" '
    'xmlns:ca="urn:ietf:params:xml:ns:pidf:geopriv10:civicAddr" '
    'xmlns:gml="http://www.opengis.net/gml" xmlns:gs="http://www.opengis.net/pidflo/1.0"'
)


def pidf(location_info: str) -> str:
    return (
        f'<presence {NS} entity="pres:a@synthetic.example"><tuple id="t"><status><gp:geopriv>'
        f"<gp:location-info>{location_info}</gp:location-info></gp:geopriv></status></tuple>"
        "</presence>"
    )


def test_civic_address() -> None:
    location = parse_pidf_lo(
        pidf(
            "<ca:civicAddress><ca:A1>IL</ca:A1><ca:A3>Springfield</ca:A3><ca:PRD>N</ca:PRD>"
            "<ca:RD>Main</ca:RD><ca:STS>St</ca:STS><ca:HNO>12</ca:HNO><ca:HNS>A</ca:HNS>"
            "<ca:FLR>2</ca:FLR><ca:UNIT>4B</ca:UNIT><ca:PC>62701</ca:PC></ca:civicAddress>"
        )
    )
    address = location.civic_address
    assert address is not None and location.coordinates is None
    assert (address.house_number, address.street) == ("12A", "N Main St")
    assert (address.locality, address.region, address.postal_code) == ("Springfield", "IL", "62701")
    assert (address.floor, address.unit) == ("2", "4B")


def test_point_and_circle() -> None:
    point = parse_pidf_lo(pidf('<gml:Point srsName="urn:ogc:def:crs:EPSG::4326">'
                               "<gml:pos>39.78 -89.65</gml:pos></gml:Point>"))  # fmt: skip
    assert point.coordinates is not None
    assert (point.coordinates.lat, point.coordinates.lng) == (39.78, -89.65)
    assert point.coordinates.uncertainty_m is None
    circle = parse_pidf_lo(pidf(
        '<gs:Circle srsName="urn:ogc:def:crs:EPSG::4326"><gml:pos>39.78 -89.65</gml:pos>'
        '<gs:radius uom="urn:ogc:def:uom:EPSG::9001">35</gs:radius></gs:Circle>'))  # fmt: skip
    assert circle.coordinates is not None and circle.coordinates.uncertainty_m == 35


@pytest.mark.parametrize(
    ("document", "reason"),
    [
        ("<!DOCTYPE x [<!ENTITY a 'b'>]><presence>&a;</presence>", "DOCTYPE"),
        ('<!DOCTYPE x SYSTEM "file:///etc/passwd"><presence/>', "DOCTYPE"),
        ("<presence><unclosed></presence>", "well-formed"),
        (pidf("<gml:Polygon><gml:exterior/></gml:Polygon>"), "no civic address"),
        (pidf('<gml:Point srsName="urn:ogc:def:crs:EPSG::3857"><gml:pos>1 2</gml:pos>'
              "</gml:Point>"), "reference system"),
        (pidf("<gml:Point><gml:pos>95 10</gml:pos></gml:Point>"), "out of range"),
        (pidf("<gml:Point><gml:pos>north</gml:pos></gml:Point>"), "latitude longitude"),
        (pidf('<gs:Circle><gml:pos>1 2</gml:pos><gs:radius uom="ft">9</gs:radius></gs:Circle>'),
         "metres"),
        (pidf('<gs:Circle><gml:pos>1 2</gml:pos><gs:radius uom="m">-1</gs:radius></gs:Circle>'),
         "positive"),
        ("x" * 20_001, "too large"),
    ],
)  # fmt: skip
def test_anything_not_fully_understood_is_refused(document: str, reason: str) -> None:
    with pytest.raises(UnreadablePidf, match=reason):
        parse_pidf_lo(document)
