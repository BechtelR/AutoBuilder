# google.adk.sessions module¶

Source: https://google.github.io/adk-docs/api-reference/python/google-adk.html#module-google.adk.sessions

***class*google.adk.sessions.BaseSessionService¶**
Bases:ABC

Base class for session services.

The service provides a set of methods for managing sessions and events.


***async*append_event(*session*,*event*)¶**
Appends an event to a session object.


**Return type:**
[Event


***abstractmethod**async*create_session(***,*app_name*,*user_id*,*state**=**None*,*session_id**=**None*)¶**
Creates a new session.


**Return type:**
[Session


**Parameters:**
**app_name**– the name of the app.

**user_id**– the id of the user.

**state**– the initial state of the session.

**session_id**– the client-provided id of the session. If not provided, a generated ID will be used.


**Returns:**
The newly created session instance.


**Return type:**
session


***abstractmethod**async*delete_session(***,*app_name*,*user_id*,*session_id*)¶**
Deletes a session.


**Return type:**
None


***abstractmethod**async*get_session(***,*app_name*,*user_id*,*session_id*,*config**=**None*)¶**
Gets a session.


**Return type:**
Optional[[Session]


***abstractmethod**async*list_sessions(***,*app_name*,*user_id**=**None*)¶**
Lists all the sessions for a user.


**Return type:**
ListSessionsResponse


**Parameters:**
**app_name**– The name of the app.

**user_id**– The ID of the user. If not provided, lists all sessions for all users.


**Returns:**
A ListSessionsResponse containing the sessions.


***class*google.adk.sessions.InMemorySessionService¶**
Bases:[BaseSessionService

An in-memory implementation of the session service.

It is not suitable for multi-threaded production environments. Use it for testing and development only.


***async*append_event(*session*,*event*)¶**
Appends an event to a session object.


**Return type:**
[Event


***async*create_session(***,*app_name*,*user_id*,*state**=**None*,*session_id**=**None*)¶**
Creates a new session.


**Return type:**
[Session


**Parameters:**
**app_name**– the name of the app.

**user_id**– the id of the user.

**state**– the initial state of the session.

**session_id**– the client-provided id of the session. If not provided, a generated ID will be used.


**Returns:**
The newly created session instance.


**Return type:**
session


**create_session_sync(***,*app_name*,*user_id*,*state**=**None*,*session_id**=**None*)¶**

**Return type:**
[Session


***async*delete_session(***,*app_name*,*user_id*,*session_id*)¶**
Deletes a session.


**Return type:**
None


**delete_session_sync(***,*app_name*,*user_id*,*session_id*)¶**

**Return type:**
None


***async*get_session(***,*app_name*,*user_id*,*session_id*,*config**=**None*)¶**
Gets a session.


**Return type:**
Optional[[Session]


**get_session_sync(***,*app_name*,*user_id*,*session_id*,*config**=**None*)¶**

**Return type:**
Optional[[Session]


***async*list_sessions(***,*app_name*,*user_id**=**None*)¶**
Lists all the sessions for a user.


**Return type:**
ListSessionsResponse


**Parameters:**
**app_name**– The name of the app.

**user_id**– The ID of the user. If not provided, lists all sessions for all users.


**Returns:**
A ListSessionsResponse containing the sessions.


**list_sessions_sync(***,*app_name*,*user_id**=**None*)¶**

**Return type:**
ListSessionsResponse


***pydantic**model*google.adk.sessions.Session¶**
Bases:BaseModel

Represents a series of interactions between a user and agents.