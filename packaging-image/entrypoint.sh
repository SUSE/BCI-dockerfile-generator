#!/bin/bash

if [[ ! -e /root/.config/osc/oscrc ]]; then
    cat << EOF
This container is expected to be launched with your oscrc mounted to
/root/.config/osc/oscrc

Please consult the README or the label 'run' for the full invocation.
EOF
fi

if [[ "-h --help -v --verbose -q --quiet --debug --debugger --post-mortem --traceback -H --http-debug --http-full-debug -A --apiurl --config --setopt --no-keyring add addchannels addcontainers addremove ar aggregatepac api branch getpac bco branchco browse build wipe shell chroot buildconfig buildhistory buildhist buildinfo buildlog buildlogtail blt bl cat less blame changedevelrequest changedevelreq cr checkconstraints checkout co clean cleanassets ca clone comment commit checkin ci config copypac create-pbuild-config cpc createincident createrequest creq delete remove del rm deleterequest deletereq droprequest dropreq dr dependson detachbranch develproject dp bsdevelproject diff di ldiff linkdiff distributions dists downloadassets da enablechannels enablechannel fork getbinaries help importsrcpkg info init jobhistory jobhist linkpac linktobranch list LL lL ll ls localbuildlog lbl lock log maintainer bugowner maintenancerequest mr mbranch maintained sm meta mkpac mv my patchinfo pdiff prdiff projdiff projectdiff prjresults pr pull pull_request rdelete rdiff rebuild rebuildpac release releaserequest remotebuildlog remotebuildlogtail rbuildlogtail rblt rbuildlog rbl repairlink repairwc repo repositories platforms repos repourls request review rq requestmaintainership reqbs reqms reqmaintainership requestbugownership reqbugownership resolved restartbuild abortbuild results r revert rpmlintlog lint rpmlint rremove search bse se sendsysrq service setdevelproject sdp setlinkrev showlinked signkey staging status st submitrequest submitpac submitreq sr token triggerreason tr undelete unlock update up updatepacmetafromspec updatepkgmetafromspec metafromspec vc version whatdependson whois user who wipebinaries unpublish workerinfo" =~ (^|[[:space:]])$1($|[[:space:]]) ]]; then
    # looks like the user is executing the container as the osc command
    osc "$@"
else
    exec "$@"
fi
