#!/usr/bin/env python3

import configparser, logging
import os, signal, psutil
from run import Run


class rffmpeg():

    def __init__(self):
        path = os.path.dirname(os.path.realpath(__file__)) + '/'
        self.state_tempdir = path + 'data/'
        
        if not os.path.exists(self.state_tempdir):
            os.mkdir(self.state_tempdir, mode=0o777)

        self.config_path = path + 'servers.conf'
        self.logger_path = self.state_tempdir + 'rffmpeg.log'
        self.initConfig()
        self.initLogger()

        self.state_filename = self.config.get("Global", "state_filename")
        self.current_statefile = self.state_tempdir + self.state_filename.format(pid=os.getpid())

        self.logger.info("-"*70)
        self.logger.info("Starting rffmpeg PID %s", os.getpid())

    def initConfig(self):
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)

    def initLogger(self):
        self.logger = logging.getLogger()
        logging.basicConfig(
            filename = self.logger_path, level = logging.INFO, 
            format="%(asctime)s - %(levelname)s - %(message)s")

    def get_target_host(self):
        """
        Determine the optimal target host
        """
        self.logger.info("Determining target host")

        # Check for existing state files
        # state_files = os.listdir(self.state_tempdir)

        # Read each statefile to determine which hosts are bad or in use
        # bad_hosts = list()
        # active_hosts = list()
        # for state_file in state_files:
        #     with open(self.state_tempdir + "/" + state_file, "r") as statefile:
        #         contents = statefile.readlines()
        #         for line in contents:
        #             if re.match("^badhost", line):
        #                 bad_hosts.append(line.split()[1])
        #                 self.logger.info("Found bad host mark from rffmpeg process %s for host '%s'", re.findall(r"[0-9]+", state_file)[0], line.split()[1])
        #             else:
        #                 active_hosts.append(line.split()[0])
        #                 self.logger.info("Found running rffmpeg process %s against host '%s'", re.findall(
        #                     r"[0-9]+", state_file)[0], line.split()[0])

        # Get the remote hosts list from the config
        remote_hosts = list()
        for section_name in self.config.sections():

            default = {
                "host": False, "port": 22, "user": False,
                "identity_file": False, "weight": 1
            }

            for name, value in self.config.items(section_name):
                if name in default:
                    default[name] = value
            
            if default['host'] and default['user'] and default['identity_file']:
                remote_hosts.append(default)

        
        # Remove any bad hosts from the remote_hosts list
        # for bhost in bad_hosts:
        #     for idx, rhost in enumerate(remote_hosts):
        #         if bhost == rhost["name"]:
        #             remote_hosts[idx]["bad"] = True

        # Find out which active hosts are in use
        # for idx, rhost in enumerate(remote_hosts):
        #     # Determine process counts in active_hosts
        #     count = 0
        #     for ahost in active_hosts:
        #         if ahost == rhost["name"]:
        #             count += 1
        #     remote_hosts[idx]["count"] = count

        # Reweight the host counts by floor dividing count by weight
        # for idx, rhost in enumerate(remote_hosts):
        #     if rhost["bad"]:
        #         continue
        #     if rhost["weight"] > 1:
        #         remote_hosts[idx]["weighted_count"] = rhost["count"] // rhost["weight"]
        #     else:
        #         remote_hosts[idx]["weighted_count"] = rhost["count"]

        # Select the host with the lowest weighted count (first host is parsed last)
        # lowest_count = 999
        # target_host = None
        # for rhost in remote_hosts:
        #     if rhost["bad"]:
        #         continue
        #     if rhost["weighted_count"] < lowest_count:
        #         lowest_count = rhost["weighted_count"]
        #         target_host = rhost["name"]

        # if not target_host:
        #     log.warning("Failed to find a valid target host - using local fallback instead")
        #     target_host = "localhost"

        # cpu1m, cpu5m, cpu15m = [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()]
        # if cpu5m > 80:
        #     target_host = remote_hosts[0]
        # else:
        #     target_host = {"host": "localhost"}

        target_host = remote_hosts[1]

        # Write to our state file
        with open(self.current_statefile, "a") as file:
            file.write(target_host.get('host') + "\n")

        self.logger.info("Selected target host '%s'", target_host)

        return target_host

    def cleanup(self, signum="", frame=""):
        # Remove the current statefile
        try:
            os.remove(self.current_statefile)
        except FileNotFoundError:
            pass

def main():
    remote = rffmpeg()
    run = Run(remote.config, remote.logger)

    # Clean up after crashed
    signal.signal(signal.SIGTERM, remote.cleanup)
    signal.signal(signal.SIGINT, remote.cleanup)
    signal.signal(signal.SIGQUIT, remote.cleanup)
    signal.signal(signal.SIGHUP, remote.cleanup)

    target_host = remote.get_target_host()
    if target_host.get('host') == "localhost":
        returncode = run.local_ffmpeg()
    else:
        returncode = run.remote_ffmpeg(target_host)

    remote.logger.info("Finished rffmpeg PID %s with return code %s", os.getpid(), returncode)

    remote.cleanup()

    if returncode > 0:
        print("returncode:", returncode)

if __name__ == "__main__":
    main()

# Create symlinks for the command names ffmpeg and ffprobe to rffmpeg.py, for example 
# sudo ln -s /etc/rffmpeg/rffmpeg.py /usr/local/bin/rffmpeg
# sudo ln -s /usr/local/bin/rffmpeg.py /usr/local/bin/ffprobe