"""Admin-only commission controls. No payment, notification or ledger mutation.

Writes remain disabled by default pending the legacy rule transition and release
approval. New acceptance snapshots protect agreed-but-uncompleted driver payouts.
"""
import hashlib
import json
from decimal import Decimal

from django.conf import settings
from django.contrib.admin.models import CHANGE, LogEntry
from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from rest_framework import serializers
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.drivers.models import BaseDriver
from apps.earnings.models import CommissionRule, DriverCommissionGroup, DriverCommissionMembership, DriverPayoutAgreement
from apps.earnings.services.commission_resolver import CommissionResolver
from apps.earnings.services.commission_lock import lock_commission_configuration
from apps.trips.models import Trip


class CommissionConflict(APIException):
    status_code = 409
    default_detail = 'Commission settings changed. Refresh before saving.'
    default_code = 'commission_conflict'


class CommissionCommand(serializers.Serializer):
    action = serializers.ChoiceField(choices=[
        'set_global', 'set_individual', 'clear_individual', 'create_group',
        'set_group_rate', 'add_members', 'release_members',
    ])
    revision = serializers.CharField(min_length=64, max_length=64)
    reason = serializers.CharField(max_length=500, allow_blank=False)
    company_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal('0'),
        max_value=Decimal('100'), required=False,
    )
    driver_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), required=False,
        allow_empty=False, max_length=1000,
    )
    group_id = serializers.IntegerField(min_value=1, required=False)
    name = serializers.CharField(max_length=120, required=False, allow_blank=False)

    def validate(self, data):
        required = {
            'set_global': {'company_percentage'},
            'set_individual': {'company_percentage', 'driver_ids'},
            'clear_individual': {'driver_ids'},
            'create_group': {'name', 'company_percentage', 'driver_ids'},
            'set_group_rate': {'group_id', 'company_percentage'},
            'add_members': {'group_id', 'driver_ids'},
            'release_members': {'group_id', 'driver_ids'},
        }[data['action']]
        missing = required - data.keys()
        unexpected = set(self.initial_data) - required - {'action', 'revision', 'reason'}
        if missing or unexpected:
            raise ValidationError('Missing or unexpected fields for this commission action.')
        ids = data.get('driver_ids', [])
        if len(ids) != len(set(ids)):
            raise ValidationError({'driver_ids': 'Select each driver only once.'})
        return data


def commission_snapshot():
    """One category per driver; conflicting legacy data is flagged, never hidden."""
    memberships = {
        item.driver_id: item
        for item in DriverCommissionMembership.objects.select_related('group').all()
    }
    drivers = []
    conflicts = []
    for driver in BaseDriver.objects.select_related('user', 'normal_driver__vehicle__vehicle_type').order_by('id'):
        member = memberships.get(driver.id)
        individual = driver.driver_commission_percentage is not None
        if member and (individual or not member.group.is_active):
            conflicts.append(driver.id)
        category = 'conflict' if member and (individual or not member.group.is_active) else 'group' if member else 'individual' if individual else 'global'
        normal = getattr(driver, 'normal_driver', None)
        vehicle_type = normal.vehicle.vehicle_type if normal and normal.vehicle else None
        rule = None if member and not member.group.is_active else CommissionResolver.get_commission_rule(vehicle_type=vehicle_type, driver=driver)
        drivers.append({
            'id': driver.id,
            'name': (' '.join([driver.user.first_name or '', driver.user.last_name or '']).strip()
                     or driver.user.username),
            'category': category,
            'group_id': member.group_id if member else None,
            'company_percentage': format(rule.company_percentage, '.2f') if rule else None,
            'driver_percentage': format(rule.driver_percentage, '.2f') if rule else None,
        })
    global_rules = list(CommissionRule.objects.filter(vehicle_type__isnull=True, is_active=True).order_by('id'))
    default = global_rules[0].company_percentage if global_rules else CommissionResolver.get_commission_rule().company_percentage
    data = {
        'global_percentage': format(default, '.2f'),
        'global_is_configured': bool(global_rules),
        'drivers': drivers,
        'groups': [
            {'id': group.id, 'name': group.name, 'is_active': group.is_active,
             'company_percentage': format(group.company_percentage, '.2f')}
            for group in DriverCommissionGroup.objects.order_by('id')
        ],
        'legacy_vehicle_rules': [
            {'id': rule.id, 'vehicle_type_id': rule.vehicle_type_id,
             'company_percentage': format(rule.company_percentage, '.2f')}
            for rule in CommissionRule.objects.filter(vehicle_type__isnull=False, is_active=True).order_by('id')
        ],
        'conflicting_driver_ids': conflicts,
        'multiple_global_rules': len(global_rules) > 1,
    }
    data['revision'] = hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    data['writes_enabled'] = getattr(settings, 'ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED', False) is True
    data['write_lock_reason'] = '' if data['writes_enabled'] else (
        'Preview only. Saving is locked until payout protection, legacy commission transition and release are approved.'
    )
    return data


def _apply_command(command, before):
    action = command['action']
    ids = command.get('driver_ids', [])
    selected = list(BaseDriver.objects.filter(id__in=ids).order_by('id'))
    if len(selected) != len(ids):
        raise ValidationError({'driver_ids': 'One or more selected drivers no longer exist.'})
    members = {item.driver_id: item for item in DriverCommissionMembership.objects.all()}
    group = None
    if 'group_id' in command:
        group = DriverCommissionGroup.objects.filter(pk=command['group_id']).first()
        if group is None:
            raise ValidationError({'group_id': 'Group not found.'})
        if not group.is_active and action != 'release_members':
            raise CommissionConflict('This group is inactive. Release its members before changing its configuration.')
    # Do not permit any new finance-category writes while legacy vehicle
    # rules can silently take precedence for global-category drivers.
    # Read-only preview and existing booking resolution remain unchanged.
    if before['legacy_vehicle_rules'] and action != 'release_members':
        raise CommissionConflict(
            'Legacy vehicle-specific rates must be explicitly reconciled before editing commission categories.'
        )
    if before['conflicting_driver_ids'] or before['multiple_global_rules']:
        raise CommissionConflict('Existing conflicting commission records require review before changes can be saved.')
    affected = ids
    if action == 'set_global':
        if before['legacy_vehicle_rules']:
            raise CommissionConflict('Legacy vehicle commission rules override the global rate. Review their transition first; none were changed.')
        affected = [item['id'] for item in before['drivers'] if item['category'] == 'global']
    elif action == 'set_group_rate':
        affected = [item.driver_id for item in members.values() if item.group_id == group.id]
    # Acceptance uses the SAME configuration lock. Only a matching persisted
    # agreement permits changes while a driver's accepted journey is unfinished.
    # Old/pending assignments without terms remain blocked; never backfill a guess.
    protected = DriverPayoutAgreement.objects.filter(
        trip_id=OuterRef('pk'), driver_id=OuterRef('base_driver_id'),
        gross_amount=OuterRef('cost'), currency='GBP', released_at__isnull=True,
    )
    unfinished = Trip.objects.filter(base_driver_id__in=affected).exclude(status__in=['completed', 'cancelled', 'canceled'])
    unsafe = unfinished.annotate(payout_protected=Exists(protected)).filter(
        Q(payout_protected=False) | ~Q(status__in=['accepted', 'driver_on_the_way', 'active'])
    )
    if unsafe.exists():
        raise CommissionConflict('A selected driver has an unfinished journey without matching accepted payout terms. No rates were changed.')
    percentage = command.get('company_percentage')
    if action == 'set_global':
        rule = CommissionRule.objects.filter(vehicle_type__isnull=True, is_active=True).first()
        if rule is None:
            rule = CommissionRule(vehicle_type=None, is_active=True)
        rule.company_percentage = percentage
        rule.driver_percentage = Decimal('100.00') - percentage
        rule.save()
    elif action == 'set_individual':
        if any(driver.id in members for driver in selected):
            raise CommissionConflict('Release selected drivers from their groups first. No rates were changed.')
        for driver in selected:
            # Legacy field is the DRIVER share, while this API accepts ACT deduction.
            driver.driver_commission_percentage = Decimal('100.00') - percentage
            driver.save(update_fields=['driver_commission_percentage'])
    elif action == 'clear_individual':
        if any(driver.id in members or driver.driver_commission_percentage is None for driver in selected):
            raise CommissionConflict('Only individual exceptions can be returned to the global category.')
        for driver in selected:
            driver.driver_commission_percentage = None
            driver.save(update_fields=['driver_commission_percentage'])
    elif action in ['create_group', 'add_members']:
        if any(driver.id in members or driver.driver_commission_percentage is not None for driver in selected):
            raise CommissionConflict('Only drivers in the global category can join a group. No memberships were changed.')
        if action == 'create_group':
            if DriverCommissionGroup.objects.filter(name__iexact=command['name']).exists():
                raise ValidationError({'name': 'A group with this name already exists.'})
            group = DriverCommissionGroup.objects.create(name=command['name'], company_percentage=percentage)
        for driver in selected:
            DriverCommissionMembership.objects.create(driver=driver, group=group)
    elif action == 'set_group_rate':
        group.company_percentage = percentage
        group.save(update_fields=['company_percentage'])
    elif action == 'release_members':
        if any(driver.id not in members or members[driver.id].group_id != group.id for driver in selected):
            raise CommissionConflict('Every selected driver must belong to the selected group.')
        DriverCommissionMembership.objects.filter(group=group, driver_id__in=ids).delete()


class CommissionManagementView(APIView):
    permission_classes = [IsAdminUser]
    http_method_names = ['get', 'post', 'head', 'options']

    def get(self, request):
        return Response({'success': True, 'data': commission_snapshot()}, headers={'Cache-Control': 'no-store'})

    def post(self, request):
        if getattr(settings, 'ACT_COMMISSION_MANAGEMENT_WRITES_ENABLED', False) is not True:
            raise PermissionDenied('Commission changes are locked pending accepted-journey payout protection and release approval.')
        serializer = CommissionCommand(data=request.data)
        serializer.is_valid(raise_exception=True)
        command = serializer.validated_data
        try:
            with transaction.atomic():
                lock_commission_configuration()
                list(BaseDriver.objects.select_for_update().order_by('id').values_list('id', flat=True))
                list(DriverCommissionGroup.objects.select_for_update().order_by('id').values_list('id', flat=True))
                list(CommissionRule.objects.select_for_update().order_by('id').values_list('id', flat=True))
                before = commission_snapshot()
                if before['revision'] != command['revision']:
                    raise CommissionConflict()
                _apply_command(command, before)
                after = commission_snapshot()
                LogEntry.objects.create(
                    user_id=request.user.pk, action_flag=CHANGE,
                    object_repr='ACT commission management',
                    change_message=json.dumps({
                        'action': command['action'], 'reason': command['reason'],
                        'before': before, 'after': after,
                    }, sort_keys=True),
                )
        except ModelValidationError as error:
            raise ValidationError(getattr(error, 'message_dict', error.messages))
        return Response({'success': True, 'message': 'Commission settings saved.', 'data': after}, headers={'Cache-Control': 'no-store'})
