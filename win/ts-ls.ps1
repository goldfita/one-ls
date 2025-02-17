param(
    [String]$ls_path,
    [string]$executable)

# The typescript language server uses vscode-languageserver, which kills itself after 3 seconds if it can't
# find the parent process, set by 'clientProcessId'. You can set this flag to 0 to disable. However, the
# typescript server will not accept this as a legitimate flag. You can bypass the options parser by using the
# end-of-paramateres token. The trouble is, it needs to happen where the executable is run: in the npx.ps1
# script. So you need to escape the end-of-parameters token by putting it in quotes. If you don't put it in
# quotes, you end up executing (1) below instead of (2).
#
# (1) node.exe npx-cli.js npx typescript-language-server --stdio --clientProcessId=0
# (2) node.exe npx-cli.js npx typescript-language-server --stdio -- --clientProcessId=0

& npx "${executable}" --stdio '--' --clientProcessId=0
