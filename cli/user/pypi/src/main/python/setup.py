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
        'stratuslab.controller',
        'stratuslab.commandbase',
        'stratuslab.image',
        #'stratuslab.installator',
        'stratuslab.marketplace',
        'stratuslab.messaging',
        'stratuslab.pat',
        'stratuslab.system',
        'stratuslab.vm_manager',
        'stratuslab.volume_manager',
        #'stratuslab.tm',
        ],

    data_files=[
        ('java', ['java/metadata-${metadata.version}-jar-with-dependencies.jar']),
        ('share/vm', ['share/vm/schema.one']),
        ('share/template', ['share/template/manifest.xml.tpl']),
        ('conf', ['conf/stratuslab-user.cfg.ref']),
        ('Scripts', ['windows/stratus-attach-volume.bat',
                     'windows/stratus-build-metadata.bat',
                     'windows/stratus-connect-instance.bat',
                     'windows/stratus-copy-config.bat',
                     'windows/stratus-create-image.bat',
                     'windows/stratus-create-volume.bat',
                     'windows/stratus-delete-volume.bat',
                     'windows/stratus-deprecate-metadata.bat',
                     'windows/stratus-describe-instance.bat',
                     'windows/stratus-describe-volumes.bat',
                     'windows/stratus-detach-volume.bat',
                     'windows/stratus-hash-password.bat',
                     'windows/stratus-kill-instance.bat',
                     'windows/stratus-prepare-context.bat',
                     'windows/stratus-run-cluster.bat',
                     'windows/stratus-run-instance.bat',
                     'windows/stratus-shutdown-instance.bat',
                     'windows/stratus-sign-metadata.bat',
                     'windows/stratus-update-volume.bat',
                     'windows/stratus-upload-image.bat',
                     'windows/stratus-upload-metadata.bat',
                     'windows/stratus-validate-metadata.bat']),
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
        "httplib2 >= 0.7.7",
        "requests >= 2.2.0"
    ],
)
