import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pact_market import minor_to_usdt,normalize,classify,run_scan
from unittest.mock import patch

def row(**extra):
    r={"id":"b1","title":"Build a small API rate-limiter service","description":"Create a small Python API service with tests","acceptanceCriteria":"Tests pass and docs included","tags":["backend","api","python"],"priceAmount":"25000000","priceCurrency":"USDT","priceUnit":"fixed","author":{"type":"human","handle":"buyer","rating":495,"reviewCount":10},"status":"open","createdAt":"2026-11-11T00:00:00Z"}
    r.update(extra);return r

class PactMarketTests(unittest.TestCase):
    def test_six_decimal_usdt_conversion(self):
        self.assertEqual(minor_to_usdt("25000000"),"25")
        self.assertEqual(minor_to_usdt("1250000"),"1.25")

    def test_cash_bounty_goes_to_escrow_gate_not_claimable(self):
        item=normalize(row(),"bounty")
        decision,reason=classify(item)
        self.assertEqual(decision,"ESCROW_GATE_REQUIRED")
        self.assertEqual(item["payment_state"],"NOT_DISCLOSED_ON_PUBLIC_LISTING")
        self.assertIn("funding",reason)

    def test_service_listing_is_not_buyer_demand(self):
        item=normalize(row(),"service")
        self.assertEqual(classify(item)[0],"SERVICE_SIDE_NOT_REVENUE")

    def test_negotiable_price_needs_quote_gate(self):
        item=normalize(row(priceUnit="negotiable"),"bounty")
        self.assertEqual(classify(item)[0],"REVIEW_REQUIRED")

    def test_zero_price_excluded(self):
        item=normalize(row(priceAmount="0"),"bounty")
        self.assertEqual(classify(item)[0],"EXCLUDED")

    def test_location_or_academic_work_excluded(self):
        for title in ("Buy me a cup of coffee from your city","Complete my homework essay","Visit the store in person"):
            item=normalize(row(title=title),"bounty")
            self.assertEqual(classify(item)[0],"EXCLUDED")

    def test_unsupported_work_requires_review(self):
        item=normalize(row(title="Host a party at a venue",description="Need people to attend",tags=[],acceptanceCriteria=None),"bounty")
        self.assertEqual(classify(item)[0],"REVIEW_REQUIRED")

    def test_live_scan_public_get_only(self):
        with patch("pact_market.get_json",side_effect=[
            ({"items":[row()]},{"url":"b"}),
            ({"items":[row(id="s1",title="JSON quality service")]},{"url":"s"})
        ]) as mock:
            result=run_scan()
        self.assertEqual(result["bounty_count"],1)
        self.assertEqual(result["service_count"],1)
        self.assertEqual(result["escrow_gate_candidates"],1)
        self.assertEqual(mock.call_count,2)
        self.assertFalse(result["marketplace_writes"])

if __name__=="__main__": unittest.main()
