$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$pythonWindowless = Join-Path $projectRoot '.venv\Scripts\pythonw.exe'
$syncScript = Join-Path $projectRoot 'python\cloud_sync.py'
$configPath = Join-Path $projectRoot 'data\cloud_sync.json'
$logPath = Join-Path $projectRoot 'data\cloud_sync.log'
if (!(Test-Path -LiteralPath $configPath)) { throw 'Missing data/cloud_sync.json' }
if (!(Test-Path -LiteralPath $pythonWindowless)) { throw 'Missing .venv/Scripts/pythonw.exe' }
$taskArgs = '"{0}" --config "{1}" --log-file "{2}"' -f $syncScript, $configPath, $logPath
$taskAction = New-ScheduledTaskAction -Execute $pythonWindowless -Argument $taskArgs -WorkingDirectory $projectRoot
$taskTrigger = New-ScheduledTaskTrigger -AtLogOn -User ([System.Security.Principal.WindowsIdentity]::GetCurrent().Name)
$taskSettings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName 'BTL-IoT-CloudSync' -Action $taskAction -Trigger $taskTrigger -Settings $taskSettings -Description 'Sync local traffic events and evidence to VPS; retries while offline.' -Force | Out-Null
Start-ScheduledTask -TaskName 'BTL-IoT-CloudSync'
Write-Output 'Cloud sync task installed and started. Log: data/cloud_sync.log'
