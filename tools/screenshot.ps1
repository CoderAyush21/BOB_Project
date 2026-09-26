<#
.SYNOPSIS
  Evidence screenshots for the Bug Vaccine hackathon run.

.EXAMPLE
  # Capture the whole screen (e.g. IBM Bob working, terminal output)
  powershell -ExecutionPolicy Bypass -File tools/screenshot.ps1 -Name 03-hunt-subagents

.EXAMPLE
  # Render an HTML report to an image (uses Microsoft Edge headless)
  powershell -ExecutionPolicy Bypass -File tools/screenshot.ps1 -Name 04-report-before -Html report-before.html

Images are saved to screenshots/auto/<timestamp>_<Name>.png.
Only this repo's own windows and reports should be captured, so close anything
private (email, chats, passwords) before running.
#>
param(
  [Parameter(Mandatory = $true)][string]$Name,
  [string]$Html,
  [int]$Width = 1200,
  [int]$Height = 1400,
  [int]$DelaySeconds = 1
)
$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$outDir = Join-Path $root 'screenshots\auto'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$safe = ($Name -replace '[^A-Za-z0-9._-]', '-')
$out = Join-Path $outDir ("{0}_{1}.png" -f (Get-Date -Format 'yyyyMMdd-HHmmss'), $safe)

if ($Html) {
  $edge = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
  ) | Where-Object { Test-Path $_ } | Select-Object -First 1
  if (-not $edge) { throw 'Microsoft Edge not found; cannot render HTML to an image.' }
  $page = (Resolve-Path $Html).Path
  $url = 'file:///' + ($page -replace '\\', '/' -replace ' ', '%20')
  # Edge logs progress to stderr; Start-Process keeps PowerShell 5.1 from treating that as an error
  $log = [System.IO.Path]::GetTempFileName()
  Start-Process -FilePath $edge -Wait -WindowStyle Hidden -RedirectStandardError $log -ArgumentList @(
    '--headless=new', '--disable-gpu', '--hide-scrollbars', "--window-size=$Width,$Height", "`"--screenshot=$out`"", "`"$url`"")
  Remove-Item $log -ErrorAction SilentlyContinue
  # Edge can return before the file is flushed
  for ($i = 0; $i -lt 20 -and -not (Test-Path $out); $i++) { Start-Sleep -Milliseconds 250 }
} else {
  Start-Sleep -Seconds $DelaySeconds
  Add-Type -AssemblyName System.Windows.Forms, System.Drawing
  Add-Type @'
using System.Runtime.InteropServices;
public static class DpiAware { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }
'@
  [DpiAware]::SetProcessDPIAware() | Out-Null   # capture at real resolution on scaled displays
  $b = [System.Windows.Forms.SystemInformation]::VirtualScreen
  $bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
  $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
}

if (-not (Test-Path $out)) { throw "Screenshot failed: $out was not created." }
Write-Output "Saved $out"
