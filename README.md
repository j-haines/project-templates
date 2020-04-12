# Project Templates
A collection of base templates for various projects, such as a C++ project built with Abseil, or a Python webapp built on aiohttp and Vue.js. Includes a script for cloning and initializing a new project based on a given template.

New templates can be created by adding a git submodule to the appropriate language folder.

## Usage

```bash
$ ./project
usage: project.py [-h] {clone} ...

positional arguments:
  {clone}     sub-command

optional arguments:
  -h, --help  show this help message and exit
```

```bash
$ ./project clone -h
usage: project.py clone [-h] {cpp,py3} template destination [project_name]

positional arguments:
  {cpp,py3}     The programming language the new project will be written in.
  template      The name of the template to clone.
  destination   The folder for the new project.
  project_name  The name of the project. Defaults to using the destination
                folder name.

optional arguments:
  -h, --help    show this help message and exit
```

```bash
$ ./project list -h 
usage: project.py list [-h] language

positional arguments:
  language    The programming language to list project templates for.

optional arguments:
  -h, --help  show this help message and exit
```