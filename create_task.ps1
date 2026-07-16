
$action = New-ScheduledTaskAction -Execute "G:\ai软件\git\zhipu manage\auto_import.bat"
$trigger = New-ScheduledTaskTrigger -Daily -At 08:00
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
Register-ScheduledTask -TaskName "AI-note-pipeline-RSS-import" -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force
