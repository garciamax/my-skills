---
name: joplin
description: Interact with Joplin notes app via REST API. Create, read, update, delete notes, notebooks (folders), tags, and resources. Search notes, manage note organization, and sync data. Use when working with Joplin notes or personal knowledge management.
---

# Joplin API

Access Joplin notes, notebooks, tags, and resources via the REST API.

## Prerequisites

1. Joplin desktop app must be running
2. Web Clipper service must be enabled:
   - Go to **Tools → Options → Web Clipper**
   - Enable the clipper service
   - Note the **port** (default: 41184)
   - Copy your **Authorization token**
3. Set environment variables in `~/.profile` or `~/.zprofile`:
   ```bash
   export JOPLIN_TOKEN="your-token-here"
   export JOPLIN_PORT="41184"  # Optional, defaults to 41184
   ```
4. Install dependencies (run once):
   ```bash
   cd {baseDir}
   npm install
   ```

## Usage

### Notes

```bash
# List all notes
{baseDir}/joplin.js notes list
{baseDir}/joplin.js notes list --limit 20 --fields "id,title,updated_time"

# Get a specific note
{baseDir}/joplin.js notes get <note-id>
{baseDir}/joplin.js notes get <note-id> --fields "id,title,body"

# Create a note
{baseDir}/joplin.js notes create --title "My Note" --body "Content in **Markdown**"
{baseDir}/joplin.js notes create --title "Note" --body "Content" --parent-id <folder-id>
{baseDir}/joplin.js notes create --title "Todo" --is-todo 1

# Update a note
{baseDir}/joplin.js notes update <note-id> --title "New Title"
{baseDir}/joplin.js notes update <note-id> --body "New content"
{baseDir}/joplin.js notes update <note-id> --parent-id <folder-id>  # Move to folder

# Delete a note (moves to trash)
{baseDir}/joplin.js notes delete <note-id>
{baseDir}/joplin.js notes delete <note-id> --permanent  # Permanently delete

# Get tags for a note
{baseDir}/joplin.js notes tags <note-id>

# Get resources attached to a note
{baseDir}/joplin.js notes resources <note-id>
```

### Notebooks (Folders)

```bash
# List all notebooks (returns tree structure)
{baseDir}/joplin.js folders list

# Get a specific notebook
{baseDir}/joplin.js folders get <folder-id>

# Create a notebook
{baseDir}/joplin.js folders create --title "My Notebook"
{baseDir}/joplin.js folders create --title "Sub Notebook" --parent-id <parent-folder-id>

# Update a notebook
{baseDir}/joplin.js folders update <folder-id> --title "New Name"

# Delete a notebook (moves to trash)
{baseDir}/joplin.js folders delete <folder-id>
{baseDir}/joplin.js folders delete <folder-id> --permanent

# List notes in a notebook
{baseDir}/joplin.js folders notes <folder-id>
```

### Tags

```bash
# List all tags
{baseDir}/joplin.js tags list

# Get a specific tag
{baseDir}/joplin.js tags get <tag-id>

# Create a tag
{baseDir}/joplin.js tags create --title "important"

# Update a tag
{baseDir}/joplin.js tags update <tag-id> --title "new-name"

# Delete a tag
{baseDir}/joplin.js tags delete <tag-id>

# List notes with a tag
{baseDir}/joplin.js tags notes <tag-id>

# Add tag to a note
{baseDir}/joplin.js tags add-note <tag-id> <note-id>

# Remove tag from a note
{baseDir}/joplin.js tags remove-note <tag-id> <note-id>
```

### Resources (Attachments)

```bash
# List all resources
{baseDir}/joplin.js resources list

# Get resource metadata
{baseDir}/joplin.js resources get <resource-id>

# Download resource file
{baseDir}/joplin.js resources download <resource-id> --output /path/to/file

# Upload a resource
{baseDir}/joplin.js resources upload /path/to/file.jpg --title "My Image"

# Delete a resource
{baseDir}/joplin.js resources delete <resource-id>

# Get notes that use a resource
{baseDir}/joplin.js resources notes <resource-id>
```

### Search

```bash
# Search notes (full-text)
{baseDir}/joplin.js search "query"
{baseDir}/joplin.js search "query" --limit 10

# Search with Joplin search syntax
{baseDir}/joplin.js search "title:meeting created:20240101"
{baseDir}/joplin.js search "notebook:Work todo:*"

# Search notebooks by name
{baseDir}/joplin.js search "recipes" --type folder

# Search tags
{baseDir}/joplin.js search "project-*" --type tag
```

### Service Status

```bash
# Check if Joplin service is running
{baseDir}/joplin.js ping
```

## Common Options

- `--limit <n>` - Number of results (default: 10, max: 100)
- `--page <n>` - Page number for pagination (default: 1)
- `--fields <list>` - Comma-separated list of fields to return
- `--order-by <field>` - Sort by field (e.g., updated_time, title)
- `--order-dir <ASC|DESC>` - Sort direction

## Output Format

Results are returned as JSON. Use `jq` for formatting:

```bash
{baseDir}/joplin.js notes list | jq '.items[].title'
{baseDir}/joplin.js notes get <id> --fields "title,body" | jq -r '.body'
```

## Note Fields Reference

Key fields for notes:
- `id` - Note ID
- `parent_id` - Notebook ID containing the note
- `title` - Note title
- `body` - Note body in Markdown
- `created_time` - Creation timestamp (ms)
- `updated_time` - Last update timestamp (ms)
- `is_todo` - 1 if todo, 0 otherwise
- `todo_completed` - Completion timestamp if completed
- `source_url` - Original URL if clipped

## Search Syntax

Joplin supports advanced search:
- `title:keyword` - Search in title
- `body:keyword` - Search in body
- `notebook:name` - Search in specific notebook
- `tag:name` - Notes with tag
- `created:YYYYMMDD` - Created on/after date
- `updated:YYYYMMDD` - Updated on/after date
- `todo:*` - All todos
- `iscompleted:1` - Completed todos
- `type:note` or `type:todo` - Filter by type
