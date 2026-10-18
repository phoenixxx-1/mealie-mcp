# Mealie MCP Server

[![Build and Push Docker Image](https://github.com/mdlopresti/mealie-mcp/actions/workflows/docker.yml/badge.svg)](https://github.com/mdlopresti/mealie-mcp/actions/workflows/docker.yml)
[![Test](https://github.com/mdlopresti/mealie-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/mdlopresti/mealie-mcp/actions/workflows/test.yml)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that enables AI assistants to interact with [Mealie](https://mealie.io/) for recipe management, meal planning, and shopping lists.

## Features

### Tools (126 total)

**Recipes**
- `mealie_recipes_add_favorite` - Add a recipe to the current user's favorites
- `mealie_recipes_bulk_categorize` - Add categories to multiple recipes at once
- `mealie_recipes_bulk_delete` - Delete multiple recipes at once
- `mealie_recipes_bulk_export` - Export multiple recipes at once
- `mealie_recipes_bulk_tag` - Add tags to multiple recipes at once
- `mealie_recipes_bulk_update_settings` - Update settings for multiple recipes at once
- `mealie_recipes_create` - Create a new recipe in Mealie
- `mealie_recipes_create_from_image` - Create a recipe from an image using AI (experimental)
- `mealie_recipes_create_from_url` - Import a recipe from a URL by scraping it
- `mealie_recipes_create_from_urls_bulk` - Import multiple recipes from URLs at once
- `mealie_recipes_delete` - Delete a recipe from Mealie
- `mealie_recipes_duplicate` - Duplicate an existing recipe
- `mealie_recipes_get` - Get complete details for a specific recipe
- `mealie_recipes_get_favorites` - Get all favorite recipes for the current user
- `mealie_recipes_get_rating` - Get rating for a specific recipe
- `mealie_recipes_get_ratings` - Get all ratings for the current user
- `mealie_recipes_get_suggestions` - Get recipe suggestions based on preferences and history
- `mealie_recipes_image_upload` - Replace a recipe's main image from a file path (`image_path`, see [Uploading images from files](#uploading-images-from-files)) or base64 (JPEG, PNG, WebP, HEIC or AVIF, up to 10 MB)
- `mealie_recipes_list` - List all recipes with pagination
- `mealie_recipes_remove_favorite` - Remove a recipe from the current user's favorites
- `mealie_recipes_search` - Search for recipes in Mealie
- `mealie_recipes_set_rating` - Set a rating (1-5 stars) for a recipe
- `mealie_recipes_shared_access` - Access a shared recipe by token (public endpoint)
- `mealie_recipes_shared_create` - Create a share link for a recipe
- `mealie_recipes_shared_delete` - Delete a share link
- `mealie_recipes_shared_get` - Get details of a shared recipe by ID
- `mealie_recipes_shared_list` - List all shared recipe links
- `mealie_recipes_update` - Update an existing recipe in Mealie (does not change the image; use the image upload tools)
- `mealie_recipes_update_last_made` - Update the last made timestamp for a recipe
- `mealie_recipes_update_structured_ingredients` - Update a recipe with structured ingredients from parser output (set `create_missing_foods=False` to refuse unmatched foods instead of creating duplicates)
- `mealie_recipes_upload_image_from_url` - Replace a recipe's main image with one downloaded from a URL (non-images are rejected)

**Recipe Actions (automation)**
- `mealie_recipe_actions_create` - Create a new recipe action
- `mealie_recipe_actions_delete` - Delete a recipe action
- `mealie_recipe_actions_get` - Get a specific recipe action by ID
- `mealie_recipe_actions_list` - List all recipe actions with pagination
- `mealie_recipe_actions_trigger` - Trigger a recipe action for a specific recipe
- `mealie_recipe_actions_update` - Update an existing recipe action

**Recipe Comments**
- `mealie_comments_create` - Create a comment on a recipe
- `mealie_comments_delete` - Delete a comment
- `mealie_comments_get` - Get a comment by ID
- `mealie_comments_get_recipe` - Get all comments for a recipe
- `mealie_comments_update` - Update a comment

**Recipe Timeline**
- `mealie_timeline_create` - Create a new timeline event for a recipe
- `mealie_timeline_delete` - Delete a timeline event
- `mealie_timeline_get` - Get a specific timeline event by ID
- `mealie_timeline_image_upload` - Attach a photo to a timeline event from a file path or base64; does not change the recipe's main image
- `mealie_timeline_list` - List all recipe timeline events with pagination
- `mealie_timeline_update` - Update an existing timeline event
- `mealie_timeline_update_image` - Attach an image downloaded from a URL to a timeline event; does not change the recipe's main image

**Meal Planning**
- `mealie_mealplans_create` - Create a new meal plan entry
- `mealie_mealplans_delete` - Delete a meal plan entry
- `mealie_mealplans_delete_range` - Delete all meal plans in a date range
- `mealie_mealplans_get` - Get a specific meal plan entry by ID
- `mealie_mealplans_get_date` - Get all meal plan entries for a specific date
- `mealie_mealplans_list` - List meal plans for a date range
- `mealie_mealplans_random` - Get a random meal suggestion from available recipes
- `mealie_mealplans_search` - Search meal plans by recipe name, title, or text content
- `mealie_mealplans_today` - Get today's meal plan entries
- `mealie_mealplans_update` - Update an existing meal plan entry
- `mealie_mealplans_update_batch` - Update multiple meal plans at once

**Meal Plan Rules**
- `mealie_mealplan_rules_create` - Create a new meal plan rule
- `mealie_mealplan_rules_delete` - Delete a meal plan rule
- `mealie_mealplan_rules_get` - Get a specific meal plan rule by ID
- `mealie_mealplan_rules_list` - List all meal plan rules
- `mealie_mealplan_rules_update` - Update an existing meal plan rule

**Shopping Lists**
- `mealie_shopping_add_recipe` - Add all ingredients from a recipe to a shopping list
- `mealie_shopping_clear_checked` - Remove all checked items from a shopping list
- `mealie_shopping_delete_recipe_from_list` - Remove recipe ingredients from a shopping list
- `mealie_shopping_generate_from_mealplan` - Generate a shopping list from meal plan entries
- `mealie_shopping_items_add` - Add an item to a shopping list
- `mealie_shopping_items_add_bulk` - Add multiple items to a shopping list at once
- `mealie_shopping_items_check` - Mark a shopping list item as checked or unchecked
- `mealie_shopping_items_delete` - Remove an item from a shopping list
- `mealie_shopping_lists_create` - Create a new shopping list
- `mealie_shopping_lists_delete` - Delete a shopping list
- `mealie_shopping_lists_get` - Get a specific shopping list with all items
- `mealie_shopping_lists_list` - List all shopping lists

**Cookbooks**
- `mealie_cookbooks_create` - Create a new cookbook
- `mealie_cookbooks_delete` - Delete a cookbook
- `mealie_cookbooks_get` - Get a cookbook by ID
- `mealie_cookbooks_list` - List all cookbooks
- `mealie_cookbooks_update` - Update a cookbook

**Foods & Units**
- `mealie_foods_create` - Create a new food
- `mealie_foods_delete` - Delete a food
- `mealie_foods_get` - Get a specific food by ID
- `mealie_foods_list` - List foods with pagination and an optional `search` by name
- `mealie_foods_merge` - Merge one food into another (combines usage across recipes)
- `mealie_foods_update` - Update an existing food
- `mealie_units_create` - Create a new unit
- `mealie_units_delete` - Delete a unit
- `mealie_units_get` - Get a specific unit by ID
- `mealie_units_list` - List units with pagination and an optional `search` by name
- `mealie_units_merge` - Merge one unit into another (combines usage across recipes)
- `mealie_units_update` - Update an existing unit

**Ingredient Aliases**

Aliases are alternate names the Mealie ingredient parser matches back to a food
or unit, so a recipe calling for "scallions" resolves to your "green onion"
food instead of creating a duplicate.

- `mealie_foods_aliases_add` - Add one or more aliases to a food, keeping the existing ones
- `mealie_foods_aliases_list` - List the aliases registered for a food
- `mealie_foods_aliases_remove` - Remove one or more aliases from a food
- `mealie_units_aliases_add` - Add one or more aliases to a unit, keeping the existing ones
- `mealie_units_aliases_list` - List the aliases registered for a unit
- `mealie_units_aliases_remove` - Remove one or more aliases from a unit

`mealie_foods_create`, `mealie_foods_update`, `mealie_units_create` and
`mealie_units_update` also accept an `aliases` list, which *replaces* the whole
set. Use the add/remove tools above for incremental changes.

**Ingredient Substitutions**

Substitutions are "may be replaced by" options, such as "passata, or chopped
tomatoes" or "butter, or vegan block". Mealie keeps them in two places: on a
single recipe ingredient line, and on a food as a standing default. This needs
Mealie 3.26.0 or later.

- `mealie_foods_substitutions_add` - Add one or more standing substitutions to a food, keeping the existing ones
- `mealie_foods_substitutions_remove` - Remove one or more standing substitutions from a food

Each substitution is a substitute food name, or a dict with `substitute_food`
(a name or `{"id", "name"}`; `food` works too) or `substitute_food_id`, plus an
optional `note`. A note on its own is fine too, e.g.
`{"note": "water and a stock cube"}`. Any other key is an error, so a misspelt
key can't quietly save a note-only substitution. Names are matched
case-insensitively against existing food names, plural names and aliases. The
accepted keys are part of each tool's input schema.

- `mealie_foods_create` and `mealie_foods_update` accept a `substitutions` list,
  which *replaces* the whole set (`[]` clears it, leaving it out changes
  nothing). Named substitute foods must already exist.
- `mealie_recipes_update_structured_ingredients` accepts a `substitutions` list
  on each ingredient line. Missing substitute foods are created, or reported as
  `unmatched_substitute_foods` when `create_missing_foods=False`. The response
  includes `saved_substitutions`, read back from Mealie.
- If Mealie saves none of the substitutions sent (a server version without
  substitution support), the response carries a `warning`.
- `mealie_recipes_get` and `mealie_foods_get` return each substitution with
  its resolved `substituteFood`.

**Organizers (categories, tags, tools)**
- `mealie_categories_create` - Create a new category
- `mealie_categories_delete` - Delete a category
- `mealie_categories_get` - Get a category by ID
- `mealie_categories_list` - List all categories
- `mealie_categories_update` - Update a category
- `mealie_tags_create` - Create a new tag
- `mealie_tags_delete` - Delete a tag
- `mealie_tags_get` - Get a tag by ID
- `mealie_tags_list` - List all tags
- `mealie_tags_update` - Update a tag
- `mealie_tools_create` - Create a new kitchen tool
- `mealie_tools_delete` - Delete a tool
- `mealie_tools_get` - Get a kitchen tool by ID
- `mealie_tools_list` - List all kitchen tools
- `mealie_tools_update` - Update a tool

**Webhooks**
- `mealie_webhooks_create` - Create a new webhook
- `mealie_webhooks_delete` - Delete a webhook
- `mealie_webhooks_get` - Get a specific webhook by ID
- `mealie_webhooks_list` - List all webhooks
- `mealie_webhooks_test` - Test a webhook by sending a test notification
- `mealie_webhooks_update` - Update an existing webhook

**Ingredient Parsing**
- `mealie_parser_ingredient` - Parse a single ingredient string to structured format
- `mealie_parser_ingredients_batch` - Parse multiple ingredient strings to structured format

**Utility**
- `ping` - Test connectivity to the MCP server and Mealie instance

`mealie_foods_list` and `mealie_units_list` accept a `search` string so an
existing food or unit can be found by name without paging the whole library.

**Linking a new recipe to existing foods without creating duplicates**

1. Import the recipe (`mealie_recipes_create_from_url` or `mealie_recipes_create`).
2. Parse the ingredient lines with `mealie_parser_ingredients_batch`. Foods that
   match an existing name or alias come back with an `id`; unmatched ones do not.
3. Call `mealie_recipes_update_structured_ingredients` with
   `create_missing_foods=False`. If any food is unmatched the recipe is left
   untouched and the unmatched names are returned.
4. For each unmatched name, find the right food with
   `mealie_foods_list(search=...)`, add the name with `mealie_foods_aliases_add`,
   re-parse that line, and call step 3 again. Once the parser is confident the
   recipe links to your existing foods.

### Resources

- `recipes://list` - Browse all recipes
- `recipes://{slug}` - View specific recipe
- `mealplans://current` - Current week's meal plan
- `mealplans://today` - Today's meals
- `mealplans://{date}` - Specific date's meals
- `shopping://lists` - All shopping lists
- `shopping://{list_id}` - Specific shopping list

## Prerequisites

- Docker (or Podman)
- A running Mealie instance
- Mealie API token

## Quick Start

### 1. Get the Docker Image

**Option A: Pull from GitHub Container Registry (recommended)**
```bash
docker pull ghcr.io/mdlopresti/mealie-mcp:latest
```

The published image is multi-architecture (`linux/amd64` and `linux/arm64`),
so the same tag works on x86 servers and on Apple Silicon Macs. Docker picks
the matching architecture automatically.

**Option B: Build from source**
```bash
git clone https://github.com/mdlopresti/mealie-mcp.git
cd mealie-mcp
docker build -t mealie-mcp:latest .
```

`build.sh` builds for the host architecture by default. Set `PLATFORM` to
cross-build:

```bash
PLATFORM=linux/arm64 ./build.sh
```

### 2. Get Your API Token

1. Log into your Mealie instance
2. Go to **User Settings** (click your name in sidebar)
3. Navigate to **API Tokens**
4. Create a new token (e.g., "MCP Server")
5. Copy the token immediately (it won't be shown again)

### 3. Configure Claude Code

Add to `.mcp.json` in your project root:

```json
{
  "mcpServers": {
    "mealie": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "MEALIE_URL=https://your-mealie-instance.com",
        "-e", "MEALIE_API_TOKEN=your-api-token-here",
        "ghcr.io/mdlopresti/mealie-mcp:latest"
      ]
    }
  }
}
```

Then add `mealie` to your `~/.claude/settings.json`:

```json
{
  "allowedMcpServers": [
    { "serverName": "mealie" }
  ]
}
```

### Uploading images from files

`mealie_recipes_image_upload` and `mealie_timeline_image_upload` can read an
image straight from a file with `image_path`, so the bytes never pass through
the model. This is off until you list the folders it may read from in
`MEALIE_MCP_IMAGE_DIRS` (`:`-separated). Mount each folder into the container
**read-only at the same path** your agent sees, so the agent can pass the path
exactly as it has it:

```json
"args": [
  "run", "-i", "--rm",
  "-e", "MEALIE_URL=https://your-mealie-instance.com",
  "-e", "MEALIE_API_TOKEN=your-api-token-here",
  "-v", "/home/you/agent/cache/images:/home/you/agent/cache/images:ro",
  "-e", "MEALIE_MCP_IMAGE_DIRS=/home/you/agent/cache/images",
  "ghcr.io/mdlopresti/mealie-mcp:latest"
]
```

A path must be absolute, and its real location (after following symlinks)
must be inside one of those folders; `..` tricks, a sibling folder with a
similar name, or a symlink pointing elsewhere are refused. The file must be a
regular file of at most 10 MB, and its format is read from its bytes, not its
name. The server only ever reads the file. Folders in `MEALIE_MCP_IMAGE_DIRS`
that don't exist are ignored.

### 4. Test the Connection

Restart Claude Code and try:
```
Can you search for recipes in Mealie?
```

## Usage Examples

### Clearing Optional Fields

To clear an optional field (remove its value), pass the special sentinel value `"__CLEAR__"`:

```python
# Remove recipe association from a meal plan entry
mealie_mealplans_update(
    mealplan_id="abc-123",
    recipe_id="__CLEAR__"
)

# Clear the title from an entry
mealie_mealplans_update(
    mealplan_id="abc-123",
    title="__CLEAR__"
)

# Clear the text/notes from an entry
mealie_mealplans_update(
    mealplan_id="abc-123",
    text="__CLEAR__"
)

# Clear multiple fields at once
mealie_mealplans_update(
    mealplan_id="abc-123",
    recipe_id="__CLEAR__",
    title="__CLEAR__",
    text="__CLEAR__"
)
```

To leave a field unchanged, simply omit it from the call:

```python
# Update only the date, preserving all other fields
mealie_mealplans_update(
    mealplan_id="abc-123",
    meal_date="2025-12-25"
)
```

## Development

### Local Development (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MEALIE_URL=https://your-mealie-instance.com
export MEALIE_API_TOKEN=your-api-token

# Run server
python -m src.server
```

### Running Tests

**Unit/Integration Tests** (mock API, always run):
```bash
# Run all tests except E2E
pytest -m "not e2e"

# Run all tests with coverage
pytest --cov=src --cov-report=term-missing
```

**End-to-End Tests** (optional):

E2E tests validate against a real Mealie instance. Two modes are supported:

**Docker E2E Tests** (recommended - isolated environment):
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run Docker E2E tests
pytest tests/e2e/test_docker_e2e.py -v

# These tests:
# - Start a containerized Mealie instance automatically
# - Run tests in isolated environment
# - Clean up containers and data after tests
# - Require Docker/Podman to be running
```

**Live Instance E2E Tests** (test against existing server):
```bash
# Set required environment variables
export MEALIE_E2E_URL="https://your-mealie-instance.com"
export MEALIE_E2E_TOKEN="your-test-api-token"

# Run E2E tests against live instance
pytest -m e2e

# These tests are skipped if environment variables are not set
```

See [tests/e2e/README.md](tests/e2e/README.md) for detailed E2E testing documentation.

Note: Live instance E2E tests create and delete test resources. Use a test/development instance, not production!

### Project Structure

```
mealie-mcp/
├── Dockerfile           # Container definition
├── requirements.txt     # Python dependencies
├── build.sh            # Build helper script
└── src/
    ├── server.py       # MCP server entry point
    ├── client.py       # Mealie API client
    ├── tools/          # MCP tool implementations
    │   ├── recipes.py
    │   ├── mealplans.py
    │   ├── shopping.py
    │   └── parser.py
    └── resources/      # MCP resource implementations
        ├── recipes.py
        ├── mealplans.py
        └── shopping.py
```

## Security

- **Never commit API tokens** - Use environment variables
- The API token has full access to your Mealie account
- Consider creating a dedicated Mealie user for the MCP server

## Requirements

- Python 3.12+
- Mealie v1.0+ (tested with v3.6.1)

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR.

## Related

- [Mealie](https://mealie.io/) - Self-hosted recipe manager
- [Model Context Protocol](https://modelcontextprotocol.io/) - MCP specification
- [FastMCP](https://github.com/jlowin/fastmcp) - Python MCP framework
