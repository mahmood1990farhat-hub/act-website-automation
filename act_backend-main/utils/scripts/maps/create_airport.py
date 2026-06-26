from django.contrib.gis.geos import Polygon
from apps.trips.models import Airport
from .data.luton import data as luton_data
from .data.heathrow import data as heathrow_data
from .data.gatwick  import data as gatwick_data
from .data.stansted  import data as stansted_data


AIRPORTS_DATA = [
    luton_data,
    heathrow_data,
    gatwick_data,
    stansted_data,
]

def import_airports():
    created = 0
    updated = 0

    for airport_data in AIRPORTS_DATA:

        coordinates = airport_data["coordinates"]

        # GeoDjango requires (lon, lat)
        polygon_points = [(c["lon"], c["lat"]) for c in coordinates]

        if polygon_points[0] != polygon_points[-1]:
            polygon_points.append(polygon_points[0])

        polygon = Polygon(polygon_points)

        airport, was_created = Airport.objects.update_or_create(
            name_en=airport_data["name_en"],
            defaults={
                "name_ar": airport_data["name_ar"],
                "pickup_vat": airport_data["pickup_vat"],
                "dropoff_vat": airport_data["dropoff_vat"],
                "detection_area": polygon,
            },
        )

        if was_created:
            created += 1
        else:
            updated += 1

    return {
        "created": created,
        "updated": updated
    }

print("Importing airports...")
import_airports()