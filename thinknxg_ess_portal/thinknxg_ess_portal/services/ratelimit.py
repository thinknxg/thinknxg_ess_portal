import frappe
from frappe import _


def check_rate(bucket, limit, seconds=3600, user=None):
    """Per-user sliding-bucket limiter backed by Redis."""
    limit = int(limit or 0)
    if limit <= 0:
        return
    user = user or frappe.session.user
    key = f"ess_rl:{bucket}:{user}"
    count = frappe.cache.incrby(key, 1)
    if count == 1:
        frappe.cache.expire(key, seconds)
    if count > limit:
        frappe.throw(_("Too many requests. Please try again later."), frappe.RateLimitExceededError)
