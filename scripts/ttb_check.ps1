$result = cat .\Output.txt

if( "0" -ne $result )
{
    Write-Output "Timetable Validation Failed with Message: "
	Write-Output $result
    exit 12345
}
else
{
    Write-Output "Timetable Validation Successful"
    exit 0
}