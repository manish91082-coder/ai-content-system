import pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from pact_agent import amount,reconcile

class PactAgentTests(unittest.TestCase):
    def test_usdt_minor_units(self):
        self.assertEqual(str(amount("85000000")),"85")
        self.assertEqual(str(amount("12500000000")),"12500")

    def test_completed_order_wallet_release_is_not_external_income(self):
        profile={"agent":{"id":"agent-1","handle":"nexus"}}
        orders={"items":[{"id":"o1","stage":"COMPLETED","sellerId":"agent-1","amount":"85000000","title":"API rate limiter","description":"Build rate limiter","acceptanceCriteria":"Token bucket + tests","updatedAt":"2026-11-11T03:00:00Z"}]}
        wallet={"wallet":{"currency":"USDT","available":"85000000","escrowed":"0","total":"85000000"},"entries":[{"kind":"escrow_release","orderId":"o1","amount":"85000000"}]}
        details={"o1":{"order":orders["items"][0],"role":"seller","events":[{"kind":"accept","toStage":"COMPLETED"}]}}
        result=reconcile(profile,orders,wallet,details)
        seller=result["seller_orders"][0]
        self.assertTrue(seller["funds_reconciled_to_platform_wallet"])
        self.assertEqual(seller["released_to_platform_wallet_usdt"],"85")
        self.assertEqual(seller["description"],"Build rate limiter")
        self.assertEqual(seller["acceptance_criteria"],"Token bucket + tests")
        self.assertEqual(seller["recognized_external_income"],"0")
        self.assertEqual(result["financial_policy"]["recognized_external_income"],"0")

    def test_same_order_release_to_other_agent_not_counted(self):
        profile={"agent":{"id":"agent-1"}}
        orders={"items":[{"id":"o2","stage":"COMPLETED","sellerId":"agent-2","amount":"5000000"}]}
        wallet={"wallet":{},"entries":[{"kind":"escrow_release","orderId":"o2","amount":"5000000"}]}
        result=reconcile(profile,orders,wallet,{})
        self.assertEqual(result["seller_orders"],[])

    def test_completed_order_without_release_not_reconciled(self):
        profile={"agent":{"id":"agent-1"}}
        orders={"items":[{"id":"o3","stage":"COMPLETED","sellerId":"agent-1","amount":"5000000"}]}
        wallet={"wallet":{},"entries":[]}
        result=reconcile(profile,orders,wallet,{})
        self.assertFalse(result["seller_orders"][0]["funds_reconciled_to_platform_wallet"])

if __name__=="__main__":unittest.main()
