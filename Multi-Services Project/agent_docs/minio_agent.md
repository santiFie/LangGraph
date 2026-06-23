# name
minio_agent

# description
Agent that manages object storage in MinIO (S3-compatible). Operates through a Docker-based MCP server with a critical isolation constraint: its container only mounts `DOWNLOADS_DIR` as `/Downloads` internally. The agent can ONLY read or write files already inside `/Downloads`. Any file to be uploaded MUST first be placed in `DOWNLOADS_DIR` by the `filesystem_agent` in a prior plan step, otherwise the operation will fail.

Use this agent for listing buckets and objects, uploading files from `/Downloads/`, downloading objects to `/Downloads/`, deleting objects, and creating new buckets.

# inputs
- task: string — MinIO storage operation (e.g., "Upload /Downloads/report.csv to bucket analytics", "List all buckets", "Download object X from bucket Y to /Downloads/", "Create bucket named Z"). Files MUST already be in /Downloads/ before upload.

# outputs
- result: string — Operation confirmation (e.g., "Successfully uploaded report.csv to bucket analytics"), object metadata, bucket/object listings, or exact error messages on failure.
