#!/usr/bin/env python

import os
import sys
import subprocess
import threading
import signal
import logging
import pty

log = logging.getLogger('aurbs')

# rediret bytes directly to from subprocess to stdout
# to prevent UTF-8 decoding errors
out = os.fdopen(sys.stdout.fileno(), 'wb')

class PTYOutputProxy(object):
	def __init__(self, pty_master_fd):
		self.master = pty_master_fd

	def pass_through(self):
		try:
			while True:
				out.write(os.read(self.master, 1024))
				out.flush()
		except OSError:
			pass

def call(*popenargs, timeout=None, interrupt=None, int_active_child=False, **kwargs):
	"""
	same args as subprocess.Popen
	interrupt: signal to send on exception
	"""
	if int_active_child:
		# this is needed, if the subprocess (or its childs)
		# spawn a new pgroup (eg. systemd-nspawn)
		pid, master = pty.fork()
		if pid == 0:
			p = subprocess.Popen(*popenargs, **kwargs)
			os._exit(p.wait(timeout=timeout))
		try:
			output = PTYOutputProxy(master)
			output_thread = threading.Thread(target=output.pass_through)
			output_thread.daemon = True
			output_thread.start()
			return os.waitpid(pid, 0)[1]
		except:
			if interrupt == signal.SIGINT:
				log.debug("Sending Ctrl-C via stdin to subprocess")
				os.write(master, b"\x03")
				try:
					os.waitpid(pid, 0)
				except Exception:
					pass
			raise
	else:
		with subprocess.Popen(*popenargs, stdin=subprocess.PIPE, preexec_fn=os.setsid, **kwargs) as p:
			try:
				return p.wait(timeout=timeout)
			except:
				if interrupt:
					log.debug("Sending signal to subprocess pgroup")
					os.killpg(p.pid, interrupt)
				else:
					log.warning("KeyboardInterrupt detected! - exiting subprocess...")
				p.wait(timeout=timeout)
				raise

def ccall(*popenargs, **kwargs):
	"""Run command with arguments.  Wait for command to complete.  If
	the exit code was zero then return, otherwise raise
	CalledProcessError.  The CalledProcessError object will have the
	return code in the returncode attribute.

	The arguments are the same as for the call function.  Example:

	ccall(["ls", "-l"])
	"""
	retcode = call(*popenargs, **kwargs)
	if retcode:
		cmd = kwargs.get("args")
		if cmd is None:
			cmd = popenargs[0]
		raise subprocess.CalledProcessError(retcode, cmd)
	return 0
