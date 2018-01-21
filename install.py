import requests
from requests.auth import HTTPBasicAuth
import json
import re
import time

#Taking in the IP address and the port info from the customer

print ('Service Container Install Wizard \n')

IP = raw_input('Enter the Guest IP address of CSR_MGMT OVA:')
PORT = raw_input('Enter the port on which RestAPI has been enabled:')

url_login = 'https://'+IP+':'+PORT+'/api/v1/auth/token-services'

header1 = { 'Accept':'application/json' }

username = raw_input('Enter the username :')
password = raw_input('Enter the password :')

try:
	response_login = requests.post(url_login, headers=header1, auth=HTTPBasicAuth(username, password), data={}, verify=False)
	#print (response_login)

	print (requests.exceptions.ConnectionError)
	#if response_login == '<Response [200]>':
	if response_login.status_code == 200:
		print ('Login successful! \n')
		logincookie = response_login.json()
		cookie = logincookie['token-id']
	        #print (cookie)
		
		#Printing basic information of router
		print ('Basic information from the router: \n =====================')
		url_uptime = 'https://'+IP+':'+PORT+'/api/v1/global/uptime'
		header = { 'Accept':'application/json', 'X-Auth-Token':cookie }
		response_uptime = requests.get(url_uptime, headers=header, verify=False)
		response_uptime_1 = response_uptime.json()
		print ('Uptime of the router:'+response_uptime_1['uptime'])

		url_show_version = 'https://'+IP+':'+PORT+'/api/v1/global/version'
		header = { 'Accept':'application/json', 'X-Auth-Token':cookie }
		response_show_ver = requests.get(url_show_version, headers=header, verify=False)
		response_show_ver_1 = response_show_ver.json()
		print ('Version:'+response_show_ver_1['version']+'\n \n')	


		#Cheking if the version supports Service Containers
		print ('Checking if the version is compataible....')
		if re.match('03.1[7-9].*',  response_show_ver_1['version']):
			print ('OK \n')
			
			url_cli = 'https://'+IP+':'+PORT+'/api/v1/global/cli'
			header2 = { 'Content-Type':'application/json', 'X-Auth-Token':cookie }
			
			show_flash = requests.put(url_cli, headers=header2, data='{"show": "flash: | inc ova"}', verify=False)
			show_flash1 = show_flash.json()
			
			#Checking if KVM is a suported type of container
			print ('Checking if KVM is supported....')
			show_service = requests.put(url_cli, headers=header2, data='{"show": "virtual-service"}', verify=False)
			#print (show_service.json())
			show_service1 = show_service.json()
				
			if re.search('Machine types supported   : KVM,.*', show_service1['results']):
					print ('OK \n')

					#Cheking for available memory
					s = show_service1['results']
					result = re.search('memory \(MB\)(.*)', s)
	             			memory_stats = result.group(1)
					x= map(int, memory_stats.split( ))
					print ('The available memory is '+str(x[2]))
					if x[2]>=500:
						print('Memory - OK \n')
			
			 
						#Looking for Sonar.ova on flash
						print ('Looking for Sonar3.ova on flash......')
						if re.search('Sonar3.ova', show_flash1['results']):
							print ('OK, proceeding with the installation! \n')
							
							#Changing the signing level to unsigned
							print ('Changing the signing level to unsigned \n')
							signing_level = requests.put(url_cli, headers=header2, data='{"config:" "virtual-service \n signing level unsigned"}', verify=False)
							
							#Displaying the list of VPGs
							print ("Here's a list of the configured Virtual Port Groups \n")
							vpg_list = requests.put(url_cli, headers=header2, data='{"show": " ip int brief | inc Virtual"}', verify=False)
							vpg_list1 = vpg_list.json()
							vpg = vpg_list1['results']
							print (vpg)

							#Getting the IP an Port info for VPG
							IP_vpg = raw_input('\n Enter the IP address with subnet mask to be used for the Virtual Port Group: ')
							vpg_number = raw_input ('Enter the Virtual Port Group number (unique): ')
						
							#Configuring the VPG
							
							vpg_com1 = json.dumps({"config" : "int VirtualPortGroup" +vpg_number + '\n ip address ' +IP_vpg+ '\n'})
							#print (vpg_com1)
							vpg_sonar = requests.put(url_cli, headers=header2, data=vpg_com1, verify=False)
							
							#Installing the Sonar OVA
							install = requests.put(url_cli, headers=header2, data='{ "exec" : "virtual-service install name Sonar package flash:Sonar3.ova" }', verify=False)
							
							print ("\n Installing...")
							time.sleep(15)
							show_virt = requests.put(url_cli, headers=header2, data='{ "show" : "virt list" }', verify=False)
							show_virt1 = show_virt.json()
							#print (show_virt1)
							virt = show_virt1['results']
							#print (virt)
							while (re.search('Installing', virt)):
								
								show_virt = requests.put(url_cli, headers=header2, data='{ "show" : "virt list" }', verify=False)
								show_virt1 = show_virt.json()
								virt = show_virt1['results']
									
							
								#print ("installing")
							print ("Installation complete! Now activating... \n")
						
							#Activating the Sonar
						
							virt_sonar = json.dumps({ "config" : "virtual-service Sonar \n vnic gateway VirtualPortGroup "+vpg_number+ "\n exit \n activate \n" }) 
							activate = requests.put(url_cli, headers=header2, data=virt_sonar, verify=False)
							time.sleep(10)
							show_virtt = requests.put(url_cli, headers=header2, data='{"show": " virt list"}', verify=False)
	                                                show_virtt1 = show_virtt.json()
	                                                virtt = show_virtt1['results']
							if (re.search('Activate Failed', virtt)):
								print ("Activate failed, please check logs for errors \n")
								# Rolling back the changes
								print ("Rolling back changes... \n")
								no_activate_data = json.dumps({"config" : "virtual-service Sonar \n no activate"})
								no_activate = requests.put(url_cli, headers=header2, data=no_activate_data, verify=False)
								time.sleep(15)
								no_sonar = requests.put(url_cli, headers=header2, data='{"config" : "no virtual-service Sonar"}', verify=False)
								del_vpg = json.dumps({ "config" : "no int VirtualPortGroup "+vpg_number})
								no_vpg = requests.put(url_cli, headers=header2, data=del_vpg, verify=False)
								uninstall = requests.put(url_cli, headers=header2, data='{"exec" : "virtual-service uninstall name Sonar"}', verify=False)
							else:
								print("Activation successful! Please wait....")
								#De-activating and activating the OVA
								deactivate_data = json.dumps({"config" : "virtual-service Sonar \n no activate"})
								deactivate = requests.put(url_cli, headers=header2, data=deactivate_data, verify=False)
								#time.sleep(15)
								show_virt = requests.put(url_cli, headers=header2, data='{ "show" : "virt list" }', verify=False)
								show_virt1 = show_virt.json()
								virt = show_virt1['results']
								while (re.search('Deactivating', virt)):
									show_virt = requests.put(url_cli, headers=header2, data='{ "show" : "virt list" }', verify=False)
									show_virt1 = show_virt.json()
									virt = show_virt1['results']
								activate_data = json.dumps({"config" : "virtual-service Sonar \n activate"})
								activate = requests.put(url_cli, headers=header2, data=activate_data, verify=False)
								print ("Networking is up") 	
						else:
							print ('Please copy the .ova to the flash of the router')
			
					else:
						print('Not enough memory. The min requirement is 500MB')
			else:
				print ('KVM is not supported')
		else:
			print ('Please ugrade the router to a version >= IOS XE 3.17')


		
	else: 
		print('Login unsuccessful!! Please check connectivity/credentials/config') 

except:
	print ("\n Unable to connect to the network specified! Please check the IP and port information again.")
