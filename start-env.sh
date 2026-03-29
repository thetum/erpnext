#!/bin/bash
export PWDEBUG=1
export $(grep -v '^#' .env | xargs)