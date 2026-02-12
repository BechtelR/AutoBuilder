# google.adk.auth module¶

Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.auth

# google.adk.cli module¶

# google.adk.code_executors module¶

***pydantic**model*google.adk.code_executors.BaseCodeExecutor¶**
Bases:BaseModel

Abstract base class for all code executors.

The code executor allows the agent to execute code blocks from model responses and incorporate the execution results into the final response.


**optimize_data_file¶**
If true, extract and process data files from the model request and attach them to the code executor. Supported data file MimeTypes are [text/csv]. Default to False.


**stateful¶**
Whether the code executor is stateful. Default to False.


**error_retry_attempts¶**
The number of attempts to retry on consecutive code execution errors. Default to 2.


**code_block_delimiters¶**
The list of the enclosing delimiters to identify the code blocks.


**execution_result_delimiters¶**
The delimiters to format the code execution result.


```
Show JSON schema{
   "title": "BaseCodeExecutor",
   "description": "Abstract base class for all code executors.\n\nThe code executor allows the agent to execute code blocks from model responses\nand incorporate the execution results into the final response.\n\nAttributes:\n  optimize_data_file: If true, extract and process data files from the model\n    request and attach them to the code executor. Supported data file\n    MimeTypes are [text/csv]. Default to False.\n  stateful: Whether the code executor is stateful. Default to False.\n  error_retry_attempts: The number of attempts to retry on consecutive code\n    execution errors. Default to 2.\n  code_block_delimiters: The list of the enclosing delimiters to identify the\n    code blocks.\n  execution_result_delimiters: The delimiters to format the code execution\n    result.",
   "type": "object",
   "properties": {
      "optimize_data_file": {
         "default": false,
         "title": "Optimize Data File",
         "type": "boolean"
      },
      "stateful": {
         "default": false,
         "title": "Stateful",
         "type": "boolean"
      },
      "error_retry_attempts": {
         "default": 2,
         "title": "Error Retry Attempts",
         "type": "integer"
      },
      "code_block_delimiters": {
         "default": [
            [
               "```tool_code\n",
               "\n```"
            ],
            [
               "```python\n",
               "\n```"
            ]
         ],
         "items": {
            "maxItems": 2,
            "minItems": 2,
            "prefixItems": [
               {
                  "type": "string"
               },
               {
                  "type": "string"
               }
            ],
            "type": "array"
         },
         "title": "Code Block Delimiters",
         "type": "array"
      },
      "execution_result_delimiters": {
         "default": [
            "```tool_output\n",
            "\n```"
         ],
         "maxItems": 2,
         "minItems": 2,
         "prefixItems": [
            {
               "type": "string"
            },
            {
               "type": "string"
            }
         ],
         "title": "Execution Result Delimiters",
         "type": "array"
      }
   }
}
```


**Fields:**
code_block_delimiters (List[tuple[str, str]])

error_retry_attempts (int)

execution_result_delimiters (tuple[str, str])

optimize_data_file (bool)

stateful (bool)


***field*code_block_delimiters*:**List**[**tuple**[**str**,**str**]**]**=**[('```tool_code\n',**'\n```'),**('```python\n',**'\n```')]*¶**
The list of the enclosing delimiters to identify the code blocks.

For example, the delimiter (’`python\n', '\n`’) can be used to identify code blocks with the following format:


```
```python
print("hello")
```
```


***field*error_retry_attempts*:**int**=**2*¶**
The number of attempts to retry on consecutive code execution errors. Default to 2.


***field*execution_result_delimiters*:**tuple**[**str**,**str**]**=**('```tool_output\n',**'\n```')*¶**
The delimiters to format the code execution result.


***field*optimize_data_file*:**bool**=**False*¶**
If true, extract and process data files from the model request and attach them to the code executor.

Supported data file MimeTypes are [text/csv]. Default to False.


***field*stateful*:**bool**=**False*¶**
Whether the code executor is stateful. Default to False.


***abstractmethod*execute_code(*invocation_context*,*code_execution_input*)¶**
Executes code and return the code execution result.


**Return type:**
CodeExecutionResult


**Parameters:**
**invocation_context**– The invocation context of the code execution.

**code_execution_input**– The code execution input.


**Returns:**
The code execution result.


***pydantic**model*google.adk.code_executors.BuiltInCodeExecutor¶**
Bases:[BaseCodeExecutor

A code executor that uses the Model’s built-in code executor.

Currently only supports Gemini 2.0+ models, but will be expanded to other models.


```
Show JSON schema{
   "title": "BuiltInCodeExecutor",
   "description": "A code executor that uses the Model's built-in code executor.\n\nCurrently only supports Gemini 2.0+ models, but will be expanded to\nother models.",
   "type": "object",
   "properties": {
      "optimize_data_file": {
         "default": false,
         "title": "Optimize Data File",
         "type": "boolean"
      },
      "stateful": {
         "default": false,
         "title": "Stateful",
         "type": "boolean"
      },
      "error_retry_attempts": {
         "default": 2,
         "title": "Error Retry Attempts",
         "type": "integer"
      },
      "code_block_delimiters": {
         "default": [
            [
               "```tool_code\n",
               "\n```"
            ],
            [
               "```python\n",
               "\n```"
            ]
         ],
         "items": {
            "maxItems": 2,
            "minItems": 2,
            "prefixItems": [
               {
                  "type": "string"
               },
               {
                  "type": "string"
               }
            ],
            "type": "array"
         },
         "title": "Code Block Delimiters",
         "type": "array"
      },
      "execution_result_delimiters": {
         "default": [
            "```tool_output\n",
            "\n```"
         ],
         "maxItems": 2,
         "minItems": 2,
         "prefixItems": [
            {
               "type": "string"
            },
            {
               "type": "string"
            }
         ],
         "title": "Execution Result Delimiters",
         "type": "array"
      }
   }
}
```


**Fields:**

**execute_code(*invocation_context*,*code_execution_input*)¶**
Executes code and return the code execution result.


**Return type:**
CodeExecutionResult


**Parameters:**
**invocation_context**– The invocation context of the code execution.

**code_execution_input**– The code execution input.


**Returns:**
The code execution result.


**process_llm_request(*llm_request*)¶**
Pre-process the LLM request for Gemini 2.0+ models to use the code execution tool.


**Return type:**
None


***class*google.adk.code_executors.CodeExecutorContext(*session_state*)¶**
Bases:object

The persistent context used to configure the code executor.

Initializes the code executor context.


**Parameters:**
**session_state**– The session state to get the code executor context from.


**add_input_files(*input_files*)¶**
Adds the input files to the code executor context.


**Parameters:**
**input_files**– The input files to add to the code executor context.


**add_processed_file_names(*file_names*)¶**
Adds the processed file name to the session state.


**Parameters:**
**file_names**– The processed file names to add to the session state.


**clear_input_files()¶**
Removes the input files and processed file names to the code executor context.


**get_error_count(*invocation_id*)¶**
Gets the error count from the session state.


**Return type:**
int


**Parameters:**
**invocation_id**– The invocation ID to get the error count for.


**Returns:**
The error count for the given invocation ID.


**get_execution_id()¶**
Gets the session ID for the code executor.


**Return type:**
Optional[str]


**Returns:**
The session ID for the code executor context.


**get_input_files()¶**
Gets the code executor input file names from the session state.


**Return type:**
list[File]


**Returns:**
A list of input files in the code executor context.


**get_processed_file_names()¶**
Gets the processed file names from the session state.


**Return type:**
list[str]


**Returns:**
A list of processed file names in the code executor context.


**get_state_delta()¶**
Gets the state delta to update in the persistent session state.


**Return type:**
dict[str,Any]


**Returns:**
The state delta to update in the persistent session state.


**increment_error_count(*invocation_id*)¶**
Increments the error count from the session state.


**Parameters:**
**invocation_id**– The invocation ID to increment the error count for.


**reset_error_count(*invocation_id*)¶**
Resets the error count from the session state.


**Parameters:**
**invocation_id**– The invocation ID to reset the error count for.


**set_execution_id(*session_id*)¶**
Sets the session ID for the code executor.


**Parameters:**
**session_id**– The session ID for the code executor.


**update_code_execution_result(*invocation_id*,*code*,*result_stdout*,*result_stderr*)¶**
Updates the code execution result.


**Parameters:**
**invocation_id**– The invocation ID to update the code execution result for.

**code**– The code to execute.

**result_stdout**– The standard output of the code execution.

**result_stderr**– The standard error of the code execution.


***pydantic**model*google.adk.code_executors.UnsafeLocalCodeExecutor¶**
Bases:[BaseCodeExecutor

A code executor that unsafely execute code in the current local context.

Initializes the UnsafeLocalCodeExecutor.


```
Show JSON schema{
   "title": "UnsafeLocalCodeExecutor",
   "description": "A code executor that unsafely execute code in the current local context.",
   "type": "object",
   "properties": {
      "optimize_data_file": {
         "default": false,
         "title": "Optimize Data File",
         "type": "boolean"
      },
      "stateful": {
         "default": false,
         "title": "Stateful",
         "type": "boolean"
      },
      "error_retry_attempts": {
         "default": 2,
         "title": "Error Retry Attempts",
         "type": "integer"
      },
      "code_block_delimiters": {
         "default": [
            [
               "```tool_code\n",
               "\n```"
            ],
            [
               "```python\n",
               "\n```"
            ]
         ],
         "items": {
            "maxItems": 2,
            "minItems": 2,
            "prefixItems": [
               {
                  "type": "string"
               },
               {
                  "type": "string"
               }
            ],
            "type": "array"
         },
         "title": "Code Block Delimiters",
         "type": "array"
      },
      "execution_result_delimiters": {
         "default": [
            "```tool_output\n",
            "\n```"
         ],
         "maxItems": 2,
         "minItems": 2,
         "prefixItems": [
            {
               "type": "string"
            },
            {
               "type": "string"
            }
         ],
         "title": "Execution Result Delimiters",
         "type": "array"
      }
   }
}
```


**Fields:**
optimize_data_file (bool)

stateful (bool)


***field*optimize_data_file*:**bool**=**False*¶**
If true, extract and process data files from the model request and attach them to the code executor.

Supported data file MimeTypes are [text/csv]. Default to False.


***field*stateful*:**bool**=**False*¶**
Whether the code executor is stateful. Default to False.


**execute_code(*invocation_context*,*code_execution_input*)¶**
Executes code and return the code execution result.


**Return type:**
CodeExecutionResult


**Parameters:**
**invocation_context**– The invocation context of the code execution.

**code_execution_input**– The code execution input.


**Returns:**
The code execution result.


# google.adk.errors module¶

# google.adk.evaluation module¶

***class*google.adk.evaluation.AgentEvaluator¶**
Bases:object

An evaluator for Agents, mainly intended for helping with test cases.


***async**static*evaluate(*agent_module*,*eval_dataset_file_path_or_dir*,*num_runs**=**2*,*agent_name**=**None*,*initial_session_file**=**None*,*print_detailed_results**=**True*)¶**
Evaluates an Agent given eval data.


**Parameters:**
**agent_module**– The path to python module that contains the definition of the agent. There is convention in place here, where the code is going to look for ‘root_agent’ or ‘get_agent_async’ in the loaded module.

**eval_dataset_file_path_or_dir**– The eval data set. This can be either a string representing full path to the file containing eval dataset, or a directory that is recursively explored for all files that have a.test.jsonsuffix.

**num_runs**– Number of times all entries in the eval dataset should be assessed.

**agent_name**– The name of the agent.

**initial_session_file**– File that contains initial session state that is needed by all the evals in the eval dataset.

**print_detailed_results**– Whether to print detailed results for each metric evaluation.


***async**static*evaluate_eval_set(*agent_module*,*eval_set*,*criteria**=**None*,*eval_config**=**None*,*num_runs**=**2*,*agent_name**=**None*,*print_detailed_results**=**True*)¶**
Evaluates an agent using the given EvalSet.


**Parameters:**
**agent_module**– The path to python module that contains the definition of the agent. There is convention in place here, where the code is going to look for ‘root_agent’ orget_agent_asyncin the loaded module.

**eval_set**– The eval set.

**criteria**– Evaluation criteria, a dictionary of metric names to their respective thresholds. This field is deprecated.

**eval_config**– The evaluation config.

**num_runs**– Number of times all entries in the eval dataset should be assessed.

**agent_name**– The name of the agent, if trying to evaluate something other than root agent. If left empty or none, then root agent is evaluated.

**print_detailed_results**– Whether to print detailed results for each metric evaluation.


***static*find_config_for_test_file(*test_file*)¶**
Find the test_config.json file in the same folder as the test file.


**Return type:**
EvalConfig


***static*migrate_eval_data_to_new_schema(*old_eval_data_file*,*new_eval_data_file*,*initial_session_file**=**None*)¶**
A utility for migrating eval data to new schema backed by EvalSet.