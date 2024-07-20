import subprocess
import os
import re

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
        matches = extract_matches(output)
        return matches
    except Exception as e:
        print(f"Error running Sherlock: {e}")
        return []

def extract_matches(output):
    # Regex to extract URLs from the output
    url_pattern = re.compile(r'http[s]?://[^\s]+')
    matches = url_pattern.findall(output)
    return matches

if __name__ == "__main__":
    # Example usage
    usernames = ['abilash']
    output_folder = 'sherlock_results'
    
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    matches = run_sherlock(usernames, output_folder=output_folder, csv=True, print_found=True)
    print("Matches found:")
    for match in matches:
        print(match)
