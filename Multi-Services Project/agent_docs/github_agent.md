# name
github_agent

# description
Agent specialized in GitHub remote operations and local filesystem management. Acts as the "file preparation agent" in multi-agent pipelines: when other agents (like `minio_agent`) need a file to be available in `DOWNLOADS_DIR`, the `github_agent` is responsible for that step. It can read, create, edit, move, and list files on the local host filesystem, as well as interact with GitHub repositories (list repos, read/write remote files, create issues and PRs).

This agent NEVER interacts with MinIO, DSpace, or Bots directly. In pipeline tasks, its final output is a confirmation that the file is ready in `DOWNLOADS_DIR`.

# inputs
- task: string — Filesystem or GitHub operation (e.g., "Copy file report.csv to DOWNLOADS_DIR", "List files in /data/", "Read content of README.md", "Create a file at path X with content Y", "Search for file named Z").

# outputs
- result: string — Confirmation of operation, file contents, directory listings, or error details. When copying to DOWNLOADS_DIR, always responds: "File [name] has been successfully copied to the shared downloads directory."
