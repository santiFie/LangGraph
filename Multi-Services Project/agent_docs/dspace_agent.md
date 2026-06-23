# name
dspace_agent

# description
Agent that administrates SEDICI, the institutional repository based on DSpace 7+. Connects via MCP to the DSpace REST API to search, create, and update communities, collections, items, and manage bitstreams. Handles metadata export to CSV (asynchronous, result stored on DSpace server) and import from CSV. All objects are identified by UUIDs; if the user provides a name, the agent resolves it to UUID automatically.

A critical constraint: exported CSV files reside on the internal DSpace server filesystem. To share them with other agents (e.g., `minio_agent`), the `filesystem_agent` must first copy the file to the shared `DOWNLOADS_DIR`.

# inputs
- task: string — DSpace operation to perform (e.g., "Export collection UUID xxxx to CSV", "List items in collection named X", "Search for item named Y", "Create community with metadata Z").

# outputs
- result: string — Operation result: UUIDs of found objects, item metadata, export file path on DSpace server, import status, or structured lists of DSpace communities/collections/items.
