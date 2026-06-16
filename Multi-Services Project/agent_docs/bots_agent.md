# name
bots_agent

# description
Specialized agent for security analysis and bot detection. Connects to a Bot Detection MCP server that maintains a database of IPs classified as bots — either permanent bans or temporary time-window blocks. It is the exclusive agent for any query related to banned IPs, bot traffic analysis, or IP reputation checks within the system.

This agent is read-only and completely independent from DSpace, MinIO, GitHub, and OpenAlex. It cannot modify the bot database, only consult and report on IP statuses.

# inputs
- task: string — Description of the security query to execute (e.g., "List all permanently banned IPs", "Check if IP 1.2.3.4 is a bot", "Get currently active temporary windows").

# outputs
- result: string — Query result including IP status (permanent bot, active temporary bot, clean), ban reasons, active timeframes, or paginated/full lists of banned IPs.
