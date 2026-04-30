from typing import Optional, Dict, Any
from django.contrib.gis.geos import Point
from apps.trips.models import Airport


class AirportResolver:
    
    @staticmethod
    def find_airport_at_location(lat: float, lng: float) -> Optional[Airport]:
        if not lat or not lng:
            return None
            
        point = Point(lng, lat, srid=4326)
    
        airports = Airport.objects.filter(
            is_active=True,
            detection_area__isnull=False,
            detection_area__contains=point
        )
        
        return airports.first()
    
    @staticmethod
    def detect_airport(
        pickup_lat: float,
        pickup_lng: float,
        dropoff_lat: float,
        dropoff_lng: float,
        manual_airport_id: Optional[int] = None
    ) -> Dict[str, Any]:
        result = {
            'pickup_in_airport': False,
            'dropoff_in_airport': False,
            'both_in_airports': False,
            'pickup_airport': None,
            'dropoff_airport': None,
        }
        
        if manual_airport_id:
            try:
                airport = Airport.objects.get(id=manual_airport_id, is_active=True)
                if airport.detection_area:
                    pickup_point = Point(pickup_lng, pickup_lat, srid=4326)
                    dropoff_point = Point(dropoff_lng, dropoff_lat, srid=4326)
                    
                    result['pickup_in_airport'] = airport.detection_area.contains(pickup_point)
                    result['dropoff_in_airport'] = airport.detection_area.contains(dropoff_point)
                    
                    if result['pickup_in_airport']:
                        result['pickup_airport'] = airport
                    if result['dropoff_in_airport']:
                        result['dropoff_airport'] = airport
                    
                    result['both_in_airports'] = result['pickup_in_airport'] and result['dropoff_in_airport']
                
                return result
            except Airport.DoesNotExist:
                pass
        
        
        pickup_airport = AirportResolver.find_airport_at_location(pickup_lat, pickup_lng)
        dropoff_airport = AirportResolver.find_airport_at_location(dropoff_lat, dropoff_lng)
        
        result['pickup_in_airport'] = pickup_airport is not None
        result['dropoff_in_airport'] = dropoff_airport is not None
        result['pickup_airport'] = pickup_airport
        result['dropoff_airport'] = dropoff_airport
        result['both_in_airports'] = pickup_airport is not None and dropoff_airport is not None

        return result

