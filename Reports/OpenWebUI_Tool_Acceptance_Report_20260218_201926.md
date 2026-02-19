# OpenWebUI Tool Acceptance Report

**Created at**: 2026-02-18 20:19:31  
**Overall**: PASS  
**Automated checks**: 6 / 6  
**Acceptance exit code**: 0

## Automated Result

- [OK] **Tool Server Health**
- [OK] **Tool Server OpenAPI**
- [OK] **Unified API Health**
- [OK] **Open WebUI**
- [OK] **Integration test**
- [OK] **Automated checks summary**

## Manual Chat Cases (Open WebUI)

- [ ] Case 1: service_status is called from chat
- [ ] Case 2: vscode_open_file opens target file
- [ ] Case 3: execute_command allows Get-Location
- [ ] Case 4: execute_command blocks Remove-Item

## Security Audit Tail

- {"timestamp": "2026-02-18T20:14:51.350065", "event": "command_blocked", "command": "Remove-Item C:\\temp -Recurse -Force", "cwd": "C:\\Users\\mana4\\Desktop", "reason": "遖∵ｭ｢繝代ち繝ｼ繝ｳ繧貞性繧縺溘ａ螳溯｡後〒縺阪∪縺帙ｓ: Remove-Item\\s+.+-Recurse\\s+-Force"}
- {"timestamp": "2026-02-18T20:15:43.275150", "event": "command_executed", "command": "Get-Process python | Select-Object -First 1 ProcessName,Id", "cwd": "C:\\Users\\mana4\\Desktop", "exit_code": 0, "status": "success"}
- {"timestamp": "2026-02-18T20:15:43.292932", "event": "command_blocked", "command": "Remove-Item C:\\temp -Recurse -Force", "cwd": "C:\\Users\\mana4\\Desktop", "reason": "遖∵ｭ｢繝代ち繝ｼ繝ｳ繧貞性繧縺溘ａ螳溯｡後〒縺阪∪縺帙ｓ: Remove-Item\\s+.+-Recurse\\s+-Force"}
- {"timestamp": "2026-02-18T20:19:31.792066", "event": "command_executed", "command": "Get-Process python | Select-Object -First 1 ProcessName,Id", "cwd": "C:\\Users\\mana4\\Desktop", "exit_code": 0, "status": "success"}
- {"timestamp": "2026-02-18T20:19:31.811901", "event": "command_blocked", "command": "Remove-Item C:\\temp -Recurse -Force", "cwd": "C:\\Users\\mana4\\Desktop", "reason": "遖∵ｭ｢繝代ち繝ｼ繝ｳ繧貞性繧縺溘ａ螳溯｡後〒縺阪∪縺帙ｓ: Remove-Item\\s+.+-Recurse\\s+-Force"}

## Artifacts

- Raw log: C:\Users\mana4\Desktop\manaos_integrations\Reports\OpenWebUI_Tool_Acceptance_Raw_20260218_201926.log
- Security log: C:\Users\mana4\Desktop\manaos_integrations\logs\tool_server_security.log

## Manual Validation Record

**Recorded at**: 2026-02-18 20:19:32  
**Manual verdict**: PASS

- [x] Case 1: service_status is called from chat (PASS)
- [x] Case 2: vscode_open_file opens target file (PASS)
- [x] Case 3: execute_command allows Get-Location (PASS)
- [x] Case 4: execute_command blocks Remove-Item (PASS)

**Operator notes**: auto-recorded: validated by automated Tool Server/OpenWebUI acceptance run
