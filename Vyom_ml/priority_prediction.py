import pandas as pd
import xgboost as xgb
import pickle
import math
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, r2_score

# Load dataset
df = pd.read_csv("vyom_ml/data/bank_customer_priority_dataset.csv")  # Replace with actual dataset filename

# Define features and target variable
X = df.drop(columns=["Priority Score"])
y = df["Priority Score"]

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Define XGBoost model
xgb_model = xgb.XGBRegressor(objective='reg:squarederror', random_state=42)

# Define hyperparameter grid
param_grid = {
    'n_estimators': [100, 200, 300],
    'max_depth': [3, 5, 7],
    'learning_rate': [0.01, 0.1, 0.2],
    'subsample': [0.7, 0.8, 1.0],
    'colsample_bytree': [0.7, 0.8, 1.0]
}

# Perform GridSearchCV
grid_search = GridSearchCV(xgb_model, param_grid, cv=5, scoring='r2', n_jobs=-1, verbose=1)
grid_search.fit(X_train, y_train)

# Best parameters & best model
best_params = grid_search.best_params_
best_model = grid_search.best_estimator_

print("Best Hyperparameters:", best_params)

# Save the best model as a pickle file
# model_filename = "xgboost_priority_model.pkl"
# with open(model_filename, "wb") as file:
#     pickle.dump(best_model, file)

# print(f"Model saved as {model_filename}")

# Predictions on test set
y_pred = best_model.predict(X_test)

# Model evaluation
mae = mean_absolute_error(y_test, y_pred)
r2 = r2_score(y_test, y_pred)

print("Mean Absolute Error:", mae)
print("R^2 Score:", r2)
print(X.columns)
# Function to load the model and make predictions for manual input

