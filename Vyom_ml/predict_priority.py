import pickle
import math
import pandas as pd

def predict_priority_score(bank_balance, age, bank_joining_year, asset_value):
    """
    Load the trained model and predict the priority score for a given manual input.

    Parameters:
        bank_balance (float): Bank balance in ₹
        age (int): Age of the customer
        bank_joining_year (int): Year when the customer joined the bank
        asset_value (float): Asset value in ₹

    Returns:
        int: Predicted Priority Score (rounded up)
    """
    
    model_filename = "vyom_ml/xgboost_priority_model.pkl"
    # Load the trained model
    with open(model_filename, "rb") as file:
        loaded_model = pickle.load(file)

    # Create DataFrame from manual input
    input_data = pd.DataFrame([[bank_balance, age, bank_joining_year, asset_value]],
                            columns=['Bank Balance (₹)', 'Age', 'Bank Joining Year', 'Asset Value (₹)'])  # Ensure feature names match # Ensure feature names match

    # Make prediction
    predicted_score = loaded_model.predict(input_data)[0]
    # Round up to the nearest whole number
    return math.ceil(predicted_score)

# # Example manual input
example_prediction = predict_priority_score(50000, 68, 2024, 1000)
print(f"Predicted Priority Score: {example_prediction}")