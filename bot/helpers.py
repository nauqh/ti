from datetime import datetime, timedelta
import pytz


def today():
    gmt7 = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.now().astimezone(gmt7).date()


def yesterday():
    gmt7 = pytz.timezone('Asia/Ho_Chi_Minh')
    return (datetime.now().astimezone(gmt7) - timedelta(days=1)).date()
