# installation

## dx-toolkit
    sudo apt-get install -y python-dev
    wget https://wiki.dnanexus.com/images/files/dx-toolkit-v0.222.0-ubuntu-14.04-amd64.tar.gz
    tar -xzvf dx-toolkit-v0.222.0-ubuntu-14.04-amd64.tar.gz 
    sudo mv dx-toolkit /usr/local

## install dx-igv-registry from source
* damn, git clone isn't working with ssh or http

    [[ -d ~/apps ]] || mkdir ~/apps
    cd ~/apps
    git clone ssh://git@kccg.garvan.org.au:7999/nex/kccg-dx-igvserver.git
    cd kccg-dx-igvserver
    git checkout PIPELINE-1215-seave.bio

## dev workaround
    cd ~/src/DNANexus_Applets/kccg-dx-igvserver/
    cat push2seave.sh
    #!/bin/bash
    server=ubuntu@dev.seave.bio
    dest=/home/ubuntu/apps/kccg-dx-igvserver/
    #rsync -av virtualenv-1.11.6 requirements.txt dx-igv-registry.py $server:$dest
    rsync requirements.txt dx-igv-registry.py $server:$dest

    ./push2seave.sh

# usage
    cd /home/ubuntu/apps/kccg-dx-igvserver/
    test -d venv || python virtualenv-1.11.6/virtualenv.py -p python2.7 venv
    source venv/bin/activate
    pip install -r requirements.txt
    dx login --no-projects
    dx select kccg

    ./dx-igv-registry.py -p $project_id -g LKCGP

## usage enmasse
    for project_id in $(dx find projects --tag LKCGP --brief); do ./dx-igv-registry.py -p $project_id -g LKCGP; done
    for project_id in $(dx find projects --tag MoST --brief); do echo ./dx-igv-registry.py -p $project_id -g MoST; done

# Configure IGV
    View > Preferences > Advanced
    https://dev.seave.bio/igvdata/LKCGP/$$_dataServerRegistry.txt

# Dev notes below
## working list LKCGP

set -e -x 
#./dx-igv-registry.py -p project-BzX90F8091y6G80k5QvfvJyj -g LKCGP
#./dx-igv-registry.py -p project-F2QQ3F80K49pYYV93vxq4jZ3 -g LKCGP
#./dx-igv-registry.py -p project-F004qXj0F45GX4x99J3Z12g0 -g LKCGP
./dx-igv-registry.py -p project-BzVbzbj0z4bY5B3jxxg2QzBz -g LKCGP
./dx-igv-registry.py -p project-F13ZJYj0PBx9f3K2PP9FBJXJ -g LKCGP
./dx-igv-registry.py -p project-F3b53pj0p96620706qfvKk2Y -g LKCGP
./dx-igv-registry.py -p project-F41Y4Xj0Bk8fbxQG68KF3x2v -g LKCGP
./dx-igv-registry.py -p project-F48p9P00z8vZ1zK9583ZQp2g -g LKCGP
./dx-igv-registry.py -p project-F40x5V80VbZ82VZg4300kBby -g LKCGP
./dx-igv-registry.py -p project-F3pbb380Xxq6j4gb5kxQXV08 -g LKCGP
./dx-igv-registry.py -p project-F0K7gb80434gp98F7v4yP4Gq -g LKCGP
./dx-igv-registry.py -p project-F30GVP00qp9gZ4vz50yvJJxj -g LKCGP
./dx-igv-registry.py -p project-F172BX009KqbF8Bk64ff0B4x -g LKCGP
./dx-igv-registry.py -p project-F40YVf80kG3bj7566869fzB7 -g LKCGP
