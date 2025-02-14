param(
    [string]$ls_path,
    [string]$executable,
    [string]$client_host=$null,
    [int]$client_port=0)

$client = ""
if ($client_host) {
    $client = "-DCLIENT_HOST=${client_host}", "-DCLIENT_PORT=${client_port}"
}

# These should be set in Windows
#$env:JAVA_HOME="${ls_path}\jdk"
#$env:PATH="${ls_path}\jdk\bin;$env:PATH"

&"${ls_path}\ls-jdk\bin\java.exe" `
  @client `
  "-DwatchParentProcess=false" `
  "-Declipse.application=org.eclipse.jdt.ls.core.id1" `
  "-Dosgi.bundles.defaultStartLevel=4" `
  "-Declipse.product=org.eclipse.jdt.ls.core.product" `
  "-Dlog.level=ALL" `
  -Xmx1G `
  --add-modules=ALL-SYSTEM `
  --add-opens java.base/java.util=ALL-UNNAMED `
  --add-opens java.base/java.lang=ALL-UNNAMED `
  -jar "${ls_path}\eclipse.jdt.ls\plugins\${executable}" `
  -configuration "${ls_path}\eclipse.jdt.ls\config_win" `
  -data "${ls_path}\ls-workspace"
