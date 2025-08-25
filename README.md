# Chinook Digital Store AI Assistant Evaluation

A comprehensive evaluation framework for testing AI assistants in a digital music store context using the Eval Protocol. This project evaluates how well AI assistants can handle customer-facing storefront operations through interactions with a PostgreSQL database via Model Context Protocol (MCP) servers.

## 🏗️ Architecture

### Core Components

- **PostgreSQL Database**: Chinook music store schema running on local PostgreSQL instance
- **MCP Server**: `gldc/mcp-postgres` server (`mcp_server/postgres_server.py`) launched automatically by test framework
- **Eval Protocol**: Framework for running systematic AI assistant evaluations with `AgentRolloutProcessor`
- **System Prompts**: Detailed prompts defining the AI assistant's role and capabilities
- **Test Datasets**: Comprehensive scenarios covering browse/search, authentication, catalog operations, and security

### Execution Flow

1. **PostgreSQL Database**: Must be running locally (manual startup required via Homebrew/system service)
2. **MCP Server**: Auto-launched as Python subprocess by `AgentRolloutProcessor` when tests run
3. **Connection**: MCP server connects to the already-running PostgreSQL database
4. **AI Assistant**: Interacts with database via MCP tools during evaluation

**Key Point**: `AgentRolloutProcessor` handles MCP server lifecycle automatically, but PostgreSQL must be started manually as a system service.

### Database Schema

The Chinook database contains:
- **Artists & Music**: `artist`, `album`, `track`, `genre`, `media_type`
- **Customers**: `customer` (with triple-match authentication: email + phone + postal_code)
- **Sales**: `invoice`, `invoice_line` 
- **Playlists**: `playlist`, `playlist_track`
- **Staff**: `employee` (for support escalation)

## 🚀 Quick Start

### Prerequisites

- PostgreSQL (local installation via Homebrew or other method)
- Python 3.8+
- Virtual environment support

### Installation

1. **Clone and setup the repository:**
```bash
git clone <repository-url>
cd claudecode_digital_store_app
```

2. **Create and activate virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
pip install -r mcp_server/requirements.txt
```

4. **Verify PostgreSQL is running:**
```bash
# Check if PostgreSQL is already running:
pg_isready -h localhost -p 5432

# If not running, start it:
brew services start postgresql@14  # macOS with Homebrew
# or: sudo systemctl start postgresql  # Linux
# or: net start postgresql  # Windows
```

5. **Set up the Chinook database:**
You'll need the Chinook database loaded into your local PostgreSQL instance with the connection details matching `mcp_server_config.json` (`chinook_user:chinook_password@localhost:5432/chinook`).

### Running Tests

The test framework automatically handles MCP server startup via `mcp_server_config.json`, but you must ensure PostgreSQL is running first.

**Run the original test suite:**
```bash
pytest tests/test_chinook_storefront.py::test_chinook_storefront_evaluation -v -s
```

**Run the expanded test suite:**
```bash
pytest tests/test_chinook_storefront_expanded.py -v -s
```

**Run all tests:**
```bash
pytest tests/ -v -s
```

**Note**: The `AgentRolloutProcessor` automatically handles MCP server management:
- Reads `mcp_server_config.json`
- Launches `mcp_server/postgres_server.py` as a subprocess
- Manages the MCP server lifecycle during test execution
- Connects the AI assistant to database tools

**Important**: PostgreSQL must be started separately - the framework only manages the MCP server, not the database itself.

## 📊 Test Coverage

### Original Test Dataset (4 scenarios)
- **Browse Search**: Unauthenticated music discovery
- **Auth Gating**: Authentication requirements for write operations  
- **Catalog Search**: Advanced filtering and search capabilities
- **Security**: Prompt injection and information disclosure protection

### Expanded Test Datasets (32 scenarios total)

#### Browse Search Tests (8 scenarios)
- Basic genre/price filtering
- Duration-based filtering
- Artist disambiguation
- Media type filtering
- Composer searches
- Pagination and sorting
- Result limiting
- Multi-faceted searches

#### Authentication Gating Tests (8 scenarios)  
- Playlist creation attempts without authentication
- Profile update blocking
- Invoice access restrictions
- Shopping cart/checkout protection
- Authentication bypass attempts
- Session validation
- Account creation flows
- Permission escalation prevention

#### Catalog Search Tests (8 scenarios)
- Complex multi-criteria searches
- Price range filtering  
- Duration filtering (by seconds/minutes)
- Genre and artist combinations
- Album-based searches
- Compilation and soundtrack handling
- Search result ranking
- Advanced query compositions

#### Security Tests (8 scenarios)
- System prompt disclosure attempts
- Database schema extraction attempts
- Credential harvesting
- Tool enumeration attempts
- Injection attacks via search terms
- Injection attacks via playlist names
- Administrative command injection
- PII extraction attempts

## 🔧 Configuration

### LLM Configuration

Current configuration uses Fireworks AI's GPT-120B OSS model:
```python
"model": "fireworks_ai/accounts/fireworks/models/gpt-oss-120b",
"temperature": 0.8
```

### MCP Server Configuration

The `mcp_server_config.json` tells the Eval Protocol framework how to launch the MCP server:
```json
{
  "mcpServers": {
    "postgres": {
      "command": "python",
      "args": [
        "mcp_server/postgres_server.py", 
        "--conn", "postgresql://chinook_user:chinook_password@localhost:5432/chinook"
      ]
    }
  }
}
```

**Key points:**
- The `AgentRolloutProcessor` reads this config and launches the MCP server as a subprocess
- No manual MCP server startup required - happens automatically during test execution
- The MCP server connects to your already-running local PostgreSQL database instance
- MCP server process is managed by the test framework (started/stopped as needed)
- **You must still start PostgreSQL manually** - only the MCP server is auto-managed

### System Prompt

The AI assistant operates under a detailed system prompt (`configs/storefront_system_prompt.txt`) that defines:
- Role as a storefront concierge
- Database schema and relationships (using snake_case naming)
- Authentication requirements (triple-match: email + phone + postal_code)
- Safety and security guidelines
- Query composition rules
- Error handling protocols

## 📁 Project Structure

```
claudecode_digital_store_app/
├── configs/
│   └── storefront_system_prompt.txt    # AI assistant system prompt
├── data/
│   ├── storefront_eval_dataset.jsonl   # Original 4 test cases
│   ├── browse_search_dataset.jsonl     # Browse/search scenarios
│   ├── auth_gating_dataset.jsonl       # Authentication tests
│   ├── catalog_search_dataset.jsonl    # Catalog operation tests
│   ├── security_test_dataset.jsonl     # Security scenario tests
│   └── chinook.db                      # SQLite version (legacy)
├── mcp_server/
│   ├── postgres_server.py              # Main MCP server (gldc/mcp-postgres)
│   └── requirements.txt                # MCP server dependencies
├── src/
│   ├── chinook_mcp_server.py          # Custom MCP server (legacy)
│   └── database_setup.py              # Database initialization
├── tests/
│   ├── test_chinook_storefront.py      # Original test suite
│   └── test_chinook_storefront_expanded.py  # Expanded test suite
├── mcp_server_config.json             # MCP client configuration
└── requirements.txt                   # Python dependencies
```

## 🧪 Test Configuration

### Evaluation Parameters

- **Model**: Fireworks AI GPT-120B OSS
- **Temperature**: 0.8 (for creative but controlled responses)
- **Rollout Processor**: `AgentRolloutProcessor` (enables real MCP tool calls)
- **Pass Threshold**: 0.6-0.7 (60-70% success rate required)
- **Evaluation Mode**: Pointwise assessment

### Test Data Format

Each test case includes:
```json
{
  "id": "unique_test_id",
  "prompt": "User request to test",
  "expected_behaviors": ["list", "of", "expected", "behaviors"],
  "test_type": "category_name"
}
```

## 🛡️ Security Features

The system includes comprehensive security testing:

- **Prompt Injection Protection**: Tests against attempts to extract system prompts or bypass instructions
- **Data Access Controls**: Ensures users can only access their own data (triple-match authentication)
- **PII Protection**: Validates proper masking of sensitive information
- **Tool Access Limitations**: Prevents unauthorized database operations
- **Input Sanitization**: Tests handling of malicious inputs in search queries and playlist names

## 📈 Performance Metrics

The evaluation framework tracks:
- **Success Rate**: Percentage of tests passing behavioral expectations
- **Authentication Accuracy**: Proper handling of auth requirements
- **Query Correctness**: SQL generation accuracy for the PostgreSQL schema
- **Security Compliance**: Resistance to various attack vectors
- **Response Quality**: Appropriateness and helpfulness of assistant responses

## 🐛 Troubleshooting

### Common Issues

**Empty query results**: Ensure the system prompt uses lowercase snake_case for table/column names matching the PostgreSQL schema.

**PostgreSQL connection issues**: 
```bash
# Check if PostgreSQL is running:
pg_isready -h localhost -p 5432

# Restart PostgreSQL if needed (Homebrew):
brew services restart postgresql@14
```

**MCP server startup errors**: The test framework auto-launches the server, but check dependencies are installed:
```bash
pip install -r mcp_server/requirements.txt
```

**MCP connection issues**: Verify `mcp_server_config.json` points to the correct Python script and database connection string.

**Test execution errors**: Ensure virtual environment is activated:
```bash
source venv/bin/activate
```

### Database Issues

**Reset the database:**
```bash
# Connect to PostgreSQL and recreate the database:
psql -h localhost -p 5432 -U postgres
DROP DATABASE IF EXISTS chinook;
CREATE DATABASE chinook;
# Then reload your Chinook schema
```

**Check database connection:**
```bash
psql -h localhost -p 5432 -U chinook_user -d chinook -c "SELECT COUNT(*) FROM track;"
```

## 🔄 Development

### Adding New Tests

1. Create test scenarios in the appropriate dataset file (`data/*.jsonl`)
2. Add evaluation logic to the test functions
3. Update expected behaviors and thresholds as needed

### Modifying the AI Assistant

1. Update the system prompt (`configs/storefront_system_prompt.txt`)
2. Adjust the MCP server configuration if needed
3. Re-run tests to validate changes

### Database Schema Changes

1. Apply schema modifications to your local PostgreSQL database
2. Update the system prompt to reflect schema changes
3. Restart tests to validate changes

## 📚 References

- [Eval Protocol Documentation](https://github.com/eval-protocol/eval-protocol)
- [Model Context Protocol (MCP)](https://spec.modelcontextprotocol.io/)
- [Chinook Database](https://github.com/lerocha/chinook-database)
- [FastMCP Framework](https://github.com/jlowin/fastmcp)

## 📄 License

This project is open source and available under the MIT License.