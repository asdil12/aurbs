> [!WARNING]
> Moved to https://codeberg.org/asdil12/aurbs

# aurbs

This is a tool to build a binary repo for aur pkgs. You simply provide a list of pkgs to build, and run it. It will then download the pkgs, compile them, (detect dependency issues and build failures) and publish the pkgs in a repo. It can even build aur-pkgs, that depend on other aur-pkgs. When you then run aurbs the next time, it will detect pkg updates (or updated dependencies) and rebuild the corresponding pkgs. It also provides a web-ui where the build-status, the build-log, and the results can be displayed, and where the pkgs can be downloaded.

## Installation

- `pacman -S devtools rsync python-setuptools python-simplejson python-yaml python-pymongo python-flask pyalpm ccache`
- `yaourt -S python-flup-hg`
- run `make install`
- `useradd --system -c 'aurbs daemon user' -g daemon -d /var/cache/aurbs -s /bin/bash aurbs`
- `chown -R aurbs: /var/cache/aurbs/ccache/*`
- `chown -R aurbs: /var/cache/aurbs/build/*`
- set PACKAGER in `/etc/makepkg.conf`
- modify `/etc/aurbs.yml` to define you pkgs and archs
- make sure that mongodb is running
- run `aurbs` to build pkgs


For the UI:
- for better performance configure your webserver to allow x-sendfile or manually serve
  /var/lib/aurbs/aurstaging to /aurstaging
- same reason, for the public repo: if you want to serve it on another url, specify that url in config
- sample config for lighttpd: `templates/lighttpd.conf.sample`
