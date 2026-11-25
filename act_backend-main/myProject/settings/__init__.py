import os
from .base import * 

# Exclude private driver data at interception, BEFORE Silk records bodies or SQL.
# Keep this callback independent of Django/DRF imports during settings loading.
SILKY_INTERCEPT_FUNC = lambda request: not request.path_info.startswith((
    '/api/drivers/', '/api/admin-panel/drivers/', '/api/admin-panel/normal-drivers/',
))
