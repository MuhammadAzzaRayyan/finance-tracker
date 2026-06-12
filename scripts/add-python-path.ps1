$add = 'C:\Users\radit\AppData\Local\Programs\Python\Python314;C:\Users\radit\AppData\Local\Programs\Python\Python314\Scripts'
$p = [Environment]::GetEnvironmentVariable('Path','User')
if (-not $p) { $p = '' }
if ($p -notlike '*Python314*') {
    $new = ($p + ';' + $add).Trim(';')
    [Environment]::SetEnvironmentVariable('Path', $new, 'User')
    Write-Output 'Added to User PATH'
} else {
    Write-Output 'Already in User PATH'
}
