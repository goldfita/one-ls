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

## Java

The language server may require a different version of the JDK than the one needed for your project. Download
the version you need into `<root>/ls-jdk` and set `JAVA_HOME="<root>\ls-jdk"`.

## Node/Npm

Install the [official .msi](https://nodejs.org/en/download/).

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
uber jar to `<root>/lemminx`.

#### TypeScript

`npm i -g typescript-language-server typescript`

#### Bash

`npm i bash-language-server -g`

Workaround for punycode deprecation:

`npm i punycode -g`

Replace `require("punycode")` with `require("punycode/")`.

#### Rust

[Download](https://github.com/rust-lang/rust-analyzer/releases/) `rust-analyzer-x86_64-pc-windows-msvc.zip` and expand into `<root>/ls-rust`.

[Install](https://www.rust-lang.org/tools/install) `rustup` and run `rustup component add rust-src`.

# Configuration

There is an `exec.conf` file in `<root>/one-ls` so that the binaries are not hard coded into the run scripts.
The format is `<server id>=<binary>`. For example:

```
jdtls=org.eclipse.equinox.launcher_1.6.400.v20210924-0641.jar
bashls=bash-language-server
```

The `server.conf` file tells `one-ls` which modes are available for each language server. All language servers
seem to be able to communicate over stdio but may not be able to operate as a client or server.

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
