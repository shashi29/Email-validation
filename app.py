import re
import smtplib
import dns.resolver
import streamlit as st
import os
import is_disposable_email
from email_validator import validate_email, EmailNotValidError, EmailSyntaxError
import logging
import subprocess
import pandas as pd
from typing import Tuple, Optional
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EmailValidationResult:
    email: str
    format_check: str
    domain: str
    disposable: str
    smtp_validation: str
    deliverable: str
    reason: str
    smtp_message: str
    email_status: str  # New column for email status
    status_code: str

class EmailValidator:
    @staticmethod
    def smtp_validate_email(address_to_verify: str) -> Tuple[str, str]:
        from_address = 'stcsu2@racfq.com'
        regex = r'^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,})$'

        if not re.match(regex, address_to_verify):
            return 'INVALID', 'Bad Syntax'

        domain = address_to_verify.split('@')[1]

        try:
            records = dns.resolver.resolve(domain, 'MX')
            mx_record = str(records[0].exchange)
        except Exception as e:
            return 'INVALID', f'DNS Lookup failed: {e}'

        try:
            with smtplib.SMTP() as server:
                server.set_debuglevel(0)
                server.connect(mx_record)
                server.helo(server.local_hostname)
                server.mail(from_address)
                code, message = server.rcpt(str(address_to_verify))

            if code == 250:
                return code, 'VALID', 'Success'
            else:
                return code, 'INVALID', message.decode()
        except Exception as e:
            return 500, 'INVALID', f'SMTP Connection failed: {e}'

    @staticmethod
    def check_email_format(email: str) -> str:
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,7}\b'
        return "VALID" if re.match(pattern, email) else "INVALID"

    @staticmethod
    def is_disposable_email(email: str) -> str:
        return "Yes" if is_disposable_email.check(email) else "No"

    @staticmethod
    def validate_email_format(email: str) -> Tuple[str, str]:
        try:
            validate_email(email, check_deliverability=True)
            return "VALID", "-"
        except EmailSyntaxError as e_syntax:
            return "INVALID", str(e_syntax)
        except EmailNotValidError as e_not_valid:
            return "INVALID", str(e_not_valid)
        except Exception as e:
            return "ERROR", str(e)

    @classmethod
    def validate_email(cls, email: str) -> EmailValidationResult:
        format_check = cls.check_email_format(email)
        domain = email.split('@')[1] if '@' in email else ''
        disposable = cls.is_disposable_email(email)
        deliverable, reason = cls.validate_email_format(email)
        status_code, smtp_validation, smtp_message = cls.smtp_validate_email(email)

        # Determine email status based on the validation results
        email_status = "Good" if format_check == "VALID" and disposable == "No" and smtp_validation == "VALID" and deliverable == "VALID" else "Bad"

        return EmailValidationResult(
            email=email,
            format_check=format_check,
            domain=domain,
            disposable=disposable,
            smtp_validation=smtp_validation,
            deliverable=deliverable,
            reason=reason,
            smtp_message=smtp_message,
            email_status=email_status,
            status_code=status_code
        )

class SherlockRunner:
    @staticmethod
    def run_sherlock(usernames: str, output_folder: Optional[str] = None, csv: bool = False) -> str:
        command = ['sherlock', usernames]
        if output_folder:
            command.extend(['--folderoutput', output_folder])
        if csv:
            command.append('--csv')
        try:
            result = subprocess.run(command, capture_output=True, text=True)
            return result.stdout
        except Exception as e:
            logger.error(f"Error running Sherlock: {e}")
            return ""

class StreamlitUI:
    def __init__(self):
        st.set_page_config(page_title="Email Validation App", page_icon="📧", layout="wide")
        st.sidebar.title("Email Validation App")
        st.sidebar.subheader("Choose your input method")

    def run(self):
        input_method = st.sidebar.selectbox("Select input method", ("Single Email", "Multiple Emails", "Upload CSV"))

        if input_method == "Single Email":
            self.single_email_validation()
        elif input_method == "Multiple Emails":
            self.multiple_email_validation()
        elif input_method == "Upload CSV":
            self.upload_csv_validation()

    def single_email_validation(self):
        email = st.text_input("Enter an email address to validate")
        if st.button("Validate"):
            result = EmailValidator.validate_email(email)
            st.write(result.__dict__)

    def multiple_email_validation(self):
        emails = st.text_area("Enter email addresses separated by commas")
        if st.button("Validate"):
            email_list = [email.strip() for email in emails.split(',')]
            results = self.process_emails_parallel(pd.Series(email_list))
            results_df = pd.DataFrame(results)
            st.dataframe(results_df)
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", csv, "email_validation_results.csv", "text/csv")

    def upload_csv_validation(self):
        uploaded_file = st.sidebar.file_uploader("Choose a CSV file", type=["csv"])

        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            if "email" in df.columns:
                start_time = time.time()
                with st.spinner('Validating emails...'):
                    results = self.process_emails_parallel(df["email"])
                    results_df = pd.DataFrame(results)
                end_time = time.time()
                total_time = end_time - start_time
                emails_per_second = len(df) / total_time if total_time > 0 else float('inf')

                st.success(f"Email validation completed in {total_time:.2f} seconds!")
                st.write(f"Speed: {emails_per_second:.2f} emails per second")

                st.dataframe(results_df)

                csv = results_df.to_csv(index=False).encode('utf-8')
                st.download_button("Download CSV", csv, "email_validation_results.csv", "text/csv")
            else:
                st.sidebar.error("The CSV file must contain a column named 'email'.")

    def process_emails_parallel(self, emails: pd.Series) -> list:
        results = []
        progress_bar = st.progress(0)
        total_emails = len(emails)
        processed_emails = 0

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {executor.submit(EmailValidator.validate_email, email): email for email in emails}
            for future in as_completed(futures):
                email = futures[future]
                try:
                    result = future.result()
                    results.append(result.__dict__)
                except Exception as e:
                    logger.error(f"Error processing email {email}: {e}")
                    results.append({
                        "email": email,
                        "format_check": "ERROR",
                        "domain": "",
                        "disposable": "",
                        "smtp_validation": "ERROR",
                        "deliverable": "ERROR",
                        "reason": str(e),
                        "smtp_message": "",
                        "email_status": "Bad",
                        "status_code": "500"
                    })

                processed_emails += 1
                progress_bar.progress(processed_emails / total_emails)

        return results

if __name__ == "__main__":
    ui = StreamlitUI()
    ui.run()
