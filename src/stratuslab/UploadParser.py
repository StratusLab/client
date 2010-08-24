import os

from stratuslab.Uploader import Uploader

def buildUploadParser(parser):
    parser.usage = '''usage: %prog [options] manifest'''

    parser.add_option('-r', '--repository', dest='repoAddress',
            help='appliance repository address. Default STRATUSLAB_REPO',
            default=os.getenv('STRATUSLAB_REPO'), metavar='ADDRESS')

    parser.add_option('--curl-option', dest='uploadOption', metavar='OPTION',
            help='additional curl option', default='')

    parser.add_option('-C', '--compress', dest='compressionFormat',
            help='compression format',
            default='gz', metavar='FORMAT')
    parser.add_option('-f', '--force', dest='forceUpload',
            help='force upload of the appliance even if already exist.',
            default=False, action='store_true')

    parser.add_option('--list-compression', dest='listCompressionFormat',
            help='list available compression format',
            default=False, action='store_true')

    parser.add_option('-U', '--repo-username', dest='repoUsername',
            help='repository username. Default STRATUSLAB_REPO_USERNAME',
            default=os.getenv('STRATUSLAB_REPO_USERNAME'))
    parser.add_option('-P', '--repo-password', dest='repoPassword',
            help='repository password. Default STRATUSLAB_REPO_PASSWORD',
            default=os.getenv('STRATUSLAB_REPO_PASSWORD'))

def checkUploadOptions(options, parser):
    if options.compressionFormat not in Uploader.availableCompressionFormat():
        parser.error('Unknow compression format')
    if not options.repoAddress:
        parser.error('Unspecified repository address')
    if not options.repoUsername:
        parser.error('Unspecified repository username')
    if not options.repoPassword:
        parser.error('Unspecified repository password')

