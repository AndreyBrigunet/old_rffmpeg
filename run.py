#!/usr/bin/env python3

import os
import re
import sys
import subprocess
import base64


class Run:

    def __init__(self, config, logger):
        self.config = config
        self.logger = logger
        self.all_args = sys.argv
        self.ffmpeg_args = self.all_args[1:]

    def setup_remote_command(self, target_host):
        """
        Craft the target command
        """
        ssh_command = []
        ffmpeg_command = []

        ssh_command.extend(['ssh', '-q'])
        ssh_command.extend(['-o', 'ConnectTimeout=1'])
        ssh_command.extend(['-o', 'ConnectionAttempts=1'])
        ssh_command.extend(['-o', 'StrictHostKeyChecking=no'])
        ssh_command.extend(['-o', 'UserKnownHostsFile=/dev/null'])

        persist = int(self.config.get('Global', 'persist', fallback=0))
        if persist > 0:
            ssh_command.extend(['-o', 'ControlMaster=auto'])
            ssh_command.extend(['-o', 'ControlPath=/etc/rffmpeg/data/ssh-%r@%h:%p'])
            ssh_command.extend(['-o', 'ControlPersist={}'.format(persist)])
    
        ssh_command.extend(['-o', 'Port={}'.format(target_host.get('port', 22))])

        path = os.path.dirname(os.path.realpath(__file__)) + '/'
        key = path + target_host.get('identity_file', None)
        if key is not None:
            ssh_command.extend(['-i', key])

        ssh_command.append('{}@{}'.format(target_host.get('user'), target_host.get('host')))

        self.logger.info('Running as %s@%s', target_host.get('user'), target_host.get('host'))

        stdin = sys.stdin
        stdout = sys.stderr
        stderr = sys.stderr

        if 'ffprobe' in self.all_args[0]:
            ffmpeg_command.append(self.config.get('Global', 'ffprobe'))
            stdout = sys.stdout
        else:
            ffmpeg_command.append(self.config.get('Global', 'ffmpeg'))

        if '-version' in self.ffmpeg_args or '-encoders' in self.ffmpeg_args or '-decoders' in self.ffmpeg_args:
            stdout = sys.stdout

        try:
            args = base64.b64decode(self.ffmpeg_args[2].encode('ascii')).decode('ascii')
            ffmpeg_command.append(args)
        except:
            self.logger.info('Argument pares error: %s', self.ffmpeg_args)
            exit()
   
        # for arg in self.ffmpeg_args:
        #     if re.search("[*'()\\s|\\[\\]]", arg):
        #         ffmpeg_command.append('"{}"'.format(arg))
        #     else:
        #         ffmpeg_command.append('{}'.format(arg))

        return (ssh_command, ffmpeg_command, stdin, stdout, stderr)

    def run_command(self, ssh_command, ffmpeg_command, stdin, stdout, stderr):
        """
        Execute the command using subprocess
        """
        command = ssh_command + ffmpeg_command

        proc = subprocess.run(command, shell=False, bufsize=0, universal_newlines=True,
                              stdin=stdin,
                              stdout=stdout,
                              stderr=stderr)

        if proc.returncode > 0:
            self.logger.error(proc)

        return proc.returncode

    def local_ffmpeg(self):
        """
        Fallback call to local ffmpeg
        """
        ffmpeg_command = []

        stdin = sys.stdin
        stdout = sys.stderr
        stderr = sys.stderr

        if 'ffprobe' in self.all_args[0]:
            ffmpeg_command.append(self.config.get('Global', 'ffprobe'))
            stdout = sys.stdout
        else:
            ffmpeg_command.append(self.config.get('Global', 'ffmpeg'))

        specials = ['-version', '-encoders', '-decoders', '-hwaccels']
        if any(item in specials for item in self.ffmpeg_args):
            stdout = sys.stdout

        for arg in self.ffmpeg_args:
            ffmpeg_command.append('{}'.format(arg))

        self.logger.info('Local command: %s', ' '.join(ffmpeg_command))
        return self.run_command([], ffmpeg_command, stdin, stdout, stderr)

    def remote_ffmpeg(self, target_host):
        ssh_command, ffmpeg_command, stdin, stdout, stderr = self.setup_remote_command(target_host)

        self.logger.info("Remote command: %s '%s'", ' '.join(ssh_command), ' '.join(ffmpeg_command))
        return self.run_command(ssh_command, ffmpeg_command, stdin, stdout, stderr)
