param(
    [string]$ls_path,
    [string]$executable)

& "${ls_path}\ls-jdk\bin\java.exe"  `
  "-DwatchParentProcess=false" `
  -jar "${ls_path}\lemminx\${executable}"
