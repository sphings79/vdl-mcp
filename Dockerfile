# vdl-mcp — MCP server for vdl.
# Runs over stdio; launch from your MCP client with:
#   docker run -i --rm -e VDL_URL -e VDL_TOKEN ghcr.io/sphings79/vdl-mcp:latest
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .

ENTRYPOINT ["vdl-mcp"]
