# ManaOS Home + Workshop Integration - Complete Overview

**Status**: ✅ Integration Complete  
**Date**: 2026-02-18  
**Strategy**: Hybrid (Home as Production, Workshop as Development)

---

## What Is ManaOS Home?

A **production-grade home automation system** that:
- ✅ Manages 16 always-on core services
- ✅ Auto-starts on Windows login (Startup folder)
- ✅ Self-heals (auto-restarts dead services every 5 seconds)
- ✅ Persists state (JSON-based runtime snapshots)
- ✅ Boots in ~2 minutes to full operational readiness
- ✅ Proven: 16/16 services + 2 optional bootstrap tested end-to-end

**Location**: `D:\ManaHome` (permanent, stable, production)

---

## What Is manaos_integrations?

A **development & customization workshop** that:
- 🔧 Hosts versioned code for system components
- 🔧 Enables collaborative development
- 🔧 Tests changes before syncing to home
- 🔧 Maintains deployment pipeline to home

**Location**: `c:\Users\mana4\Desktop\manaos_integrations` (volatile, experimental)

---

## The Integration Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  WORKSHOP: manaos_integrations (Development)                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ├─ system/boot/                    (orchestrator code)     │
│  ├─ system/services/registry.yaml   (service definitions)   │
│  ├─ skills/                         (capability modules)    │
│  ├─ adapters/                       (system adapters)       │
│  │                                                          │
│  └─ tools/                          (deployment pipeline)   │
│     ├─ deploy_to_home.ps1           (sync script)          │
│     └─ home_config.yaml             (home reference)       │
│                                                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ (Controlled Sync)
                     │ ↓ deploy_to_home.ps1
                     │
┌────────────────────v────────────────────────────────────────┐
│  HOME: D:\ManaHome (Production)                              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ├─ system/boot/                    ← Synced from workshop  │
│  │   ├─ startup_boot.ps1            ← From workshop         │
│  │   ├─ startup_update.ps1          ← From workshop         │
│  │   ├─ home_boot_v2.py             ← Updated by workshop   │
│  │   └─ home_update_v2.py           ← Updated by workshop   │
│  │                                                          │
│  ├─ system/services/registry.yaml   ← Synced from workshop  │
│  ├─ skills/                         ← Synced from workshop  │
│  ├─ adapters/                       ← Synced from workshop  │
│  │                                                          │
│  ├─ system/runtime/                 🔒 PROTECTED           │
│  │   ├─ state.json                  (runtime state)        │
│  │   ├─ pid/                        (process IDs)          │
│  │   ├─ locks/                      (boot lock)            │
│  │   └─ logs/                       (accumulated logs)     │
│  │                                                          │
│  ├─ memory/                         🔒 PROTECTED           │
│  ├─ logs/                           🔒 PROTECTED           │
│  └─ backups/deploy/                 🔒 PROTECTED           │
│                                                          │
│  [16/16 Services Always Online]                         │
│  [8088 / 8188 Optional Services]                         │
│  [Startup Folder Active]                               │
│                                                          │
└─────────────────────────────────────────────────────────────┘
```

---

## For Operators

### Daily Operations

**Home is always running:**
```powershell
# Check status anytime
netstat -an -p tcp | Select-String "LISTENING" | Select-String "9502|5106|5104"

# View latest boot log
Get-Content "D:\ManaHome\system\runtime\logs\startup_autorun_*.log" -Tail 20

# View runtime state
Get-Content "D:\ManaHome\system\runtime\state.json" | ConvertFrom-Json
```

**Nothing needs manual intervention.** System is self-healing.

### If You Reboot

Services automatically come back online via Startup folder. ~2 minutes to full operational state.

---

## For Developers

### Development Workflow

1. **Make changes in workshop**
   ```
   Edit: c:\Users\mana4\Desktop\manaos_integrations\(code)
   ```

2. **Test locally in workshop**
   ```powershell
   # Test your changes in isolation
   cd c:\Users\mana4\Desktop\manaos_integrations
   python tests/your_test.py
   ```

3. **Deploy to home when ready**
   ```powershell
   cd c:\Users\mana4\Desktop\manaos_integrations\tools
   .\deploy_to_home.ps1 -DryRun          # Preview
   .\deploy_to_home.ps1                  # Deploy with backup
   ```

4. **Verify home still works**
   ```powershell
   # Health check runs automatically
   # Or manually:
   python "D:\ManaHome\system\boot\home_update_v2.py" --auto-restart
   ```

5. **Rollback if needed**
   ```powershell
   .\deploy_to_home.ps1 -Rollback
   ```

### Safe Deployment Features

✅ **Automatic Backup**
- Before each sync, saves previous state
- Keeps last 5 deployments
- Enables single-click rollback

✅ **Diff Preview**
```powershell
.\deploy_to_home.ps1 -DryRun        # Shows what would change
```

✅ **Health Verification**
- Post-deploy TCP probes
- Validates 9502 + 5106 responding
- Warns if health check fails

✅ **Protected Paths**
- Memory, runtime, logs never touched
- State.json never overwritten
- Lock files never deleted

---

## File Organization

### In Workshop (manaos_integrations)

```
manaos_integrations/
├─ system/
│  ├─ boot/
│  │  ├─ home_boot_v2.py         ← Always syncs to home
│  │  ├─ home_update_v2.py       ← Always syncs to home
│  │  ├─ startup_boot.ps1        ← Always syncs to home
│  │  └─ startup_update.ps1      ← Always syncs to home
│  │
│  └─ services/
│     └─ registry.yaml           ← Always syncs to home
│
├─ skills/                        ← Always syncs to home
├─ adapters/                      ← Always syncs to home
│
├─ tools/
│  ├─ deploy_to_home.ps1         ← Deployment script
│  └─ home_config.yaml           ← Config file
│
└─ docs/
   ├─ mana_home_architecture.md  ← This architecture
   ├─ registry_schema.md         ← Service registry guide
   └─ boot_sequence.md           ← Boot process deep-dive
```

### In Home (D:\ManaHome)

```
D:\ManaHome/
├─ system/
│  ├─ boot/                      ← Synced from workshop
│  ├─ services/registry.yaml     ← Synced from workshop
│  ├─ runtime/                   ← NEVER synced (protected)
│  └─ adapters/                  ← Synced from workshop
│
├─ skills/                        ← Synced from workshop
├─ memory/                        ← NEVER synced (protected)
├─ logs/                          ← NEVER synced (protected)
├─ backups/deploy/               ← Auto-managed by deploy
│
└─ docs/
   ├─ PRODUCTION_OPERATIONS_AUTOSTART_GUIDE.md
   ├─ PHASE2_COMPLETION_REPORT.md
   └─ DEPLOYMENT_COMPLETE.md
```

---

## Deployment Commands Cheat Sheet

### Preview Changes (Safe)
```powershell
cd C:\Users\mana4\Desktop\manaos_integrations\tools
.\deploy_to_home.ps1 -DryRun
```

### Deploy with Backup (Recommended)
```powershell
.\deploy_to_home.ps1
```

### Deploy Without Health Checks (Quick)
```powershell
.\deploy_to_home.ps1 -SkipHealthCheck
```

### Rollback to Last Backup (Emergency)
```powershell
.\deploy_to_home.ps1 -Rollback
```

### View Available Backups
```powershell
Get-ChildItem "D:\ManaHome\system\backups\deploy" -Directory | Sort-Object Name -Descending | Select-Object -First 5 Name, LastWriteTime
```

---

## Modified Service Registry (How to Update)

### Edit in Workshop
```
c:\Users\mana4\Desktop\manaos_integrations\system\services\registry.yaml
```

### Test Locally (Optional)
```powershell
cd D:\ManaHome
python system/boot/home_boot_v2.py --max-parallel 3  # Test on home
```

### Deploy to Home
```powershell
cd c:\Users\mana4\Desktop\manaos_integrations\tools
.\deploy_to_home.ps1
```

### Verify Services
```powershell
python "D:\ManaHome\system\boot\home_update_v2.py" --auto-restart
```

---

## Common Scenarios

### Scenario: Add a New Service

1. **Edit** `manaos_integrations\system\services\registry.yaml`
   - Add service definition (follow schema)
   - Set `always_on: true` or `false`
   - Define port and health check

2. **Test** (optional)
   ```powershell
   cd D:\ManaHome
   python system/boot/home_boot_v2.py --max-parallel 3
   ```

3. **Deploy** to home
   ```powershell
   cd manaos_integrations\tools
   .\deploy_to_home.ps1
   ```

### Scenario: Update Orchestrator Logic

1. **Edit** `manaos_integrations\system\boot\home_boot_v2.py`
   - Test changes locally first
   - Ensure exit code is 0 on success

2. **Deploy** to home
   ```powershell
   .\deploy_to_home.ps1 -DryRun     # Preview
   .\deploy_to_home.ps1             # Deploy
   ```

3. **Trigger** manual boot to test
   ```powershell
   cd D:\ManaHome
   Remove-Item system\runtime\locks\*.lock -Force
   python system\boot\home_boot_v2.py --max-parallel 3
   ```

### Scenario: Emergency Rollback

If deployment breaks home:

```powershell
cd c:\Users\mana4\Desktop\manaos_integrations\tools
.\deploy_to_home.ps1 -Rollback      # Restores last good backup
```

Home will be brought back to previous state. Takes ~10 seconds.

---

## Documentation Reference

**For Operators**:
- [PRODUCTION_OPERATIONS_AUTOSTART_GUIDE.md](D:\ManaHome\PRODUCTION_OPERATIONS_AUTOSTART_GUIDE.md)
  - Daily operations, troubleshooting, performance metrics

**For Developers**:
- [mana_home_architecture.md](docs/mana_home_architecture.md)
  - System design, components, integration strategy
- [registry_schema.md](docs/registry_schema.md)
  - Service definition format, examples, best practices
- [boot_sequence.md](docs/boot_sequence.md)
  - Detailed boot flow, failure recovery, monitoring

---

## Architecture Decision: Why Hybrid?

### ❌ Don't: Migrate home to repo
- Risk: Break running system
- Result: Death of production environment
- Cost: High (manual recovery needed)

### ✅ Do: Keep home separate, connect via pipeline
- Benefit: Home stays stable while workshop experiments
- Result: Development agility + production safety
- Cost: Low (rollback always available)

### Bottom Line

**You have a winning system running at D:\ManaHome. Don't move it. Instead, build a controlled bridge to it from the workshop. That's smarter.**

---

## Quick Links

| File | Purpose | Location |
|------|---------|----------|
| **deploy_to_home.ps1** | Sync workshop → home | `tools/` |
| **home_config.yaml** | Home reference | `tools/` |
| **mana_home_architecture.md** | System overview | `docs/` |
| **registry_schema.md** | Service definition guide | `docs/` |
| **boot_sequence.md** | Boot process details | `docs/` |
| **startup_boot.ps1** | Phase 1 script | `system/boot/` |
| **startup_update.ps1** | Phase 3 script | `system/boot/` |
| **home_boot_v2.py** | Boot orchestrator | `system/boot/` |
| **home_update_v2.py** | Health monitor | `system/boot/` |
| **registry.yaml** | Service registry | `system/services/` |

---

## Status Summary

✅ **HomeSetup Complete**
- 16 always-on services configured
- Windows Startup registered
- 2 optional services (8088, 8188) bootstrap enabled
- Proven uptime & self-healing

✅ **Workshop Connected**
- Deployment pipeline ready
- Safe backup & rollback enabled
- Documentation complete

✅ **Integration Verified**
- Both systems tested end-to-end
- Syncing mechanism validated
- Health checks functional

**Ready for production use.** 🎉

---

**Conclusion**: ManaOS is now both a running home system AND a development platform. Home stays stable (production). Workshop enables evolution (development). Bridge (deploy_to_home.ps1) keeps them connected.
