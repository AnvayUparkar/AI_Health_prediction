import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import os

print("="*70)
print("CHECKING LUNG CANCER MODEL ACCURACY")
print("="*70)

# Paths
MODEL_PATH = 'models/lung_cancer_model.pkl'
ENCODER_PATH = 'models/lung_cancer_label_encoder.pkl'
DATA_PATH = 'cancer patient data sets.csv'

# Check if files exist
if not os.path.exists(MODEL_PATH):
    print(f"\n✗ Model not found: {MODEL_PATH}")
    print("   Please train the model first using the training script.")
    exit(1)

if not os.path.exists(DATA_PATH):
    print(f"\n✗ Dataset not found: {DATA_PATH}")
    exit(1)

# Load model
print("\n1. Loading model...")
try:
    model = joblib.load(MODEL_PATH)
    print(f"   ✓ Model loaded successfully")
    print(f"   ✓ Model type: {type(model).__name__}")
except Exception as e:
    print(f"   ✗ Failed to load model: {e}")
    exit(1)

# Load encoder (if exists)
label_encoder = None
if os.path.exists(ENCODER_PATH):
    try:
        label_encoder = joblib.load(ENCODER_PATH)
        print(f"   ✓ Label encoder loaded")
        print(f"   ✓ Classes: {label_encoder.classes_}")
    except Exception as e:
        print(f"   ⚠ Could not load encoder: {e}")

# Load data
print("\n2. Loading dataset...")
df = pd.read_csv(DATA_PATH)
print(f"   ✓ Dataset loaded: {df.shape[0]} rows, {df.shape[1]} columns")

# Find target column
target_candidates = ['Level', 'Level_encoded', 'class', 'target']
target_col = None
for col in target_candidates:
    if col in df.columns:
        target_col = col
        break

if target_col is None:
    print(f"   ✗ Could not find target column")
    print(f"   Available columns: {df.columns.tolist()}")
    exit(1)

print(f"   ✓ Target column: '{target_col}'")

# Prepare data
X = df.drop(columns=[target_col])
y = df[target_col]

# Remove other target-like columns
cols_to_drop = [col for col in X.columns if 'level' in col.lower() or col == 'Level_encoded' or col == 'Level_encoded ']
if cols_to_drop:
    X = X.drop(columns=cols_to_drop)

print(f"   ✓ Features: {X.columns.tolist()}")

if label_encoder is not None:
    y_encoded = label_encoder.transform(y)
else:
    y_encoded = y.values

y_encoded = np.array(y_encoded)   # ✅ Ensure numpy array for stratify


# Split data (same way as training)
print("\n3. Splitting data (80/20)...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
)
print(f"   ✓ Train: {len(X_train)}, Test: {len(X_test)}")

# Make predictions
print("\n4. Making predictions...")
y_pred_train = model.predict(X_train)
y_pred_test = model.predict(X_test)

# Calculate accuracy
train_accuracy = accuracy_score(y_train, y_pred_train)
test_accuracy = accuracy_score(y_test, y_pred_test)

print("\n" + "="*70)
print("MODEL ACCURACY RESULTS")
print("="*70)
print(f"\n📊 Training Accuracy: {train_accuracy:.4f} ({train_accuracy*100:.2f}%)")
print(f"📊 Test Accuracy:     {test_accuracy:.4f} ({test_accuracy*100:.2f}%)")

# Get confidence scores if available
if hasattr(model, 'predict_proba'):
    test_proba = model.predict_proba(X_test)
    avg_confidence = np.mean(np.max(test_proba, axis=1)) * 100
    print(f"📊 Average Confidence: {avg_confidence:.2f}%")

# Decode predictions for report
if label_encoder is not None:
    y_test_labels = label_encoder.inverse_transform(y_test)
    y_pred_labels = label_encoder.inverse_transform(y_pred_test)
    target_names = label_encoder.classes_
else:
    y_test_labels = y_test
    y_pred_labels = y_pred_test
    target_names = None

# Classification report
print("\n" + "="*70)
print("DETAILED CLASSIFICATION REPORT")
print("="*70)
print(classification_report(y_test_labels, y_pred_labels, target_names=target_names))

# Confusion matrix
print("\n" + "="*70)
print("CONFUSION MATRIX")
print("="*70)
cm = confusion_matrix(y_test_labels, y_pred_labels)
print(cm)

if label_encoder is not None:
    print(f"\nRows = Actual, Columns = Predicted")
    print(f"Classes: {label_encoder.classes_}")

# Per-class accuracy
print("\n" + "="*70)
print("PER-CLASS ACCURACY")
print("="*70)
for i, cls in enumerate(target_names if target_names is not None else range(len(np.unique(y_test)))):
    mask = y_test_labels == cls
    if np.sum(mask) > 0:
        class_acc = accuracy_score(y_test_labels[mask], y_pred_labels[mask])
        print(f"{cls}: {class_acc:.4f} ({class_acc*100:.2f}%)")

# Overfitting check
print("\n" + "="*70)
print("OVERFITTING CHECK")
print("="*70)
diff = train_accuracy - test_accuracy
print(f"Accuracy difference: {diff:.4f} ({diff*100:.2f}%)")
if diff < 0.05:
    print("✓ Model is well-balanced (low overfitting)")
elif diff < 0.10:
    print("⚠ Slight overfitting detected")
else:
    print("✗ Significant overfitting - model may not generalize well")

print("\n" + "="*70)
print("✓ ACCURACY CHECK COMPLETE")
print("="*70)