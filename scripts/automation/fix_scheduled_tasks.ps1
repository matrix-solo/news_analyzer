# Fix Scheduled Tasks Script
# Run as Administrator

$projectPath = "C:\Users\matrix\Desktop\news_workflow\news_analyzer"
$scriptsPath = "$projectPath\scripts\automation"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  News Analyzer - Fix Scheduled Tasks" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Delete old tasks
$oldTasks = @(
    "News-Collect-7AM",
    "News-Collect-3PM", 
    "News-Collect-11PM",
    "News-Report-Generate",
    "News-Email-Send",
    "News-Collect-Report-7AM"
)

foreach ($task in $oldTasks) {
    Unregister-ScheduledTask -TaskName $task -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Deleted: $task" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Creating new tasks..." -ForegroundColor Green
Write-Host ""

# Create collect tasks
$collectTimes = @(
    @{Name="News-Collect-7AM"; Time="07:00"},
    @{Name="News-Collect-3PM"; Time="15:00"},
    @{Name="News-Collect-11PM"; Time="23:00"}
)

foreach ($item in $collectTimes) {
    $action = New-ScheduledTaskAction -Execute "$scriptsPath\run_collect_auto.bat" -WorkingDirectory $projectPath
    $trigger = New-ScheduledTaskTrigger -Daily -At $item.Time
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    
    Register-ScheduledTask -TaskName $item.Name -Action $action -Trigger $trigger -Settings $settings -Description "Auto collect news" -RunLevel Highest | Out-Null
    
    Write-Host "Created: $($item.Name) ($($item.Time))" -ForegroundColor Green
}

# Create report task
$action = New-ScheduledTaskAction -Execute "$scriptsPath\run_report_auto.bat" -WorkingDirectory $projectPath
$trigger = New-ScheduledTaskTrigger -Daily -At "07:05"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "News-Report-Generate" -Action $action -Trigger $trigger -Settings $settings -Description "Auto generate report" -RunLevel Highest | Out-Null

Write-Host "Created: News-Report-Generate (07:05)" -ForegroundColor Green

# Create email task
$action = New-ScheduledTaskAction -Execute "$scriptsPath\run_send_email_auto.bat" -WorkingDirectory $projectPath
$trigger = New-ScheduledTaskTrigger -Daily -At "08:30"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName "News-Email-Send" -Action $action -Trigger $trigger -Settings $settings -Description "Auto send email" -RunLevel Highest | Out-Null

Write-Host "Created: News-Email-Send (08:30)" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  All tasks created!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Schedule:" -ForegroundColor Yellow
Write-Host "  07:00  Collect news"
Write-Host "  07:05  Generate report"
Write-Host "  08:30  Send email"
Write-Host "  15:00  Collect news"
Write-Host "  23:00  Collect news"
