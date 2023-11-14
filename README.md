# One-LS Overview

This is a simple service that starts and stops language servers. It's intented
to work with Emacs, but it will work with any client as long as you have the
ability to prepend a small amount of data to the socket when it's first opened.

# Windows Install

I will assume everything in installed in <root>. Set environment variable
`ONE_LS_PATH="<root>/one-ls"`. Put one-ls files in this directory. Install
python if you don't have it already. If you want to run it as a Window's
service, run the commands below. Then you just need to find "Language Server
Service" in services and set it to automatic.

`python.exe -m pip install --upgrade pywin32
python.exe one-ls.py install`


## Java

The language server may require a different version of the JDK than the one
needed for your project. Download the version you need into <root>/ls-jdk and
set `JAVA_HOME="<root>\ls-jdk"`.

## Node/Npm

Install the official .msi: https://nodejs.org/en/download/

Create the following files.

> <root>
>   nodejs
>     npm
>       .npmrc
> C:\Users\<username>\.npmrc
      
Add the following text to both .npmrc files.

`prefix=<root>\\nodejs\\npm
cache="<root>\\nodejs\\npm-cache"`

Set environment variable `NODE_PATH="<root>\nodejs\npm"`.

## Language Servers

### Clients

#### Emacs

Check specific package's `xxx-download-url` for version number.

### Servers

#### Java

Download JKD and expand into <root>/eclipse.jdt.ls.
https://download.eclipse.org/jdtls/milestones/

#### XML

Download uber jar to <root>/lemminx.
https://repo.eclipse.org/content/repositories/lemminx-releases/org/eclipse/lemminx/org.eclipse.lemminx/

#### Bash

`npm i bash-language-server -g`

Workaround for punycode deprecation:

`npm i punycode -g`
Replace **require("punycode")** with **require("punycode/")**.

# Configuration

There is an exec.conf file in <root>/one-ls so that the binaries are not hard coded
into the run scripts. The format is `<server id>=<binary>`. For example:

`jdtls=org.eclipse.equinox.launcher_1.6.400.v20210924-0641.jar
bashls=bash-language-server`
