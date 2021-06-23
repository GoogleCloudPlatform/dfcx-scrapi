#!/bin/bash
# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# Checks that all python files under have the following license:
#
# Copyright 2021 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

header="Copyright [0-9]{4} Google LLC. This software is provided as-is"
files=("$(git ls-files '*[a-z].py')")
bad_files=()

if [ -z "$files" ]; then exit 0; fi
for file in "${files[@]}"; do
    bad_files+=($(grep -EL "$header" $file))
done

if [ -n "$bad_files" ]
then
    echo "Copyright header missing from following files:"
    for file in "${bad_files[@]}"; do
        echo "   - $file";
    done
    exit 1;
else
    echo "Check completed successfully.";
    exit 0;
fi