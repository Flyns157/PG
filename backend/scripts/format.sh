#! /usr/bin/env bash
set -x

ruff check app tests --fix
ruff format app tests
