import pathlib
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import elgora_public as elgora


def detail(
    bounty_id="4",
    status="open",
    chain_id=8453,
    token=elgora.BASE_USDC,
    amount="20000000",
    deadline=1795564740,
    guardian_fee=1000,
    treasury_fee=0,
    submissions=7,
    winner=None,
):
    return {
        "bounty": {
            "bounty_id": bounty_id,
            "status": status,
            "chain_id": chain_id,
            "escrow": {"token_address": token, "amount": amount},
            "submission_deadline": deadline,
            "guardian_fee_bps": guardian_fee,
            "treasury_fee_bps": treasury_fee,
            "submission_count": submissions,
            "winner": winner,
            "payout_policy": "winner_take_all",
            "spec_commitment": "0xabc",
        },
        "challenge": "# Evidence-level map for 10 research peptides\\n",
        "verification_record": {"status": "pending", "winner": None},
    }


class ElgoraPublicTests(unittest.TestCase):
    def test_six_decimal_usdc_conversion(self):
        self.assertEqual(elgora.parse_amount("20000000"), elgora.Decimal("20"))
        self.assertEqual(elgora.parse_amount("25000000"), elgora.Decimal("25"))

    def test_estimated_reward_deducts_guardian_and_treasury_fees(self):
        self.assertEqual(
            elgora.expected_solver_reward("20000000", 1000, 0),
            "18",
        )
        self.assertEqual(
            elgora.expected_solver_reward("25000000", 1000, 0),
            "22.5",
        )
        self.assertEqual(
            elgora.expected_solver_reward("10000000", 500, 250),
            "9.25",
        )

    def test_open_escrow_is_preparable_but_owner_signing_required(self):
        item = elgora.normalize(detail(), now_epoch=1795000000)
        self.assertEqual(item["decision"], "PREPARABLE_OWNER_SIGNING_REQUIRED")
        self.assertEqual(item["title"], "Evidence-level map for 10 research peptides")
        self.assertEqual(item["expected_solver_reward_usdc"], "18")
        self.assertTrue(item["wallet_signature_required"])
        self.assertTrue(item["base_native_gas_required_for_transaction"])
        self.assertFalse(item["solver_wallet_or_gas_balance_verified"])
        self.assertFalse(item["marketplace_writes"])
        self.assertFalse(item["submission_attempted"])
        self.assertEqual(item["recognized_external_income"], "0")

    def test_closed_bounty_excluded(self):
        item = elgora.normalize(detail(status="awarded"), now_epoch=1795000000)
        self.assertEqual(item["decision"], "EXCLUDED")
        self.assertEqual(item["reason"], "bounty_not_open")

    def test_expired_deadline_excluded(self):
        item = elgora.normalize(detail(deadline=1000), now_epoch=2000)
        self.assertEqual(item["decision"], "EXCLUDED")
        self.assertEqual(item["reason"], "submission_deadline_passed")

    def test_wrong_chain_requires_review(self):
        item = elgora.normalize(detail(chain_id=84532), now_epoch=1795000000)
        self.assertEqual(item["decision"], "REVIEW_REQUIRED")
        self.assertEqual(item["reason"], "unsupported_or_unverified_chain")

    def test_wrong_token_requires_review(self):
        item = elgora.normalize(detail(token="0x0000000000000000000000000000000000000001"),
                                now_epoch=1795000000)
        self.assertEqual(item["decision"], "REVIEW_REQUIRED")
        self.assertEqual(item["reason"], "escrow_token_not_verified_base_usdc")

    def test_missing_challenge_requires_review(self):
        payload = detail()
        payload["challenge"] = None
        item = elgora.normalize(payload, now_epoch=1795000000)
        self.assertEqual(item["decision"], "REVIEW_REQUIRED")
        self.assertEqual(item["reason"], "canonical_challenge_text_missing")

    def test_winner_already_recorded_excluded(self):
        item = elgora.normalize(detail(winner="0xsolver"), now_epoch=1795000000)
        self.assertEqual(item["decision"], "EXCLUDED")
        self.assertEqual(item["reason"], "winner_already_recorded")

    def test_zero_escrow_excluded(self):
        item = elgora.normalize(detail(amount="0"), now_epoch=1795000000)
        self.assertEqual(item["decision"], "EXCLUDED")
        self.assertEqual(item["reason"], "zero_or_invalid_escrow")

    def test_open_listing_scan_fetches_details_get_only(self):
        with patch("elgora_public.get_json", side_effect=[
            ({"bounties":[{"bounty_id":"4","status":"open","submission_count":7}]},
             {"http_status":200,"url":"listing"}),
            (detail(), {"http_status":200,"url":"detail"}),
        ]) as mocked:
            result = elgora.run_scan(now_epoch=1795000000)
        self.assertEqual(result["unique_bounty_count"], 1)
        self.assertEqual(result["decision_counts"]["PREPARABLE_OWNER_SIGNING_REQUIRED"], 1)
        self.assertEqual(mocked.call_count, 2)
        self.assertEqual(mocked.call_args_list[0].args[0], "/api/bounties?status=open")
        self.assertEqual(mocked.call_args_list[1].args[0], "/api/bounties/4")
        self.assertEqual(result["submissions_attempted"], 0)
        self.assertEqual(result["claims_attempted"], 0)
        self.assertFalse(result["marketplace_writes"])

    def test_duplicate_listing_ids_are_deduplicated(self):
        with patch("elgora_public.get_json", side_effect=[
            ({"bounties":[
                {"bounty_id":"4","status":"open"},
                {"bounty_id":"4","status":"open"},
            ]}, {"http_status":200,"url":"listing"}),
            (detail(), {"http_status":200,"url":"detail"}),
        ]):
            result = elgora.run_scan(now_epoch=1795000000)
        self.assertEqual(result["open_listing_count"], 2)
        self.assertEqual(result["unique_bounty_count"], 1)


if __name__ == "__main__":
    unittest.main()
