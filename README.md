# LDOCE5 Viewer

**:warning: This repository is no longer actively maintained.**

-----

The LDOCE5 Viewer is an alternative dictionary viewer for the Longman Dictionary of Contemporary English 5th Edition (LDOCE 5).

![image](https://cloud.githubusercontent.com/assets/15828926/24585732/efb068a4-17bb-11e7-8294-7241f73d9ed8.png)

It runs on macOS, Linux and Microsoft Windows.

This software is free and open source software licensed under the terms of GPLv3.

As of 2021/12/26, m1 mac brew does not have QtWebEngine in qt@5 so using x86_64 version is necessary.

```
brew install python@3.9 qt@5

## install libraries
pip3 install pyqt5
pip3 install pyqt5-tools
pip3 install PyQtWebEngine
pip3 install whoosh
pip3 install lxml

## sound on macos
pip3 install PyObjC

## build
make install

## for macos app
pip3 install py2app
pip3 install opencv-python-headless
python3 ./setup.py py2app
```
