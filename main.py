import pandas as pd
import re
import is_disposable_email
from email_validator import validate_email, EmailNotValidError, EmailSyntaxError
import logging
from tqdm import tqdm
from sklearn.metrics import classification_report, confusion_matrix
from concurrent.futures import ThreadPoolExecutor
import seaborn as sns
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to check the format of an email
def check_email(s):
    pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b'
    if re.match(pattern, s):
        return "VALID"
    else:
        return "INVALID"

# Function to check if an email is disposable
def disposable_email(email):
    result = is_disposable_email.check(email)
    return "Yes" if result else "No"

# Function to validate the format and deliverability of an email
def validate_email_format(email):
    try:
        email_info = validate_email(email, check_deliverability=True)
        return "VALID", "-"
    except EmailSyntaxError as e_syntax:
        return "INVALID", str(e_syntax)
    except EmailNotValidError as e_not_valid:
        return "INVALID", str(e_not_valid)
    except Exception as e:
        return "ERROR", str(e)

# Function to process a single email
def process_email(index, row):
    email = row['email']
    validate_email_result = check_email(email)
    domain_address = email.split('@')[1] if '@' in email else ''
    disposable_email_result = disposable_email(email)
    deliverable_email, reason = validate_email_format(email)
    return index, validate_email_result, domain_address, disposable_email_result, deliverable_email, reason

# Load dataset
from glob import glob
df_list = list()
for path in glob(f"/workspaces/Email-validation/Email-Data/*.csv"):
    df = pd.read_csv("/workspaces/Email-validation/Email-Data/1@abn.csv")

    # Add new columns
    df['validate_email'] = ''
    df['domain_address'] = ''
    df['disposable_email'] = ''
    df['deliverable_email'] = ''
    df['reason'] = ''

    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for index, row in tqdm(df.iterrows(), total=df.shape[0], desc="Validating emails"):
            futures.append(executor.submit(process_email, index, row))

        for future in tqdm(futures, desc="Processing results"):
            index, validate_email_result, domain_address, disposable_email_result, deliverable_email, reason = future.result()
            df.at[index, 'validate_email'] = validate_email_result
            df.at[index, 'domain_address'] = domain_address
            df.at[index, 'disposable_email'] = disposable_email_result
            df.at[index, 'deliverable_email'] = deliverable_email
            df.at[index, 'reason'] = reason

    # Generate classification report
    y_true = df['clean_status']
    y_pred = df['deliverable_email']
    report = classification_report(y_true, y_pred, target_names=['INVALID', 'VALID'], output_dict=True)

    # Convert the classification report to a DataFrame
    report_df = pd.DataFrame(report).transpose()

    # Generate confusion matrix
    conf_matrix = confusion_matrix(y_true, y_pred, labels=['INVALID', 'VALID'])

    # Plot confusion matrix
    plt.figure(figsize=(8, 6))
    sns.heatmap(conf_matrix, annot=True, fmt='d', cmap='Blues', xticklabels=['INVALID', 'VALID'], yticklabels=['INVALID', 'VALID'])
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    plt.title('Confusion Matrix')
    plt.show()

    # Output results
    print("Validation Results:")
    print(df)
    print("\nClassification Report:")
    print(report_df)
    df_list.append(df)

single_df = pd.concat(df_list, ignore_index=True)
single_df.to_csv("final_output.csv", index=False)