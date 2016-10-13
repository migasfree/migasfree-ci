#!/bin/bash
set -x

_VERSION=stable
_ARCH="i386 amd64 armel armhf"


function build_pkg_with_pip()
{
    local _USER=$1
    local _REPO=$2
    local _RELEASE=${3:-latest} # master
    local _CFG="$4"

    if ! [ -f /pub/dists/$_VERSION/PKGS/python-${_REPO}_$_RELEASE*_all.deb ]
    then
        pip install $_REPO==$_RELEASE  --download="."

        if [ -f  $_REPO-$_RELEASE.zip ]; then
            unzip $_REPO-$_RELEASE.zip
            rm $_REPO-$_RELEASE.zip
            cd $_REPO-$_RELEASE
        fi

        if [ -f  $_REPO-$_RELEASE.tar.gz ]; then
            tar -xvf $_REPO-$_RELEASE.tar.gz
            rm $_REPO-$_RELEASE.tar.gz
            cd  $_REPO-$_RELEASE
        fi

        if [ -f setup.py ]
        then

            if ! [ -z "$_CFG" ]
            then
                printf "$_CFG" > stdeb.cfg
            fi

            python setup.py --command-packages=stdeb.command bdist_deb
        else
            /usr/bin/debuild --no-tgz-check -us -uc -b
            cp ../$_REPO*.deb ../dists/$_VERSION/PKGS
            rm -rf ../$_REPO*
        fi
        cd ..
        cp  $_REPO-$_RELEASE/deb_dist/*.deb /pub/dists/$_VERSION/PKGS
        rm -rf $_REPO-$_RELEASE
    fi
}


function build_pkg()
{
    local _USER=$1
    local _REPO=$2
    local _RELEASE=${3:-latest} # master
    local _CFG="$4"

    if ! [ -f /pub/dists/$_VERSION/PKGS/python-${_REPO}_${_RELEASE}-*_all.deb ]
    then

        git clone https://github.com/$_USER/$_REPO.git
        cd  $_REPO
        git checkout tags/$_RELEASE
        git submodule update --init --recursive
        if [ $_REPO = "migasfree" -o $_REPO = "migasfree-client" ]
        then
            cd bin
            ./create-package
            cd ..
        else
            if [ -f setup.py ]
            then

                if ! [ -z "$_CFG" ]
                then
                    printf "$_CFG" > stdeb.cfg
                fi

                python setup.py --command-packages=stdeb.command bdist_deb
            else
                /usr/bin/debuild --no-tgz-check -us -uc -b
                cp ../$_REPO*.deb ../dists/$_VERSION/PKGS
                rm -rf ../$_REPO*
            fi
        fi
        cd ..

        cp $_REPO/deb_dist/*_all.deb /pub/dists/$_VERSION/PKGS
        rm -rf $_REPO
    fi
}

function build_dependences()
{
    local _TARGET_PATH=$1

    mkdir -p $_TARGET_PATH/dists/$_VERSION/PKGS

    cd $_TARGET_PATH/dists/$_VERSION/PKGS/

    # migasfree_4.12-1 requery packages
    build_pkg_with_pip yourlabs django-autocomplete-light 3.1.1
    build_pkg crucialfelix django-ajax-selects 1.4.2
    build_pkg django django 1.9.8
    build_pkg dyve django-bootstrap3 6.2.2
    build_pkg django-admin-bootstrapped django-admin-bootstrapped 2.5.7
    build_pkg django-import-export django-import-export 0.4.5
    build_pkg_with_pip kelp404 six 1.10.0

    build_pkg_with_pip kennethreitz tablib 0.9.11

    build_pkg tomchristie django-rest-framework 3.4.0
    build_pkg philipn django-rest-framework-filters v0.8.0
    build_pkg marcgibbons django-rest-swagger 0.3.10
    build_pkg carltongibson django-filter 0.13.0 '[DEFAULT]\nProvides: django-filter\n'


    apt-get update
    apt-get --force-yes --assume-yes install libxml2 libxml2-dev libxslt-dev


    build_pkg_with_pip adi- django-markdownx 1.6
    build_pkg_with_pip Kozea pygal 2.2.3
    build_pkg_with_pip carljm django-form-utils 1.0.3 '[DEFAULT]\nProvides: django-form-utils\n'



    # for migasfree-client 5 REST-API requery packages
    # ================================================
    # build_pkg_with_pip mpdavis jose 1.0.0 '[DEFAULT]\nPackage: python-jose\n'
    # build_pkg sigmavirus24 requests-toolbelt 0.6.2
    # build_pkg_with_pip kennethreitz requests 2.4.3



    cd $_TARGET_PATH/dists/$_VERSION/PKGS/  

    # python-diff-match-patch requerido por python-django-import-export
    if ! [ -f $_TARGET_PATH/dists/$_VERSION/PKGS/python-diff-match-patch_20121119-1_all.deb ]
    then
        wget http://mirrors.kernel.org/ubuntu/pool/universe/p/python-diff-match-patch/python-diff-match-patch_20121119-1_all.deb
    fi

    # Ponemos la version minima de lshw en el repositorio

    for _arch in $_ARCH
    do
        if ! [ -f $_TARGET_PATH/dists/$_VERSION/PKGS/lshw_02.16-1_$_arch.deb ]
        then
            wget http://ftp.debian.org/debian/pool/main/l/lshw/lshw_02.16-1_$_arch.deb
        fi
    done

    cd $_TARGET_PATH

}

function build_migasfree_suite()
{
    local _TARGET_PATH=$1
    local _PKGS="migasfree migasfree-client"

    for _PKG in $_PKGS
    do
        if [ -d /git/$_PKG ]
        then # from local
            rm -rf /git/$_PKG/deb_dist || :
            cd /git/$_PKG/bin
            ./create-package
            cd ..
            cp deb_dist/*_all.deb $_TARGET_PATH/dists/$_VERSION/PKGS
        else # from github
            cd $_TARGET_PATH/dists/$_VERSION/PKGS/
            build_pkg migasfree $_PKG latest
        fi
    done

    if [ -d /git/migasfree-launcher ]
    then
        cd /git/migasfree-launcher/
        python setup.py --command-packages=stdeb.command bdist_deb
        cp deb_dist/*_all.deb /pub/dists/$_VERSION/PKGS
        rm -rf deb_dist/*_all.deb
    else
        cd $_TARGET_PATH/dists/$_VERSION/PKGS/
        build_pkg migasfree "migasfree-launcher" latest
    fi

}

function build_repo_metadata()
{
    local _TARGET_PATH=$1
    local _KEYS_PATH=/var/lib/migasfree.org/keys/.gnupg




    # make metadata
    cd $_TARGET_PATH

    rm dists/$_VERSION/Contents*
    rm dists/$_VERSION/Release* || :
    rm dists/$_VERSION/InRelease || :




    for _arch in $_ARCH
    do
        rm -rf dists/$_VERSION/PKGS/binary-$_arch
        mkdir -p dists/$_VERSION/PKGS/binary-$_arch
    done

    mkdir -p .cache

    cat > apt-ftparchive.conf <<EOF
Dir {
 ArchiveDir ".";
 CacheDir "./.cache";
};
Default {
 Packages::Compress ". gzip bzip2";
 Contents::Compress ". gzip bzip2";
};
TreeDefault {
 BinCacheDB "packages-\$(SECTION)-\$(ARCH).db";
 Directory "dists/$_VERSION/\$(SECTION)";
 SrcDirectory "dists/$_VERSION/\$(SECTION)";
 Packages "\$(DIST)/\$(SECTION)/binary-\$(ARCH)/Packages";
 Contents "\$(DIST)/Contents-\$(ARCH)";
};
Tree "dists/$_VERSION" {
 Sections "PKGS";
 Architectures "$_ARCH";
}
EOF
    apt-ftparchive generate apt-ftparchive.conf 2> ./err
    if [ $? != 0 ]
    then
      cat ./err >&2
    fi
    rm ./err
    cat > apt-release.conf <<EOF
APT::FTPArchive::Release::Codename "$_VERSION";
APT::FTPArchive::Release::Origin "migasfree";
APT::FTPArchive::Release::Components "PKGS";
APT::FTPArchive::Release::Label "migasfree $_VERSION Repository";
APT::FTPArchive::Release::Architectures "$_ARCH";
APT::FTPArchive::Release::Suite "$_VERSION";
EOF

    apt-ftparchive -c apt-release.conf release dists/$_VERSION > dists/$_VERSION/Release

    gpg -u migasfree-repository --homedir $_KEYS_PATH -abs -o dists/$_VERSION/Release.gpg dists/$_VERSION/Release

    gpg -u migasfree-repository --homedir $_KEYS_PATH --clearsign -o dists/$_VERSION/InRelease dists/$_VERSION/Release
    rm -rf apt-release.conf apt-ftparchive.conf

    ls -la $_TARGET_PATH/dists/$_VERSION/PKGS

    # copy migasfree-repositories public key
    cp $_KEYS_PATH/migasfree-repository.gpg $_TARGET_PATH/gpg_key
    chmod 444 $_TARGET_PATH/gpg_key

    rm -rf $_TARGET_PATH/.cache ||:

    # Install Server Script
    cat > $_TARGET_PATH/install-server <<EOF
# To install migasfree-server execute:
#    wget -O - http://migasfree.org/pub/install-server | bash

wget -O - http://migasfree.org/pub/gpg_key | apt-key add -
echo "deb http://migasfree.org/pub $_VERSION PKGS" > /etc/apt/sources.list.d/migasfree.list
apt-get update
apt-get -y install --no-install-recommends migasfree-server
EOF

    # Install Client Script
    cat > $_TARGET_PATH/install-client <<EOF
# To install migasfree-client execute:
#    wget -O - http://migasfree.org/pub/install-client | bash

wget -O - http://migasfree.org/pub/gpg_key | apt-key add -
echo "deb http://migasfree.org/pub $_VERSION PKGS" > /etc/apt/sources.list.d/migasfree.list
apt-get update
apt-get -y install --no-install-recommends migasfree-client
EOF


}
