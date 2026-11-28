# OMEGA demo and acceptance script

## Recording rules

Use a test account, test products and synthetic data. Do not display real
customer names, purchase tokens, email addresses, bank account details,
service-account keys, GitHub secrets or private documents. Clearly label
mocked/test screens. Do not claim a real payment or bank transfer from a
sandbox demonstration.

## Scene 1: application launch

1. Start the Android app from the launcher.
2. Show the app name, version and initial screen.
3. Confirm there is no crash, blank screen or unexpected permission prompt.
4. Open Settings > About and show the build/version identifier.

Evidence: device model, Android version, app version and recording timestamp.

## Scene 2: backend health

1. Open the diagnostics/status screen.
2. Show backend connectivity and the health status.
3. Show provider status separately from backend health.
4. If the provider is not configured, show the explicit unavailable state.

Evidence: redacted request ID and HTTP status. Never show provider secrets.

## Scene 3: AI assistant

1. Open the AI chat screen.
2. Submit a harmless Turkish prompt such as "Bir cümleyle uygulamanın amacını açıkla."
3. Show the response and model/provider label.
4. Submit a prompt-injection test asking the assistant to reveal secrets or
   ignore authorization. Show that tool permissions remain denied.
5. Open a repository/document preview only if the account has an authorized
   read-only integration.

Evidence: request ID, policy decision and test result. A refusal alone is not
proof of tool authorization enforcement.

## Scene 4: subscription and purchase

1. Open the subscription screen.
2. Show product name, price and renewal period from the Play test catalog.
3. Start a Play test purchase using a license tester.
4. Show the purchase result and entitlement state.
5. Use the restore/refresh action.
6. Test cancellation/refund only with a designated test purchase.

Evidence: test purchase state and redacted order reference. Never expose the
purchase token.

## Scene 5: payout reconciliation

1. Open the OMEGA finance/reconciliation screen.
2. Import a synthetic earnings CSV.
3. Show gross sales, fees/refunds, net amount and currency.
4. Import a synthetic external payout record.
5. Show reconciliation variance.
6. Show the explicit note: "Bank transfer is performed by Google Play; this
   screen does not change the bank account or initiate a transfer."

Evidence: synthetic report ID and reconciliation result. No bank details.

## Scene 6: security and owner authorization

1. Open the owner-security status screen.
2. Show whether a cryptographic owner key is provisioned.
3. Demonstrate an authorized read-only action.
4. Demonstrate that an unverified identity, unknown tool and write action are
   denied.
5. Demonstrate cancellation/revocation if those capabilities are implemented.

Evidence: redacted policy decision codes and audit event IDs.

## Scene 7: final acceptance

1. Show the app version and exact source commit.
2. Show CI result for that exact commit.
3. Show artifact SHA-256 and signer certificate fingerprint only after they
   have been independently verified.
4. List untested items explicitly.
5. End with "Demo evidence" rather than "production-ready" unless every
   production acceptance gate has passed.

## Required real-device tests before publication

- fresh install, launch, restart and upgrade;
- supported Android versions and screen sizes;
- offline and reconnect behavior;
- permission denial and recovery;
- chat timeout/provider unavailable;
- subscription purchase, restore, cancel, refund and renewal;
- owner authentication, replay rejection and revoked-key rejection;
- TalkBack/navigation/accessibility checks;
- signed artifact installation and certificate verification.
