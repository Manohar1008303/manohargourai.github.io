import pandas as pd
import os


def prepare_data(file_path):
    """
    Load and clean the loan dataset
    """

    print("Loading dataset...")

    # Load dataset
    df = pd.read_csv(file_path)

    # Convert numeric columns
    numeric_cols = ["Loan_Amount", "Interest_Rate", "Default_Prob", "WARF"]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop missing values
    df = df.dropna()

    return df


if __name__ == "__main__":

    # Get project root automatically
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)

    # Build dataset path
    data_path = os.path.join(project_root, "Data", "clo_loan_dataset.csv")

    # Load dataset
    df = prepare_data(data_path)

    print("Dataset loaded successfully")
    print("Total loans:", len(df))

    print("\nPreview of dataset:")
    print(df.head())

    # Save cleaned dataset
    results_path = os.path.join(project_root, "Results", "cleaned_dataset.csv")
    df.to_csv(results_path, index=False)

    print("\nCleaned dataset saved in Results folder")