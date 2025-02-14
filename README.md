# One-LS Overview

This is a simple service that starts and stops language servers. It's intended to work with Emacs, but it will
work with any client as long as you have the ability to prepend a small amount of data to the socket when it's
first opened.

# Windows Install

I will assume everything is installed in `<root>`. Set a global environment variable
`ONE_LS_PATH="<root>/one-ls"`. Put one-ls files in this directory. Install python if you don't have it
already. If you want to run it as a Window's service, run the commands below as admin. Then you just need to
find **Language Server Service** in services and set it to automatic.

``` powershell
python.exe -m pip install --upgrade pywin32
python.exe one-ls.py install
```

Environment variables need to be defined for the system. If they're only defined for your user, the service
won't see them. Check the event viewer under `Windows Logs -> Applications` for diagnostic log messages.

## Java

The language server may require a different version of the JDK than the one needed for your project. Download
the version you need for the language server into `<root>/ls-jdk` and create `<root>/ls-workspace`. The log
file will be `<root>/ls-workspace/.metadata/.log`. JAVA_HOME will point to the build JDK.

## Node/Npm

Install the [official .msi](https://nodejs.org/en/download/) or better use [NVM for
Windows](https://github.com/coreybutler/nvm-windows).

Create the following files.

```
<root>
  nodejs
    npm
      .npmrc
C:\Users\<username>\.npmrc
```
   
Add the following text to both .npmrc files.

```
prefix=<root>\\nodejs\\npm
cache="<root>\\nodejs\\npm-cache"
```

Set environment variable `NODE_PATH="<root>\nodejs\npm"`.

## Language Servers

### Clients

#### Emacs

Check specific package's `xxx-download-url` for version number.

### Servers

#### Java

[Download](https://download.eclipse.org/jdtls/milestones/) and expand into `<root>/eclipse.jdt.ls`.

#### XML

[Download](https://repo.eclipse.org/content/repositories/lemminx-releases/org/eclipse/lemminx/org.eclipse.lemminx/)
uber jar to `<root>/lemminx`. Create `<root>/.lsp4xml` directory.

#### TypeScript

`npm i -g typescript-language-server typescript`

#### Bash

`npm i bash-language-server -g`

Workaround for punycode deprecation:

`npm i punycode -g`

Replace `require("punycode")` with `require("punycode/")`.

#### Rust

Set environment variables:

```
RUSTUP_HOME=<root>/rustup
CARGO_HOME=<root>/cargo
```

[Install](https://www.rust-lang.org/tools/install) `rustup` and run:

```
rustup install stable
rustup component add rust-analyzer
rustup component add rust-src
```

# Configuration

There is an `exec.conf` file in `<root>/one-ls` so that the binaries are not hard coded into the run scripts.
The format is `<server id>=<binary>`. For example:

```
jdtls=org.eclipse.equinox.launcher_1.6.400.v20210924-0641.jar
bashls=bash-language-server
```

This executable information gets passed to the relevant script under `<root>/onel-ls/win` to start the
language server. The `server.conf` file tells `one-ls` which modes are available for each language server. All
language servers seem to be able to communicate over stdio but may not be able to operate as a client or
server.

## P

The language server communicates over stdio and `one-ls` will forward IO back to the client. The opening
string sent to `one-ls`:

`language server name>::`

## S

The client connects to the language server on a given port.

`<language server name>::<port #>`

## C

The language server connects back to the client on a given port.

`<language server name>:<host name>:<port #>`
