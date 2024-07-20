import streamlit as st
import re
import os
import is_disposable_email
from email_validator import validate_email, EmailNotValidError, EmailSyntaxError
import logging
import subprocess
import pandas as pd

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

# Sherlock Functions
def run_sherlock(usernames, output_folder=None, output_file=None, tor=False, unique_tor=False, csv=False, xlsx=False, site=None, proxy=None, json_file=None, timeout=60, print_all=False, print_found=False, no_color=False, browse=False, local=False, nsfw=False):
    # Construct the command
    command = ['sherlock']
    
    # Add usernames
    if isinstance(usernames, list):
        command.extend(usernames)
    else:
        command.append(usernames)
    
    # Add optional arguments
    if output_folder:
        command.extend(['--folderoutput', output_folder])
    if output_file:
        command.extend(['--output', output_file])
    if tor:
        command.append('--tor')
    if unique_tor:
        command.append('--unique-tor')
    if csv:
        command.append('--csv')
    if xlsx:
        command.append('--xlsx')
    if site:
        if isinstance(site, list):
            for s in site:
                command.extend(['--site', s])
        else:
            command.extend(['--site', site])
    if proxy:
        command.extend(['--proxy', proxy])
    if json_file:
        command.extend(['--json', json_file])
    if timeout:
        command.extend(['--timeout', str(timeout)])
    if print_all:
        command.append('--print-all')
    if print_found:
        command.append('--print-found')
    if no_color:
        command.append('--no-color')
    if browse:
        command.append('--browse')
    if local:
        command.append('--local')
    if nsfw:
        command.append('--nsfw')
    
    # Run the command
    try:
        result = subprocess.run(command, capture_output=True, text=True)
        output = result.stdout
        #matches = extract_matches(output)
        return output
    except Exception as e:
        print(f"Error running Sherlock: {e}")
        return []

def extract_matches(output):
    # Regex to extract matches from the output
    lines = output.splitlines()
    matches = []
    for line in lines:
        if ',' in line:  # Check if the line has the CSV format
            parts = line.split(',')
            if len(parts) >= 4:
                username, name, url_main, url_user, exists, http_status, response_time_s = parts
                matches.append({
                    'username': username,
                    'name': name,
                    'url_main': url_main,
                    'url_user': url_user,
                    'exists': exists,
                    'http_status': http_status,
                    'response_time_s': response_time_s
                })
    return matches

# Streamlit App
st.set_page_config(page_title="Validation Application", page_icon="🔍", layout="wide")

# Sidebar for input
st.sidebar.title("Validation Application")
st.sidebar.subheader("Enter details to validate")

# Input email address
email = st.sidebar.text_input("Email Address")

if st.sidebar.button("Validate"):
    # Email validation
    if email:
        with st.spinner('Validating email...'):
            validate_email_result = check_email(email)
            domain_address = email.split('@')[1] if '@' in email else ''
            disposable_email_result = disposable_email(email)
            deliverable_email, reason = validate_email_format(email)
        
        st.success("Email validation completed!")
        
        st.markdown("### Email Validation Results")
        st.write(f"**Email:** `{email}`")
        
        result_columns = st.columns(2)
        
        with result_columns[0]:
            st.markdown("#### Validation Checks")
            st.write(f"**Format:** `{validate_email_result}`")
            st.write(f"**Domain:** `{domain_address}`")
            st.write(f"**Disposable:** `{disposable_email_result}`")
        
        with result_columns[1]:
            st.markdown("#### Deliverability")
            st.write(f"**Deliverable:** `{deliverable_email}`")
            if reason != "-":
                st.write(f"**Reason:** `{reason}`")

        # Extract username from email
        username = email.split('@')[0]
        st.sidebar.write(f"Extracted Username: `{username}`")

        # Sherlock validation
        if username:
            with st.spinner(f'Searching for {username} ...'):
                matches = run_sherlock(username, output_folder=".", csv=True)
            
            st.success("Search completed!")
            
            if matches:
                username_dataframe = pd.read_csv(f"{username}.csv")
                os.remove(f"{username}.csv")
                st.dataframe(username_dataframe)
    if not email:
        st.sidebar.error("Please enter an email address.")
