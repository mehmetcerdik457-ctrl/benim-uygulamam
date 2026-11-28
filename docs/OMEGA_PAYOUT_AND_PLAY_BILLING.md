# OMEGA payout and Google Play billing boundary

## Non-negotiable invariant

This implementation does not change the existing Play Console payments profile,
bank account, subscription catalog, prices, renewal rules, purchase tokens or
existing customer subscriptions. It does not initiate bank transfers and does
not store bank account numbers, IBANs, card data or bank credentials.

## Correct money flow

1. A customer buys or renews a digital product through Google Play Billing.
2. Google Play processes the buyer payment and maintains the merchant balance.
3. Google calculates fees, refunds, chargebacks, taxes and currency conversion
   according to the merchant's account and transaction terms.
4. Google initiates the merchant payout to the verified primary bank method in
   the existing Play Console payments profile.
5. OMEGA may import the official earnings report and reconcile it against
   payout evidence. It cannot select or change the destination bank account.

Google's published guidance says Play merchant payouts are generally initiated
around the 15th for the prior month's sales, subject to the account's profile,
thresholds, holds, holidays and payment method. The payments profile is the
source of truth for bank destination and payout status.

## Backend code boundary

backend/payouts/ledger.py is a local SQLite reconciliation ledger:
- imports financial report lines using stable idempotency keys;
- records externally reported payout references and states;
- calculates period/currency variance;
- explicitly returns bank_transfer_initiated=false;
- stores no bank details.

It is not a payment processor, payout API, or substitute for Google accounting
reports. Import must be performed by an authorized operator or a separately
approved read-only report adapter.

## Google Play Billing and Developer API

- Keep the current Play Billing integration and subscription product IDs.
- Verify purchase tokens on a trusted backend using the Subscriptions and
  In-App Purchases API before granting entitlements.
- Treat purchase-token verification and merchant payout reporting as separate
  systems: purchase APIs are not bank-transfer APIs.
- Use the official financial/earnings reports for settlement reconciliation.
- Never put a service-account private key or OAuth refresh token in the Android
  app, repository, issue, prompt, or logs.
- RevenueCat may simplify subscription entitlement management, but it does not
  become the Google merchant's bank payout destination. Stripe is not a
  replacement payout route for Google Play processed digital purchases.

## Operator checklist

1. Do not change the existing payment profile or bank account.
2. Confirm the existing merchant account remains verified and not on hold.
3. Export the monthly Google Play earnings report from Play Console.
4. Import rows into the reconciliation ledger using stable report and row IDs.
5. Record the payout reference only after Google reports it as paid.
6. Investigate any non-zero variance; do not trigger a second transfer.
7. Compare the actual bank statement outside OMEGA. Do not upload bank secrets.

## Current integration status

- Reconciliation primitives: implemented in this branch.
- Play Billing client integration: not verified by this branch.
- Purchase-token verification: not implemented by this branch.
- Google Cloud service-account/OAuth setup: not provisioned here.
- Automated earnings-report ingestion: not implemented.
- Actual bank payout: controlled by Google and the existing payments profile.
