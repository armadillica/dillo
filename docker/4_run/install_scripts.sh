
if [ ! -f /installed ]; then
    SITEPKG=$(echo /opt/python/lib/python3.*/site-packages)
    echo "Installing Dillo packages into $SITEPKG"

    # TODO: 'pip3 install -e' runs 'setup.py develop', which runs 'setup.py egg_info',
    # which can't write the egg info to the read-only /data/git volume. This is why
    # we manually install the links.
    for SUBPROJ in /data/git/{pillar,pillar-python-sdk,dillo}; do
        NAME=$(python3 $SUBPROJ/setup.py --name)
        echo "... $NAME"
        echo $SUBPROJ >> $SITEPKG/easy-install.pth
        echo $SUBPROJ > $SITEPKG/$NAME.egg-link
    done
    echo "All packages installed."

    touch /installed
fi
