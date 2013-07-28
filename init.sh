#!/bin/bash

mkdir -p cache db build_db build

mkdir -p aurstaging/{x86_64,i686}



#  pacman -S devtools

mkdir -p ~/chroot
CHROOT=$HOME/chroot
if [ ! -e $CHROOT/root ] ; then
	mkarchroot $CHROOT/root base-devel
fi

# add aurbs staging repo to chroot
if ! grep -q aurstaging $CHROOT/root/etc/pacman.conf ; then
	pcfg=$CHROOT/root/etc/pacman.conf
	echo "[aurstaging]" >> $pcfg
	echo "SigLevel = Never" >> $pcfg
	echo "Server = http://127.0.0.1:8024/\$arch" >> $pcfg
fi

if ! [ -e ~/.makepkg.conf ] || ! grep -q PACKAGER ~/.makepkg.conf ; then
	echo "PACKAGER=\"Dominik Heidler <dheidler@gmail.com>\"" >> ~/.makepkg.conf
fi
