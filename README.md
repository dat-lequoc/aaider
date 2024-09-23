# aaider.py - Asynchronized Automated Aider Task Executor

*Note*: Feel free to open an issue if you have any questions. This isn't user-friendly due to my little time. 

`aaider.py` is a script designed to automate the execution of multiple tasks using the Aider AI assistant. 
It receives an output file of a bigger model using a specific format (`example.xml`), parses it into Tasks and executes them asynchronously using Aider.

## Example Usage

0. Install requirements
1. Configure DeepSeek API KEY, OpenRouter (if you want to use 'o1') like me
2. Prepare your prompt: 
   - Modify instructions in `example.xml`
   - Run `files-to-prompt --cxml YOUR_FILES_&_FOLDER | cop`
   - Paste in `<code-files>`
3. `llm -m o1-mini < example.xml > out.xml`
4. `cd` to your current repo:
   - Make sure you commit your code for backup
   - `python PATH_TO_AAIDER.py --input out.xml`

## Notes
- Be very specific in your `<purpose>`
- You can add more `<instruction>` if you want
- For me, o1 works very well with this setup.
- Instead of `OpenRouter API`, you can copy and paste the full prompt with code to `o1` and copy back and apply to the code base with `aaider.py`.

## Options

- `--input FILE`: Output of bigger LLM
- `--deepseek`: Use deepseek/deepseek-coder model (default)
- `--model MODEL`: Specify the model to use for the main chat
- `--opus`: Use claude-3-opus-20240229 model
- `--sonnet`: Use claude-3-5-sonnet-20240620 model
- `--4`: Use gpt-4-0613 model
- `--4o`: Use gpt-4o-2024-08-06 model
- `--mini`: Use gpt-4o-mini model
- `--4-turbo`: Use gpt-4-1106-preview model
- `--auto-commits`: Enable automatic Git commits
- `--no-auto-commits`: Disable automatic Git commits (default)
- `--skip N`: Number of tasks to skip
- `--only N [N ...]`: Only execute specified task numbers
- `--use-json`: Use JSON parsing instead of XML

### Aider Arguments

Any additional arguments after the script options will be passed directly to the Aider command.

## Input Format

The script accepts input in either XML or JSON format. Here's an example of the XML format:

```xml
<root>
  <file>
    <path>/path/to/file.py</path>
    <action>update</action>
    <description>Add a new function to calculate factorial</description>
    <code>
def factorial(n):
    if n == 0:
        return 1
    else:
        return n * factorial(n-1)
    </code>
  </file>
  <!-- More file elements... -->
</root>
```

For JSON format, use the `--use-json` flag and provide input in this structure:

```json
{
  "filesContent": [
    {
      "file": "/path/to/file.py",
      "action": "update",
      "description": "Add a new function to calculate factorial",
      "code": "def factorial(n):\n    if n == 0:\n        return 1\n    else:\n        return n * factorial(n-1)"
    }
  ]
}
```

## Examples

1. Execute tasks from an XML file using the Claude 3 Opus model:
   ```bash
   python aaider.py --opus --input tasks.xml
   ```

2. Execute tasks from a JSON file, skipping the first 2 tasks:
   ```bash
   python aaider.py --use-json --input tasks.json --skip 2
   ```

3. Execute only tasks 3 and 5 with auto-commits enabled:
   ```bash
   python aaider.py --auto-commits --only 3 5 --input tasks.xml
   ```

4. Pass additional arguments to Aider:
   ```bash
   python aaider.py --input tasks.xml --model gpt-4 -- --openai-api-key YOUR_API_KEY
   ```

## Output

The script will create a `log` directory containing:
- A log file for each executed task (`task_N.log`)
- A `tasks.json` file with all tasks and their assigned IDs

After execution, a summary of task results will be displayed in the console.

## Contributing

Contributions to improve `aaider.py` are welcome. Please submit pull requests or open issues on the project's repository.
