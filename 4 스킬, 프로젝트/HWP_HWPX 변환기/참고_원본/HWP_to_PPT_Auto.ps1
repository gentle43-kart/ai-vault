#requires -version 5.1

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.Windows.Forms.Application]::EnableVisualStyles()

$script:AppDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:DefaultTemplate = Join-Path $script:AppDir "MBC_자체심의_템플릿.pptx"
$script:TempDirectories = New-Object System.Collections.Generic.List[string]

function New-TempDirectory {
    $path = Join-Path ([System.IO.Path]::GetTempPath()) ("HwpPptAuto_" + [guid]::NewGuid().ToString("N"))
    [System.IO.Directory]::CreateDirectory($path) | Out-Null
    $script:TempDirectories.Add($path)
    return $path
}

function Normalize-Whitespace([string]$Text) {
    if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
    $value = $Text -replace "`r", "" -replace "[\u0000\u000B\u000C]", " "
    $value = $value -replace "[ \u00A0]+", " "
    $value = $value -replace " *`n *", "`n"
    return $value.Trim()
}

function Get-XmlAttributeByLocalName($Node, [string[]]$Names) {
    if ($null -eq $Node -or $null -eq $Node.Attributes) { return $null }
    foreach ($attribute in $Node.Attributes) {
        if ($Names -contains $attribute.LocalName) { return $attribute.Value }
    }
    return $null
}

function Read-HwpxPackage([string]$Path) {
    $tempDir = New-TempDirectory
    [System.IO.Compression.ZipFile]::ExtractToDirectory($Path, $tempDir)

    $itemMap = @{}
    $manifestCandidates = @(
        (Join-Path $tempDir "Contents\content.hpf"),
        (Join-Path $tempDir "content.hpf")
    )
    foreach ($manifestPath in $manifestCandidates) {
        if (-not (Test-Path -LiteralPath $manifestPath)) { continue }
        [xml]$manifest = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8
        foreach ($item in $manifest.SelectNodes("//*[local-name()='item']")) {
            $id = Get-XmlAttributeByLocalName $item @("id")
            $href = Get-XmlAttributeByLocalName $item @("href")
            if ($id -and $href) {
                $decodedHref = [System.Uri]::UnescapeDataString($href).Replace("/", "\")
                $candidate = Join-Path (Split-Path -Parent $manifestPath) $decodedHref
                if (-not (Test-Path -LiteralPath $candidate)) { $candidate = Join-Path $tempDir $decodedHref }
                if (Test-Path -LiteralPath $candidate) { $itemMap[$id] = $candidate }
            }
        }
    }

    $sectionRoot = Join-Path $tempDir "Contents"
    if (-not (Test-Path -LiteralPath $sectionRoot)) { $sectionRoot = $tempDir }
    $sectionFiles = Get-ChildItem -LiteralPath $sectionRoot -Filter "section*.xml" -File | Sort-Object Name
    $blocks = New-Object System.Collections.Generic.List[object]
    foreach ($section in $sectionFiles) {
        [xml]$xml = Get-Content -LiteralPath $section.FullName -Raw -Encoding UTF8
        foreach ($paragraph in $xml.SelectNodes("//*[local-name()='p']")) {
            $pieces = New-Object System.Collections.Generic.List[string]
            foreach ($textNode in $paragraph.SelectNodes(".//*[local-name()='t']")) {
                if ($null -ne $textNode.InnerText) { $pieces.Add($textNode.InnerText) }
            }
            $imagePaths = New-Object System.Collections.Generic.List[string]
            foreach ($img in $paragraph.SelectNodes(".//*[local-name()='img']")) {
                $ref = Get-XmlAttributeByLocalName $img @("binaryItemIDRef", "binaryItemID", "idRef")
                if ($ref -and $itemMap.ContainsKey($ref) -and -not $imagePaths.Contains($itemMap[$ref])) {
                    $imagePaths.Add($itemMap[$ref])
                }
            }
            $blocks.Add([pscustomobject]@{
                Text = (Normalize-Whitespace ($pieces -join ""))
                Images = @($imagePaths)
            })
        }
    }

    if ($itemMap.Count -eq 0) {
        $binDir = Join-Path $tempDir "BinData"
        if (-not (Test-Path -LiteralPath $binDir)) { $binDir = Join-Path $tempDir "Contents\BinData" }
        if (Test-Path -LiteralPath $binDir) {
            $allImages = Get-ChildItem -LiteralPath $binDir -File | Where-Object { $_.Extension -match '^\.(png|jpe?g|bmp|gif|tif?f)$' }
            if ($blocks.Count -eq 0) { $blocks.Add([pscustomobject]@{ Text = ""; Images = @($allImages.FullName) }) }
        }
    }

    $flatText = Normalize-Whitespace (($blocks | ForEach-Object { $_.Text }) -join "`n")
    return [pscustomobject]@{ Text = $flatText; Blocks = @($blocks); TempDir = $tempDir }
}

function Read-HwpWithHancom([string]$Path) {
    $hwp = $null
    $tempDir = New-TempDirectory
    $hwpxPath = Join-Path $tempDir "converted.hwpx"
    try {
        $hwp = New-Object -ComObject HWPFrame.HwpObject
        try { $hwp.XHwpWindows.Item(0).Visible = $false } catch {}
        try { $hwp.SetMessageBoxMode(0x00020000) | Out-Null } catch {}
        $opened = $hwp.Open($Path, "", "forceopen:true;suspendpassword:true")
        if (-not $opened) { throw "한글 문서를 열지 못했습니다." }
        $text = $hwp.GetTextFile("TEXT", "")
        $saved = $hwp.SaveAs($hwpxPath, "HWPX", "")
        if (-not $saved -or -not (Test-Path -LiteralPath $hwpxPath)) {
            return [pscustomobject]@{ Text = (Normalize-Whitespace $text); Blocks = @(); TempDir = $tempDir }
        }
        $package = Read-HwpxPackage $hwpxPath
        if (-not [string]::IsNullOrWhiteSpace($text)) { $package.Text = Normalize-Whitespace $text }
        return $package
    }
    catch {
        throw "HWP 읽기 실패: $($_.Exception.Message)`n한글에서 파일을 HWPX로 저장한 뒤 다시 시도할 수 있습니다."
    }
    finally {
        if ($null -ne $hwp) {
            try { $hwp.Clear(1) | Out-Null } catch {}
            try { $hwp.Quit() } catch {}
            try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($hwp) } catch {}
        }
        [gc]::Collect()
        [gc]::WaitForPendingFinalizers()
    }
}

function Read-InputDocument([string]$Path) {
    $ext = [System.IO.Path]::GetExtension($Path).ToLowerInvariant()
    switch ($ext) {
        ".hwp"  { return Read-HwpWithHancom $Path }
        ".hwpx" { return Read-HwpxPackage $Path }
        ".txt"  { return [pscustomobject]@{ Text = (Get-Content -LiteralPath $Path -Raw -Encoding UTF8); Blocks = @(); TempDir = $null } }
        ".md"   { return [pscustomobject]@{ Text = (Get-Content -LiteralPath $Path -Raw -Encoding UTF8); Blocks = @(); TempDir = $null } }
        default  { throw "지원 형식은 HWP, HWPX, TXT, MD입니다." }
    }
}

function Get-FieldKey([string]$Line) {
    $patterns = @(
        @{ Key = "ignore"; Pattern = '^\s*[■□●○▪▶\-]*\s*심의규정\s*위반사항\s*및\s*특이사항\s*[:：]?\s*(.*)$' },
        @{ Key = "program"; Pattern = '^\s*[■□●○▪▶\-]*\s*(?:프로그램\s*(?:명칭|명)|프로그램\s*\(등급\)|프\s+로\s+그\s+램\s*(?:\(등급\))?)\s*[:：]?\s*(.*)$' },
        @{ Key = "date"; Pattern = '^\s*[■□●○▪▶\-]*\s*(?:방송\s*(?:일자|일시|일))\s*[:：]?\s*(.*)$' },
        @{ Key = "span"; Pattern = '^\s*[■□●○▪▶\-]*\s*방송\s*시간\s*[:：]?\s*(.*)$' },
        @{ Key = "time"; Pattern = '^\s*[■□●○▪▶\-]*\s*(?:방송\s*시각|시\s*각)\s*[:：]?\s*(.*)$' },
        @{ Key = "related"; Pattern = '^\s*[■□●○▪▶\-]*\s*(?:심의규정|심\s*의\s*규\s*정|관련조항|관련\s*조항)\s*[:：]?\s*(.*)$' },
        @{ Key = "content"; Pattern = '^\s*[■□●○▪▶\-]*\s*방송내용\s*(?:-\s*특이사항)?\s*[:：]?\s*(.*)$' },
        @{ Key = "opinion"; Pattern = '^\s*[■□●○▪▶\-]*\s*(?:(?:문제제기\s*및\s*)?의견|검토의견)\s*[:：]?\s*(.*)$' },
        @{ Key = "images"; Pattern = '^\s*[■□●○▪▶\-]*\s*방송화면\s*(?:\(필요시\s*첨부\))?\s*[:：]?\s*(.*)$' },
        @{ Key = "ignore"; Pattern = '^\s*[■□●○▪▶\-]*\s*(?:프로그램\s*(?:유형|종류|장르|성격|형태)|방송\s*(?:지역|구분|형태|분야|시점)|방\s*송\s*광\s*고|필\s*러|특\s*이\s*사\s*항|심의규정\s*위반사항\s*및\s*특이사항)\s*[:：]?\s*(.*)$' },
        @{ Key = "station"; Pattern = '^\s*[■□●○▪▶\-]*\s*(?:방송사\s*명칭|방송사명|방송사|채널명|채\s*널)\s*[:：]?\s*(.*)$' }
    )
    foreach ($entry in $patterns) {
        if ($Line -match $entry.Pattern) {
            return [pscustomobject]@{ Key = $entry.Key; Rest = $Matches[1].Trim() }
        }
    }
    return $null
}

function New-EmptyCase {
    return [ordered]@{ station = ""; program = ""; date = ""; span = ""; time = ""; related = ""; content = ""; opinion = ""; images = @() }
}

function Add-CaseIfMeaningful($Cases, $Case) {
    if (-not [string]::IsNullOrWhiteSpace($Case.program) -or -not [string]::IsNullOrWhiteSpace($Case.content) -or -not [string]::IsNullOrWhiteSpace($Case.opinion)) {
        $Cases.Add([pscustomobject]$Case)
    }
}

function Parse-MonitorReport([string]$Text, [object[]]$Blocks, [string]$InputPath) {
    $normalized = Normalize-Whitespace ($Text -replace "`t", "`n")
    $normalized = $normalized -replace '(?m)^심\s*\n의\s*\n규\s*\n정$', '심 의 규 정'
    $normalized = $normalized -replace '(?m)^특\s*\n이\s*\n사\s*\n항$', '특 이 사 항'
    $normalized = $normalized -replace '(?m)^방송\s*\n(개요|분야|시점)$', '방송 $1'
    $lines = @($normalized -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" })
    $cases = New-Object System.Collections.Generic.List[object]
    $current = New-EmptyCase
    $activeKey = $null

    foreach ($line in $lines) {
        $field = Get-FieldKey $line
        if ($null -ne $field) {
            if ($field.Key -in @("program", "station") -and -not [string]::IsNullOrWhiteSpace($current.program) -and
                (-not [string]::IsNullOrWhiteSpace($current.content) -or -not [string]::IsNullOrWhiteSpace($current.opinion))) {
                Add-CaseIfMeaningful $cases $current
                $stationCarry = $current.station
                $current = New-EmptyCase
                $current.station = $stationCarry
            }
            $activeKey = $field.Key
            if ($activeKey -notin @("images", "ignore")) {
                $current[$activeKey] = $field.Rest
            }
            continue
        }
        if ($activeKey -and $activeKey -notin @("images", "ignore")) {
            if ($activeKey -eq "program" -and $line -match '^\(등급\)$') { continue }
            if ([string]::IsNullOrWhiteSpace($current[$activeKey])) { $current[$activeKey] = $line }
            else { $current[$activeKey] = ($current[$activeKey] + "`n" + $line).Trim() }
        }
    }
    Add-CaseIfMeaningful $cases $current

    if ($cases.Count -eq 0) { throw "'프로그램명/방송내용/의견' 구조를 찾지 못했습니다." }

    $imageGroups = @()
    for ($i = 0; $i -lt $cases.Count; $i++) { $imageGroups += ,(New-Object System.Collections.Generic.List[string]) }
    $caseIndex = -1
    foreach ($block in @($Blocks)) {
        if ($block.Text -match '프로그램\s*(?:명|명칭)|프\s*로\s*그\s*램') { $caseIndex++ }
        if ($caseIndex -ge 0 -and $caseIndex -lt $cases.Count) {
            foreach ($img in @($block.Images)) {
                if ((Test-Path -LiteralPath $img) -and -not $imageGroups[$caseIndex].Contains($img)) { $imageGroups[$caseIndex].Add($img) }
            }
        }
    }

    $filename = [System.IO.Path]::GetFileNameWithoutExtension($InputPath)
    $stationGuess = ""
    if ($normalized -match '(?im)^\s*(TBC|대구\s*MBC|MBC|KBS|SBS|EBS|CBS|YTN)\b') { $stationGuess = $Matches[1] }
    elseif ($filename -match '(TBC|MBC|KBS|SBS|EBS|CBS|YTN)') { $stationGuess = $Matches[1] }

    for ($i = 0; $i -lt $cases.Count; $i++) {
        if ([string]::IsNullOrWhiteSpace($cases[$i].station)) { $cases[$i].station = $stationGuess }
        $cases[$i].images = @($imageGroups[$i])
    }
    return @($cases)
}

function Shorten-Text([string]$Text, [int]$MaxLength) {
    $value = (Normalize-Whitespace $Text) -replace "`n+", " "
    if ($value.Length -le $MaxLength) { return $value }
    $cut = $value.Substring(0, $MaxLength)
    $last = $cut.LastIndexOf(" ")
    if ($last -gt [math]::Floor($MaxLength * 0.7)) { $cut = $cut.Substring(0, $last) }
    return $cut.TrimEnd(" ", ".", ",") + "…"
}

function Get-CaseTitle($Case) {
    $all = (($Case.content + " " + $Case.opinion + " " + $Case.related) -replace "`n", " ")
    if ($all -match '선거인\s*수' -and $all -match '증가|감소|줄었|늘었|증감') { return "선거인 수 증감 관련 부정확한 보도" }
    if ($all -match '소방\s*(안전\s*)?기준|스프링클러' -and $all -match '미적용|충족|소급|설치') { return "소방설비 현황 관련 부정확한 보도" }
    if ($all -match '자료화면.*(재사용|과거|무관)|과거.*(영상|화면).*재사용') { return "자료화면 재사용 및 미고지" }
    if ($all -match '역주행|인도.*(주행|운행)|공원.*(주행|운행)|교통법규') { return "교통법규 위반 장면 등 송출" }
    if ($all -match '신용카드|CVC|개인정보|금융정보') { return "민감한 개인정보 노출" }
    if ($all -match '안전띠|동승\s*보호자') { return "안전띠 미착용 등 법령 위반 장면" }
    if ($all -match '오송출|무음|방송사고|강제\s*종료') { return "자료화면·음향 방송사고" }
    if ($all -match '관람등급') { return "공연 관람등급 미고지" }
    if ($all -match '비속어|욕설|방송언어') { return "부적절한 방송언어" }
    if ($all -match '부정확|사실과\s*다르|오인|객관성') { return "사실관계가 불명확한 보도" }
    $first = (Normalize-Whitespace $Case.content) -split '[.!?。]|`n' | Select-Object -First 1
    if ([string]::IsNullOrWhiteSpace($first)) { return "자체심의 검토사항" }
    return Shorten-Text $first 28
}

function Get-CaseSummary($Case) {
    $content = Normalize-Whitespace $Case.content
    $opinion = Normalize-Whitespace $Case.opinion
    if ([string]::IsNullOrWhiteSpace($content)) { $content = $opinion }
    $summary = Shorten-Text $content 360
    if (-not [string]::IsNullOrWhiteSpace($opinion)) {
        $opinionSentences = @($opinion -split '(?<=[.!?])\s+|`n+' | Where-Object { $_ -match '오인|우려|소지|위반|부적절|미고지|노출|정확성|객관성' })
        if ($opinionSentences.Count -gt 0) {
            $point = Shorten-Text $opinionSentences[0] 150
            if ($summary -notlike "*$point*") { $summary = "$summary`n`n($point)" }
        }
    }
    return Shorten-Text $summary 480
}

function Get-CaseWarnings($Case) {
    $warnings = New-Object System.Collections.Generic.List[string]
    foreach ($pair in @(@("program", "프로그램명"), @("date", "방송일"), @("related", "관련조항"), @("content", "방송내용"))) {
        if ([string]::IsNullOrWhiteSpace($Case.($pair[0]))) { $warnings.Add("$($pair[1]) 누락") }
    }
    if ($Case.related -match '법|시행령|시행규칙|제\s*\d+\s*조') { $warnings.Add("법령·조문 최신성 확인 필요") }
    if ($Case.date -match '^\d{1,2}[./-]\d{1,2}') { $warnings.Add("방송일 연도 확인 필요") }
    if (@($Case.images).Count -eq 0) { $warnings.Add("방송화면 미추출") }
    return @($warnings)
}

function Convert-ToSlideCases([object[]]$Cases) {
    $result = New-Object System.Collections.Generic.List[object]
    foreach ($case in $Cases) {
        $displayTime = $case.time
        if ([string]::IsNullOrWhiteSpace($displayTime)) { $displayTime = $case.span }
        $dateTime = ("$($case.date) $displayTime").Trim()
        $program = (Normalize-Whitespace $case.program) -replace "`n", " "
        $program = $program -replace '\s*\((?:등급없음|등급제외|\d+세\s*이상|전체관람가)\)\s*$', ''
        $relatedText = Normalize-Whitespace $case.related
        $relatedLines = @($relatedText -split "`n" | Where-Object { $_ -match '제\s*\d+\s*조|법|규정' })
        if ($relatedLines.Count -gt 1) {
            $specific = @($relatedLines | Where-Object { $_ -match '제\s*\d+\s*조' })
            if ($specific.Count -gt 0) { $related = ($specific -join " ") } else { $related = ($relatedLines -join " ") }
        } else { $related = (Normalize-Whitespace $case.related) -replace "`n", " " }
        $result.Add([pscustomobject]@{
            station = $case.station
            title = Get-CaseTitle $case
            program = $program
            datetime = $dateTime -replace "`n", " "
            related = $related
            summary = Get-CaseSummary $case
            images = @($case.images | Select-Object -First 3)
            warnings = @(Get-CaseWarnings $case)
            source_content = $case.content
            source_opinion = $case.opinion
        })
    }
    return @($result)
}

function Get-ShapeByName($Slide, [string]$Name) {
    for ($i = 1; $i -le $Slide.Shapes.Count; $i++) {
        $shape = $Slide.Shapes.Item($i)
        if ($shape.Name -eq $Name) { return $shape }
    }
    return $null
}

function Set-ShapeText($Slide, [string]$Name, [string]$Text) {
    $shape = Get-ShapeByName $Slide $Name
    if ($null -eq $shape) { throw "템플릿 도형을 찾지 못했습니다: $Name" }
    $shape.TextFrame.TextRange.Text = $Text
    try { $shape.TextFrame2.AutoSize = 2 } catch {}
}

function Add-ImagesToSlide($Slide, [string[]]$ImagePaths) {
    $old = Get-ShapeByName $Slide "Picture 3"
    if ($null -ne $old) {
        $left = $old.Left; $top = $old.Top; $width = $old.Width; $height = $old.Height
        $old.Delete()
    } else {
        $left = 540; $top = 160; $width = 630; $height = 390
    }
    $paths = @($ImagePaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 3)
    if ($paths.Count -eq 0) { return }

    $gap = 6
    for ($i = 0; $i -lt $paths.Count; $i++) {
        if ($paths.Count -eq 1) { $boxLeft = $left; $boxTop = $top; $boxWidth = $width; $boxHeight = $height }
        elseif ($paths.Count -eq 2) { $boxLeft = $left; $boxTop = $top + $i * (($height + $gap) / 2); $boxWidth = $width; $boxHeight = ($height - $gap) / 2 }
        else {
            if ($i -eq 0) { $boxLeft = $left; $boxTop = $top; $boxWidth = $width; $boxHeight = ($height - $gap) * 0.58 }
            else { $boxWidth = ($width - $gap) / 2; $boxHeight = ($height - $gap) * 0.42; $boxLeft = $left + ($i - 1) * ($boxWidth + $gap); $boxTop = $top + ($height - $boxHeight) }
        }
        $pic = $Slide.Shapes.AddPicture($paths[$i], 0, -1, $boxLeft, $boxTop, -1, -1)
        $pic.LockAspectRatio = -1
        $scale = [math]::Min($boxWidth / $pic.Width, $boxHeight / $pic.Height)
        $pic.Width = $pic.Width * $scale
        $pic.Height = $pic.Height * $scale
        $pic.Left = $boxLeft + ($boxWidth - $pic.Width) / 2
        $pic.Top = $boxTop + ($boxHeight - $pic.Height) / 2
    }
}

function Write-AuditJson([string]$Path, [object[]]$Cases, [string]$InputPath, [string]$TemplatePath) {
    $payload = [ordered]@{
        schema_version = "1.0"
        generated_at = (Get-Date).ToString("o")
        input = $InputPath
        template = $TemplatePath
        cases = $Cases
    }
    $json = $payload | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText($Path, $json, (New-Object System.Text.UTF8Encoding($false)))
}

function Create-Presentation([string]$TemplatePath, [string]$OutputPath, [object[]]$Cases) {
    if (-not (Test-Path -LiteralPath $TemplatePath)) { throw "PPT 템플릿을 찾을 수 없습니다." }
    Copy-Item -LiteralPath $TemplatePath -Destination $OutputPath -Force

    $ppt = $null
    $presentation = $null
    try {
        $ppt = New-Object -ComObject PowerPoint.Application
        $presentation = $ppt.Presentations.Open($OutputPath, 0, 0, 0)
        if ($presentation.Slides.Count -lt 3) { throw "템플릿에 사례 원형 슬라이드(3번)가 없습니다." }

        $originalIds = @()
        for ($i = 1; $i -le $presentation.Slides.Count; $i++) {
            $originalIds += [int]$presentation.Slides.Item($i).SlideID
        }
        $coverId = [int]$presentation.Slides.Item(1).SlideID
        $sourceSlide = $presentation.Slides.Item(3)

        $station = @($Cases | ForEach-Object { $_.station } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -First 1)
        if ($station.Count -eq 0) { $stationName = "방송사" } else { $stationName = $station[0] }
        Set-ShapeText $presentation.Slides.Item(1) "직사각형 6" "$stationName 자체심의 참고사항"

        foreach ($case in $Cases) {
            $range = $sourceSlide.Duplicate()
            $slide = $range.Item(1)
            $slide.MoveTo($presentation.Slides.Count)
            Set-ShapeText $slide "Google Shape;103;p15" $case.summary
            Set-ShapeText $slide "Google Shape;107;p15" $case.program
            Set-ShapeText $slide "Google Shape;109;p15" $case.datetime
            Set-ShapeText $slide "Google Shape;111;p15" $case.related
            Set-ShapeText $slide "Google Shape;112;p15" $case.title
            Add-ImagesToSlide $slide $case.images
            if ($case.warnings.Count -gt 0) {
                try { $slide.NotesPage.Shapes.Placeholders.Item(2).TextFrame.TextRange.Text = "자동검토: " + ($case.warnings -join "; ") } catch {}
            }
        }

        for ($i = $presentation.Slides.Count; $i -ge 1; $i--) {
            $slide = $presentation.Slides.Item($i)
            if (($originalIds -contains [int]$slide.SlideID) -and [int]$slide.SlideID -ne $coverId) { $slide.Delete() }
        }
        $presentation.Save()
    }
    finally {
        if ($null -ne $presentation) { try { $presentation.Close() } catch {}; try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($presentation) } catch {} }
        if ($null -ne $ppt) { try { $ppt.Quit() } catch {}; try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($ppt) } catch {} }
        [gc]::Collect(); [gc]::WaitForPendingFinalizers()
    }
}

function Show-Error([string]$Message) {
    [System.Windows.Forms.MessageBox]::Show($Message, "HWP → PPT 자동생성기", "OK", "Error") | Out-Null
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "HWP → PPT 자체심의 참고자료 자동생성기"
$form.Size = New-Object System.Drawing.Size(820, 510)
$form.StartPosition = "CenterScreen"
$form.Font = New-Object System.Drawing.Font("맑은 고딕", 10)
$form.MaximizeBox = $false
$form.FormBorderStyle = "FixedDialog"

function Add-Label([string]$Text, [int]$X, [int]$Y, [int]$Width = 110) {
    $label = New-Object System.Windows.Forms.Label
    $label.Text = $Text; $label.Location = New-Object System.Drawing.Point($X, $Y); $label.Size = New-Object System.Drawing.Size($Width, 25)
    $form.Controls.Add($label); return $label
}

Add-Label "모니터 보고서" 25 28 | Out-Null
$inputBox = New-Object System.Windows.Forms.TextBox
$inputBox.Location = New-Object System.Drawing.Point(145, 25); $inputBox.Size = New-Object System.Drawing.Size(545, 26)
$form.Controls.Add($inputBox)
$inputButton = New-Object System.Windows.Forms.Button
$inputButton.Text = "찾기"; $inputButton.Location = New-Object System.Drawing.Point(705, 23); $inputButton.Size = New-Object System.Drawing.Size(75, 30)
$form.Controls.Add($inputButton)

Add-Label "PPT 템플릿" 25 73 | Out-Null
$templateBox = New-Object System.Windows.Forms.TextBox
$templateBox.Location = New-Object System.Drawing.Point(145, 70); $templateBox.Size = New-Object System.Drawing.Size(545, 26); $templateBox.Text = $script:DefaultTemplate
$form.Controls.Add($templateBox)
$templateButton = New-Object System.Windows.Forms.Button
$templateButton.Text = "찾기"; $templateButton.Location = New-Object System.Drawing.Point(705, 68); $templateButton.Size = New-Object System.Drawing.Size(75, 30)
$form.Controls.Add($templateButton)

Add-Label "저장 폴더" 25 118 | Out-Null
$outputBox = New-Object System.Windows.Forms.TextBox
$outputBox.Location = New-Object System.Drawing.Point(145, 115); $outputBox.Size = New-Object System.Drawing.Size(545, 26)
$form.Controls.Add($outputBox)
$outputButton = New-Object System.Windows.Forms.Button
$outputButton.Text = "찾기"; $outputButton.Location = New-Object System.Drawing.Point(705, 113); $outputButton.Size = New-Object System.Drawing.Size(75, 30)
$form.Controls.Add($outputButton)

$notice = New-Object System.Windows.Forms.Label
$notice.Location = New-Object System.Drawing.Point(25, 160); $notice.Size = New-Object System.Drawing.Size(755, 55)
$notice.Text = "HWP 입력에는 한글 프로그램이 필요합니다. PowerPoint가 설치되어 있어야 PPTX를 생성할 수 있습니다.`r`n생성 결과와 함께 검토용 JSON이 저장됩니다. 법령·조문과 자동 요약은 최종 확인이 필요합니다."
$form.Controls.Add($notice)

$logBox = New-Object System.Windows.Forms.TextBox
$logBox.Location = New-Object System.Drawing.Point(25, 225); $logBox.Size = New-Object System.Drawing.Size(755, 170)
$logBox.Multiline = $true; $logBox.ReadOnly = $true; $logBox.ScrollBars = "Vertical"
$form.Controls.Add($logBox)

$generateButton = New-Object System.Windows.Forms.Button
$generateButton.Text = "PPT 생성"; $generateButton.Location = New-Object System.Drawing.Point(650, 410); $generateButton.Size = New-Object System.Drawing.Size(130, 42)
$form.Controls.Add($generateButton)

$inputButton.Add_Click({
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Filter = "한글·텍스트 문서|*.hwp;*.hwpx;*.txt;*.md|모든 파일|*.*"
    if ($dialog.ShowDialog() -eq "OK") {
        $inputBox.Text = $dialog.FileName
        if ([string]::IsNullOrWhiteSpace($outputBox.Text)) { $outputBox.Text = Split-Path -Parent $dialog.FileName }
    }
})
$templateButton.Add_Click({
    $dialog = New-Object System.Windows.Forms.OpenFileDialog
    $dialog.Filter = "PowerPoint 템플릿|*.pptx"
    if ($dialog.ShowDialog() -eq "OK") { $templateBox.Text = $dialog.FileName }
})
$outputButton.Add_Click({
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    if ($dialog.ShowDialog() -eq "OK") { $outputBox.Text = $dialog.SelectedPath }
})

$generateButton.Add_Click({
    try {
        $inputPath = $inputBox.Text.Trim(); $templatePath = $templateBox.Text.Trim(); $outputDir = $outputBox.Text.Trim()
        if (-not (Test-Path -LiteralPath $inputPath)) { throw "모니터 보고서 파일을 선택하십시오." }
        if (-not (Test-Path -LiteralPath $templatePath)) { throw "PPT 템플릿 파일을 확인하십시오." }
        if ([string]::IsNullOrWhiteSpace($outputDir)) { $outputDir = Split-Path -Parent $inputPath; $outputBox.Text = $outputDir }
        if (-not (Test-Path -LiteralPath $outputDir)) { [System.IO.Directory]::CreateDirectory($outputDir) | Out-Null }

        $generateButton.Enabled = $false; $form.UseWaitCursor = $true; $logBox.Clear()
        $logBox.AppendText("1/4 문서를 읽는 중...`r`n"); [System.Windows.Forms.Application]::DoEvents()
        $document = Read-InputDocument $inputPath
        $logBox.AppendText("2/4 사례를 구조화하는 중...`r`n"); [System.Windows.Forms.Application]::DoEvents()
        $parsed = Parse-MonitorReport $document.Text $document.Blocks $inputPath
        $slideCases = Convert-ToSlideCases $parsed
        $logBox.AppendText("   사례 $($slideCases.Count)건을 확인했습니다.`r`n")

        $base = [System.IO.Path]::GetFileNameWithoutExtension($inputPath)
        $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $pptPath = Join-Path $outputDir ("${base}_자체심의_참고자료_${stamp}.pptx")
        $jsonPath = [System.IO.Path]::ChangeExtension($pptPath, ".json")
        $logBox.AppendText("3/4 PPT를 생성하는 중...`r`n"); [System.Windows.Forms.Application]::DoEvents()
        Create-Presentation $templatePath $pptPath $slideCases
        Write-AuditJson $jsonPath $slideCases $inputPath $templatePath
        $warningCount = @($slideCases | ForEach-Object { $_.warnings }).Count
        $logBox.AppendText("4/4 완료`r`nPPT: $pptPath`r`n검토 JSON: $jsonPath`r`n검토표시: ${warningCount}건`r`n")
        [System.Windows.Forms.MessageBox]::Show("PPT 생성이 완료되었습니다.`n사례 $($slideCases.Count)건, 검토표시 ${warningCount}건", "완료", "OK", "Information") | Out-Null
        Start-Process explorer.exe "/select,`"$pptPath`""
    }
    catch { Show-Error $_.Exception.Message; $logBox.AppendText("오류: $($_.Exception.Message)`r`n") }
    finally { $generateButton.Enabled = $true; $form.UseWaitCursor = $false }
})

$form.Add_FormClosed({
    foreach ($tempDir in $script:TempDirectories) {
        if (Test-Path -LiteralPath $tempDir) { try { Remove-Item -LiteralPath $tempDir -Recurse -Force } catch {} }
    }
})

[void]$form.ShowDialog()
