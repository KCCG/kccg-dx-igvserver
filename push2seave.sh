#!/bin/bash
# simple script to push the latest version of the app to seave.bio.
# it's here becacuse you can't git pull the repo from outside GIMR w/out VPN.
#
# Mark Cowley
server=ubuntu@seave.bio
dest=/home/ubuntu/apps/kccg-dx-igvserver/
#rsync -av virtualenv-1.11.6 requirements.txt dx-igv-registry.py $server:$dest
rsync Readme.md Readme.Developer.md requirements.txt dx-igv-registry.py $server:$dest
