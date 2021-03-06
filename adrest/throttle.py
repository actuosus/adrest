import time

from django.core.cache import cache
from adrest.utils import HttpError
from adrest.status import HTTP_503_SERVICE_UNAVAILABLE
from adrest.settings import THROTTLE_AT, THROTTLE_TIMEFRAME


class BaseThrottle(object):
    """ Fake throttle class.
    """
    def __init__(self, throttle_at=THROTTLE_AT, timeframe=THROTTLE_TIMEFRAME):
        self.throttle_at = throttle_at
        self.timeframe = timeframe

    def convert_identifier_to_key(self, identifier):
        """ Takes an identifier (like a username or IP address) and converts it
            into a key usable by the cache system.
        """
        return "%s_accesses" % ''.join(
            char for char in identifier if char.isalnum() or char in ( '_', '.', '-' )
        )

    def should_be_throttled(self, identifier, **kwargs):
        """ Returns whether or not the user has exceeded their throttle limit.
        """
        return 0


class CacheThrottle(BaseThrottle):
    """ A throttling mechanism that uses just the cache.
    """
    def _get_params(self, key):
        count, expiration = cache.get(key, (1, None))
        now = time.time()
        if expiration is None:
            expiration = now + self.timeframe
        return count, expiration, now

    def should_be_throttled(self, identifier, **kwargs):
        key = self.convert_identifier_to_key(identifier)
        count, expiration, now = self._get_params(key)
        if count >= self.throttle_at and expiration > now:
            return expiration - now

        cache.set(key, (count+1, expiration), (expiration - now))
        return 0


class ThrottleMixin(object):

    throttle = BaseThrottle

    def throttle_check(self):
        throttle = self.throttle()
        wait = throttle.should_be_throttled(self.identifier)
        if wait:
            raise HttpError("Throttled, wait %d seconds." % wait, status=HTTP_503_SERVICE_UNAVAILABLE)
