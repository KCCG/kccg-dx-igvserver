#!/bin/bash
server=ubuntu@seave.bio
dest=/home/ubuntu/apps/kccg-dx-igvserver/
#rsync -av virtualenv-1.11.6 requirements.txt dx-igv-registry.py $server:$dest
rsync Readme.md Readme.Developer.md requirements.txt dx-igv-registry.py $server:$dest
