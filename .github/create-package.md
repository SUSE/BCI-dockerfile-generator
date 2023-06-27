---
title: Packages are missing on OBS for {{ env.DEPLOYMENT_BRANCH_NAME }}
assignees: dcermak
---

The following packages are missing in the devel project on OBS: {{ env.pkgs }}

Please create them via:
```ShellSession
export OSC_PASSWORD=#insert_bugzilla_password
pkgs="{{ env.pkgs }}"
for pkg in ${pkgs//,/}; do
    poetry run scratch-build-bot --os-version={{ env.OS_VERSION }} --osc-user=$YOUR_USERNAME_HERE \
        setup_obs_package --package-name=$pkg
done
```
