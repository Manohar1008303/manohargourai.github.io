import pandas as pd

def prepare_data(file_path):

    # Load dataset
    df = pd.read_csv(file_path)

    print("Dataset Loaded Successfully")
    print("Number of Loans:", len(df))

    # Map credit ratings to WARF scores
    rating_map = {
        "BB": 2000,
        "B": 3000,
        "CCC": 4500
    }

    df["WARF"] = df["Rating"].map(rating_map)

    # Calculate Expected Return
    df["Expected_Return"] = (
        df["Spread"] * df["Utilization"]
        - df["Default_Prob"] * (1 - df["Recovery_Rate"])
    )

    print("\nData Preparation Completed")

    return df


if __name__ == "__main__":

    file_path = "/Users/manohargourai/Desktop/My Projects/Loan Portfolio Optimization/Data/clo_loan_dataset.csv"

    df = prepare_data(file_path)

    print("\nPreview of Prepared Data:")
    print(df.head())