# tests/test_smoke.py
import offlinestreetview
from offlinestreetview.app import make_layout
from offlinestreetview.tiles import deg2num


def _ids(node, out):
    if isinstance(node, (list, tuple)):
        for item in node:
            _ids(item, out)
        return
    nid = getattr(node, "id", None)
    if isinstance(nid, str):
        out.add(nid)
    _ids(getattr(node, "children", None) or [], out)


def test_version():
    assert offlinestreetview.__version__


def test_layout_ids_after_cleanup():
    ids = set()
    _ids(make_layout(), ids)
    # removed by the requested changes
    assert "bubble-column" not in ids            # change 2
    assert "cfg-bar-width-pct" not in ids        # change 4
    # still required
    assert {"image-slider", "bar-subheading", "map-opacity-slider",
            "cfg-bar-height-vh", "bar-plot", "map"} <= ids


def test_deg2num():
    x, y = deg2num(38.89, -77.03, 18)
    assert isinstance(x, int) and isinstance(y, int)