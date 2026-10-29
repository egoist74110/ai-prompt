# Windows Shell Commands

Applies whenever you run commands whose execution side is native Windows: the runtime's shell tool on Windows (PowerShell 5.1, pwsh 7+, cmd, Git Bash/MSYS) and calls from WSL into Windows executables. Not for macOS/Linux. Writing a maintained script deliverable -> also the `script-engineering` Skill.

## 1. Know the tool's shell

The shell is the one your command tool actually runs, not the OS. Identify it once per session (Git Bash / Windows PowerShell 5.1 / pwsh 7+ / cmd) and write commands in that language. Reuse an already-known fact; do not probe every command.

## 2. One parsing layer, or a file

- Direct: commands written in the tool's own shell that call cmdlets/executables directly.
- MUST NOT pass non-trivial code as a string to another interpreter: `powershell -Command`, `pwsh -c`, `cmd /c`, `bash -c`, `wsl ...`, `ssh host "..."`. Trivial = one call, no argument containing whitespace, none of `` ` `` `$ " ' ( ) { } ; | & % ! @ #`, no non-ASCII. Anything else is non-trivial.
- Non-trivial PowerShell -> write a `.ps1` with the file-write tool into the scratch/temp directory (a task-owned temporary under `capabilities/cleanup.md`: track it when written, delete it once its last run is done), then run it: `pwsh -NoProfile -NonInteractive -File "<path>" [args]`; only 5.1 present -> `powershell.exe -NoProfile -NonInteractive -File "<path>" [args]`. `-File` arguments arrive as literal strings, so the outer layer adds no quoting.
- Never create the script with `echo`/`>`/`Out-File` (5.1 writes UTF-16/ANSI). Encoding per `script-engineering`: ASCII, or UTF-8 with BOM when 5.1 may run it.
- Execution policy blocks the file -> add `-ExecutionPolicy Bypass` to that one invocation only; never `Set-ExecutionPolicy`.
- Prefer literals inside the file over values passed as arguments; an argument starting with `-` may bind as a parameter.
- C# MUST NOT be inlined: no `Add-Type -TypeDefinition`/`-MemberDefinition` with a here-string or string. Write a `.cs` file and load it with `Add-Type -Path "<path>"` from the `.ps1`. Rules: `script-engineering` §3 C#.
- Logic that is mostly data/JSON/filesystem work -> a Python script file run the same way, if Python is available.

## 3. Native executables inside PowerShell

- Single-quote every argument containing `( ) { } @ ; , $ # ' <space>`, e.g. `icacls $f /grant '*S-1-5-32-544:(F)'`.
- `--%` forwards the rest of the line verbatim to the executable (no `$var` expansion; ends at newline or `|`). Use it for cmd-style strings such as SDDL; never with values that must expand.
- Embedded double quotes in native arguments are mangled by 5.1 and pwsh < 7.3: avoid them (use `--%`, a file, or stdin).
- Check `$LASTEXITCODE` after a native call whose result matters; `$?` and `-ErrorAction` do not cover it.

## 4. Git Bash calling Windows programs

- MSYS rewrites `/switch` and POSIX-looking arguments into Windows paths (`/grant` -> `C:/Program Files/Git/grant`). Prefix with `MSYS_NO_PATHCONV=1` or use the PowerShell file route.
- Bash expands `$`, backticks, and `!` inside double quotes before PowerShell sees them: never inline PowerShell code there; use §2.

## 5. When bitten

Symptoms: `ParserError`, `Unexpected token`, `Missing expression`, an argument fragment reported as "not recognized as the name of a cmdlet", a mangled path, a variable that arrived empty. Treat it as a quoting-layer failure: switch to the §2 file route immediately. At most one requoting attempt before switching; never cycle quote styles.

## 6. Boundaries

- Every temporary `.ps1`/`.cs`/`.py` follows `capabilities/cleanup.md`; delete them before reporting.
- Changing the runtime's default shell (e.g. to Git Bash) is persistent config: suggest it to the user if bites keep recurring; never change it yourself.
