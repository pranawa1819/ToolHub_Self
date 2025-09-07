# knn_evaluation_db.py
"""
Safe KNN evaluation script that auto-detects Django settings and uses the project's Product model.
It is read-only: model save/delete operations are disabled while this runs.

Usage:
  - Place this file in the project root (same folder as manage.py).
  - Activate your project's virtualenv.
  - Run: python knn_evaluation_db.py
"""

import os
import sys
import time
import traceback
from collections import Counter
import matplotlib
matplotlib.use("Agg")

# ------------ Confusion Matrix Visualization ------------
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay

# -------------------------
# Configuration
# -------------------------
MERGE_RARE = False   # If True, merge classes with < RARE_THRESHOLD samples into "OTHER"
RARE_THRESHOLD = 2   # min samples needed per class for stratification (used when MERGE_RARE=True)
TEST_SIZE = 0.25
K_NEIGHBORS = 5
MAX_FEATURES = 2000  # TF-IDF max features

# ------------ Helper: try to auto-detect settings module ------------
def find_settings_module(start_dir="."):
    """
    Walk start_dir for settings.py and return a candidates list of module strings like 'toolhub.settings'.
    Prefer a settings.py inside a subfolder (common Django layout).
    """
    candidates = []
    start_dir = os.path.abspath(start_dir)
    for root, dirs, files in os.walk(start_dir):
        if "settings.py" in files:
            # If settings.py sits in root/subdir/settings.py -> module is <subdir>.settings
            rel = os.path.relpath(root, start_dir)
            if rel == ".":
                candidates.append("settings")
            else:
                module = rel.replace(os.sep, ".") + ".settings"
                candidates.append(module)
    # remove duplicates while keeping order
    seen = set()
    uniq = []
    for c in candidates:
        if c not in seen:
            uniq.append(c)
            seen.add(c)
    return uniq

# Try auto-detect
candidates = find_settings_module()
if not candidates:
    print("ERROR: Could not find any settings.py under the current directory.")
    print("Make sure you're running this from the Django project root (same folder as manage.py).")
    sys.exit(1)

if len(candidates) > 1:
    print("Multiple potential settings modules found. Will try the first one:")
    for i, c in enumerate(candidates, 1):
        print(f"  {i}. {c}")
chosen_settings = candidates[0]
print(f"Using settings module: {chosen_settings}")

# Ensure project root is on sys.path
project_root = os.path.abspath(".")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", chosen_settings)

# ------------ Now import Django and setup ------------
try:
    import django
    django.setup()
except Exception:
    print("Failed to set up Django with the chosen settings module.")
    traceback.print_exc()
    print("If this fails, set DJANGO_SETTINGS_MODULE manually in this script to the correct value.")
    sys.exit(1)

# ------------ Safety lock: disable any accidental writes ------------
try:
    from django.db import models as dj_models
    _orig_save = getattr(dj_models.Model, "save", None)
    _orig_delete = getattr(dj_models.Model, "delete", None)

    def _read_only_save(self, *args, **kwargs):
        raise RuntimeError("Database writes are disabled in this evaluation script. 'save' is blocked.")

    def _read_only_delete(self, *args, **kwargs):
        raise RuntimeError("Database writes are disabled in this evaluation script. 'delete' is blocked.")

    dj_models.Model.save = _read_only_save
    dj_models.Model.delete = _read_only_delete
    print("Safety lock enabled: model save/delete operations are disabled.")
except Exception:
    print("WARNING: Could not enable safety lock for models (continuing without it).")

# ------------ Imports for evaluation ------------
try:
    from hardware.models import Product
except Exception:
    print("ERROR: Could not import Product from hardware.models.")
    traceback.print_exc()
    sys.exit(1)

# sklearn imports
try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.neighbors import NearestNeighbors
    from sklearn.metrics import precision_score, recall_score, f1_score
    from sklearn.model_selection import train_test_split
except Exception:
    print("ERROR: Required scikit-learn / numpy not found. Install them in your environment:")
    print("  pip install numpy scikit-learn")
    sys.exit(1)

# ------------ Fetch data (read-only) ------------
products_qs = Product.objects.all()
n_products = products_qs.count()
print(f"Found {n_products} products in DB (read-only).")
if n_products < 4:
    print("Not enough products to evaluate KNN reliably (need at least 4). Exiting.")
    sys.exit(1)

docs = []
labels = []
pids = []
for p in products_qs:
    # Defensive attribute access
    name = getattr(p, "name", "") or ""
    desc = getattr(p, "description", "") or ""
    spec = getattr(p, "specification", "") or ""
    # Get category; prefer category_id, else category, else str(category)
    category = getattr(p, "category_id", None)
    if category is None:
        category = getattr(p, "category", "") or ""
        try:
            category = str(category)
        except Exception:
            category = ""
    text = f"{name} {desc} {spec} {category}"
    docs.append(text)
    labels.append(str(category))
    pid_val = getattr(p, "pid", None) or getattr(p, "id", None)
    pids.append(pid_val)

# Optionally merge rare classes into 'OTHER' to enable stratification
if MERGE_RARE:
    label_counts = Counter(labels)
    rare_labels = {lab for lab, cnt in label_counts.items() if cnt < RARE_THRESHOLD}
    if rare_labels:
        print(f"Merging {len(rare_labels)} rare labels into 'OTHER' (examples: {list(rare_labels)[:5]})")
        labels = [("OTHER" if lab in rare_labels else lab) for lab in labels]

# ------------ Vectorize ------------
vectorizer = TfidfVectorizer(stop_words="english", max_features=MAX_FEATURES)
X = vectorizer.fit_transform(docs)

# ------------ Decide whether stratify is possible ------------
label_counts = Counter(labels)
min_count = min(label_counts.values())
print(f"Label counts sample (up to 10): {dict(list(label_counts.items())[:10])}")
print(f"Total distinct labels: {len(label_counts)}. Minimum samples in any label: {min_count}")

if min_count < 2:
    print("WARNING: Some classes have fewer than 2 samples. Stratified train/test split is not possible.")
    print("Proceeding with a random (non-stratified) split. If you prefer, set MERGE_RARE=True to merge rare classes.")
    stratify_arg = None
else:
    stratify_arg = labels

# ------------ Train-test split ------------
try:
    X_train, X_test, y_train, y_test = train_test_split(
        X, labels, test_size=TEST_SIZE, random_state=42, stratify=stratify_arg
    )
except ValueError as e:
    # Fallback: if sklearn still complains for other reasons, do non-stratified split
    print("train_test_split failed with stratify. Falling back to non-stratified split. Exception:", e)
    X_train, X_test, y_train, y_test = train_test_split(
        X, labels, test_size=TEST_SIZE, random_state=42, stratify=None
    )

# ------------ Train KNN (NearestNeighbors for similarity) ------------
k = K_NEIGHBORS
from math import ceil
# Fit on training vectors
knn = NearestNeighbors(metric="cosine", algorithm="brute")
knn.fit(X_train)

# ------------ Evaluate ------------
y_pred = []
start_time = time.time()
for i in range(X_test.shape[0]):
    n_req = min(k, X_train.shape[0])
    distances, indices = knn.kneighbors(X_test[i], n_neighbors=n_req)
    neighbor_labels = [y_train[j] for j in indices[0]]
    # majority vote (tie handled by set order; acceptable for evaluation)
    pred = max(set(neighbor_labels), key=neighbor_labels.count)
    y_pred.append(pred)
end_time = time.time()
exec_time = end_time - start_time

# compute metrics (weighted to account for class imbalance)
precision = precision_score(y_test, y_pred, average="weighted", zero_division=0)
recall = recall_score(y_test, y_pred, average="weighted", zero_division=0)
f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)

print("\n=== KNN Evaluation Results (DB) ===")
print(f"Products total        : {n_products}")
print(f"Train samples         : {X_train.shape[0]}")
print(f"Test samples          : {X_test.shape[0]}")
print(f"K (neighbors)         : {k}")
print(f"Precision (weighted)  : {precision:.4f}")
print(f"Recall (weighted)     : {recall:.4f}")
print(f"F1-score (weighted)   : {f1:.4f}")
print(f"Execution time (queries only): {exec_time:.4f} seconds")

# ------------ Clean up: restore save/delete to originals (optional) ------------
try:
    if '_orig_save' in globals() and _orig_save is not None:
        dj_models.Model.save = _orig_save
    if '_orig_delete' in globals() and _orig_delete is not None:
        dj_models.Model.delete = _orig_delete
    print("\nSafety lock removed (restored original Model.save/delete).")
except Exception:
    pass

print("Done.")


# Create confusion matrix
unique_labels = sorted(set(labels))  # consistent label order
cm = confusion_matrix(y_test, y_pred, labels=unique_labels)

# Display confusion matrix as heatmap-like plot
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=unique_labels)

plt.figure(figsize=(8, 6))
disp.plot(cmap="Blues", values_format="d")
plt.title("Confusion Matrix - KNN Recommender")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig("confusion_matrix.png")
print("Confusion matrix saved as confusion_matrix.png")