#!/bin/bash

python3 -m scanner.scanner &
sleep 8
python3 -m processing.publisher &
