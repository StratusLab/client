import os
import os.path

from setuptools import setup

try:
    rootdir = os.path.join('lib', 'stratuslab', 'python')
    for f in os.listdir(rootdir):
        src = os.path.join(rootdir, f)
        os.symlink(src, f)
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
        # 'stratuslab.installator',
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

    entry_points={
        'console_scripts': [
            'stratus-attach-volume = stratuslab.cmd.stratus_attach_volume:main',
            'stratus-build-metadata = stratuslab.cmd.stratus_build_metadata:main',
            'stratus-connect-instance = stratuslab.cmd.stratus_connect_instance:main',
            'stratus-copy-config = stratuslab.cmd.stratus_copy_config:main',
            'stratus-create-image = stratuslab.cmd.stratus_create_image:main',
            'stratus-create-volume = stratuslab.cmd.stratus_create_volume:main',
            'stratus-delete-volume = stratuslab.cmd.stratus_delete_volume:main',
            'stratus-deprecate-metadata = stratuslab.cmd.stratus_deprecate_metadata:main',
            'stratus-describe-instance = stratuslab.cmd.stratus_describe_instance:main',
            'stratus-describe-volumes = stratuslab.cmd.stratus_describe_volumes:main',
            'stratus-detach-volume = stratuslab.cmd.stratus_detach_volume:main',
            'stratus-hash-password = stratuslab.cmd.stratus_hash_password:main',
            'stratus-kill-instance = stratuslab.cmd.stratus_kill_instance:main',
            'stratus-list-instances = stratuslab.cmd.stratus_list_instances:main',
            'stratus-prepare-context = stratuslab.cmd.stratus_prepare_context:main',
            'stratus-run-cluster = stratuslab.cmd.stratus_run_cluster:main',
            'stratus-run-instance = stratuslab.cmd.stratus_run_instance:main',
            'stratus-search-image = stratuslab.cmd.stratus_search_image:main',
            'stratus-show-image = stratuslab.cmd.stratus_show_image:main',
            'stratus-shutdown-instance = stratuslab.cmd.stratus_shutdown_instance:main',
            'stratus-sign-metadata = stratuslab.cmd.stratus_sign_metadata:main',
            'stratus-update-volume = stratuslab.cmd.stratus_update_volume:main',
            'stratus-upload-image = stratuslab.cmd.stratus_upload_image:main',
            'stratus-upload-metadata = stratuslab.cmd.stratus_upload_metadata:main',
            'stratus-validate-metadata = stratuslab.cmd.stratus_validate_metadata:main',
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
        # "dirq >= 1.2.2",
        #"stomp.py >= 3.1.3",
        "httplib2 >= 0.7.7",
        "requests >= 2.2.0"
    ],
)
