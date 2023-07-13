#!/bin/bash

PNAME=deseccam-0.1a
BUILDP=/home/tobi/packaging/
ROOTP=/home/tobi/PycharmProjects/deseccam/
DESTP=${BUILDP}${PNAME}/

cp -R ${ROOTP}/*.py ${DESTP}/usr/bin/deseccam/
cp ${ROOTP}/init.d/deseccam ${DESTP}/etc/init.d/deseccam
cp ${ROOTP}/config.cfg ${DESTP}/etc/deseccam/config.cfg
cd ${BUILDP}
dpkg -b ./${PNAME}
