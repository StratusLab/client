
import re
import time
from subprocess import Popen, PIPE, STDOUT

from stratuslab.pdiskbackend.utils import abort, print_detail

#######################################################
# Class representing a command passed to the back-end #
#######################################################

class CommandRunner(object):
    cmd_output_start = '<<<<<<<<<<'
    cmd_output_end = '>>>>>>>>>>'
    
    RETRY_ERRORS = [(255, re.compile('^Connection to .* closed by remote host.', re.MULTILINE)),
                    (1, re.compile('^ssh: connect to host .* Connection refused', re.MULTILINE)),
                    (255, re.compile('^ssh: connect to host .* No route to host', re.MULTILINE))]
    MAX_RETRIES = 3
    
    def __init__(self, action, cmd, successMsgs=[], failureOkMsgs=[]):
        self.action = action
        self.action_cmd = cmd
        self.successMsgs = successMsgs or []
        self.failureOkMsgs = failureOkMsgs or []
        self.proc = None

    def execute(self):
        status = 0
        self.debug("Executing command: '%s'" % (' '.join(self.action_cmd)), 1)
        try:
            self.proc = Popen(self.action_cmd, shell=False, stdout=PIPE, stderr=STDOUT)
        except OSError, details:
            abort('Failed to execute %s action: %s' % (self.action, details))
            status = 1
        return status
    
    def checkStatus(self):
        optInfo = ()
        try:
            retcode, output = self._getStatusOutputOrRetry(self.action)
            output = self._filter_command_output(output)
            if retcode != 0 and len(output) != 0:
                self.debug("ERROR: %s action, exit code %s. Command output:\n%s\n%s\n%s" % \
                           (self.action, retcode, self.cmd_output_start, output, self.cmd_output_end))
                # In some cases we are OK when failure happens.
                for failurePattern in self.failureOkMsgs:
                    output_regexp = re.compile(failurePattern, re.MULTILINE)
                    matcher = output_regexp.search(output)
                    if matcher:
                        retcode = 0
                        self.debug('... But we are OK to proceed. Setting retcode to 0.')
                        break
            else:
                # Need to check if the command is expected to return an output when successful
                success = False
                if len(output) == 0:
                    success = True
                if self.successMsgs and len(output) > 0:
                    success = False
                    for successPattern in self.successMsgs:
                        output_regexp = re.compile(successPattern, re.MULTILINE)
                        matcher = output_regexp.search(output)
                        if matcher:
                            # Return only the first capturing group
                            if output_regexp.groups > 0:
                                optInfo = matcher.groups()
                            success = True
                            break
                if success:
                    self.debug("SUCCESS: %s action completed successfully." % self.action, 1)
                    if len(output) > 0:
                        self.debug('Command output:\n%s\n%s\n%s' % (self.cmd_output_start, output, self.cmd_output_end), 2)
                else:
                    self.debug("ERROR: %s action, exit code %s. But a failure case detected after parsing the output. Command output:\n%s\n%s\n%s" % \
                              (self.action, retcode, self.cmd_output_start, output, self.cmd_output_end))
                    retcode = -1
                    self.debug('exit code was reset to %i' % retcode)
        except OSError as ex:
            abort('Failed to execute %s action: %s' % (self.action, ex))

        if self.action in ['map', 'delete'] and retcode == 255 and not output.strip():
            retcode = 0
            self.debug('map and delete actions (command exited with 255 and no output returned) - exit code was reset to %i.' % retcode)

        if retcode == 255:
            if self.action in ['map', 'delete'] and not output.strip():
                retcode = 0
                self.debug('map and delete actions (no output returned) - exit code was reset to %i.' % retcode)
            if self.action in ['unmap']:
                retcode = 0
                self.debug('unmap action - exit code was reset to %i.' % retcode)

        return retcode, optInfo
    
    def _filter_command_output(self, output):
        lines = []
        for line in output.split('\n'):
            line = line.strip().strip('\r').strip()
            if not line:
                continue
            if line.startswith('Warning: Permanently added'):
                continue
            # NetApp Clustered may return a bell... crazy.
            if line.startswith('\x07'):
                continue
            lines.append(line)
        return '\n'.join(lines)

    def _getStatusOutputOrRetry(self, _action=''):
        """_action parameter is required only for testability: for mocking the method
        with 'side_effect'."""
        retcode, output = self._getStatusOutput()
        return self._retryOnError(retcode, output)
    
    def _getStatusOutput(self):
        retcode = self.proc.wait()
        return retcode, self.proc.communicate()[0]
    
    def _retryOnError(self, retcode, output):
        retries = 0
        while self._needToRetry(retcode, output) and retries < self.MAX_RETRIES:
            time.sleep(1)
            self.execute()
            retcode, output = self._getStatusOutput()
            retries += 1
        return retcode, output
    
    def _needToRetry(self, retcode, output):
        if retcode == 0:
            return False
        for rc, re_out in self.RETRY_ERRORS:
            if rc == retcode and re_out.match(output):
                return True
        return False

    def debug(self, msg, level=0):
        print_detail(msg, level)
