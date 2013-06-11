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
    name='${project.artifactId}',
    version='${project.version}',
    author='StratusLab',
    author_email='contact@stratuslab.eu',
    url='http://stratuslab.eu/',
    license='Apache Software License 2.0',
    description='${project.description}',
    long_description=open('README.txt').read(),

    scripts=[
        'bin/stratus-attach-volume',
        'bin/stratus-build-metadata',
        'bin/stratus-connect-instance',
        'bin/stratus-copy-config',
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
        'bin/stratus-run-cluster',
        'bin/stratus-run-instance',
        'bin/stratus-shutdown-instance',
        'bin/stratus-sign-metadata',
        'bin/stratus-update-volume',
        'bin/stratus-upload-image',
        'bin/stratus-upload-metadata',
        'bin/stratus-validate-metadata',
        ],

     packages=[
        'stratuslab',
        'stratuslab.api',
        'stratuslab.cloud',
        'stratuslab.cloudinit',
        'stratuslab.commandbase',
        'stratuslab.image',
        #'stratuslab.installator',
        'stratuslab.marketplace',
        'stratuslab.messaging',
        'stratuslab.pat',
        'stratuslab.system',
        #'stratuslab.tm',
        ],

    data_files=[
        ('java', ['java/metadata-13.05.0-SNAPSHOT-jar-with-dependencies.jar']),
        ('share/vm', ['share/vm/schema.one']),
        ('share/template', ['share/template/manifest.xml.tpl']),
        ('conf', ['conf/stratuslab-user.cfg.ref']),
        ],

    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python :: 2.6',
        'Topic :: System :: Distributed Computing',
        ],

    install_requires=[
        "dirq >= 1.2.2",
        "stomp.py >= 3.1.3",
        "pika >= 0.9.9",
        "httplib2 >= 0.7.7",
        "couchbase == 0.8.2"
    ],
)
