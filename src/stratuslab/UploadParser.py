import os

from stratuslab.Uploader import Uploader

def buildUploadParser(parser):
    parser.usage = 'usage: %prog [options] manifest'

    parser.add_option('-r', '--repo', dest='repoAddress',
            help='appliance repository address', metavar='FILE',
            default=None)
    parser.add_option('--protocol', dest='uploadProtocol',
            help='upload protocol', default='https', metavar='NAME')

    parser.add_option('--curl-option', dest='option',
            help='additional curl option', default='')

    parser.add_option('-C', '--compress', dest='archiveFormat',
            help='archive and compression format (e.g. tar.gz, tar.bz2, ...)',
            default='tar.gz', metavar='FORMAT')
    parser.add_option('-f', '--force', dest='forceUpload',
            help='force upload of the appliance even if already exist.',
            default=False, action='store_true')

    parser.add_option('--list-protocol', dest='listUploadProtocol',
            help='list available upload protocol',
            default=False, action='store_true')
    parser.add_option('--list-compress', dest='listCompressFormat',
            help='list available compression format',
            default=False, action='store_true')

    parser.add_option('-U', '--repo-username', dest='username',
            help='repository username. Default STRATUSLAB_REPO_USERNAME',
            default=os.getenv('STRATUSLAB_REPO_USERNAME', ''))
    parser.add_option('-P', '--repo-password', dest='password',
            help='repository password. Default STRATUSLAB_REPO_PASSWORD',
            default=os.getenv('STRATUSLAB_REPO_PASSWORD', ''))

def checkUploadOptions(options, config, parser):
    if not options.uploadProtocol in Uploader.availableUploadProtocol():
        parser.error('Unknow upload protocol.\n')

    if options.archiveFormat not in Uploader.availableCompressionFormat():
        parser.error('Unknow compression format')

    if not options.repoAddress:
        options.repoAddress = config.get('app_repo_url')

    if not options.username:
        options.username = config.get('app_repo_username')

    if not options.password:
        options.password = config.get('app_repo_password')

def displayUploadOptions(options):
    if options.listCompressFormat:
        Uploader.availableCompressionFormat(True)
    elif options.listUploadProtocol:
        Uploader.availableUploadProtocol(True)
