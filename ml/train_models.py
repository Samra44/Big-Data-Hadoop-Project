"""Stand-alone training script (same engine the web app uses).
    python train_models.py                 -> trains on data/sample_dataset.csv, evaluates on testing_dataset.csv
Outputs: ml/earthscape_models.pkl (pickle deliverable) and ml/metrics.json"""
import os, sys, json, pickle
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "app"))
os.environ.setdefault("EARTHSCAPE_MODEL_DIR", os.path.join(HERE, "registry_offline"))
import pandas as pd, numpy as np, ml_engine as ml
from sklearn.metrics import f1_score, mean_absolute_error, classification_report

train = pd.read_csv(os.path.join(HERE, "..", "data", "sample_dataset.csv"))
test = pd.read_csv(os.path.join(HERE, "..", "data", "testing_dataset.csv"))
b = ml.train(train, reason="offline training script")
s = ml.score(test)
ext = {"external_test_event_f1_macro": round(float(f1_score(test.event_type, s.pred_event, average="macro")), 4),
       "external_test_event_report": classification_report(test.event_type, s.pred_event, output_dict=True, zero_division=0)}
# next-day forecast on the 2024 test year (lags from the test data itself)
L = ml.lag_features(ml.clean(test)).dropna(subset=["target_next", "t_lag1"])
ext["external_test_forecast_mae"] = round(float(mean_absolute_error(L.target_next, b["forecast_model"].predict(L[ml.FC_NUM + ml.FC_CAT]))), 3)
tp = int(((s.pred_anomaly == 1) & (test.is_anomaly == 1)).sum())
ext["external_test_anomaly_precision"] = round(tp / max(int(s.pred_anomaly.sum()), 1), 3)
ext["external_test_anomaly_recall"] = round(tp / max(int(test.is_anomaly.sum()), 1), 3)
pickle.dump(b, open(os.path.join(HERE, "earthscape_models.pkl"), "wb"))
json.dump({"training": b["metrics"], "external_test_2024": ext, "trends": b["trends"], "runtime": b["runtime"]},
          open(os.path.join(HERE, "metrics.json"), "w"), indent=2, default=str)
print(json.dumps({k: v for k, v in ext.items() if "report" not in k}, indent=2))
