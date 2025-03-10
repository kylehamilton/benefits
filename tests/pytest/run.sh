#!/usr/bin/env bash
set -eu

pytest --cov=benefits --cov-branch --import-mode=importlib --no-migrations

# clean out old coverage results
rm -rf benefits/static/coverage
coverage html --directory benefits/static/coverage
