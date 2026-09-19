import json
import os
from typing import Callable, Dict

def compute_metrics(get_predicted_status: Callable[[str], str]) -> Dict:
    # holdout.json could be in data/seed/holdout.json or bundled locally
    # We will try both paths
    paths = [
        os.path.join(os.path.dirname(__file__), "..", "data", "seed", "holdout.json"),
        os.path.join(os.path.dirname(__file__), "holdout.json"),
        os.path.join(os.path.dirname(__file__), "..", "holdout.json") # For api Lambda context
    ]
    
    holdout_path = next((p for p in paths if os.path.exists(p)), None)
    if not holdout_path:
        raise FileNotFoundError("holdout.json not found")
        
    with open(holdout_path, 'r') as f:
        holdout = json.load(f)
        
    tp = 0 # Actual Contest, Predicted Contest
    fp = 0 # Actual Not Contest, Predicted Contest
    tn = 0 # Actual Not Contest, Predicted Not Contest
    fn = 0 # Actual Contest, Predicted Not Contest
    
    for item in holdout:
        dispute_id = item["dispute"]["dispute_id"]
        actual = item["label"]
        predicted = get_predicted_status(dispute_id)
        
        actual_contest = (actual == "contest")
        predicted_contest = (predicted == "contest")
        
        if actual_contest and predicted_contest:
            tp += 1
        elif not actual_contest and predicted_contest:
            fp += 1
        elif not actual_contest and not predicted_contest:
            tn += 1
        else:
            fn += 1
            
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "confusion": {
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn": fn
        },
        "n": len(holdout)
    }
