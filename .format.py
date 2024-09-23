import subprocess
import pyperclip
import re

# Read the file content
with open('.run.xml', 'r') as file:
    content = file.read()

# Remove XML comments (<!-- comment -->)
# The regex pattern looks for <!-- followed by any characters (including newlines) until the next -->
content_no_comments = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

# Split the content on the <code-files> tag
parts = content_no_comments.split('<code-files>')
if len(parts) != 2:
    print("Error: Could not find <code-files> tag")
    exit(1)

before, rest = parts

# Further split to isolate the command between <code-files> and </code-files>
after_parts = rest.split('</code-files>')
if len(after_parts) != 2:
    print("Error: Could not find </code-files> tag")
    exit(1)
command_block, after = after_parts

# Combine multiple lines in the command block into a single command line
# This handles cases where the command is spread across multiple lines
# Example:
# <code-files>
#   files-to-prompt --cxml 
#   researcher.py 
#   tutorial.py 
#   text_source.py
# </code-files>
# Will be converted to:
# files-to-prompt --cxml researcher.py tutorial.py text_source.py

# Split the command block into individual lines, strip whitespace, and join with spaces
command_lines = command_block.strip().splitlines()
# Remove any leading/trailing whitespace from each line and filter out empty lines
command_cleaned = ' '.join(line.strip() for line in command_lines if line.strip())

# Now, command_cleaned contains the combined single command line
command = command_cleaned

# Run the command
try:
    result = subprocess.check_output(command, shell=True, text=True)
except subprocess.CalledProcessError as e:
    print(f"Error running command: {e}")
    exit(1)

# Construct the new content by replacing the old command with the command's output
new_content = f"{before}<code-files>\n{result}</code-files>{after}"

# Copy the modified content to the clipboard
pyperclip.copy(new_content)
print("Modified content copied to clipboard.")
