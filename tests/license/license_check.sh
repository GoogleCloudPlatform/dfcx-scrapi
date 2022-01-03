#!/bin/bash
# Copyright 2021 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

header="Copyright [0-9]{4} Google LLC."
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