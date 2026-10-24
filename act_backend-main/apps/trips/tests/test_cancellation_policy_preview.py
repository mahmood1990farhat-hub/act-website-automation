"""Finite pure-function tests; no Django setup, database or external requests."""
import importlib.util
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

SOURCE = Path(__file__).resolve().parents[1] / "services/cancellation_policy.py"
spec = importlib.util.spec_from_file_location("act_cancellation_candidate", SOURCE)
policy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = policy
spec.loader.exec_module(policy)
PICKUP = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)


def preview(hours=18, **changes):
    values = dict(accepted_policy_version=policy.CANDIDATE_POLICY_VERSION,
                  confirmed_pickup_at=PICKUP,
                  cancellation_received_at=PICKUP - timedelta(hours=hours),
                  captured_amount_pence=10000)
    values.update(changes)
    return policy.preview_cancellation_refund(**values)


class RefundPolicyPreviewTests(unittest.TestCase):
    def test_more_than_24h_full(self):
        self.assertEqual(preview(25).additional_refund_pence, 10000)

    def test_exact_24h_half_and_not_yet_authorised(self):
        result = preview(24)
        self.assertEqual(result.standard_total_refund_pence, 5000)
        self.assertTrue(result.review_required)
        self.assertIsNone(result.additional_refund_pence)

    def test_24h_plus_microsecond_full(self):
        result = preview(cancellation_received_at=PICKUP-timedelta(hours=24, microseconds=1))
        self.assertEqual(result.standard_refund_percent, 100)

    def test_24h_minus_microsecond_half(self):
        self.assertEqual(preview(cancellation_received_at=PICKUP-timedelta(hours=24)+timedelta(microseconds=1)).standard_refund_percent, 50)

    def test_exact_12h_zero_schedule_requires_review(self):
        result = preview(12)
        self.assertEqual(result.standard_refund_percent, 0)
        self.assertIsNone(result.assessed_total_refund_pence)
        self.assertTrue(result.review_required)

    def test_12h_plus_microsecond_half(self):
        self.assertEqual(preview(cancellation_received_at=PICKUP-timedelta(hours=12, microseconds=1)).standard_refund_percent, 50)

    def test_12h_minus_microsecond_zero(self):
        self.assertEqual(preview(cancellation_received_at=PICKUP-timedelta(hours=12)+timedelta(microseconds=1)).standard_refund_percent, 0)

    def test_half_refund_rounds_customer_up(self):
        result = preview(captured_amount_pence=10001, reviewed_net_loss_pence=10001, loss_review_reference="synthetic-review")
        self.assertEqual(result.additional_refund_pence, 5001)

    def test_lower_loss_increases_refund(self):
        self.assertEqual(preview(reviewed_net_loss_pence=2000, loss_review_reference="synthetic").additional_refund_pence, 8000)

    def test_zero_evidenced_loss_full(self):
        self.assertEqual(preview(6, reviewed_net_loss_pence=0, loss_review_reference="synthetic").additional_refund_pence, 10000)

    def test_loss_cannot_exceed_schedule_deduction(self):
        self.assertEqual(preview(reviewed_net_loss_pence=999999, loss_review_reference="synthetic").additional_refund_pence, 5000)

    def test_within12_reviewed_full_loss_zero(self):
        result = preview(6, reviewed_net_loss_pence=10000, loss_review_reference="synthetic")
        self.assertEqual(result.additional_refund_pence, 0)
        self.assertFalse(result.review_required)

    def test_missing_version_not_new_policy(self):
        self.assertEqual(preview(25, accepted_policy_version=None).outcome, "accepted_terms_review_required")

    def test_old_unknown_and_empty_versions_not_repriced(self):
        for version in ("legacy-3h", "", "future-unknown"):
            with self.subTest(version=version):
                self.assertIsNone(preview(25, accepted_policy_version=version).standard_refund_percent)

    def test_act_failure_separate_full_refund(self):
        self.assertEqual(preview(1, accepted_policy_version=None, cancellation_kind="act_unable_to_supply").additional_refund_pence, 10000)

    def test_no_show_cannot_be_assumed(self):
        self.assertEqual(preview(-1, cancellation_kind="no_show").outcome, "cancellation_reason_review_required")

    def test_elapsed_pickup_requires_review(self):
        for hours in (0, -1):
            self.assertEqual(preview(hours).outcome, "pickup_elapsed_review_required")

    def test_started_completed_cancelled_or_unknown_status_review(self):
        for state in ("active", "completed", "cancelled", "driver_on_the_way", "unexpected"):
            self.assertEqual(preview(25, journey_status=state).outcome, "journey_state_review_required")

    def test_accepted_trip_supported(self):
        self.assertEqual(preview(25, journey_status="accepted").additional_refund_pence, 10000)

    def test_prior_refund_subtracted(self):
        result = preview(already_refunded_pence=2000, reviewed_net_loss_pence=5000, loss_review_reference="synthetic")
        self.assertEqual(result.assessed_total_refund_pence, 5000)
        self.assertEqual(result.additional_refund_pence, 3000)

    def test_no_negative_refund_or_clawback(self):
        result = preview(already_refunded_pence=8000, reviewed_net_loss_pence=5000, loss_review_reference="synthetic")
        self.assertEqual(result.additional_refund_pence, 0)

    def test_unpaid_zero(self):
        self.assertEqual(preview(captured_amount_pence=0).additional_refund_pence, 0)

    def test_invalid_money_rejected(self):
        for field in ("captured_amount_pence", "already_refunded_pence", "reviewed_net_loss_pence"):
            for value in (-1, 1.5, True, "100"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    preview(**{field: value})

    def test_refunded_more_than_capture_rejected(self):
        with self.assertRaises(ValueError):
            preview(already_refunded_pence=10001)

    def test_review_requires_both_amount_and_reference(self):
        for changes in ({"reviewed_net_loss_pence": 10}, {"loss_review_reference": "x"},
                        {"reviewed_net_loss_pence": 10, "loss_review_reference": " "}):
            with self.assertRaises(ValueError):
                preview(**changes)

    def test_unknown_currency_and_reason_rejected(self):
        for changes in ({"currency":"USD"}, {"cancellation_kind":"driver_cancel"},
                        {"accepted_policy_version":123}, {"journey_status":False}):
            with self.assertRaises(ValueError):
                preview(**changes)

    def test_naive_or_invalid_dates_rejected(self):
        for field in ("confirmed_pickup_at", "cancellation_received_at"):
            for value in (datetime(2026, 1, 1), "2026-01-01", None):
                with self.assertRaises(ValueError):
                    preview(**{field:value})

    def test_autumn_elapsed_time_not_wall_time(self):
        london = ZoneInfo("Europe/London")
        result = preview(confirmed_pickup_at=datetime(2026,10,25,12,tzinfo=london),
                         cancellation_received_at=datetime(2026,10,24,12,tzinfo=london))
        self.assertEqual(result.standard_refund_percent, 100)  # 25 elapsed hours

    def test_spring_elapsed_time_not_wall_time(self):
        london = ZoneInfo("Europe/London")
        result = preview(confirmed_pickup_at=datetime(2026,3,29,13,tzinfo=london),
                         cancellation_received_at=datetime(2026,3,28,12,30,tzinfo=london))
        self.assertEqual(result.standard_refund_percent, 50)  # 23.5 elapsed hours

    def test_nonexistent_local_time_rejected(self):
        with self.assertRaises(ValueError):
            preview(confirmed_pickup_at=datetime(2026,3,29,1,30,tzinfo=ZoneInfo("Europe/London")))

    def test_repeated_hour_fold_respected(self):
        london = ZoneInfo("Europe/London")
        start = datetime(2026,10,24,13,30,tzinfo=london)
        results = [preview(confirmed_pickup_at=datetime(2026,10,25,1,30,tzinfo=london,fold=f), cancellation_received_at=start) for f in (0,1)]
        self.assertEqual([x.standard_refund_percent for x in results], [0, 50])

    def test_outputs_immutable_and_repeatable(self):
        result = preview(25)
        self.assertEqual(result, preview(25))
        with self.assertRaises(FrozenInstanceError):
            result.additional_refund_pence = 1

    def test_amount_invariants_small_pence_grid(self):
        for amount in range(1, 100):
            for hours in (6, 18, 30):
                for loss in (0, amount // 3, amount, amount+1):
                    result = preview(hours, captured_amount_pence=amount, reviewed_net_loss_pence=loss, loss_review_reference="synthetic")
                    self.assertLessEqual(result.standard_total_refund_pence, result.assessed_total_refund_pence)
                    self.assertLessEqual(result.assessed_total_refund_pence, amount)
                    self.assertGreaterEqual(result.additional_refund_pence, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
