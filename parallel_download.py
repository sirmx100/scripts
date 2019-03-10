#!/usr/bin/env python
import os
import urllib2
import time
import multiprocessing.dummy as multiprocessing
import string
from random import choice
import socket
from ctypes import c_int
import tempfile
import requests
import re
import sys

import dummy

# change this
url = "https://url/file"

headers = {'user-agent': 'test-app/0.0.1'}

shared_bytes_var = multiprocessing.Value(c_int, 0) # a ctypes var that counts the bytes already downloaded

def DownloadFile(url, path, startByte=0, endByte=None, ShowProgress=True):
	url = url.replace(' ', '%20')
	headers = {}
	if endByte is not None:
	headers['Range'] = 'bytes=%d-%d' % (startByte,endByte)
	req = urllib2.Request(url, headers=headers)

	try:
	urlObj = urllib2.urlopen(req, timeout=4)
	except urllib2.HTTPError, e:
	if "HTTP Error 416" in str(e):
	print " Retrying..."
	time.sleep(5)
	return DownloadFile(url, path, startByte, endByte, ShowProgress)
	else:
	raise e

	f = open(path, 'wb')
	meta = urlObj.info()
	try:
	filesize = int(meta.getheaders("Content-Length")[0])
	except IndexError:
	print "Server did not send Content-Length."
	ShowProgress=False

	filesize_dl = 0
	block_sz = 8192
	while True:
	try:
	buff = urlObj.read(block_sz)
	except (socket.timeout, socket.error, urllib2.HTTPError), e:
	dummy.shared_bytes_var.value -= filesize_dl
	raise e

	if not buff:
	break

	filesize_dl += len(buff)
	try:
	dummy.shared_bytes_var.value += len(buff)
	except AttributeError:
	pass
	f.write(buff)

	if ShowProgress:
	status = r"%.2f MB / %.2f MB %s [%3.2f%%]" % (filesize_dl / 1024.0 / 1024.0,
	filesize / 1024.0 / 1024.0, progress_bar(1.0*filesize_dl/filesize),
	filesize_dl * 100.0 / filesize)
	status += chr(8)*(len(status)+1)
	print status,
	if ShowProgress:
	print "\n"

	f.close()
	return path

def DownloadFile_Parall(url, path=None, processes=6,
	minChunkFile=1024**2, nonBlocking=False):
	from HTTPQuery import Is_ServerSupportHTTPRange
	global shared_bytes_var
	shared_bytes_var.value = 0
	url = url.replace(' ', '%20')

	if not path:
	path = get_rand_filename(os.environ['temp'])
	if not os.path.exists(os.path.dirname(path)):
	os.makedirs(os.path.dirname(path))
	print "Downloading to %s..." % path

	urlObj = urllib2.urlopen(url)
	meta = urlObj.info()
	filesize = int(meta.getheaders("Content-Length")[0])

	if filesize/processes > minChunkFile and Is_ServerSupportHTTPRange(url):
	args = []
	pos = 0
	chunk = filesize/processes
	for i in range(processes):
	startByte = pos
	endByte = pos + chunk
	if endByte > filesize-1:
	endByte = filesize-1
	args.append([url, path+".%.3d" % i, startByte, endByte, False])
	pos += chunk+1
	else:
	args = [[url, path+".000", None, None, False]]

	print "Running %d processes..." % processes
	pool = multiprocessing.Pool(processes, initializer=_initProcess,initargs=(shared_bytes_var,))
	mapObj = pool.map_async(lambda x: DownloadFile(*x) , args)
	if nonBlocking:
	return mapObj, pool
	while not mapObj.ready():
	status = r"%.2f MB / %.2f MB %s [%3.2f%%]" % (shared_bytes_var.value / 1024.0 / 1024.0,
	filesize / 1024.0 / 1024.0, progress_bar(1.0*shared_bytes_var.value/filesize),
	shared_bytes_var.value * 100.0 / filesize)
	status = status + chr(8)*(len(status)+1)
	print status,
	time.sleep(0.1)

	file_parts = mapObj.get()
	pool.terminate()
	pool.join()

	combine_files(file_parts, path)

def combine_files(parts, path):
	with open(path,'wb') as output:
	for part in parts:
	with open(part,'rb') as f:
	output.writelines(f.readlines())
	os.remove(part)

def progress_bar(progress, length=20):
	length -= 2 # The bracket are 2 chars long.
	return "[" + "#"*int(progress*length) + "-"*(length-int(progress*length)) + "]"

def get_rand_filename(dir_=os.getcwd()):
	return tempfile.mkstemp('.tmp', '', dir_)[1]

def _initProcess(x):
  dummy.shared_bytes_var = x

def dlfile(url):
	filename = get_fname(url)
	dlitem(url, filename)

DownloadFile_Parall(url)
