---
name: script-engineering
description: Mandatory guardrail when writing, modifying, reviewing, or debugging PowerShell, CMD/Batch, Bash, sh, zsh, WSL glue, installer/bootstrap scripts, CI shell snippets, or cross-platform command sequences. Prevents AI-authored script failures from shell/version mismatch, encoding, quoting, paths, line endings, environment assumptions, and missing verification.
---

# Script Engineering

Write scripts that survive the actual target environment, not just the model's imagined environment.

## Core rule

**Never write a non-trivial script before identifying the execution contract. Never claim it works before validating that contract.**

The contract is:

- operating system: Windows / macOS / Linux;
- execution side: native Windows / WSL / container / remote host / CI runner;
- shell and version: Windows PowerShell 5.1 / PowerShell 7+ / cmd.exe / Bash / sh / zsh / other;
- script file vs interactive command;
- file encoding and line-ending requirements;
- required external executables and how they are discovered;
- privilege level and working-directory assumptions.

If a fact is already available from current tool output or local runtime state, reuse it. Do not rediscover it every activation.

## 1. Discover before authoring

For any script that depends on platform behavior, resolve only the facts that matter.

Useful probes include:

### PowerShell

```powershell
$PSVersionTable.PSVersion
$PSVersionTable.PSEdition
[Environment]::OSVersion
(Get-Location).Path
```

Do not infer PowerShell version from the operating system. Windows may run either `powershell.exe` 5.1 or `pwsh.exe` 7+.

### POSIX shells

```sh
uname -s
printf '%s\n' "${SHELL-}"
printf '%s\n' "${BASH_VERSION-}"
```

Do not assume `/bin/sh` is Bash. Do not use Bash-only syntax in a script declared as `#!/bin/sh`.

### WSL

Treat WSL as a separate execution environment. Detect it when relevant rather than assuming that "Windows" implies Windows paths or Windows executables.

Do not mix `C:\...` and `/mnt/c/...` paths casually. Convert at the boundary and keep one path model inside a script.

## 2. Persist machine facts, not machine assumptions

In this repository, machine-specific discoveries belong in `.local/runtime.json` or `.local/state.json`, not in central scripts or skills.

Cache facts such as:

- resolved executable path;
- shell/version actually used;
- WSL/native execution side;
- verified invocation strategy;
- tool availability;
- external config locator;
- last verified success/failure and invalidation condition.

Never commit usernames, home-directory prefixes, tokens, cookies, passwords, private keys, or other secrets.

Do not hard-code product names or executable locations when a runtime registry or discovery mechanism already exists.

## 3. PowerShell compatibility and encoding

### Unknown Windows PowerShell target

If a `.ps1` may run under Windows PowerShell and the version is unknown, **assume Windows PowerShell 5.1 compatibility** unless the project explicitly requires PowerShell 7+.

Do not silently test only with `pwsh` and then claim compatibility with `powershell.exe`.

### Windows PowerShell 5.1 encoding trap

Windows PowerShell 5.1 can misinterpret a UTF-8 script without a BOM when the file contains non-ASCII characters. On a Simplified Chinese Windows installation this can surface as apparent GBK/ANSI decoding corruption, including corruption caused by comments or string literals.

For `.ps1` files that must run under Windows PowerShell 5.1:

- prefer ASCII-only source for generated infrastructure/bootstrap scripts when practical;
- if non-ASCII source text is required, save the file as **UTF-8 with BOM**;
- never assume BOM-less UTF-8 is safe merely because it works in PowerShell 7+ or an editor;
- validate the actual file bytes and run the parser under `powershell.exe` when 5.1 compatibility matters.

For PowerShell 7+-only scripts, UTF-8 without BOM is normally appropriate.

Do not "fix" this problem globally by adding a BOM to every text file.

### PowerShell syntax/version discipline

- Avoid syntax or parameters introduced after 5.1 when 5.1 is in scope.
- Prefer full cmdlet names in maintained scripts; do not rely on interactive aliases.
- Set `$ErrorActionPreference = 'Stop'` when the script requires fail-fast semantics, but understand which native-command failures are not converted into PowerShell exceptions.
- Check `$LASTEXITCODE` for native executables when their exit status matters.
- Quote paths as values; do not construct command lines by concatenating untrusted text.
- Use the call operator `&` for executable paths stored in variables.

## 4. Bash / sh / zsh discipline

Choose the interpreter first, then write to that language.

### Bash

For maintained Bash scripts, normally start with:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

Only use strict mode when the script has been written to handle its semantics correctly. Do not paste it into unknown legacy scripts as a cosmetic change.

### sh

If the shebang is `/bin/sh`, stay POSIX-compatible. Avoid arrays, `[[ ... ]]`, `source`, Bash process substitution, and other Bash-only features.

### Encoding

Shell scripts should normally be UTF-8 **without BOM**. A BOM before a shebang may prevent the operating system from recognizing the interpreter line.

### Quoting

- Quote variable expansions unless splitting/globbing is deliberately required.
- Prefer arrays in Bash for argument vectors instead of building command strings.
- Do not use `eval` to solve ordinary quoting problems.
- Use `--` before user-controlled positional paths when supported by the command.

## 5. CMD / Batch discipline

Batch parsing is unusually fragile. Prefer PowerShell or a portable language for non-trivial new logic unless `.cmd`/`.bat` is required as a compatibility entrypoint.

When Batch is required:

- keep the entrypoint small;
- prefer ASCII-only source;
- treat `%`, `!`, `^`, `&`, `|`, `<`, `>`, parentheses, delayed expansion, and nested quoting as parser-sensitive;
- do not assume UTF-8 code-page changes make arbitrary Unicode batch files reliable;
- test the actual `.cmd`/`.bat` file with `cmd.exe`, not an equivalent interactive command typed elsewhere.

## 6. Cross-platform path rules

Never hard-code examples such as:

```text
C:\Users\alice\...
/Users/alice/...
/home/alice/...
```

unless the user explicitly requested a machine-specific script and that path is a confirmed current fact.

Prefer platform-native discovery:

- PowerShell: `$HOME`, `$env:USERPROFILE`, `[Environment]::GetFolderPath(...)`, `Join-Path`;
- shell: `$HOME`, XDG variables where relevant, `dirname`, `realpath` only if availability is known;
- repository-relative resources: resolve relative to the script's own directory when that is the intended contract, not the caller's current working directory.

Be explicit about path boundaries between Windows and WSL.

## 7. Do not confuse interactive commands with script files

A command that works when pasted interactively may fail when placed in a file because of:

- encoding;
- quoting layer changes;
- variable interpolation;
- shell startup profile differences;
- current directory;
- execution policy or executable bit;
- shebang handling;
- CI runner shell selection.

If the deliverable is a script file, verify the file itself.

## 8. Minimize shell layers

Every additional parsing layer multiplies quoting risk.

Bad pattern:

```text
host language -> shell string -> ssh -> remote shell string -> nested powershell/bash -Command string
```

Prefer, in order:

1. direct process invocation with an argument array;
2. a checked-in or temporary script file passed to the target interpreter;
3. stdin/script-block transport;
4. nested command strings only when unavoidable.

When crossing shells, identify which layer expands each `$`, `%`, quote, backslash, glob, and newline.

## 9. Prefer a portable language when shell is the wrong abstraction

For substantial cross-platform logic, filesystem transforms, JSON mutation, complex retry/state handling, or many quoting layers, prefer an already-available portable runtime such as Python or Node over duplicating large PowerShell and Bash implementations.

Do not introduce a new runtime dependency merely to avoid writing five lines of shell. Reuse what the project already guarantees.

Keep `.ps1`, `.sh`, or `.cmd` wrappers thin when they only need to locate and invoke a portable implementation.

## 10. Validation gate

Before claiming a generated or modified script is correct, validate at the cheapest meaningful layers that are available.

### Byte/encoding checks

For `.ps1` targeting Windows PowerShell 5.1 and containing non-ASCII text, verify the UTF-8 BOM (`EF BB BF`) is actually present.

For shebang-driven Unix scripts, verify there is no BOM before `#!`.

### Parser/syntax checks

Examples:

```sh
bash -n path/to/script.sh
sh -n path/to/script.sh
```

For PowerShell, parse the actual file with the target engine. A useful parser check is:

```powershell
$tokens = $null
$errors = $null
[System.Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$errors) | Out-Null
if ($errors.Count -gt 0) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }
```

When PowerShell 5.1 compatibility matters, execute that check via `powershell.exe`; checking only via `pwsh` is insufficient.

### Linters when already available

Use tools such as ShellCheck or PSScriptAnalyzer when present and relevant. Do not silently install new dependencies just to satisfy this skill.

### Behavioral verification

Run the smallest safe end-to-end invocation that proves:

- arguments survive quoting;
- paths resolve;
- required tools are found;
- expected files/output are produced;
- errors produce a non-zero exit;
- cleanup occurs when applicable.

If the true target environment is unavailable, state exactly what was and was not verified. Do not replace evidence with confidence.

## 11. Review checklist

Before delivery, check:

- [ ] Target OS, execution side, shell, and shell version are known or conservative defaults are explicit.
- [ ] Script file encoding is correct for that interpreter/version.
- [ ] Line endings and shebang are appropriate.
- [ ] No unverified absolute user/machine paths are hard-coded.
- [ ] Repository resources do not depend accidentally on caller cwd.
- [ ] Arguments are passed structurally instead of concatenated into shell code where possible.
- [ ] Variables and paths are quoted for the target shell.
- [ ] Native exit codes are propagated correctly.
- [ ] Temporary resources have cleanup paths.
- [ ] WSL/native path boundaries are explicit.
- [ ] The actual script file was parser-checked with the intended interpreter when available.
- [ ] A representative behavioral invocation was run when safe and possible.

## 12. Handoff on failure

If the script still fails after establishing a deterministic reproduction, hand the concrete reproduction and evidence to the `diagnose` skill. Do not restart from speculative debugging.

If about to claim completion, also obey `verification-before-completion`.
