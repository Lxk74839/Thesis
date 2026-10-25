param([Parameter(Mandatory=$true)][string]$InputDocx,[Parameter(Mandatory=$true)][string]$OutputPdf)
$ErrorActionPreference='Stop'
$application=$null
$document=$null
try {
    $application=New-Object -ComObject Word.Application
    $application.Visible=$false
    $application.DisplayAlerts=0
    if ($application.Documents.Count -ne 0) { throw 'unexpected_existing_Word_documents' }
    $document=$application.Documents.Open($InputDocx,$false,$true,$false)
    $document.ExportAsFixedFormat($OutputPdf,17)
    $pages=$document.ComputeStatistics(2)
    Write-Output "Exported PDF with $pages pages"
} finally {
    $discard=0
    if ($null -ne $document) { $document.Close([ref]$discard); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($document) }
    if ($null -ne $application) { $application.Quit([ref]$discard); [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($application) }
}
