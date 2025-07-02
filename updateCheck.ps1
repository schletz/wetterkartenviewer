#Requires -Version 3

# Vor der Ausführung des Skriptes muss 
# Set-ExecutionPolicy Bypass
# einmalig als Admin in der PowerShell konsole ausgeführt werden.

$ErrorActionPreference = 'SilentlyContinue'

# Die Konfiguration lesen. Der notwendige Aufbau ist:
# <Jobs delay="60" outDir = "C:/Users/Michael/Desktop/">
#   <Job title="wetter3" url="http://www1.wetter3.de/Animation_18_UTC_GEFS/384_1_ens.gif" />
#   ...
# </Jobs>

[xml]$jobs = Get-Content -Path "$PSScriptRoot/updateCheck.xml"
"Readed Jobs"
$jobs.Jobs.Job | Format-Table -AutoSize
# Defaultwerte setzen, falls keine Option im XML gesetzt wurde.
# Siehe https://stackoverflow.com/questions/10623907/null-coalescing-in-powershell
$outDir = ($jobs.Jobs.outDir , '.' -ne $null)[0]
$delay = ($jobs.Jobs.delay , 60 -ne $null)[0]

while (1) {
    foreach ($job in $jobs.Jobs.Job) {
        "Process $($job.title)..."
        # In ein Temp File laden
        $tempFilename = (New-Guid).Guid + ".tmp"
        $hash = "NULL"
        try {
            # Die URL (vom XML) laden
            $randomNr = (New-Guid).Guid.Replace("-", "");
            Invoke-WebRequest -Uri "$($job.url)?rand=$randomNr" -OutFile "$outDir/$tempFilename"
            # Den Hash berechnen
            $hash = (Get-FileHash "$outDir/$tempFilename" -Algorithm SHA256).hash
            $ext = $job.url.SubString($job.url.LastIndexOf(".") + 1, $job.url.Length - $job.url.LastIndexOf(".") - 1)
            # Das Tempfile in den Titel (vom XML), gefolgt von _ und den Hash mit der Erweiterung aus der URL umbenennen
            # Wenn sich der Hash ändert, wird so eine neue Datei erstellt.
            Rename-Item -Path "$outDir/$tempFilename" -NewName "$outDir/$($job.title)_$hash.$ext"
        }
        catch {

        }
        finally {
            # Wenn was schiefgeht, haben wir so keine unnötigen temporären Dateien
            Remove-Item "$outDir/$tempFilename"
        }


        $date = (Get-Date).ToUniversalTime()
        $printDate = $date.ToString("u")        
        $unixDate = Get-Date $date -UFormat "%s"
        # Datum, Titel (vom XML) und Hash in die Logdatei (updateCheck.log.txt) schreiben.
        "$printDate`t$unixDate`t$($job.title)`t$hash" >> "$outDir/updateCheck.log.txt"
        "$printDate`t$($job.title)`t$hash"
    }
    Start-Sleep -Seconds $delay
}

