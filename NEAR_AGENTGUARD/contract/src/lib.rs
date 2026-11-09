use near_sdk::borsh::{self, BorshDeserialize, BorshSerialize};
use near_sdk::collections::UnorderedSet;
use near_sdk::json_types::U128;
use near_sdk::serde_json;
use near_sdk::{env, near, AccountId, NearToken, PanicOnDefault, Promise};

const NANOS_PER_DAY: u64 = 86_400_000_000_000;

#[near(contract_state)]
#[derive(PanicOnDefault)]
pub struct AgentGuard {
    owner: AccountId,
    agents: UnorderedSet<AccountId>,
    recipients: UnorderedSet<AccountId>,
    blocked: UnorderedSet<AccountId>,
    max_single: u128,
    daily_limit: u128,
    spent_today: u128,
    spend_day: u64,
    frozen: bool,
}

#[near]
impl AgentGuard {
    #[init]
    pub fn new(owner: AccountId, max_single: U128, daily_limit: U128) -> Self {
        assert!(!env::state_exists(), "already initialized");
        assert!(max_single.0 > 0, "max_single must be positive");
        assert!(
            daily_limit.0 >= max_single.0,
            "daily_limit must cover max_single"
        );
        Self {
            owner,
            agents: UnorderedSet::new(b"a"),
            recipients: UnorderedSet::new(b"r"),
            blocked: UnorderedSet::new(b"b"),
            max_single: max_single.0,
            daily_limit: daily_limit.0,
            spent_today: 0,
            spend_day: env::block_timestamp() / NANOS_PER_DAY,
            frozen: false,
        }
    }

    fn assert_owner(&self) {
        assert_eq!(env::predecessor_account_id(), self.owner, "owner only");
    }

    pub fn register_agent(&mut self, agent: AccountId) {
        self.assert_owner();
        self.agents.insert(&agent);
    }

    pub fn revoke_agent(&mut self, agent: AccountId) {
        self.assert_owner();
        self.agents.remove(&agent);
    }

    pub fn allow_recipient(&mut self, recipient: AccountId) {
        self.assert_owner();
        self.blocked.remove(&recipient);
        self.recipients.insert(&recipient);
    }

    pub fn block_recipient(&mut self, recipient: AccountId) {
        self.assert_owner();
        self.recipients.remove(&recipient);
        self.blocked.insert(&recipient);
    }

    pub fn set_limits(&mut self, max_single: U128, daily_limit: U128) {
        self.assert_owner();
        assert!(max_single.0 > 0, "max_single must be positive");
        assert!(
            daily_limit.0 >= max_single.0,
            "daily_limit must cover max_single"
        );
        self.max_single = max_single.0;
        self.daily_limit = daily_limit.0;
    }

    pub fn set_frozen(&mut self, frozen: bool) {
        self.assert_owner();
        self.frozen = frozen;
    }

    /// Agent-initiated native NEAR payment from the contract treasury.
    /// Recipient and limits are enforced on-chain, independently of any LLM.
    #[payable]
    pub fn pay(&mut self, recipient: AccountId, amount: U128, memo: String) -> Promise {
        assert_eq!(
            env::attached_deposit(),
            NearToken::from_yoctonear(0),
            "no attached deposit accepted"
        );
        assert!(!self.frozen, "payments frozen");
        let agent = env::predecessor_account_id();
        assert!(self.agents.contains(&agent), "agent not registered");
        assert!(!self.blocked.contains(&recipient), "recipient blocked");
        assert!(
            self.recipients.contains(&recipient),
            "recipient not allowlisted"
        );
        assert!(amount.0 > 0, "amount must be positive");
        assert!(amount.0 <= self.max_single, "single payment limit exceeded");

        let today = env::block_timestamp() / NANOS_PER_DAY;
        if today != self.spend_day {
            self.spend_day = today;
            self.spent_today = 0;
        }
        let new_spend = self
            .spent_today
            .checked_add(amount.0)
            .expect("spend overflow");
        assert!(new_spend <= self.daily_limit, "daily spend limit exceeded");

        self.spent_today = new_spend;
        env::log_str(
            &serde_json::json!({
                "event": "AgentGuardPaymentAuthorized",
                "agent": agent,
                "recipient": recipient,
                "amount_yocto": amount.0.to_string(),
                "day": today,
                "memo": memo,
            })
            .to_string(),
        );
        Promise::new(recipient).transfer(NearToken::from_yoctonear(amount.0))
    }

    pub fn get_policy(&self) -> PolicyView {
        PolicyView {
            owner: self.owner.clone(),
            max_single: U128(self.max_single),
            daily_limit: U128(self.daily_limit),
            spent_today: U128(self.spent_today),
            frozen: self.frozen,
        }
    }

    pub fn is_agent(&self, account: AccountId) -> bool {
        self.agents.contains(&account)
    }

    pub fn is_allowed_recipient(&self, account: AccountId) -> bool {
        self.recipients.contains(&account) && !self.blocked.contains(&account)
    }
}

#[near(serializers = [json])]
#[derive(Clone)]
pub struct PolicyView {
    pub owner: AccountId,
    pub max_single: U128,
    pub daily_limit: U128,
    pub spent_today: U128,
    pub frozen: bool,
}

#[cfg(test)]
mod tests {
    use super::*;
    use near_sdk::test_utils::VMContextBuilder;
    use near_sdk::{testing_env, NearToken};

    fn account(name: &str) -> AccountId {
        name.parse().unwrap()
    }

    fn context(predecessor: AccountId, timestamp: u64) {
        let mut builder = VMContextBuilder::new();
        builder
            .current_account_id(account("guard.testnet"))
            .signer_account_id(predecessor.clone())
            .predecessor_account_id(predecessor)
            .block_timestamp(timestamp)
            .account_balance(NearToken::from_near(100));
        testing_env!(builder.build());
    }

    fn setup() -> AgentGuard {
        context(account("owner.testnet"), 1);
        let mut contract = AgentGuard::new(account("owner.testnet"), U128(10), U128(20));
        contract.register_agent(account("worker.testnet"));
        contract.allow_recipient(account("vendor.testnet"));
        contract
    }

    #[test]
    fn owner_can_register_agent_and_allow_recipient() {
        let contract = setup();
        assert!(contract.is_agent(account("worker.testnet")));
        assert!(contract.is_allowed_recipient(account("vendor.testnet")));
    }

    #[test]
    #[should_panic(expected = "owner only")]
    fn non_owner_cannot_register_agent() {
        let mut contract = setup();
        context(account("attacker.testnet"), 1);
        contract.register_agent(account("attacker.testnet"));
    }

    #[test]
    #[should_panic(expected = "agent not registered")]
    fn unregistered_agent_cannot_pay() {
        let mut contract = setup();
        context(account("stranger.testnet"), 1);
        let _ = contract.pay(account("vendor.testnet"), U128(1), "test".into());
    }

    #[test]
    #[should_panic(expected = "recipient not allowlisted")]
    fn unknown_recipient_is_denied() {
        let mut contract = setup();
        context(account("worker.testnet"), 1);
        let _ = contract.pay(account("unknown.testnet"), U128(1), "test".into());
    }

    #[test]
    #[should_panic(expected = "recipient blocked")]
    fn blocked_recipient_is_denied() {
        let mut contract = setup();
        context(account("owner.testnet"), 1);
        contract.block_recipient(account("vendor.testnet"));
        context(account("worker.testnet"), 1);
        let _ = contract.pay(account("vendor.testnet"), U128(1), "test".into());
    }

    #[test]
    #[should_panic(expected = "single payment limit exceeded")]
    fn single_payment_limit_is_enforced() {
        let mut contract = setup();
        context(account("worker.testnet"), 1);
        let _ = contract.pay(account("vendor.testnet"), U128(11), "test".into());
    }

    #[test]
    #[should_panic(expected = "daily spend limit exceeded")]
    fn daily_limit_is_enforced() {
        let mut contract = setup();
        context(account("worker.testnet"), 1);
        let _ = contract.pay(account("vendor.testnet"), U128(10), "first".into());
        let _ = contract.pay(account("vendor.testnet"), U128(10), "second".into());
    }

    #[test]
    #[should_panic(expected = "payments frozen")]
    fn frozen_contract_denies_payments() {
        let mut contract = setup();
        context(account("owner.testnet"), 1);
        contract.set_frozen(true);
        context(account("worker.testnet"), 1);
        let _ = contract.pay(account("vendor.testnet"), U128(1), "test".into());
    }

    #[test]
    #[should_panic(expected = "agent not registered")]
    fn revoked_agent_cannot_pay() {
        let mut contract = setup();
        context(account("owner.testnet"), 1);
        contract.revoke_agent(account("worker.testnet"));
        context(account("worker.testnet"), 1);
        let _ = contract.pay(account("vendor.testnet"), U128(1), "revoked".into());
    }

    #[test]
    fn daily_limit_resets_on_next_utc_day() {
        let mut contract = setup();
        context(account("worker.testnet"), 1);
        let _ = contract.pay(account("vendor.testnet"), U128(10), "day-one".into());
        context(account("worker.testnet"), NANOS_PER_DAY + 1);
        let _ = contract.pay(account("vendor.testnet"), U128(10), "day-two".into());
        assert_eq!(contract.spent_today, 10);
    }
}
