def predict_resolution_time(priority_score, dept, sub_dept, service_level):
    """
    Predicts query resolution time in minutes based on:
      - priority_score: 1 (highest priority) to 10 (lowest)
      - dept: Department name (e.g., "Credit", "General Banking", "Forex")
      - sub_dept: Sub-Department name within the department
      - service_level: 1 (very easy), 2 (medium), or 3 (hard)
    
    Note: For some services with low base times, a high priority and low service level may result in 
    a resolution time of less than 10 minutes.
    
    Returns:
      Predicted resolution time (in minutes) as a float, rounded to one decimal.
    """
    # Predefined base resolution times (in minutes)
    base_times = {
        "Credit": {
            "Retail Loans": {1: 40, 2: 80, 3: 120},
            "Corporate Loans": {1: 35, 2: 70, 3: 105},
            "Credit Cards": {1: 30, 2: 60, 3: 90},
            "Mortgage & Secured Loans": {1: 45, 2: 90, 3: 135},
            "Microfinance & Agricultural Loans": {1: 25, 2: 50, 3: 75}
        },
        "General Banking": {
            "Accounts & Deposits": {1: 10, 2: 20, 3: 30},
            "Transactions & Payments": {1: 15, 2: 30, 3: 45},
            "Cards & Banking Services": {1: 12, 2: 24, 3: 36},
            "KYC & Documentation": {1: 8, 2: 16, 3: 24},
            "Banking Tech & Digital Services": {1: 10, 2: 20, 3: 30}
        },
        "Forex": {
            "Currency Exchange": {1: 5, 2: 10, 3: 15},
            "International Transactions": {1: 8, 2: 16, 3: 24},
            "Trade Finance": {1: 20, 2: 40, 3: 60},
            "Foreign Investments & NRI Banking": {1: 25, 2: 50, 3: 75}
        }
    }
    
    # Check if the department exists.
    if dept not in base_times:
        return f"Department '{dept}' not recognized."
    
    # Check if the sub-department exists in the department.
    if sub_dept not in base_times[dept]:
        return f"Sub-Department '{sub_dept}' not recognized in Department '{dept}'."
    
    # Check if the service level exists for the given sub-department.
    if service_level not in base_times[dept][sub_dept]:
        return f"Service Level '{service_level}' not recognized for Department '{dept}' and Sub-Department '{sub_dept}'."
    
    # Retrieve the base resolution time.
    base_time = base_times[dept][sub_dept][service_level]
    
    # Compute the priority multiplier.
    multiplier = 1 + 0.1 * (priority_score - 5)
    
    # Calculate the final resolution time.
    resolution_time = base_time * multiplier
    
    # Return the result rounded to one decimal place.
    return round(resolution_time, 1)

# Example usages:

# 1. Forex, Currency Exchange, Level 1, with highest priority (1)
# Expected: Base time = 5, multiplier = 0.6, so 5 * 0.6 = 3.0 minutes.
print("Example 1:", predict_resolution_time(1, "Forex", "Currency Exchange", 1))

# 2. General Banking, Accounts & Deposits, Level 1, with highest priority (1)
# Expected: Base time = 10, multiplier = 0.6, so 10 * 0.6 = 6.0 minutes.
print("Example 2:", predict_resolution_time(1, "General Banking", "Accounts & Deposits", 1))

# 3. Credit, Retail Loans, Level 3, with low priority (10)
# Expected: Base time = 120, multiplier = 1.5, so 120 * 1.5 = 180.0 minutes.
print("Example 3:", predict_resolution_time(10, "Credit", "Retail Loans", 3))
