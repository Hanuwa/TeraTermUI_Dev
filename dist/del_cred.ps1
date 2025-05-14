$TargetName = "TeraTermUI/Passphrase/$env:USERNAME@$env:COMPUTERNAME"
try {
    $cred = Get-StoredCredential -Target $TargetName -ErrorAction Stop
    if ($cred) {
        Remove-StoredCredential -Target $TargetName -ErrorAction Stop
        Write-Host "Credential deleted."
    }
} catch {
    if ($_.Exception.HResult -ne -2147023728) {
        Write-Warning "Could not delete credential: $($_.Exception.Message)"
    }
}
