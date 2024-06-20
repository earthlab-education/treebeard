"""""" # start delvewheel patch
def _delvewheel_patch_1_5_4():
    import os
    libs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'shapely.libs'))
    if os.path.isdir(libs_dir):
        os.add_dll_directory(libs_dir)


_delvewheel_patch_1_5_4()
del _delvewheel_patch_1_5_4
# end delvewheel patch

from shapely.lib import GEOSException  # NOQA
from shapely.lib import Geometry  # NOQA
from shapely.lib import geos_version, geos_version_string  # NOQA
from shapely.lib import geos_capi_version, geos_capi_version_string  # NOQA
from shapely.errors import setup_signal_checks  # NOQA
from shapely._geometry import *  # NOQA
from shapely.creation import *  # NOQA
from shapely.constructive import *  # NOQA
from shapely.predicates import *  # NOQA
from shapely.measurement import *  # NOQA
from shapely.set_operations import *  # NOQA
from shapely.linear import *  # NOQA
from shapely.coordinates import *  # NOQA
from shapely.strtree import *  # NOQA
from shapely.io import *  # NOQA

# Submodule always needs to be imported to ensure Geometry subclasses are registered
from shapely.geometry import (  # NOQA
    Point,
    LineString,
    Polygon,
    MultiPoint,
    MultiLineString,
    MultiPolygon,
    GeometryCollection,
    LinearRing,
)

from shapely import _version

__version__ = _version.get_versions()["version"]

setup_signal_checks()