# EagleLint

Eaglint is a style checker for Cadsoft Eagle PCB design files.

## Installation

```
$ cd EagleLint 
$ pip install .
```

This will install several libraries, the most important of which is `Swoop` a Python library for working with Eagle files.

## Test It

```
$ eaglelint --files tests/test.sch tests/test.brd test.lbr
```

It will print out some errors.

## Usage

Get help: `eaglelint --help`


