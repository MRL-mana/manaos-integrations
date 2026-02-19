# OpenWebUI Tool Acceptance Report

**Created at**: 2026-02-18 16:35:14  
**Overall**: PASS  
**Automated checks**: 6 / 6  
**Acceptance exit code**: 0

## Automated Result

- 笨・**Tool Server Health**
- 笨・**Tool Server OpenAPI**
- 笨・**Unified API Health**
- 笨・**Open WebUI**
- 笨・**Integration test**
- 笨・**Automated checks summary**

## Manual Chat Cases (Open WebUI)

- [ ] Case 1: service_status is called from chat
- [ ] Case 2: vscode_open_file opens target file
- [ ] Case 3: execute_command allows Get-Location
- [ ] Case 4: execute_command blocks Remove-Item

## Security Audit Tail

- {"timestamp": "2026-02-18T13:13:31.155772", "event": "command_blocked", "command": "Remove-Item C:\\temp -Recurse -Force", "cwd": "C:\\Users\\mana4\\Desktop", "reason": "遖∵ｭ｢繝代ち繝ｼ繝ｳ繧貞性繧縺溘ａ螳溯｡後〒縺阪∪縺帙ｓ: Remove-Item\\s+.+-Recurse\\s+-Force"}
- {"timestamp": "2026-02-18T13:20:09.646442", "event": "command_executed", "command": "Get-Process python | Select-Object -First 1 ProcessName,Id", "cwd": "C:\\Users\\mana4\\Desktop", "exit_code": 0, "status": "success"}
- {"timestamp": "2026-02-18T13:20:09.672348", "event": "command_blocked", "command": "Remove-Item C:\\temp -Recurse -Force", "cwd": "C:\\Users\\mana4\\Desktop", "reason": "遖∵ｭ｢繝代ち繝ｼ繝ｳ繧貞性繧縺溘ａ螳溯｡後〒縺阪∪縺帙ｓ: Remove-Item\\s+.+-Recurse\\s+-Force"}
- {"timestamp": "2026-02-18T16:35:14.428533", "event": "command_executed", "command": "Get-Process python | Select-Object -First 1 ProcessName,Id", "cwd": "C:\\Users\\mana4\\Desktop", "exit_code": 0, "status": "success"}
- {"timestamp": "2026-02-18T16:35:14.453846", "event": "command_blocked", "command": "Remove-Item C:\\temp -Recurse -Force", "cwd": "C:\\Users\\mana4\\Desktop", "reason": "遖∵ｭ｢繝代ち繝ｼ繝ｳ繧貞性繧縺溘ａ螳溯｡後〒縺阪∪縺帙ｓ: Remove-Item\\s+.+-Recurse\\s+-Force"}

## Artifacts

- Raw log: C:\Users\mana4\Desktop\manaos_integrations\Reports\OpenWebUI_Tool_Acceptance_Raw_20260218_163458.log
- Security log: C:\Users\mana4\Desktop\manaos_integrations\logs\tool_server_security.log
