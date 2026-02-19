# ManaHome Boot Sequence - Technical Deep Dive

**Location**: `D:\ManaHome\system\boot/`  
**Purpose**: Complete documentation of the 3-phase boot workflow  
**Audience**: Operators, developers, maintainers

---

## Boot Sequence Overview

```
Windows Login
    ↓
Startup Folder Triggers: ManaOS_AutoStart.cmd
    ↓
PHASE 1: Boot Orchestrator (0-1 second)
    ├─ startup_boot.ps1 executes
    ├─ home_boot_v2.py loads registry
    ├─ Spawn 16 services (max_parallel=3)
    └─ Return with exit code 0
    ↓
PHASE 2: Stabilization (1-66 seconds)
    └─ Hard-coded 65-second wait
    └─ Services bind ports, initialize state
    ↓
PHASE 3: Health Monitoring + Optional (66-110 seconds)
    ├─ startup_update.ps1 executes
    ├─ home_update_v2.py probes all services
    ├─ Auto-restart any failures
    ├─ Optional bootstrap (8088, 8188)
    └─ Update state.json
    ↓
Complete: All services online (~2 minutes)
```

---

## Phase 1: Boot Orchestrator (0-1 second)

### Entry Point

**File**: `C:\Users\mana4\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\ManaOS_AutoStart.cmd`

```batch
@echo off
REM ManaOS Home Auto-Startup Chain (Windows Startup Folder)
REM Executes on every login with user privileges

setlocal enabledelayedexpansion

set "LOG_DIR=D:\ManaHome\system\runtime\logs"
set "LOG_FILE=%LOG_DIR%\startup_autorun_%date:~0,4%-%date:~5,2%-%date:~8,2%.log"
set "BOOT_SCRIPT=D:\ManaHome\system\boot\startup_boot.ps1"
set "UPDATE_SCRIPT=D:\ManaHome\system\boot\startup_update.ps1"

REM ... [logging setup] ...

REM Phase 1: Boot orchestration (concurrent spawn of 16 always_on services)
echo [%date% %time%] PHASE-1: Boot orchestrator launching >> "%LOG_FILE%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%BOOT_SCRIPT%" >> "%LOG_FILE%" 2>&1
echo [%date% %time%] PHASE-1: Boot exit code %ERRORLEVEL% >> "%LOG_FILE%"

REM Phase 2: Stabilization wait (allow services to bind ports)
echo [%date% %time%] PHASE-2: Waiting 65 seconds for service stabilization >> "%LOG_FILE%"
timeout /t 65 /nobreak >> nul

REM Phase 3: Update daemon + optional service bootstrap (8088/8188)
echo [%date% %time%] PHASE-3: Update + optional bootstrap starting >> "%LOG_FILE%"
powershell -NoProfile -ExecutionPolicy Bypass -File "%UPDATE_SCRIPT%" >> "%LOG_FILE%" 2>&1
echo [%date% %time%] PHASE-3: Update exit code %ERRORLEVEL% >> "%LOG_FILE%"

echo [%date% %time%] === AutoStart Chain Complete === >> "%LOG_FILE%"
```

**How It's Triggered**:
- Windows calls all `.bat` and `.cmd` scripts in Startup folder on login
- User privilege level (no admin required)
- .cmd extension is associated with `cmd.exe`

---

### PowerShell Script: startup_boot.ps1

**Location**: `D:\ManaHome\system\boot\startup_boot.ps1`

**Responsibilities**:
1. Call Python orchestrator
2. Capture output and exit code
3. Log results

**Pseudo-code**:

```powershell
param([int]$MaxParallel = 3)

$pythonPath = "D:\ManaHome\system\boot\home_boot_v2.py"
$homePath = "D:\ManaHome"

cd $homePath
python $pythonPath --max-parallel $MaxParallel

exit $LASTEXITCODE  # Pass through exit code
```

**Exit Code Meaning**:
- `0` = Success (all services spawned)
- `1` = Failure (likely due to config error)

---

### Python Orchestrator: home_boot_v2.py

**Location**: `D:\ManaHome\system\boot\home_boot_v2.py`

**Core Algorithm**:

```python
def main(max_parallel=3):
    """
    Bootstrap orchestrator: spawn 16 services concurrently.
    
    Algorithm:
    1. Load registry.yaml
    2. Filter to always_on=true (16 services)
    3. Group into batches of max_parallel
    4. For each batch:
       a. Spawn processes in parallel
       b. Track PID files
       c. Set boot lock
       d. Wait for batch completion
       e. Move to next batch
    5. Return immediately (don't wait for services to be ready)
    """
    
    # Step 1: Load registry
    registry = load_yaml("system/services/registry.yaml")
    
    # Step 2: Filter always-on services
    always_on = [s for s in registry if registry[s].get("always_on", False)]
    # Result: 16 services in always_on list
    
    # Step 3: Create boot lock (prevent double-boot)
    lock_file = "system/runtime/locks/home_boot.lock"
    if lock_exists_and_fresh(lock_file):
        log("Boot already in progress, exiting")
        return 1
    create_lock_file(lock_file)
    
    # Step 4: Spawn batches
    batch_size = max_parallel  # Default 3
    processes = {}
    
    for i, service_name in enumerate(always_on):
        service_config = registry[service_name]
        
        # Every batch_size services, pause and wait
        if i > 0 and i % batch_size == 0:
            wait_for_all_processes(processes)
            processes = {}
        
        # Spawn service
        process = subprocess.Popen(
            service_config["command"],
            shell=True,
            start_new_session=True,  # Detach from parent
            stdout=PIPE,
            stderr=PIPE
        )
        
        processes[service_name] = process
        
        # Save PID file
        pid_file = f"system/runtime/pid/{service_name}.pid"
        save_pid(pid_file, process.pid)
        
        log(f"Started {service_name} (PID: {process.pid})")
    
    # Final wait
    wait_for_all_processes(processes)
    
    # Step 5: Update boot state
    state = {
        "boot": {
            "timestamp": ISO8601_now(),
            "status": "running",
            "always_on_services_count": len(always_on),
            "services_online": 0  # Will be updated by health check
        }
    }
    save_json("system/runtime/state.json", state)
    
    log("Boot orchestration complete")
    return 0
```

**Key Behaviors**:

1. **Concurrent Spawning** (max_parallel=3)
   - Service 0, 1, 2 spawn → wait for completion
   - Service 3, 4, 5 spawn → wait for completion
   - … repeat for all 16 services
   - Total time: ~200ms

2. **Detached Processes**
   - `start_new_session=True` detaches services
   - If boot.py exits, services continue running
   - Services are NOT children of boot process

3. **Boot Lock**
   ```bash
   Lock file: D:\ManaHome\system\runtime\locks\home_boot.lock
   TTL: 5 minutes (auto-release on stale)
   Purpose: Prevent accidental double-boots
   ```

4. **PID Tracking**
   ```bash
   Files: D:\ManaHome\system\runtime\pid\{service_name}.pid
   Used by: Auto-restart logic to kill zombies
   ```

5. **Immediate Return**
   - Doesn't wait for services to be ready
   - Returns immediately after spawning
   - Phase 2 stabilization handles readiness

---

## Phase 2: Stabilization (1-66 seconds)

### Hard-Coded Wait

**Duration**: 65 seconds (set in `ManaOS_AutoStart.cmd`)

```batch
timeout /t 65 /nobreak >> nul
```

### Why 65 Seconds?

**Empirical Data**:
- Unified API: 1-2 seconds to port bind
- Memory systems (MRL/RAG): 15-25 seconds to initialize
- Orchestrator + Trinity router: 10-20 seconds
- **Max service**: ~45 seconds (memory DB warmup)
- **Safety margin**: +20 seconds for variance
- **Total**: ~65 seconds

**Timing Breakdown**:
- 0-5s: Core services bind ports
- 5-30s: Memory systems initialize
- 30-45s: Slow services (learning, DB) complete startup
- 45-65s: Inter-service sync + safety buffer

### What's Happening During Wait

1. **Port Binding** (0-5s)
   - Services call `listen(port)`
   - OS assigns resources
   - Port becomes connectable

2. **Initialization** (5-30s)
   - Load config files
   - Connect to dependencies
   - Prepare internal state

3. **Warmup** (30-45s)
   - Load cache/memory data
   - Run startup procedures
   - Complete handshakes

4. **Stabilization** (45-65s)
   - Services exchange heartbeats
   - Any late dependencies resolve
   - System reaches equilibrium

---

## Phase 3: Health Monitoring & Optional Bootstrap (66-110 seconds)

### Entry Point

**File**: `startup_update.ps1`

```powershell
# Simplified pseudo-code
param([switch]$AutoRestart = $true)

# Call health monitor
python "D:\ManaHome\system\boot\home_update_v2.py" --auto-restart

# Optional: Bootstrap missing services
if ($AutoRestart) {
    # Check port 8088 (Moltbot Gateway)
    if (-not (Test-PortOpen 8088)) {
        Write-Log "Port 8088 down; launching gateway"
        & "run_gateway_wrapper_production.ps1"
    }
    
    # Check port 8188 (ComfyUI)
    if (-not (Test-PortOpen 8188)) {
        Write-Log "Port 8188 down; launching ComfyUI"
        & "start_comfyui_local.ps1" -Background -Port 8188
    }
}
```

---

### Python Health Monitor: home_update_v2.py

**Location**: `D:\ManaHome\system\boot\home_update_v2.py`

**Responsibilities**:
1. Probe all 16 services
2. Report online count
3. Auto-restart dead services
4. Update state.json

**Algorithm**:

```python
def main(auto_restart=True):
    """
    Health monitoring daemon.
    
    Loop:
    1. Load registry
    2. For each always_on service:
       a. Probe port (TCP 900ms timeout)
       b. If alive: mark online
       c. If dead and auto_restart: restart
    3. Update state.json
    4. Log results
    5. Continue indefinitely (every 5 seconds)
    """
    
    while True:
        registry = load_yaml("system/services/registry.yaml")
        always_on = [s for s in registry if registry[s].get("always_on")]
        
        online_count = 0
        
        for service_name in always_on:
            config = registry[service_name]
            port = config["port"]
            
            # Probe with 900ms timeout
            is_alive = probe_tcp_port("127.0.0.1", port, timeout=0.9)
            
            if is_alive:
                online_count += 1
                log(f"{service_name}: ONLINE")
            else:
                log(f"{service_name}: OFFLINE")
                
                if auto_restart:
                    log(f"Auto-restarting {service_name}...")
                    # Kill old process if exists
                    pid_file = f"system/runtime/pid/{service_name}.pid"
                    old_pid = load_pid_file(pid_file)
                    if old_pid:
                        kill_process(old_pid)
                    
                    # Restart service
                    process = subprocess.Popen(
                        config["command"],
                        shell=True,
                        start_new_session=True
                    )
                    save_pid_file(pid_file, process.pid)
                    log(f"Restarted {service_name} (PID: {process.pid})")
        
        # Update state
        state = load_json("system/runtime/state.json")
        state["health_check"] = {
            "timestamp": ISO8601_now(),
            "online_count": online_count,
            "total_services": len(always_on),
            "offline_ports": [
                config["port"] for s, config in registry.items()
                if not probe_tcp_port("127.0.0.1", config["port"], timeout=0.5)
            ]
        }
        save_json("system/runtime/state.json", state)
        
        log(f"Health check: {online_count}/{len(always_on)} online")
        
        # Wait before next probe
        time.sleep(5)  # Run every 5 seconds
```

**Key Features**:

1. **TCP Probe (900ms timeout)**
   ```python
   def probe_tcp_port(host, port, timeout=0.9):
       try:
           sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
           sock.settimeout(timeout)
           result = sock.connect_ex((host, port)) == 0
           sock.close()
           return result
       except:
           return False
   ```

2. **Auto-Restart with Backoff** (exponential)
   - 1st failure: Restart immediately
   - 2nd failure within 5min: Restart after 5s delay
   - 3rd failure: Restart after 30s delay
   - 4th+ failure: Mark as "stuck", log escalation

3. **State Persistence**
   ```json
   {
     "health_check": {
       "timestamp": "2026-02-18T06:13:43+09:00",
       "online_count": 16,
       "total_services": 16,
       "offline_ports": []
     }
   }
   ```

---

### Optional Service Bootstrap

**For Port 8088 (Moltbot Gateway)**:

```powershell
if (-not (Test-PortOpen 8088)) {
    Write-Log "Gateway not responding; launching bootstrap"
    & "C:\Users\mana4\Desktop\manaos_integrations\moltbot_gateway\deploy\run_gateway_wrapper_production.ps1"
}
```

**For Port 8188 (ComfyUI)**:

```powershell
if (-not (Test-PortOpen 8188)) {
    Write-Log "ComfyUI not responding; launching bootstrap"
    & "start_comfyui_local.ps1" -Background -Port 8188
}
```

**Bootstrap Strategy**: Best-Effort
- Non-blocking (doesn't delay core boot)
- Fails silently (wrapped in try-catch)
- Logged but not critical

---

## State Persistence: state.json

**Location**: `D:\ManaHome\system\runtime\state.json`

**Format**: JSON object

**Structure**:

```json
{
  "boot": {
    "timestamp": "2026-02-18T06:03:19.98+09:00",
    "status": "running",
    "always_on_services_count": 16,
    "services_online": 16
  },
  "health_check": {
    "timestamp": "2026-02-18T06:13:43.00+09:00",
    "online_count": 16,
    "offline_ports": [],
    "port_8088_gateway": true,
    "port_8188_comfyui": true,
    "last_restart": {
      "service_name": "mrl_memory",
      "timestamp": "2026-02-18T06:05:30+09:00",
      "reason": "tcp_probe_timeout"
    }
  }
}
```

**Used By**:
- Dashboards (monitoring status)
- Debugging (tracing recent activity)
- Automation (checking readiness)

**Updated By**:
- `home_boot_v2.py` (initial state)
- `home_update_v2.py` (health snapshots every 5s)

---

## Lock Mechanism: home_boot.lock

**Location**: `D:\ManaHome\system\runtime\locks\home_boot.lock`

**Purpose**: Prevent accidental double-boots

**Strategy**:
1. On boot start: Create lock file with timestamp
2. On next boot wait: Check if lock exists
3. If lock exists + timestamp < 5 minutes: Wait/exit (avoid double-boot)
4. If lock exists + timestamp > 5 minutes: Release (assume stale, proceed)

**Example**:

```python
def acquire_boot_lock(lock_path, ttl_minutes=5):
    if os.path.exists(lock_path):
        stat = os.stat(lock_path)
        age_minutes = (time.time() - stat.st_mtime) / 60
        
        if age_minutes < ttl_minutes:
            log("Boot lock exists and is fresh; exiting")
            return False  # Already booting
        else:
            log("Boot lock is stale; releasing")
            os.remove(lock_path)
    
    # Create lock
    with open(lock_path, 'w') as f:
        f.write(f"{os.getpid()}\n{time.time()}\n")
    
    return True
```

---

## Failure Scenarios & Recovery

### Scenario 1: Service Fails to Come Online (Phase 2)

**Detection**: TCP probe timeout at 66-second mark

**Recovery**:
```
Phase 3 runs:
  → health_check detects port not listening
  → auto_restart triggered
  → Kill old process
  → Spawn new process
  → Log restart event
  → Probe again in 5 seconds
  → Repeat until success or 10+ failures
```

### Scenario 2: Service Crashes After Boot

**Detection**: Periodic 5-second health probes

**Recovery**:
```
health_check detects port down:
  → Auto-restart enabled?
    → YES: Spawn new process (same as above)
    → NO: Log only, no auto-recovery
```

### Scenario 3: Double-Boot Attempt

**Cause**: User logs in while boot still in progress

**Prevention**:
```
Boot lock acquired in Phase 1
→ Second boot attempt detects lock
→ Checks lock age (TTL 5 minutes)
→ If fresh: Exit immediately (avoid double-boot)
→ If stale: Release lock, proceed (zombie recovery)
```

### Scenario 4: Port Binding Conflict

**Cause**: Last boot didn't clean up, new process can't bind same port

**Detection**: Service spawns but immediately exits (parent process exit)

**Recovery**: Auto-restart with exponential backoff
```
Attempt 1: Restart immediately
Attempt 2 (within 5min): Wait 5s, restart
Attempt 3: Wait 30s, restart
Attempt 4+: Log escalation, manual intervention needed
```

---

## Monitoring & Debugging

### View Boot Log

```powershell
Get-Content "D:\ManaHome\system\runtime\logs\startup_autorun_*.log" -Tail 50
```

### View Health Snapshots

```powershell
# Real-time state
Get-Content "D:\ManaHome\system\runtime\state.json" | ConvertFrom-Json | Format-Table -AutoSize

# Historical logs
Get-Content "D:\ManaHome\system\runtime\logs\home_update_v2.log" -Tail 100
```

### Check Service PIDs

```powershell
Get-ChildItem "D:\ManaHome\system\runtime\pid\*.pid" | 
  ForEach-Object { 
    $name = $_.BaseName; 
    $pid = Get-Content $_.FullName;
    Get-Process -Id $pid -ErrorAction SilentlyContinue |
      Select-Object @{n='Service'; e={$name}}, Id, ProcessName
  }
```

### Manual Trigger

```powershell
cd "D:\ManaHome"

# Phase 1 only
python system/boot/home_boot_v2.py --max-parallel 3

# Phase 3 only (needs Phase 1 to have completed)
python system/boot/home_update_v2.py --auto-restart

# Full chain (simulated)
Remove-Item "system/runtime/locks\*" -Force
python system/boot/home_boot_v2.py --max-parallel 3
Start-Sleep -Seconds 65
python system/boot/home_update_v2.py --auto-restart
```

---

## Performance Characteristics

### Boot Timeline (Typical)

| Time | Phase | Activity | Duration |
|------|-------|----------|----------|
| 0s | 1 | startup_boot.ps1 executes | 100ms |
| 0.1s | 1 | home_boot_v2.py loads registry | 50ms |
| 0.15s | 1 | Spawn services (batch 1: 3 services) | 50ms |
| 0.2s | 1 | Spawn services (batch 2: 3 services) | 50ms |
| 0.25s | 1 | Spawn services (batch 3: 3 services) | 50ms |
| 0.3s | 1 | Spawn services (batch 4: 3 services) | 50ms |
| 0.35s | 1 | Spawn services (batch 5: 4 services) | 50ms |
| 0.4s | 1 | Update state.json, return | 50ms |
| 0.45s | 2 | Stabilization begins | — |
| 65.45s | 2 | Stabilization ends | 65s |
| 65.5s | 3 | startup_update.ps1 executes | 100ms |
| 65.6s | 3 | home_update_v2.py probes services | 5-10s |
| 75.6s | 3 | Optional bootstrap (if needed) | 10-30s |
| **~110s** | **3** | **Complete** | **~2 minutes** |

### Resource Usage (Once Online)

- CPU: ~0.5-2% (idle, except during probes)
- Memory: ~300-400 MB (16 Python services)
- Disk I/O: Minimal (idle)
- Network: Local only (127.0.0.1)

---

## Best Practices for Operators

1. **Understand Phase 2 Significance**
   - Don't reduce 65-second wait arbitrarily
   - If services fail at health check, increase gradually
   - Monitor actual service startup times

2. **Watch for Boot Loop**
   - Service restarts infinitely
   - Check logs for error pattern
   - May indicate port conflict or bad config

3. **Lock File Management**
   - Don't manually delete .lock files
   - If truly stuck, 5-minute TTL will auto-release
   - Or just reboot Windows

4. **PID File Hygiene**
   - PIDs are auto-cleaned on next boot
   - Don't manually edit .pid files
   - Kill processes via process ID, not by editing

---

**Summary**: ManaHome boot sequence is a 3-phase process: spawn services (Phase 1, ~0.5s), stabilize (Phase 2, 65s), health check + auto-restart (Phase 3, ~40s). Total time to full operation: ~2 minutes. The system is fault-tolerant, self-healing, and well-logged.
