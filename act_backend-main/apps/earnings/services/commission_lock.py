"""Serializes commission commands and driver acceptance in one lock order.

The production database and the isolated acceptance suite use PostgreSQL.
Call inside atomic(), BEFORE taking driver/group/rule/trip row locks.
"""
from django.db import connection
from django.db.transaction import TransactionManagementError

COMMISSION_LOCK_KEY = 1094931523


def lock_commission_configuration():
    if not connection.in_atomic_block:
        raise TransactionManagementError('Commission locking requires an atomic transaction.')
    if connection.vendor == 'postgresql':
        with connection.cursor() as cursor:
            cursor.execute('SELECT pg_advisory_xact_lock(%s)', [COMMISSION_LOCK_KEY])
