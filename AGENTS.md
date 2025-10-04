# meetup_bot Project Reference

## General Instructions

- Minimize inline comments
- Retain tabs, spaces, and encoding
- Fix linting errors before saving files.
  - Respect `.markdownlint.jsonc` rules for all markdown files
- If under 50 lines of code (LOC), print the full function or class
- If the token limit is close or it's over 50 LOC, print the line numbers and avoid comments altogether
- Explain as much as possible in the chat unless asked to annotate (i.e., docstrings, newline comments, etc.)

## Build, Lint, and Test Commands

- Full test suite: `uv run pytest` or `task test`
- Single test: `uv run pytest tests/test_filename.py::test_function_name`
- Linting: `uv run ruff check --fix --respect-gitignore` or `task lint`
- Formatting: `uv run ruff format --respect-gitignore` or `task format`
- Check dependencies: `uv run deptry .` or `task deptry`
- Pre-commit hooks: `pre-commit run --all-files` or `task pre-commit`

## Code Style Guidelines

- **Formatting**: 4 spaces, 130-char line limit, LF line endings
- **Imports**: Ordered by type, combined imports when possible
- **Naming**: snake_case functions/vars, PascalCase classes, UPPERCASE constants
- **Type Hints**: Use Optional for nullable params, pipe syntax for Union
- **Error Handling**: Specific exception types, descriptive error messages
- **File Structure**: Core logic in app/core/, utilities in app/utils/
- **Docstrings**: Use double quotes for docstrings
- **Tests**: Files in tests/, follow test_* naming convention

## GraphQL API Troubleshooting

When debugging GraphQL API issues (particularly for Meetup API):

### 1. Direct GraphQL Testing
- Test queries directly against the GraphQL endpoint using curl before debugging application code
- Example: `curl -X POST "https://api.meetup.com/gql-ext" -H "Authorization: Bearer <token>" -H "Content-Type: application/json" -d '{"query": "query { self { id name } }"}'`
- Start with simple queries (like `self { id name }`) then gradually add complexity

### 2. API Migration Validation
- Check API documentation for migration guides when encountering field errors
- Common Meetup API changes:
  - `count` → `totalCount`
  - `upcomingEvents` → `memberEvents(first: N)` for self queries
  - `upcomingEvents` → `events(first: N)` for group queries
  - Syntax changes: `field(input: {first: N})` → `field(first: N)`

### 3. Response Structure Analysis
- Add temporary debug logging to inspect actual GraphQL responses
- Check for `errors` array in GraphQL responses, not just HTTP status codes
- Verify field existence with introspection or simple field queries
- Example debug pattern:
  ```python
  response_data = r.json()
  if 'errors' in response_data:
      print('GraphQL Errors:', json.dumps(response_data['errors'], indent=2))
  ```

### 4. Field Validation Process
- Use GraphQL validation errors to identify undefined fields
- Test field names individually: `{ self { fieldName } }`
- Check if field requires parameters (e.g., `memberEvents` requires `first`)
- Validate nested field access patterns

### 5. Token and Authentication Debugging
- Verify token generation is working: `uv run python -c "from app.sign_jwt import main; print(main())"`
- Test tokens directly against GraphQL endpoint outside of application
- Check token expiration and refresh token logic
