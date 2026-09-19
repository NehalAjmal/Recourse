import json
import os
import random
import time
import urllib.request
import urllib.error
import string

# Fixed seed for deterministic dataset
random.seed(42)

# Generate ULIDs (simplified random string for deterministic generation)
def gen_id(prefix: str) -> str:
    chars = string.ascii_lowercase + string.digits
    return prefix + "_" + "".join(random.choices(chars, k=16))


def generate_dispute(category: str, previous_dispute: dict = None, i: int = 0) -> tuple[dict, str]:
    if category == "near_duplicate" and previous_dispute:
        # Create a duplicate of the previous dispute
        d = dict(previous_dispute)
        d["dispute_id"] = gen_id("dsp")
        d["txn_ts"] = d["txn_ts"] + random.randint(1, 100) # within 300s window
        # Update actions to match new txn_ts
        actions = []
        for a in d["actions"]:
            actions.append(dict(a, ts=a["ts"] + (d["txn_ts"] - previous_dispute["txn_ts"])))
        d["actions"] = actions
        # Update fulfilment delivered_ts
        d["fulfilment"] = dict(d["fulfilment"])
        if d["fulfilment"]["delivered_ts"]:
            d["fulfilment"]["delivered_ts"] += (d["txn_ts"] - previous_dispute["txn_ts"])
        return d, "escalate" # duplicates fail check 6 (5 passes -> escalate)

    # Use a fixed base time, plus some offset so they aren't all exactly identical
    now = 1726600000 + i * 3600
    merchants = ["zomato", "swiggy", "zepto"]
    
    merchant = random.choice(merchants)
    other_merchant = random.choice([m for m in merchants if m != merchant])
    
    mandate_merchant = merchant
    spend_cap = 50000  # 500 rupees
    valid_from = now - 86400 * 30
    valid_until = now + 86400 * 30
    status = "active"
    
    amount = random.randint(10000, 40000)
    txn_ts = now - random.randint(3600, 86400)
    
    actions_timeline_ok = True
    fulfilment_ok = True
    
    if category == "over-cap":
        amount = spend_cap + random.randint(1000, 10000)
    elif category == "expired/revoked":
        if random.random() < 0.5:
            status = "expired"
            txn_ts = valid_until + 86400
        else:
            status = "revoked"
    elif category == "merchant_mismatch":
        mandate_merchant = other_merchant
    elif category == "broken_timeline":
        actions_timeline_ok = False
    elif category == "multi_fail":
        amount = spend_cap + 1000
        mandate_merchant = other_merchant
        status = "revoked"

    actions = []
    if actions_timeline_ok:
        ts = txn_ts - 120
        actions.append({"seq": 1, "action": "search", "ts": ts, "payload": {"q": "food"}})
        actions.append({"seq": 2, "action": "select", "ts": ts + 30, "payload": {"item": "pizza"}})
        actions.append({"seq": 3, "action": "confirm", "ts": ts + 60, "payload": {}})
        actions.append({"seq": 4, "action": "pay", "ts": txn_ts, "payload": {}})
    else:
        ts = txn_ts - 120
        actions.append({"seq": 1, "action": "pay", "ts": ts, "payload": {}})
        actions.append({"seq": 2, "action": "confirm", "ts": txn_ts + 60, "payload": {}})

    mandate = {
        "mandate_id": gen_id("mnd"),
        "user_id": gen_id("usr"),
        "agent_id": "agent_claude_v1",
        "merchant_slug": mandate_merchant,
        "spend_cap_paise": spend_cap,
        "valid_from": valid_from,
        "valid_until": valid_until,
        "status": status,
    }
    
    fulfilment = {
        "order_id": gen_id("ord"),
        "delivered": fulfilment_ok,
        "delivered_ts": txn_ts + 1800 if fulfilment_ok else None,
        "amount_paise": amount,
    }

    dispute = {
        "dispute_id": gen_id("dsp"),
        "mandate": mandate,
        "merchant_slug": merchant,
        "amount_paise": amount,
        "txn_ts": txn_ts,
        "actions": actions,
        "fulfilment": fulfilment,
    }
    
    fails = 0
    if amount > spend_cap: fails += 1
    if merchant != mandate_merchant: fails += 1
    if status != "active" or not (valid_from <= txn_ts <= valid_until): fails += 1
    if not fulfilment_ok: fails += 1
    if not actions_timeline_ok: fails += 1
    
    passes = 6 - fails
    if passes == 6:
        label = "contest"
    elif passes >= 4:
        label = "escalate"
    else:
        label = "accept"
        
    return dispute, label

def main():
    api_url = os.environ.get("API_URL")
    if not api_url:
        print("API_URL environment variable required.")
        return
        
    if not api_url.endswith("/disputes"):
        api_url = api_url.rstrip("/") + "/disputes"

    # 120 disputes total
    # Distribution roughly:
    # 35% clean contests -> 42
    # 20% over-cap -> 24
    # 15% expired/revoked -> 18
    # 10% merchant mismatch -> 12
    # 10% broken timeline -> 12
    # 10% near-duplicate (I'll make half of these multi-fail to ensure some "accept" statuses) -> 6 duplicate, 6 multi-fail
    
    categories = (
        ["contest"] * 42 +
        ["over-cap"] * 24 +
        ["expired/revoked"] * 18 +
        ["merchant_mismatch"] * 12 +
        ["broken_timeline"] * 12 +
        ["near_duplicate"] * 6 +
        ["multi_fail"] * 6
    )
    
    random.shuffle(categories)
    
    dataset = []
    previous = None
    for i, cat in enumerate(categories):
        if cat == "near_duplicate" and previous:
            d, l = generate_dispute(cat, previous, i)
        else:
            if cat == "near_duplicate":
                cat = "contest" # Fallback if first item is duplicate
            d, l = generate_dispute(cat, previous_dispute=None, i=i)
            previous = d
        dataset.append((d, l))
        
    # Split 100 for POST, 20 for holdout
    post_set = dataset[:100]
    holdout_set = dataset[100:]
    
    # Save holdout
    holdout_path = os.path.join(os.path.dirname(__file__), "holdout.json")
    with open(holdout_path, "w") as f:
        json.dump([{"dispute": d, "label": l} for d, l in holdout_set], f, indent=2)
    print(f"Saved 20 holdout disputes to {holdout_path}")
    
    # Seed 100 via API
    # Since we need to mock duplicate orders, for near_duplicate, we'll post the first order, then post the duplicate.
    # Actually, the duplicate check is based on DynamoDB. We'll just POST the dispute.
    # Wait, check 6 requires "no other dispute under the same mandate with the same amount within +-300s".
    # Oh! Duplicate *disputes*, not duplicate orders! 
    # To trigger a duplicate, we need to POST two disputes with the same mandate and amount within 300s.
    
    print(f"Posting {len(dataset)} disputes to {api_url} ...")
    success = 0
    for i, (d, l) in enumerate(dataset):
        req = urllib.request.Request(
            api_url,
            data=json.dumps(d).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    success += 1
        except Exception as e:
            print(f"Failed to post dispute {i}: {e}")
        time.sleep(3)
            
    print(f"Successfully posted {success}/{len(dataset)} disputes.")

if __name__ == "__main__":
    main()
