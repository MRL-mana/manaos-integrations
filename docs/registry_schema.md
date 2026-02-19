# Registry Schema - ManaHome Service Definition

**Location**: `D:\ManaHome\system\services\registry.yaml`  
**Purpose**: Defines all services managed by the boot orchestrator  
**Format**: YAML

---

## Schema Definition

### Root Level

```yaml
# Each key is a service name (unique identifier)
# Each value is a service definition object

service_name_here:
  # Service definition fields follow...
```

---

## Service Definition Fields

### Required Fields

#### `port`
- **Type**: Integer
- **Range**: 1-65535
- **Description**: TCP port number where service listens
- **Usage**: Used for health checks (TCP connectivity probe)
- **Example**: `9502`

#### `command`
- **Type**: String (multi-line permitted)
- **Description**: Exact shell command to spawn the service
- **Notes**:
  - Must be a full, executable command
  - Can include working directory change
  - Multi-line OK (use `|` for YAML block scalar)
- **Example**:
  ```yaml
  command: |
    cd D:\ManaHome && python unified_api_server.py
  ```

#### `always_on`
- **Type**: Boolean
- **Description**: Whether service should auto-recover on failure
- **Value `true`**: Orchestrator monitors and restarts if dead
- **Value `false`**: Service starts on-demand only (no auto-restart)
- **Example**: `always_on: true`

---

### Optional Fields

#### `health_check`
- **Type**: Object
- **Description**: Customizes health probe behavior
- **Sub-fields**:

##### `health_check.method`
- **Type**: String
- **Valid Values**: `tcp`, `http`
- **Default**: `tcp`
- **Description**:
  - `tcp` = Raw socket probe (more reliable)
  - `http` = HTTP GET to endpoint
- **Example**: `method: tcp`

##### `health_check.endpoint`
- **Type**: String (URL or port number)
- **Default**: `127.0.0.1:{port}`
- **Required if**: `method: http`
- **Format**:
  - Full URL: `http://127.0.0.1:9502/health`
  - Port only: `9502` (will use TCP probe)
- **Example**: `endpoint: http://127.0.0.1:9502/health`

##### `health_check.timeout`
- **Type**: Integer (seconds)
- **Default**: `5`
- **Range**: 1-30
- **Description**: Max seconds to wait for health probe response
- **Example**: `timeout: 5`

#### `description`
- **Type**: String
- **Description**: Human-readable service description
- **Optional**: Yes
- **Example**: `description: "Central API gateway for all integrations"`

#### `priority`
- **Type**: Integer
- **Range**: 0-100 (higher = earlier boot)
- **Description**: Boot order priority (currently unused, reserved)
- **Default**: 50
- **Example**: `priority: 90`  (would boot early)

#### `environment`
- **Type**: Object (key-value pairs)
- **Description**: Environment variables to set before spawn
- **Example**:
  ```yaml
  environment:
    PYTHONUNBUFFERED: "1"
    FLASK_ENV: "production"
  ```

---

## Common Service Definition Patterns

### Pattern 1: Core Service (TCP Health Check)

```yaml
unified_api_server:
  port: 9502
  command: |
    cd D:\ManaHome && python unified_api_server.py
  always_on: true
  health_check:
    method: tcp
    timeout: 5
  description: "Central API gateway"
```

**Characteristics**:
- Always-on (auto-restart on failure)
- Simple TCP probe (no HTTP dependency)
- 5-second timeout (conservative)

### Pattern 2: HTTP Health Endpoint Service

```yaml
orchestrator:
  port: 5106
  command: cd D:\ManaHome && python adapters/orchestrator/router.py
  always_on: true
  health_check:
    method: http
    endpoint: http://127.0.0.1:5106/health
    timeout: 5
  description: "Trinity orchestrator"
```

**Characteristics**:
- HTTP health endpoint available
- More comprehensive probe (checks app logic, not just connectivity)
- Provides richer status info

### Pattern 3: Optional Service (Manual Startup)

```yaml
external_webhook_service:
  port: 8765
  command: python external_service.py
  always_on: false
  health_check:
    method: tcp
    timeout: 3
  description: "External webhook processor"
```

**Characteristics**:
- Not auto-recovered (manual or triggered start)
- Shorter timeout (optional service, less critical)

### Pattern 4: Service with Environment Variables

```yaml
learning_system:
  port: 5126
  command: |
    cd D:\ManaHome && python learning_system_api.py
  always_on: true
  environment:
    PYTHONUNBUFFERED: "1"
    LOG_LEVEL: "INFO"
    MEMORY_MAX_GB: "4"
  health_check:
    method: tcp
    timeout: 8
  description: "Adaptive learning engine"
```

**Characteristics**:
- Custom environment setup
- Longer timeout (memory-intensive service)

---

## Current Registry Contents (as of 2026-02-18)

### Core Infrastructure (2)
- `unified_api_server` (9502) - API gateway
- `orchestrator` (5106) - Routing & orchestration

### Memory Systems (4)
- `mrl_memory` (5105) - Multi-modal recurrent learning
- `rag_memory` (5104) - RAG-based retrieval
- `learning_system` (5126) - Learning engine
- `llm_routing` (5111) - LLM delegation

### Operations (8)
- `pico_hid` (5120) - Hardware interface
- `intent_router` (5121) - Intent processing
- `memory_cache` (5122) - Cache layer
- `monitoring` (5123) - System monitoring
- `logging` (5124) - Centralized logging
- `gateway_control` (5125) - Gateway management
- `backup_failover` (5127) - Backup systems
- `service_discovery` (5128) - Service registry

### Additional Services (2)
- `pico_extra_1` (5129)
- `pico_extra_2` (5130)

**Total**: 16 always-on + 8 optional = 24 services

---

## Best Practices

### Naming
- Use snake_case for service names
- Be descriptive (e.g., `unified_api_server` not `api`)
- Avoid abbreviations that aren't universal

### Port Assignment
- Use ranges to group by function:
  - 9500-9599: Core APIs
  - 5100-5199: Core services
  - 5120-5199: Operations
  - 8000-8999: Optional/external

### Commands
- Always use full paths (avoid chdir-dependent behavior)
- Use `|` for multi-line YAML if > 80 chars
- Include error redirection if needed

### Health Checks
- TCP for simple services (fast, reliable)
- HTTP for complex services (app-aware checks)
- Keep timeouts conservative (3-8 seconds)

### Documentation
- Always include `description` field
- Document any special startup requirements
- Note dependencies between services (if any)

---

## Modifying the Registry

### Add a New Service

1. **Edit** `D:\ManaHome\system\services\registry.yaml`
2. **Add** entry following the schema above
3. **Test** locally:
   ```powershell
   cd "D:\ManaHome"
   python system/boot/home_boot_v2.py --max-parallel 3
   python system/boot/home_update_v2.py --auto-restart
   ```
4. **Commit** to `manaos_integrations/system/services/registry.yaml`
5. **Deploy** using `deploy_to_home.ps1`

### Modify Existing Service

1. **Edit** in home first (test)
2. **Update** in `manaos_integrations` repo
3. **Deploy** via `deploy_to_home.ps1`

### Remove a Service

1. **Delete** entry from registry
2. **Test** startup sequence
3. **Commit** and deploy

---

## Validation & Troubleshooting

### Validate YAML Syntax

```powershell
# Using Python
python -c "import yaml; yaml.safe_load(open('registry.yaml'))"

# Using online validator
# https://www.yamllint.com/
```

### Missing Port

**Error**: Port not defined in registry entry

**Fix**: Add `port: NNNN` to service definition

### Command Execution Fails

**Symptom**: Service starts but immediately exits

**Debug**:
1. Copy command and run manually
2. Check working directory
3. Verify all dependencies available
4. Check environment variables

### Port Already in Use

**Symptom**: Multiple services can't claim same port

**Fix**:
1. Assign unique port numbers
2. Kill previous process: `netstat -ano | Select-String ":XXXX"`
3. Restart without duplicate

---

## YAML Formatting Notes

### Proper YAML Indentation
```yaml
# ✓ Correct (2-space indentation)
service_name:
  port: 9502
  command: |
    cd D:\Path && python script.py
  health_check:
    method: tcp
    timeout: 5

# ✗ Wrong (inconsistent indentation)
service_name:
 port: 9502
  command: python script.py
```

### Multi-line Commands
```yaml
# ✓ Correct (literal block scalar with |)
command: |
  cd D:\ManaHome && python script.py

# ✓ Also OK (single line)
command: cd D:\ManaHome && python script.py

# ✗ Wrong (line break without |)
command: cd D:\ManaHome && 
  python script.py
```

---

## Integration with Orchestrator

**How Registry is Used**:
1. `home_boot_v2.py` loads `registry.yaml` on startup
2. Parses service definitions
3. Filters to `always_on: true` services (16 total)
4. Spawns each service with `command` field
5. Tracks PID in `system/runtime/pid/{service_name}.pid`
6. Stores boot entry in `state.json`

**How Health Check Works**:
1. `home_update_v2.py` runs every 5 seconds
2. For each service, probes health per `health_check` config
3. If probe fails, marks service as offline
4. If `always_on: true`, auto-restarts the service
5. Updates `state.json` with health snapshot

---

**Summary**: Registry is the single source of truth for ManaHome service definitions. Modifying it is safe—just test locally before deploying to production via `deploy_to_home.ps1`.
