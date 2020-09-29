Expand-Archive -LiteralPath 'software\TimetableChecker.zip'
Copy-Item -Path 'test_ttbs\master.ttb' 'test.ttb'
Copy-Item -Path 'test_rlys\railway.rly' 'railway.rly'
& ".\TimetableChecker\TimetableChecker\TimetableChecker.exe"

Get-ChildItem .

$result = cat .\Output.txt

if( "0" -ne $result )
{
    Write-Output $result
    exit 12345
}
else
{
    Write-Output "Timetable Validation Successful"
    exit 0
}