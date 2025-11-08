import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import numpy as np

# Load the dataset
file_path = 'synthetic_med_device_energy.csv'
try:
    df = pd.read_csv(file_path)

    print("--- Building a TRUE Predictive Model ---")
    
    # --- 1. Define Prediction Horizon ---
    # Data is in 5-minute intervals. Let's predict a spike 30 minutes in advance.
    # 30 minutes / 5 minutes = 6 steps (rows)
    horizon_steps = 6
    target_name = 'is_spike_in_30_min'

    # --- 2. Engineer the Future Target ---
    # We shift the 'is_spike' column *backwards* by 6 steps.
    df[target_name] = df['is_spike'].shift(-horizon_steps)
    
    # --- 3. Define Features (X) and Target (y) ---
    
    # Define all "leaky" columns that the model MUST NOT see.
    leaky_cols = [
        'is_spike',                     # This is the current spike (target leakage)
        'power_kW',                     # This is the current power (target leakage)
        'power_kW_previous_5min',     # Too close to the event (leaky)
        'power_kW_previous_15min',    # Too close to the event (leaky)
        'power_kW_rolling_std_15min'  # Too close to the event (leaky)
    ]
    
    # Define other columns to drop (IDs, timestamps)
    other_drops = ['timestamp', 'order_id']

    # Create Features (X)
    X = df.drop(columns=leaky_cols + other_drops + [target_name])
    
    # Create Target (y)
    y = df[target_name]
    
    # --- 4. Handle Categorical Features ---
    categorical_cols = ['facility_id', 'line_id', 'product_type', 'batch_status', 'autoclave_state']
    cols_to_encode = [col for col in categorical_cols if col in X.columns]
    
    X = pd.get_dummies(X, columns=cols_to_encode, drop_first=True)

    # --- 5. Clean NaN values ---
    # The last 6 rows of 'y' will be NaN. We must drop them from both X and y.
    temp_df = pd.concat([X, y], axis=1)
    temp_df.dropna(subset=[target_name], inplace=True)
    
    X_clean = temp_df.drop(columns=[target_name])
    y_clean = temp_df[target_name]
    
    # --- 6. Split Data ---
    X_train, X_test, y_train, y_test = train_test_split(X_clean, y_clean, test_size=0.2, random_state=42)

    # --- 7. Train the RandomForest Classifier ---
    print("\n--- Training RandomForest Classifier to Predict Future Spike ---")
    
    # Use class_weight='balanced' to handle any potential imbalance
    model = RandomForestClassifier(n_estimators=100, 
                                   random_state=42, 
                                   n_jobs=-1,
                                   class_weight='balanced')

    model.fit(X_train, y_train)
    print("Model training complete.")

    # --- 8. Model Evaluation ---
    y_pred = model.predict(X_test)

    accuracy = accuracy_score(y_test, y_pred)
    conf_matrix = confusion_matrix(y_test, y_pred)
    class_report = classification_report(y_test, y_pred, target_names=['No Spike (0)', 'Spike (1)'])

    print("\n--- Predictive Model Evaluation Results ---")
    print(f"Target: {target_name} (Predicting a spike 30 minutes in advance)")
    print(f"Overall Accuracy: {accuracy:.4f}")
    print("\nConfusion Matrix:")
    print(conf_matrix)
    print("\nClassification Report:")
    print(class_report)

except FileNotFoundError:
    print(f"Error: The file '{file_path}' was not found.")
except Exception as e:
    print(f"An error occurred: {e}")