import pytz
from datetime import datetime
import pytz
from datetime import datetime


def get_locale(request):
    return request.query_params.get("locale" , "en")


def get_time_zone():
    tz = pytz.timezone("Asia/Damascus")
    return tz



def is_past_datetime(date_str, time_str, request, timezone_header='X-Timezone'):
    """
    Verify if the sent date and time are in the past according to the user's time zone.

    Args:
        date_str (str): 'YYYY-MM-DD'
        time_str (str): 'HH:MM'
        request (HttpRequest): The request object to read the time zone from it.
        timezone_header (str): The name of the header that contains the time zone.

    Returns:
     bool: True if datetime in past else return False
    """
    try:
        dt_str = f"{date_str} {time_str}"
        user_datetime_naive = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")


        tz_name = request.headers.get(timezone_header, 'UTC')
        user_tz = pytz.timezone(tz_name)
        user_datetime = user_tz.localize(user_datetime_naive)

        now = datetime.now(user_tz)

        return user_datetime < now
    except Exception as e:
        raise ValueError({"details" : "Error in is_past_datetime"})
        



