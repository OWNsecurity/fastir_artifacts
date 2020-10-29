# FastIR Artifacts

## What is FastIR Artifacts

FastIR Artifacts is a forensic artifacts collector that can be used on a live host.

FastIR Artifacts is focused on artifact collection, there is no parsing or analysis of the collected artifacts.

It is cross platform: there is one code base that can run on GNU/Linux, Windows or Mac OS X.

It leverages the [Digital Forensics Artifact Repository](https://github.com/ForensicArtifacts/artifacts) for artifact definitions (the Digital Forensics Artifact Repository is a free, community-sourced, machine-readable knowledge base of digital forensic artifacts).

It also leverages the [Sleuth Kit library](https://github.com/py4n6/pytsk) if the file system is supported.

## Download

Binaries for Windows, GNU/Linux and Mac OS X can be downloaded from the [release page](../../releases) of the project.

## Running

FastIR Artifacts must be run with admin rights (for instance using sudo on GNU/Linux or Mac OS X, or an UAC elevation on Windows).

Run FastIR Artifacts with -h argument to see available options.
```
C:\Users\sekoia\Desktop\fastir_artifacts>fastir_artifacts.exe -h
usage: fastir_artifacts.exe [-h] [-i INCLUDE] [-e EXCLUDE]
                            [-d DIRECTORY [DIRECTORY ...]] [-l] [-m MAXSIZE]
                            [-o OUTPUT] [-s]

FastIR Artifacts - Collect ForensicArtifacts Args that start with '--' (eg.
-i) can also be set in a config file
(fastir_artifacts.ini). Config file
syntax allows: key=value, flag=true, stuff=[a,b,c] (for details, see syntax at
https://goo.gl/R74nmi). If an arg is specified in more than one place, then
commandline values override config file values which override defaults.

optional arguments:
  -h, --help            show this help message and exit
  -i INCLUDE, --include INCLUDE
                        Artifacts to collect (comma-separated)
  -e EXCLUDE, --exclude EXCLUDE
                        Artifacts to ignore (comma-separated)
  -d DIRECTORY [DIRECTORY ...], --directory DIRECTORY [DIRECTORY ...]
                        Directory containing Artifacts definitions
  -l, --library         Keep loading Artifacts definitions from the
                        ForensicArtifacts library (in addition to custom
                        directories)
  -m MAXSIZE, --maxsize MAXSIZE
                        Do not collect file with size > n
  -o OUTPUT, --output OUTPUT
                        Directory where the results are created
  -s, --sha256          Compute SHA-256 of collected files
```

Options can be taken from command line switches or from a `fastir_artifacts.ini` configuration file.

Without any `include` or `exclude` argument set, FastIR Artifacts will collect a set of artifacts
defined in `examples/sekoia.yaml` designed for quick acquisition.

## Creating a custom FastIR Artifacts collector from a release

To create a custom FastIR Artifacts collector (custom artifact definitions and custom options):

- download a release for your operating system, unzip it
- create a directory with your custom artifact definitions inside the `fastir_artifacts` folder, for instance `custom_artifacts`
- create a `fastir_artifacts.ini` file
- add a `directory = custom_artifacts` line to the `fastir_artifacts.ini` file
- add more options to the `fastir_artifacts.ini` file for instance `library = True` and  `exclude = BrowserCache,WindowsSearchDatabase`
- zip the `fastir_artifacts` folder and ship it

## Custom Artifact Types

FastIR Artifacts supports the following artifact types in addition to the types defined by the [Digital Forensics Artifact Repository](https://github.com/ForensicArtifacts/artifacts).

### FileInfo

The FileInfo artifact type can be used to collect metadata about files instead of collecting the files themselves:

```yaml
name: System32 Metadata
doc: Metadata about dll and exe files in System32.
sources:
- type: FILE_INFO
  attributes:
    paths:
    - '%%environ_systemroot%%\System32\*.dll'
    - '%%environ_systemroot%%\System32\*.exe'
    - '%%environ_systemroot%%\System32\**\*.dll'
    - '%%environ_systemroot%%\System32\**\*.exe'
    separator: '\'
supported_os: [Windows]
```

It collects the following information (stored in a JSONL file using [Elastic Common Schema](https://www.elastic.co/guide/en/ecs/current/index.html)):

- MD5 hash
- SHA-1 hash
- SHA-256 hash
- Mime type
- File size
- Imphash (PE only)
- Compilation Date (PE only)
- Company Name (PE only)
- File Description (PE only)
- File Version (PE only)
- Internal Name (PE only)
- Product Name (PE only)

## Development

### Requirements

python 3 and pip must be installed.  FastIR was successfully tested with python 3.6 and 3.7.

On Windows, Microsoft Visual C++ 14.0 is needed (See [Windows Compilers](https://wiki.python.org/moin/WindowsCompilers)).

Dependencies can be installed with:
```
pip install -U -r requirements.txt
```

### Generating binaries

PyInstaller can freeze FastIR Artifacts into a one-folder bundle:
```
pyinstaller fastir_artifacts.spec
```
