# HWP -> HWPX 일괄 변환기 (한글 COM 사용)
# 변환 로직 기준: 참고_원본\HWP_to_PPT_Auto.ps1 의 Read-HwpWithHancom (Open -> SaveAs "HWPX")
# 사용: HWP_to_HWPX_Batch.cmd 더블클릭. input\ 의 *.hwp 를 output\ 에 같은 이름 .hwpx 로 저장.

# ===== 설정값 (여기만 고치면 된다) =====
$ToolRoot          = $PSScriptRoot                    # 이 스크립트가 있는 폴더
$InputDir          = Join-Path $ToolRoot 'input'      # 변환할 원본 HWP
$OutputDir         = Join-Path $ToolRoot 'output'     # HWPX와 로그 저장 위치
$IncludeSubfolders = $false                           # $true 면 input 하위 폴더도 처리(output에 같은 폴더 구조로 저장)
$OpenOptions       = 'forceopen:true;suspendpassword:true'   # 암호 입력 창을 띄우지 않음(우회 아님)
# ======================================

$ErrorActionPreference = 'Stop'
foreach ($d in @($InputDir, $OutputDir)) {
    if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

$gci = @{ LiteralPath = $InputDir; File = $true }
if ($IncludeSubfolders) { $gci.Recurse = $true }
$files = @(Get-ChildItem @gci | Where-Object { $_.Extension -ieq '.hwp' } | Sort-Object FullName)

$results = New-Object System.Collections.Generic.List[object]
function Add-Result([string]$Name, [string]$Result, [string]$Reason) {
    $results.Add([pscustomobject]@{ '파일명' = $Name; '결과' = $Result; '사유' = $Reason })
    Write-Host ("[{0}] {1} {2}" -f $Result, $Name, $Reason)
}

Write-Host "입력: $InputDir"
Write-Host "출력: $OutputDir"
Write-Host ("대상 HWP: {0}개" -f $files.Count)

$prefix = ($InputDir.TrimEnd('\') + '\')
$jobs = foreach ($f in $files) {
    $rel = $f.FullName.Substring($prefix.Length)
    $out = Join-Path $OutputDir ([System.IO.Path]::ChangeExtension($rel, '.hwpx'))
    [pscustomobject]@{ File = $f; Rel = $rel; Out = $out }
}

$todo = @()
foreach ($j in $jobs) {
    if (Test-Path -LiteralPath $j.Out) { Add-Result $j.Rel '건너뜀' 'output에 같은 이름의 HWPX가 이미 있음' }
    else { $todo += $j }
}

if ($todo.Count -gt 0) {
    $hwp = $null
    $hwpBefore = @(Get-Process -Name Hwp -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
    try {
        $hwp = New-Object -ComObject HWPFrame.HwpObject
        # 창 숨기기(Visible=false)를 쓰면 문서 열기에서 멈추는 경우가 있어 창을 숨기지 않는다
        try { $hwp.SetMessageBoxMode(0x00020000) | Out-Null } catch {}

        foreach ($j in $todo) {
            $tmp = $null
            try {
                $outDir = Split-Path -Parent $j.Out
                if (-not (Test-Path -LiteralPath $outDir)) { New-Item -ItemType Directory -Path $outDir | Out-Null }
                $tmp = Join-Path $outDir ('~tmp_' + [guid]::NewGuid().ToString('N') + '.hwpx')

                $opened = $hwp.Open($j.File.FullName, '', $OpenOptions)
                if (-not $opened) { throw '한글에서 문서를 열지 못함(배포용·암호·보안 문서이거나 보안 승인 창 문제일 수 있음)' }
                $saved = $hwp.SaveAs($tmp, 'HWPX', '')
                if (-not $saved -or -not (Test-Path -LiteralPath $tmp)) { throw 'HWPX 저장 실패' }
                # 저장 직후 한글이 파일을 잡고 있으므로 문서를 닫은 뒤 이름을 바꾼다
                try { $hwp.Clear(1) | Out-Null } catch {}
                $moved = $false
                for ($k = 0; $k -lt 10 -and -not $moved; $k++) {
                    try { Move-Item -LiteralPath $tmp -Destination $j.Out; $moved = $true }
                    catch { Start-Sleep -Milliseconds 500; if ($k -eq 9) { throw } }
                }
                Add-Result $j.Rel '성공' ''
            }
            catch {
                Add-Result $j.Rel '실패' $_.Exception.Message
            }
            finally {
                if ($tmp -and (Test-Path -LiteralPath $tmp)) { Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue }
                try { $hwp.Clear(1) | Out-Null } catch {}
            }
        }
    }
    catch {
        foreach ($j in $todo) {
            if (-not ($results | Where-Object { $_.'파일명' -eq $j.Rel })) { Add-Result $j.Rel '실패' ("한글 실행 오류: " + $_.Exception.Message) }
        }
    }
    finally {
        if ($null -ne $hwp) {
            try { $hwp.Quit() } catch {}
            try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($hwp) } catch {}
        }
        [gc]::Collect()
        [gc]::WaitForPendingFinalizers()
        # Quit 뒤에도 남는 한글 프로세스 중 이 스크립트가 시작한 것만 정리(원래 열려 있던 한글은 건드리지 않음)
        Start-Sleep -Seconds 2
        Get-Process -Name Hwp -ErrorAction SilentlyContinue |
            Where-Object { $hwpBefore -notcontains $_.Id } |
            Stop-Process -Force -ErrorAction SilentlyContinue
    }
}

$logPath = Join-Path $OutputDir ('변환로그_{0}.csv' -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
$csv = ($results | ConvertTo-Csv -NoTypeInformation) -join "`r`n"
[System.IO.File]::WriteAllText($logPath, $csv + "`r`n", (New-Object System.Text.UTF8Encoding($true)))

$ok   = @($results | Where-Object { $_.'결과' -eq '성공' }).Count
$skip = @($results | Where-Object { $_.'결과' -eq '건너뜀' }).Count
$fail = @($results | Where-Object { $_.'결과' -eq '실패' }).Count
Write-Host ""
Write-Host ("완료: 성공 {0} / 건너뜀 {1} / 실패 {2}" -f $ok, $skip, $fail)
Write-Host "로그: $logPath"
