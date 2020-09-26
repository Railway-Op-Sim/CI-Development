$url = "https://github.com/AlbertBall/railway-dot-exe/releases/download/v2.5.1/Release.v2.5.1.zip"

$output = "RailwayOperationSimulator.zip"

$wc = New-Object System.Net.WebClient

$wc.DownloadFile($url, $output)

Expand-Archive -LiteralPath $output

Get-ChildItem .
