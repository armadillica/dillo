# This functions come from Reddit
# https://github.com/reddit/reddit/blob/master/r2/r2/lib/db/_sorts.pyx

# Additional resources
# http://www.redditblog.com/2009/10/reddits-new-comment-sorting-system.html
# http://www.evanmiller.org/how-not-to-sort-by-average-rating.html
# http://amix.dk/blog/post/19588

from datetime import datetime, timezone
from math import log
from math import sqrt

epoch = datetime(1970, 1, 1, 0, 0, 0, 0, timezone.utc)


def epoch_seconds(date):
    """Returns the number of seconds from the epoch to date."""
    td = date - epoch
    return td.days * 86400 + td.seconds + (float(td.microseconds) / 1000000)


def score(ups, downs):
    return ups - downs


def hot(ups, downs, date):
    """The hot formula. Reddit's hot ranking uses the logarithm function to
    weight the first votes higher than the rest.
    The first 10 upvotes have the same weight as the next 100 upvotes which
    have the same weight as the next 1000, etc.

    Dillo authors: we modified the formula to give more weight to negative
    votes when the post is not controversial.
    """

    s = score(ups, downs)
    order = log(max(abs(s), 1), 10)
    sign = 1 if s > 0 else -1 if s < 0 else 0
    seconds = epoch_seconds(date) - 1134028003
    base_hot = round(sign * order + seconds / 45000, 7)

    if downs > 1:
        rating_delta = 100 * (downs - ups) / downs
        if rating_delta < 25:
            # The post is controversial
            return base_hot
        base_hot = base_hot - (downs * 6)

    return base_hot


def _confidence(ups, downs):
    n = ups + downs

    if n == 0:
        return 0

    z = 1.0 #1.0 = 85%, 1.6 = 95%
    phat = float(ups) / n
    return sqrt(phat+z*z/(2*n)-z*((phat*(1-phat)+z*z/(4*n))/n))/(1+z*z/n)


def confidence(ups, downs):
    if ups + downs == 0:
        return 0
    else:
        return _confidence(ups, downs)
