from django.contrib import admin
from .models import (
    CommissionRule,
    DriverEarningLedger,
    CompanyRevenueLedger,
    DriverRefundLedger,
    CompanyRefundLedger,
    PayoutBatch
)


@admin.register(CommissionRule)
class CommissionRuleAdmin(admin.ModelAdmin):
    list_display = ['id', 'vehicle_type', 'company_percentage', 'driver_percentage', 'is_active', 'created_at']
    list_filter = ['is_active', 'vehicle_type']
    search_fields = ['vehicle_type__name_en']


@admin.register(DriverEarningLedger)
class DriverEarningLedgerAdmin(admin.ModelAdmin):
    list_display = ['id', 'driver', 'trip', 'gross_amount', 'net_amount', 'status', 'created_at', 'paid_at']
    list_filter = ['status', 'currency']
    search_fields = ['driver__user__email', 'trip__id']
    readonly_fields = ['created_at', 'paid_at']


@admin.register(CompanyRevenueLedger)
class CompanyRevenueLedgerAdmin(admin.ModelAdmin):
    list_display = ['id', 'trip', 'amount', 'currency', 'created_at']
    list_filter = ['currency']
    search_fields = ['trip__id']
    readonly_fields = ['created_at']


@admin.register(DriverRefundLedger)
class DriverRefundLedgerAdmin(admin.ModelAdmin):
    list_display = ['id', 'driver', 'trip', 'refund_amount', 'refund_rule', 'created_at']
    list_filter = ['refund_rule', 'currency']
    search_fields = ['driver__user__email', 'trip__id']
    readonly_fields = ['created_at']


@admin.register(CompanyRefundLedger)
class CompanyRefundLedgerAdmin(admin.ModelAdmin):
    list_display = ['id', 'trip', 'refund_amount', 'currency', 'created_at']
    list_filter = ['currency']
    search_fields = ['trip__id']
    readonly_fields = ['created_at']


@admin.register(PayoutBatch)
class PayoutBatchAdmin(admin.ModelAdmin):
    list_display = ['batch_id', 'status', 'total_amount', 'currency', 'total_earnings', 'successful_transfers', 'failed_transfers', 'created_at']
    list_filter = ['status', 'currency']
    search_fields = ['batch_id']
    readonly_fields = ['created_at', 'completed_at']

