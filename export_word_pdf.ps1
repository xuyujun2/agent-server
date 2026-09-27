param(
    [Parameter(Mandatory = $true)][string]$InputPath,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
    $doc = $word.Documents.Open($InputPath, $false, $true)
    try {
        $doc.ExportAsFixedFormat($OutputPath, 17)
    }
    finally {
        $doc.Close($false)
    }
}
finally {
    $word.Quit()
}
