from distutils.core import setup

import os
import os.path

try:
    rootdir = os.path.join('lib','stratuslab','python')
    for file in os.listdir(rootdir):
        src = os.path.join(rootdir, file)
        os.symlink(src, file)
except:
    # assume links have already been made
    pass

setup(
    name='stratuslab-client',
    version='13.02.dev',
    author='StratusLab',
    author_email='contact@stratuslab.eu',
    url='http://stratuslab.eu/',
    license='Apache 2.0',
    description='StratusLab client',
    long_description="Command line client for accessing StratusLab cloud infrastrutures.",

    scripts=[
        'bin/stratus-attach-volume',
        'bin/stratus-build-metadata',
        'bin/stratus-connect-instance',
        'bin/stratus-create-image',
        'bin/stratus-create-volume',
        'bin/stratus-delete-volume',
        'bin/stratus-deprecate-metadata',
        'bin/stratus-describe-instance',
        'bin/stratus-describe-volumes',
        'bin/stratus-detach-volume',
        'bin/stratus-hash-password',
        'bin/stratus-kill-instance',
        'bin/stratus-prepare-context',
        'bin/stratus-run-benchmark',
        'bin/stratus-run-cluster',
        'bin/stratus-run-instance',
        'bin/stratus-save-instance',
        'bin/stratus-shutdown-instance',
        'bin/stratus-sign-metadata',
        'bin/stratus-update-volume',
        'bin/stratus-upload-image',
        'bin/stratus-upload-metadata',
        'bin/stratus-validate-metadata',
        ],

     packages=[
        'dirq',
        'httplib2',
        'pika',
        'pika.adapters',
        'stomp',
        'stomp.bridge',
        'stratuslab',
        'stratuslab.cloud',
        'stratuslab.cloudinit',
        'stratuslab.commandbase',
        'stratuslab.image',
        'stratuslab.installator',
        'stratuslab.marketplace',
        'stratuslab.messaging',
        'stratuslab.pat',
        'stratuslab.system',
        'stratuslab.tm',
        'stratuslab.web',
        ],

#    install_requires=[
#        "dirq",
#        "stomp",
#        "pika",
#    ],
)
