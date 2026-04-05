# Windows 任务计划程序 - 一键设置脚本
# 以管理员身份运行 PowerShell 后执行此脚本

# 项目路径（自动获取脚本所在目录）
$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  新闻分析工作流 - 自动任务设置" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "项目路径: $projectPath" -ForegroundColor Yellow
Write-Host ""

# 检查批处理文件是否存在
$batchFiles = @(
    "run_collect_auto.bat",
    "run_report_auto.bat",
    "run_send_email_auto.bat"
)

foreach ($file in $batchFiles) {
    $filePath = Join-Path $projectPath $file
    if (-not (Test-Path $filePath)) {
        Write-Host "错误: 找不到 $file" -ForegroundColor Red
        exit 1
    }
}

Write-Host "批处理文件检查通过" -ForegroundColor Green
Write-Host ""

# 创建采集任务
$collectTimes = @(
    @{Name="早上7点"; Time="07:00"},
    @{Name="下午3点"; Time="15:00"},
    @{Name="晚上11点"; Time="23:00"}
)

foreach ($item in $collectTimes) {
    $taskName = "新闻采集-$($item.Name)"

    # 删除已存在的任务
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

    # 创建新任务
    $action = New-ScheduledTaskAction -Execute "$projectPath\run_collect_auto.bat" -WorkingDirectory $projectPath
    $trigger = New-ScheduledTaskTrigger -Daily -At $item.Time
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries

    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "自动采集新闻" -RunLevel Highest | Out-Null

    Write-Host "已创建任务: $taskName ($($item.Time))" -ForegroundColor Green
}

# 创建报告生成任务（采集后5分钟生成报告）
$taskName = "新闻报告生成"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "$projectPath\run_report_auto.bat" -WorkingDirectory $projectPath
$trigger = New-ScheduledTaskTrigger -Daily -At "07:05"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "自动生成报告" -RunLevel Highest | Out-Null

Write-Host "已创建任务: $taskName (07:05)" -ForegroundColor Green

# 创建邮件发送任务
$taskName = "新闻邮件发送"
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

$action = New-ScheduledTaskAction -Execute "$projectPath\run_send_email_auto.bat" -WorkingDirectory $projectPath
$trigger = New-ScheduledTaskTrigger -Daily -At "08:30"
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "自动发送邮件" -RunLevel Highest | Out-Null

Write-Host "已创建任务: $taskName (08:30)" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  所有任务创建完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "时间表（北京时间）：" -ForegroundColor Yellow
Write-Host "  07:00  采集新闻"
Write-Host "  07:05  生成报告"
Write-Host "  08:30  发送邮件"
Write-Host "  15:00  采集新闻"
Write-Host "  23:00  采集新闻"
Write-Host ""
Write-Host "提示: 打开'任务计划程序'可以查看和管理这些任务" -ForegroundColor Yellow
