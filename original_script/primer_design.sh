#! /usr/bin/bash
version="v1.0"

process_file="/home/ngs/PrimerDesign/script/process_file.sh"

inotifywait -mrq --exclude "\.tmp$|\.swp$" --timefmt '%y-%m-%d %H:%M' --format '%w%f' \
-e create /home/ngs/PrimerDesign/production | xargs -n1 -P10 -I {} bash -c "$process_file {}"
