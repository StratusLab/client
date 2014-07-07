from distutils.core import setup
from setuptools import setup, find_packages

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
    author_email='support@stratuslab.eu',
    url='http://stratuslab.eu/',
    license='Apache Software License 2.0',
    description='${project.description}',
    long_description=open('README.txt').read(),
    keywords="IaaS cloud",

    packages=[
        'stratuslab',
        'stratuslab.api',
        'stratuslab.cloud',
        'stratuslab.cloudinit',
        'stratuslab.cmd',
        'stratuslab.controller',
        'stratuslab.commandbase',
        'stratuslab.image',
        #'stratuslab.installator',
        'stratuslab.marketplace',
        #'stratuslab.messaging',
        'stratuslab.pat',
        'stratuslab.system',
        'stratuslab.vm_manager',
        'stratuslab.volume_manager',
        #'stratuslab.tm',
        ],

    data_files=[
        ('java', ['java/metadata-fatjar-jar-with-dependencies.jar']),
        ('share/vm', ['share/vm/schema.one']),
        ('share/template', ['share/template/manifest.xml.tpl']),
        ('conf', ['conf/stratuslab-user.cfg.ref']),
        ],

    entry_points = {
        'console_scripts': [
            'stratus-attach-volume = stratuslab.cmd.stratus_attach_volume:MainProgram',
            'stratus-build-metadata = stratuslab.cmd.stratus_build_metadata:MainProgram',
            'stratus-connect-instance = stratuslab.cmd.stratus_connect_instance:MainProgram',
            'stratus-copy-config = stratuslab.cmd.stratus_copy_config:MainProgram',
            'stratus-create-image = stratuslab.cmd.stratus_create_image:MainProgram',
            'stratus-create-volume = stratuslab.cmd.stratus_create_volume:MainProgram',
            'stratus-delete-volume = stratuslab.cmd.stratus_delete_volume:MainProgram',
            'stratus-deprecate-metadata = stratuslab.cmd.stratus_deprecate_metadata:MainProgram',
            'stratus-describe-instance = stratuslab.cmd.stratus_describe_instance:MainProgram',
            'stratus-describe-volumes = stratuslab.cmd.stratus_describe_volumes:MainProgram',
            'stratus-detach-volume = stratuslab.cmd.stratus_detach_volume:MainProgram',
            'stratus-hash-password = stratuslab.cmd.stratus_hash_password:MainProgram',
            'stratus-kill-instance = stratuslab.cmd.stratus_kill_instance:MainProgram',
            'stratus-prepare-context = stratuslab.cmd.stratus_prepare_context:MainProgram',
            'stratus-run-cluster = stratuslab.cmd.stratus_run_cluster:MainProgram',
            'stratus-run-instance = stratuslab.cmd.stratus_run_instance:MainProgram',
            'stratus-shutdown-instance = stratuslab.cmd.stratus_shutdown_instance:MainProgram',
            'stratus-sign-metadata = stratuslab.cmd.stratus_sign_metadata:MainProgram',
            'stratus-update-volume = stratuslab.cmd.stratus_update_volume:MainProgram',
            'stratus-upload-image = stratuslab.cmd.stratus_upload_image:MainProgram',
            'stratus-upload-metadata = stratuslab.cmd.stratus_upload_metadata:MainProgram',
            'stratus-validate-metadata = stratuslab.cmd.stratus_validate_metadata:MainProgram',
            ],
        },

    package_data={
        '': ['*.tpl', '*.ref', '*.jar', '*.one'],
        },

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
        #"dirq >= 1.2.2",
        #"stomp.py >= 3.1.3",
        "httplib2 >= 0.7.7",
        "requests >= 2.2.0"
    ],
)
