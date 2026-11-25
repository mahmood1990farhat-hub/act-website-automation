"""Public route preview for the passenger website's first booking step."""

from ipaddress import ip_address

from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.parsers import JSONParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.trips.services.route_preview import ROUTE_FIELDS, preview_route_arguments, sign_route
from utils.common.google_map import get_route_with_distance


class RoutePreviewThrottle(SimpleRateThrottle):
    scope = 'trip-route-preview'
    rate = '12/min'

    def get_cache_key(self, request, view):
        # On the ACT host Nginx proxies to loopback. Only trust its appended
        # rightmost forwarding entry, not a list of client-supplied values.
        peer = request.META.get('REMOTE_ADDR', '')
        if peer in ('127.0.0.1', '::1'):
            tail = request.META.get('HTTP_X_FORWARDED_FOR', '').rsplit(',', 1)[-1].strip()
            try:
                peer = str(ip_address(tail))
            except ValueError:
                pass
        return self.cache_format % {'scope': self.scope, 'ident': peer}


class RoutePreviewTotalThrottle(SimpleRateThrottle):
    scope = 'trip-route-preview-total'
    rate = '60/min'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': 'all'}


@method_decorator(never_cache, name='dispatch')
class RoutePreviewView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    parser_classes = (JSONParser,)
    throttle_classes = (RoutePreviewThrottle, RoutePreviewTotalThrottle)

    def post(self, request):
        try:
            arguments = preview_route_arguments(request.data)
        except ValueError:
            return Response({'code': 'invalid_route'}, status=400)
        try:
            route = get_route_with_distance(**arguments)
        except Exception:
            # Provider exceptions may include credentials or customer coordinates.
            return Response({'code': 'route_preview_unavailable'}, status=503)
        result = {key: route[key] for key in ROUTE_FIELDS}
        result['route_proof'] = sign_route(arguments, result)
        return Response(result)
