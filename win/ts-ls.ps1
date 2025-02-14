param(
    [String]$ls_path,
    [string]$executable)

& npx "${executable}" --stdio -- --clientProcessId=0
