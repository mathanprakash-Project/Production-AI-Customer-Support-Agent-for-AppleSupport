# Golden Set Labelling Guide & Annotation Protocol

This document defines the annotation protocol, intent boundary definitions, and decision guidelines used to construct the 200-example golden evaluation set for **@AppleSupport**.

---

## 1. Golden Set Construction & Stratification

The golden set contains **200 customer inquiries** sampled from real Twitter support conversations, stratified to mirror real-world customer support traffic:

| Stratum | Proportion | Count | Description |
|---|---|---|---|
| Core Technical Issues | 50% | 100 | Clear hardware, charging, battery, and iOS update problems |
| Account & Billing | 20% | 40 | Apple ID password resets, 2FA, App Store charges |
| Accessories & Mac | 15% | 30 | AirPods audio dropouts, Mac freezing, Apple Watch |
| Edge Cases & Adversarial | 15% | 30 | Sarcasm, multiple issues in 1 tweet, PII leaks, severe distress |

---

## 2. Intent Taxonomy Definitions & Boundaries

1. **`iphone_wont_charge`**:
   - *Includes*: Port loose/dirty, cable uncertified warnings, device unresponsive to charger, wireless MagSafe charging failures.
   - *Boundary vs `battery_drain`*: If the device refuses to charge or power on, use `iphone_wont_charge`. If the battery charges but depletes rapidly, use `battery_drain`.

2. **`battery_drain`**:
   - *Includes*: Rapid battery drop, iPhone overheating while idle, battery health service alerts (<80%).

3. **`apple_id_account_access`**:
   - *Includes*: Forgotten password, locked accounts, 2FA verification SMS not received, stolen credentials.

4. **`ios_update_issue`**:
   - *Includes*: Stuck on Apple logo / boot loop, error codes during iTunes/Finder update, verification failures.

5. **`airpods_sound_connectivity`**:
   - *Includes*: Left or right AirPod silent, crackling audio, Bluetooth pairing failure, case not charging.

6. **`hardware_damage_repair`**:
   - *Includes*: Cracked OLED screens, liquid/water damage, swollen batteries, repair cost inquiries.

7. **`billing_and_subscriptions`**:
   - *Includes*: Unrecognized `apple.com/bill` credit card charges, unwanted subscriptions, refund requests.

8. **`icloud_storage_sync`**:
   - *Includes*: "iCloud storage full" notifications, photos not syncing across devices, backup failures.

9. **`mac_performance_macos`**:
   - *Includes*: MacBook spinning beachball, kernel panics, fan noise, slow boot times, macOS Sonoma glitches.

10. **`app_store_downloads`**:
    - *Includes*: Apps stuck on "Waiting", redemption code errors, payment method declined in App Store.

11. **`watch_fitness_sync`**:
    - *Includes*: Activity rings not syncing to iPhone, Apple Watch battery drain, watchOS pairing errors.

12. **`other_inquiry`**:
    - *Includes*: Compliments, non-support general banter, spam, non-English tweets.

---

## 3. Escalation Decision Rules for Annotators

Label a ticket as **`escalate`** if ANY of the following apply:
1. Contains customer PII (credit card number, phone number, email address, serial number, IMEI).
2. Legal threat, regulatory complaint, or physical safety hazard (smoke, fire, explosion).
3. The issue inherently requires backend account access or payment authentication (e.g. billing disputes, account recovery).
4. Customer explicitly expresses severe distress or refuses automated assistance.

Otherwise, label as **`auto`** (candidate for automated resolution with standard troubleshooting).

---

## 4. Inter-Rater Agreement Protocol

For 50 randomly sampled items from the golden set, independent dual annotations are collected to measure human-to-human reliability:
- Cohen's Kappa $\kappa$ target: $\ge 0.70$ on intent classification.
- For reply quality, annotations are scored on a 1–5 scale across 5 rubric dimensions (Relevance, Accuracy, Tone, Completeness, Groundedness).

