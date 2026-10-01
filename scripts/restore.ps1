param([string]$Directory = 'downloads')
$ErrorActionPreference = 'Stop'
$transferRoot = (Resolve-Path -LiteralPath $Directory).Path
$manifests = @(Get-ChildItem -LiteralPath $transferRoot -Filter '*.manifest.json' -File)
if ($manifests.Count -eq 0) { throw "No manifests found in $transferRoot" }
foreach ($manifestFile in $manifests) {
    $manifest = Get-Content -LiteralPath $manifestFile.FullName -Raw | ConvertFrom-Json
    if ([IO.Path]::GetFileName($manifest.filename) -ne $manifest.filename) { throw 'Invalid filename' }
    $outputPath = [IO.Path]::GetFullPath((Join-Path $transferRoot $manifest.filename))
    if ([IO.Path]::GetDirectoryName($outputPath) -ne $transferRoot.TrimEnd('\')) { throw 'Output escapes transfer folder' }
    $temporaryPath = "$outputPath.assembling"
    $destinationStream = $null
    try {
        $destinationStream = [IO.File]::Create($temporaryPath)
        [long]$total = 0
        foreach ($part in $manifest.parts) {
            if ([IO.Path]::GetFileName($part.name) -ne $part.name) { throw 'Invalid part filename' }
            $partPath = Join-Path $transferRoot $part.name
            $partFile = Get-Item -LiteralPath $partPath
            if ($partFile.Length -ne $part.size -or (Get-FileHash -LiteralPath $partPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $part.sha256) {
                throw "Corrupt or incomplete part: $($part.name)"
            }
            $sourceStream = [IO.File]::OpenRead($partPath)
            try { $sourceStream.CopyTo($destinationStream) } finally { $sourceStream.Dispose() }
            $total += $partFile.Length
        }
        $destinationStream.Dispose()
        $destinationStream = $null
        if ($total -ne $manifest.size -or (Get-FileHash -LiteralPath $temporaryPath -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.sha256) {
            throw "Full-file checksum mismatch: $($manifest.filename)"
        }
        Move-Item -LiteralPath $temporaryPath -Destination $outputPath -Force
        Write-Output "VERIFIED $($manifest.filename) $total $($manifest.sha256)"
    } finally {
        if ($null -ne $destinationStream) { $destinationStream.Dispose() }
        if (Test-Path -LiteralPath $temporaryPath) { Remove-Item -LiteralPath $temporaryPath }
    }
}
