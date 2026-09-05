#!/bin/bash
# Build script for Mealie MCP Server

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="mealie-mcp"
IMAGE_TAG="${1:-latest}"

# Defaults to the host architecture, which is what you want for a local run.
# Override to cross-build, e.g. PLATFORM=linux/arm64 ./build.sh
PLATFORM="${PLATFORM:-}"

echo "Building Mealie MCP Server..."
echo "Image: ${IMAGE_NAME}:${IMAGE_TAG}"

# Build the Docker image
if [ -n "${PLATFORM}" ]; then
  echo "Platform: ${PLATFORM}"
  # A multi-platform build cannot load into the local daemon, so push or
  # export those instead of leaving the caller with nothing.
  if [ "${PLATFORM}" != "${PLATFORM#*,}" ]; then
    echo "Note: multi-platform builds cannot be loaded into the local Docker" \
         "daemon; add --push or --output to keep the result." >&2
    docker buildx build --platform "${PLATFORM}" \
      -t "${IMAGE_NAME}:${IMAGE_TAG}" "${SCRIPT_DIR}"
  else
    docker buildx build --platform "${PLATFORM}" --load \
      -t "${IMAGE_NAME}:${IMAGE_TAG}" "${SCRIPT_DIR}"
  fi
else
  docker build -t "${IMAGE_NAME}:${IMAGE_TAG}" "${SCRIPT_DIR}"
fi

echo ""
echo "Build complete!"
echo ""
echo "To run the MCP server:"
echo "  docker run -i --rm \\"
echo "    -e MEALIE_URL=https://your-mealie-instance.com \\"
echo "    -e MEALIE_API_TOKEN=your-api-token \\"
echo "    ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""
echo "To use with Claude Code, add to your MCP configuration:"
echo "  {"
echo "    \"mcpServers\": {"
echo "      \"mealie\": {"
echo "        \"command\": \"docker\","
echo "        \"args\": [\"run\", \"-i\", \"--rm\","
echo "          \"-e\", \"MEALIE_URL=https://your-mealie-instance.com\","
echo "          \"-e\", \"MEALIE_API_TOKEN=your-api-token\","
echo "          \"${IMAGE_NAME}:${IMAGE_TAG}\"]"
echo "      }"
echo "    }"
echo "  }"
