import re
import subprocess
import argparse
import shlex
import sys
import json
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
import asyncio
import shutil  # Added for cleaning log directory

def parse_fault_tolerant_xml(xml_string: str) -> List[Dict[str, Any]]:
    # Normalize line endings
    xml_string = xml_string.replace('\r\n', '\n').replace('\r', '\n')

    # Remove any XML declaration to avoid parsing issues
    xml_string = re.sub(r'<\?xml.*?\?>', '', xml_string)

    # Wrap content in a root element if not present
    if not xml_string.strip().startswith('<root>'):
        xml_string = f"<root>{xml_string}</root>"

    # Replace problematic characters
    xml_string = re.sub(r'&(?!amp;|lt;|gt;|apos;|quot;)', '&amp;', xml_string)

    result = []

    try:
        # Parse the entire XML structure
        root = ET.fromstring(xml_string)

        # Find all file elements
        file_elements = root.findall('.//file')

        for file_elem in file_elements:
            file_info = {}
            for child in file_elem:
                if child.tag == 'code':
                    file_info[child.tag] = child.text.strip() if child.text else ""
                else:
                    file_info[child.tag] = child.text.strip() if child.text else ""
            result.append(file_info)
    except ET.ParseError as e:
        print(f"Warning: Error parsing XML, attempting manual extraction: {str(e)}", file=sys.stderr)
        # If parsing fails, try to extract information manually
        file_blocks = re.findall(r'<file>.*?</file>', xml_string, re.DOTALL)
        for block in file_blocks:
            file_info = {}
            for tag in ['path', 'action', 'description', 'code']:
                match = re.search(f'<{tag}>(.*?)</{tag}>', block, re.DOTALL)
                if match:
                    file_info[tag] = match.group(1).strip()
            if file_info:
                result.append(file_info)
            else:
                print(f"Warning: Unable to extract information from block: {block[:100]}...", file=sys.stderr)

    return result

def extract_tasks(text, use_json=False):
    if use_json:
        # Try to parse as JSON
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "filesContent" in data:
                return [
                    {
                        "file": file_info['file'],
                        "action": file_info['action'],
                        "description": file_info['description'],
                        "code": file_info.get('code', '')
                    }
                    for file_info in data["filesContent"]
                ]
        except json.JSONDecodeError:
            print("Warning: Failed to parse JSON, falling back to XML parsing", file=sys.stderr)

    # Default to XML parsing
    return parse_fault_tolerant_xml(text)

def trim_command(command, max_length=400):
    if len(command) <= max_length:
        return command
    head = command[:max_length//2 - 3]
    tail = command[-max_length//2 + 3:]
    return f"{head}...{tail}"

def parse_arguments():
    parser = argparse.ArgumentParser(description="Execute tasks using aider with custom arguments.")

    # Model selection group
    model_group = parser.add_mutually_exclusive_group()
    model_group.add_argument('--model', help="Specify the model to use for the main chat [env var: AIDER_MODEL]")
    model_group.add_argument('--opus', action='store_true', help="Use claude-3-opus-20240229 model for the main chat [env var: AIDER_OPUS]")
    model_group.add_argument('--sonnet', action='store_true', help="Use claude-3-5-sonnet-20240620 model for the main chat [env var: AIDER_SONNET]")
    model_group.add_argument('--4', '-4', action='store_true', help="Use gpt-4-0613 model for the main chat [env var: AIDER_4]")
    model_group.add_argument('--4o', action='store_true', help="Use gpt-4o-2024-08-06 model for the main chat [env var: AIDER_4O]")
    model_group.add_argument('--mini', action='store_true', help="Use gpt-4o-mini model for the main chat [env var: AIDER_MINI]")
    model_group.add_argument('--4-turbo', action='store_true', help="Use gpt-4-1106-preview model for the main chat [env var: AIDER_4_TURBO]")
    model_group.add_argument('--deepseek', action='store_true', help="Use deepseek/deepseek-coder model for the main chat [env var: AIDER_DEEPSEEK]")

    # Auto-commit flags
    auto_commit_group = parser.add_mutually_exclusive_group()
    auto_commit_group.add_argument('--auto-commits', dest='auto_commits', action='store_true', help='Enable automatic Git commits.')
    auto_commit_group.add_argument('--no-auto-commits', dest='auto_commits', action='store_false', help='Disable automatic Git commits (default).')
    parser.set_defaults(auto_commits=False)  # Default to --no-auto-commits

    parser.add_argument('--input', help="Path to the input file (XML or JSON)")
    parser.add_argument('--skip', type=int, default=0, help="Number of tasks to skip")
    parser.add_argument('--only', type=int, nargs='+', help="Only execute specified task numbers")
    parser.add_argument('--use-json', action='store_true', help="Use JSON parsing instead of XML")
    parser.add_argument('aider_args', nargs=argparse.REMAINDER, help="Arguments to pass to aider command")
    return parser.parse_args()

def get_input(input_file=None):
    if input_file:
        try:
            with open(input_file, 'r') as file:
                return file.read().strip()
        except IOError as e:
            print(f"Error reading input file: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("Please paste your text below. When finished, press Ctrl+D (Unix) or Ctrl+Z (Windows) followed by Enter:")
        return sys.stdin.read().strip()

def delete_file(file_path, log_fh, auto_commits):
    try:
        os.remove(file_path)
        message = f"File deleted successfully: {file_path}"
        print(message)
        log_fh.write(message + "\n")

        if auto_commits:
            # Git operations
            try:
                # Remove the file from Git
                subprocess.run(['git', 'rm', file_path], check=True)
                message = f"File removed from Git: {file_path}"
                print(message)
                log_fh.write(message + "\n")

                # Commit the change
                commit_message = f"Remove file: {file_path}"
                subprocess.run(['git', 'commit', '-m', commit_message], check=True)
                message = f"Changes committed: {commit_message}"
                print(message)
                log_fh.write(message + "\n")
            except subprocess.CalledProcessError as e:
                error_message = f"Error performing Git operations: {e}"
                print(error_message)
                log_fh.write(error_message + "\n")
        else:
            message = "Auto commits are disabled. Skipping Git operations."
            print(message)
            log_fh.write(message + "\n")
    except FileNotFoundError:
        message = f"File not found: {file_path}"
        print(message)
        log_fh.write(message + "\n")
    except PermissionError:
        message = f"Permission denied: Unable to delete {file_path}"
        print(message)
        log_fh.write(message + "\n")
    except Exception as e:
        message = f"An error occurred while deleting {file_path}: {e}"
        print(message)
        log_fh.write(message + "\n")

def get_model_flag(args):
    if args.model:
        return f'--model {args.model}'
    elif args.opus:
        return '--opus'
    elif args.sonnet:
        return '--sonnet'
    elif getattr(args, '4'):
        return '--4'
    elif args.__dict__['4o']:
        return '--4o'
    elif args.mini:
        return '--mini'
    elif args.__dict__['4_turbo']:
        return '--4-turbo'
    elif args.deepseek:
        return '--deepseek'
    else:
        return '--deepseek'  # Default to deepseek if no model is specified

def format_task(task):
    formatted_task = f"Update file: {task['path']}\n\n"
    formatted_task += f"\"action\": \"{task['action']}\"\n\n"
    formatted_task += f"Description: {task['description']}\n\n"
    if task['action'].lower() != 'delete':
        if 'code' in task and task['code'].strip():
            formatted_task += f"New content:\n\n{task['code']}"
        else:
            formatted_task += "No code provided.\n"
    return formatted_task

async def run_task(i, task, model_flag, aider_args, args, total_tasks, results, timeout_event):
    if timeout_event.is_set():
        return  # Skip execution if timeout has occurred

    print("#" * 20)
    print("#" * 20)

    # Calculate the original task number
    original_task_number = args.only[i] if args.only else i + args.skip + 1

    print(f"Executing task {original_task_number}/{total_tasks}...")

    file_path = task['path']
    action = task['action'].lower()

    print(f"[Action]: {action}")

    # Collect per-task result
    task_result = {
        'status': False,  # Will update to True if successful
        'code_missing': False,
        'unexpected_action': False,
        'action': action,   # Added action
        'path': file_path,  # Added path
    }

    expected_actions = ['create', 'update', 'delete']
    if action not in expected_actions:
        print(f"Warning: Unexpected action '{action}' in task {original_task_number}")
        task_result['unexpected_action'] = True
        # Proceed with caution or handle accordingly

    if 'code' not in task or not task.get('code'):
        print(f"Notice: 'code' field is missing in task {original_task_number}")
        task_result['code_missing'] = True

    # Prepare the log file
    log_folder = 'log'
    os.makedirs(log_folder, exist_ok=True)
    log_file = os.path.join(log_folder, f'task_{original_task_number}.log')

    try:
        with open(log_file, 'w') as log_fh:
            if action == "delete":
                delete_file(file_path, log_fh, args.auto_commits)
                task_result['status'] = True  # Mark as success
                results[original_task_number] = task_result
                return  # Skip to the next task after deletion

            dir_path = os.path.dirname(file_path)

            if action == "create" and dir_path:
                # Create directory only if action is create and dir_path is not empty
                mkdir_command = f'mkdir -p {shlex.quote(dir_path)}'
                log_fh.write(f"Creating directory: {mkdir_command}\n")
                print(f"Creating directory: {mkdir_command}")
                try:
                    subprocess.run(mkdir_command, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    warning_message = f"Warning: Failed to create directory: {e}"
                    print(warning_message)
                    log_fh.write(warning_message + "\n")

            # Touch file for create or update actions
            if action in ["create", "update"]:
                touch_command = f'touch {shlex.quote(file_path)}'
                log_fh.write(f"Creating/updating file: {touch_command}\n")
                print(f"Creating/updating file: {touch_command}")
                try:
                    subprocess.run(touch_command, shell=True, check=True)
                except subprocess.CalledProcessError as e:
                    warning_message = f"Warning: Failed to create/update file: {e}"
                    print(warning_message)
                    log_fh.write(warning_message + "\n")

            # Format the task to string before sending to the command
            formatted_task = format_task(task)
            escaped_task = shlex.quote(formatted_task)
            command = (
                f'python -m aider '
                f'--yes '
                f'{model_flag} '
                f'--no-suggest-shell-commands '
                f'{aider_args} '
                f'--message {escaped_task}'
            )
            if action.lower() != 'delete':
                command += f' {shlex.quote(file_path)}'

            log_fh.write(f"Running command: {command}\n")
            print(f"Running command: {trim_command(command)}")

            try:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await process.communicate()

                # Write outputs to log file
                log_fh.write("Standard Output:\n")
                log_fh.write(stdout.decode() + "\n")
                log_fh.write("Standard Error:\n")
                log_fh.write(stderr.decode() + "\n")

                if process.returncode == 0:
                    success_message = f"Task {original_task_number} executed successfully."
                    print(success_message)
                    log_fh.write(success_message + "\n")
                    task_result['status'] = True  # Mark as success
                else:
                    error_message = f"Error executing task {original_task_number}. See {log_file} for details."
                    print(error_message)
                    log_fh.write(error_message + "\n")
                    task_result['status'] = False  # Mark as failure

            except Exception as e:
                exception_message = f"Exception while executing task {original_task_number}: {e}"
                print(exception_message)
                log_fh.write(exception_message + "\n")
                task_result['status'] = False  # Mark as failure

    except Exception as e:
        print(f"Failed to write to log file {log_file}: {e}")
        task_result['status'] = False

    # Update results
    results[original_task_number] = task_result

async def main():
    args = parse_arguments()
    aider_args = ' '.join(args.aider_args)

    # Append auto-commit flags to aider_args
    if args.auto_commits:
        aider_args += ' --auto-commits'
    else:
        aider_args += ' --no-auto-commits'

    text = get_input(args.input)

    tasks = extract_tasks(text, args.use_json)
    if not tasks:
        print("No tasks found in the input.")
        return

    model_flag = get_model_flag(args)

    # Assign IDs to tasks and save to tasks.json
    log_folder = 'log'
    
    # Clean log/* before running
    if os.path.exists(log_folder):
        try:
            shutil.rmtree(log_folder)
            print(f"Cleaned the '{log_folder}' directory before running.")
        except Exception as e:
            print(f"Error cleaning the '{log_folder}' directory: {e}", file=sys.stderr)
            sys.exit(1)
    os.makedirs(log_folder, exist_ok=True)

    tasks_with_ids = []
    for idx, task in enumerate(tasks, start=1):
        task_with_id = {'id': idx, **task}
        tasks_with_ids.append(task_with_id)

    # Save tasks to tasks.json
    tasks_json_path = os.path.join(log_folder, 'tasks.json')
    try:
        with open(tasks_json_path, 'w') as f:
            json.dump(tasks_with_ids, f, indent=4)
        print(f"Tasks saved to {tasks_json_path}")
    except IOError as e:
        print(f"Error saving tasks to {tasks_json_path}: {e}", file=sys.stderr)
        sys.exit(1)

    # Apply task selection based on --skip and --only arguments
    if args.only:
        selected_tasks = [tasks_with_ids[i-1] for i in args.only if 1 <= i <= len(tasks)]
    else:
        selected_tasks = tasks_with_ids[args.skip:]

    total_tasks = len(tasks)  # Store the total number of tasks

    # Dictionary to keep track of task results
    results = {}

    # Create an event to signal timeout
    timeout_event = asyncio.Event()

    # Create a list of tasks to run asynchronously
    task_coroutines = []
    for i, task in enumerate(selected_tasks):
        task_coroutines.append(
            run_task(i, task, model_flag, aider_args, args, total_tasks, results, timeout_event)
        )

    # Set the timeout
    timeout_seconds = 600  # 5 minutes

    try:
        await asyncio.wait_for(
            asyncio.gather(*task_coroutines),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        print(f"\nTimeout reached after {timeout_seconds} seconds.")
        timeout_event.set()  # Signal tasks to stop if possible

    # After all tasks are completed or timeout occurred, report the results
    print("\nSummary of task execution:")
    for task_num in sorted(results.keys()):
        task_result = results[task_num]
        status = "Success" if task_result['status'] else "Failed"
        code_missing = "Yes" if task_result.get('code_missing') else "No"
        unexpected_action = "Yes" if task_result.get('unexpected_action') else "No"
        action = task_result.get('action', 'N/A')
        path = task_result.get('path', 'N/A')
        print(f"Task {task_num}: {status}, Action: {action}, Path: {path}, Code Missing: {code_missing}, Unexpected Action: {unexpected_action}")

if __name__ == "__main__":
    asyncio.run(main())

