#!/bin/bash
sha=$(git log -1 --pretty=oneline | awk '{ print $1 }' | cut -c1-10)
date=$(date '+%Y%m%d-%H%M%S')
echo "$date-$sha"
