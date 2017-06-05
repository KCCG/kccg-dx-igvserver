We’ve setup an IGV server to make it easier to access the WGS data.

# IGV Setup
Setup is simple, and you only have to do this once:
* open IGV, version 2.3.90 or newer
* View > Preferences > Advanced
* set Data Registry URL = https://seave.bio/igvdata/LKCGP/$$_dataServerRegistry.txt
* Change LKCGP to your group if necessary, eg MoST, TxGen, ...
* Hit OK
* Ensure that your reference genome is “Human (1kg, b37+decoy)”

# Usage:
* open IGV, version 2.3.90 or newer
* File > Load from Server...
* Enter your username + password
* Select the appropriate data to load.

## Hints:
* the BAM files with (tdf) at the end of their name are BAM files that are linked to genome-wide coverage files (tdf format). These will let you still see read coverage if you zoom out beyond 10Kb.
* The data lives in the US, so loading the reads can be slow. So I disable IGV from loading them by default, via: View > Preferences > Alignments: On initial load show: only Coverage Track.
* You can load the reads when you need them by right clicking the coverage track, and then ‘load alignments’

## Getting Access
If you’d like access, please choose a username + password, then visit http://www.kxs.net/support/htaccess_pw.html, 
enter this information, and let Mark, or Vel know.

# Installation
* See Readme.Developer.md for instructions on how to install it.

# Administration
* To add a project to the server:


    ./dx-igv-registry.py -p $project_id -g LKCGP
* To add many projects to the server:


    for project_id in $(dx find projects --tag LKCGP --brief); do ./dx-igv-registry.py -p $project_id -g LKCGP; done
