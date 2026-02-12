# google.adk.tools.bigquery

## Module Overview

The `BigQueryToolset` provides integration with Google BigQuery through seven specialized tools for data analysis and SQL execution within ADK agents.

**Module:** `google.adk.tools.bigquery`
**Primary Class:** `BigQueryToolset`
**Configuration Class:** `BigQueryCredentialsConfig`
**Tool Config Class:** `BigQueryToolConfig`
**Availability:** Python ADK v1.1.0+

## Available Tools

The `BigQueryToolset` includes seven specialized tools:

1. **list_dataset_ids** — Retrieves dataset identifiers from a GCP project
2. **get_dataset_info** — Obtains metadata regarding a specific dataset
3. **list_table_ids** — Fetches table identifiers within a dataset
4. **get_table_info** — Retrieves metadata about a particular table
5. **execute_sql** — Runs SQL queries and retrieves results
6. **forecast** — Performs time series forecasting using `AI.FORECAST`
7. **ask_data_insights** — Answers questions about table data through natural language

## Python API

### Import

```python
from google.adk.tools.bigquery import BigQueryToolset, BigQueryCredentialsConfig
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode
```

### BigQueryCredentialsConfig Class

Handles authentication for BigQuery operations.

#### Constructor

```python
BigQueryCredentialsConfig(credentials=...)
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `credentials` | Google credentials object | Yes | Authentication credentials for BigQuery API |

#### Methods

##### `model_post_init()`

Initialization hook for post-processing the model after instantiation.

**Note:** This method is called automatically by Pydantic after model initialization.

### BigQueryToolConfig Class

Controls tool behavior and access permissions.

#### Constructor

```python
BigQueryToolConfig(write_mode: WriteMode)
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `write_mode` | `WriteMode` | Yes | Controls write access to BigQuery resources |

#### WriteMode Enum

- **`WriteMode.BLOCKED`**: Prevents write operations on BigQuery resources (read-only mode)
- **`WriteMode.ALLOWED`**: Allows write operations (use with caution)

### BigQueryToolset Class

**Module Path:** `google.adk.tools.bigquery.BigQueryToolset`

#### Constructor

```python
BigQueryToolset(
    credentials_config: BigQueryCredentialsConfig,
    bigquery_tool_config: BigQueryToolConfig
)
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `credentials_config` | `BigQueryCredentialsConfig` | Yes | Authentication configuration |
| `bigquery_tool_config` | `BigQueryToolConfig` | No | Tool behavior configuration |

#### Methods

##### `close()`

Closes the toolset and releases any associated resources.

```python
await bigquery_toolset.close()
```

**Returns:** `None`

**Note:** Should be called when the toolset is no longer needed to properly clean up connections.

##### `get_tools()`

Retrieves all available BigQuery tools from the toolset.

```python
tools = bigquery_toolset.get_tools()
```

**Returns:** List of tool objects that can be passed to an agent's `tools` parameter.

## Usage Example

### Basic Setup

```python
import asyncio
import google.auth
from google.adk.agents import LlmAgent
from google.adk.runners import InMemorySessionService
from google.adk.tools.bigquery import BigQueryCredentialsConfig, BigQueryToolset
from google.adk.tools.bigquery.config import BigQueryToolConfig, WriteMode

# Obtain application default credentials
application_default_credentials, _ = google.auth.default()

# Configure credentials
credentials_config = BigQueryCredentialsConfig(
    credentials=application_default_credentials
)

# Configure tool behavior (read-only mode)
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)

# Create the toolset
bigquery_toolset = BigQueryToolset(
    credentials_config=credentials_config,
    bigquery_tool_config=tool_config
)

# Create agent with BigQuery tools
bigquery_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="bigquery_agent",
    tools=[bigquery_toolset],
    instruction="You are a data analyst that can query and analyze BigQuery datasets."
)
```

### Complete Example with Session

```python
import asyncio
from google.adk.agents import LlmAgent
from google.adk.runners import InMemorySessionService, Runner

async def main():
    # Setup credentials
    application_default_credentials, _ = google.auth.default()
    credentials_config = BigQueryCredentialsConfig(
        credentials=application_default_credentials
    )

    # Configure read-only access
    tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)

    # Create toolset
    bigquery_toolset = BigQueryToolset(
        credentials_config=credentials_config,
        bigquery_tool_config=tool_config
    )

    # Create agent
    agent = LlmAgent(
        model="gemini-2.0-flash",
        name="bigquery_analyst",
        tools=[bigquery_toolset],
        instruction="Help analyze BigQuery data. Use available tools to query tables."
    )

    # Create session and runner
    session_service = InMemorySessionService()
    runner = Runner(agent=agent, session_service=session_service)

    # Execute query
    result = await runner.run("What datasets are available in the project?")
    print(result)

    # Clean up
    await bigquery_toolset.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration Requirements

### Prerequisites

1. **Google Cloud Project:** Active GCP project with BigQuery API enabled
2. **Authentication:** Application default credentials or service account credentials
3. **Permissions:** BigQuery IAM permissions for the service account:
   - `bigquery.datasets.get`
   - `bigquery.tables.get`
   - `bigquery.tables.list`
   - `bigquery.jobs.create` (for queries)
   - Additional permissions for write operations if enabled

### Authentication Methods

#### Application Default Credentials (Recommended)

```python
import google.auth

credentials, project = google.auth.default()
credentials_config = BigQueryCredentialsConfig(credentials=credentials)
```

#### Service Account Key File

```python
from google.oauth2 import service_account

credentials = service_account.Credentials.from_service_account_file(
    'path/to/service-account-key.json'
)
credentials_config = BigQueryCredentialsConfig(credentials=credentials)
```

## Tool Capabilities

### 1. list_dataset_ids

Lists all dataset IDs in the configured GCP project.

**Agent Usage:** "What datasets are available?"

### 2. get_dataset_info

Retrieves metadata for a specific dataset including:
- Dataset description
- Creation time
- Last modified time
- Location
- Labels

**Agent Usage:** "Tell me about the 'analytics' dataset"

### 3. list_table_ids

Lists all table IDs within a specified dataset.

**Agent Usage:** "What tables are in the 'sales' dataset?"

### 4. get_table_info

Retrieves table schema and metadata including:
- Column names and types
- Table description
- Row count
- Size in bytes
- Last modified time

**Agent Usage:** "Describe the 'customers' table schema"

### 5. execute_sql

Executes SQL queries and returns results.

**Agent Usage:** "Run this query: SELECT * FROM `project.dataset.table` LIMIT 10"

**Security Note:** With `WriteMode.BLOCKED`, only SELECT queries are allowed.

### 6. forecast

Performs time series forecasting using BigQuery ML's `AI.FORECAST` function.

**Agent Usage:** "Forecast sales for the next quarter based on historical data"

### 7. ask_data_insights

Natural language interface for querying table data. The LLM generates appropriate SQL based on the question.

**Agent Usage:** "What are the top 5 customers by revenue?"

## Security Best Practices

### Read-Only Mode

For most use cases, use `WriteMode.BLOCKED` to prevent accidental data modifications:

```python
tool_config = BigQueryToolConfig(write_mode=WriteMode.BLOCKED)
```

### Write Mode (Use with Caution)

Only enable write mode when absolutely necessary:

```python
tool_config = BigQueryToolConfig(write_mode=WriteMode.ALLOWED)
```

**Warning:** Write mode allows the agent to execute INSERT, UPDATE, DELETE, and DDL operations. Use with extreme caution and appropriate access controls.

### Least Privilege Principle

Grant only the minimum required BigQuery permissions to the service account:

```bash
# Read-only permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
    --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:SERVICE_ACCOUNT_EMAIL" \
    --role="roles/bigquery.jobUser"
```

## Use Cases

- **Data Analysis:** Query and analyze large datasets
- **Reporting:** Generate reports from BigQuery data
- **Business Intelligence:** Answer questions about business metrics
- **Forecasting:** Predict future trends using historical data
- **Schema Discovery:** Explore available datasets and tables
- **Data Quality:** Validate and check data integrity

## Limitations

- **Query Costs:** BigQuery charges for data processed by queries
- **Query Timeouts:** Long-running queries may timeout
- **Result Size:** Large result sets may need pagination
- **Write Operations:** Require explicit enablement via `WriteMode.ALLOWED`
- **Concurrent Queries:** Subject to BigQuery quota limits

## Best Practices

1. **Use Read-Only Mode:** Default to `WriteMode.BLOCKED` for safety
2. **Clear Instructions:** Provide specific instructions about available datasets and expected queries
3. **Resource Cleanup:** Always call `close()` when done to release connections
4. **Error Handling:** Implement proper error handling for query failures
5. **Cost Awareness:** Monitor BigQuery costs, especially for large queries
6. **Query Optimization:** Encourage the agent to use efficient queries with appropriate WHERE clauses

## Related Tools

- **BigQuery Agent Analytics:** Observability and analytics for BigQuery agents
- **Bigtable Tools:** For NoSQL data access
- **Spanner Tools:** For distributed SQL databases

## References

- [BigQuery Integration](https://google.github.io/adk-docs/integrations/bigquery/)
- [BigQuery Agent Analytics](https://google.github.io/adk-docs/tools/google-cloud/bigquery-agent-analytics/)
- [Google Cloud Tools](https://google.github.io/adk-docs/tools/google-cloud/)
- [Python API Reference](https://google.github.io/adk-docs/api-reference/python/)
