# Authentication in Agent Development Kit

## Overview

The ADK provides a comprehensive system for handling authentication across tools requiring access to protected resources. The framework supports multiple authentication methods aligned with OpenAPI 3.0 standards.

## Supported Credential Types

The system recognizes five initial credential categories:

- **API_KEY**: Simple key/value authentication requiring no exchange
- **HTTP**: Basic Auth or Bearer tokens (Bearer tokens need no exchange)
- **OAUTH2**: Standard OAuth 2.0 flows requiring configuration and user interaction
- **OPEN_ID_CONNECT**: OpenID Connect authentication, similar to OAuth2
- **SERVICE_ACCOUNT**: Google Cloud Service Account credentials exchanged for Bearer tokens

## Core Components

Two primary objects manage authentication:

1. **AuthScheme**: Defines how an API expects credentials (e.g., API Key in header, OAuth Bearer token)
2. **AuthCredential**: Holds initial information needed to start authentication (client ID/Secret, API key values)

## Two Implementation Journeys

### Journey 1: Using Pre-Built Authenticated Tools

This path focuses on configuring existing tools like RestApiTool, OpenAPIToolset, or GoogleApiToolSet with authentication, then handling interactive OAuth flows on the client side.

**Configuration Steps:**
- Pass `auth_scheme` and `auth_credential` during toolset initialization
- Use helper functions like `token_to_scheme_credential()` for API keys or `service_account_dict_to_scheme_credential()` for service accounts

**Client-Side OAuth Flow:**
1. Detect authentication requests by identifying `adk_request_credential` function calls
2. Extract the authorization URL from the AuthConfig
3. Append your pre-registered redirect_uri to the authorization URL
4. Direct users to complete login and authorization
5. Capture the callback URL containing the authorization code
6. Send the callback URL back via a FunctionResponse with name `adk_request_credential`
7. ADK handles token exchange and retries the original tool call

### Journey 2: Custom FunctionTools with Built-in Authentication

This approach embeds authentication logic directly within your tool function using ToolContext.

**Implementation Pattern:**
1. Check for cached, valid credentials in `tool_context.state`
2. Refresh expired tokens using google.auth.transport.requests
3. Call `tool_context.get_auth_response()` to check for client-provided auth responses
4. If credentials unavailable, call `tool_context.request_credential()` to initiate the flow
5. Cache obtained tokens in session state
6. Execute the authenticated API call
7. Return results with status indicators

## Security Considerations

The documentation emphasizes that storing sensitive credentials (particularly refresh tokens) in session state poses risks:

- **InMemorySessionService**: Suitable only for testing; data lost on process end
- **Database Storage**: "Strongly consider encrypting" token data before persistence
- **Recommended Approach**: Use dedicated secret managers (Google Cloud Secret Manager, HashiCorp Vault) storing only short-lived access tokens or secure references

## Resume Feature Integration

When using the Resume feature, authentication responses must include the original Invocation ID to ensure responses correlate with their generating invocations.

## Key Helper Functions

Client applications typically need:
- `get_auth_request_function_call()`: Identifies auth request events
- `get_auth_config()`: Extracts AuthConfig from function arguments
- Callback URL capture mechanism for OAuth redirects

The framework automatically handles token exchange after receiving authorization responses, eliminating manual token management complexity for pre-built tools.

---

*Source: https://google.github.io/adk-docs/tools-custom/authentication/*
*Downloaded: 2026-02-11*
