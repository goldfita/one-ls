param(
    [String]$ls_path,
    [string]$executable)

& npx "${executable}" start --clientProcessId=0
