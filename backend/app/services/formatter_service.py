from datetime import datetime


def pretty_time(iso_time):

    try:

        dt = datetime.fromisoformat(
            iso_time.replace("Z", "+00:00")
        )

        return dt.strftime("%I:%M %p")

    except:
        return iso_time