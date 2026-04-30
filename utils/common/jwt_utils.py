from __future__ import annotations

from typing import Optional

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


def get_user_from_access_token(access_token: str):
    """
    يفك ويتحقق من access token (SimpleJWT) ثم يرجع المستخدم (CustomUser) أو None.

    - يتحقق من التوقيع ووقت الانتهاء (exp) تلقائياً عبر SimpleJWT.
    - يعتمد على claim الافتراضي للمستخدم: user_id.
    """
    if not access_token or not isinstance(access_token, str):
        return None

    token_str = access_token.strip()
    if not token_str:
        return None

    try:
        token = AccessToken(token_str)
    except TokenError:
        return None
    except Exception:
        return None

    user_id = token.get("user_id")
    if not user_id:
        return None

    User = get_user_model()
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


