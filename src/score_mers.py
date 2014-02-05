#!/usr/bin/env python
import sys
import os

from multiprocessing import Pool
from subprocess import *
from itertools  import combinations
from itertools  import ifilter

import numpy as np
import pdb

fg_mers = {}
bg_mers = {}

if(len(sys.argv) == 5):
	selectivity_fn =  sys.argv[1]
	fg_fasta_fn    =  sys.argv[2]
	bg_fasta_fn    =  sys.argv[3]
	output_file    =  sys.argv[4]
else:
	print "please specify your inputs"
	print "ex: select_mers.py fg_counts_file fg_fasta_file bg_counts_file bg_fasta_file output_file"
	exit()

# empty class to fill up mer information with
class Mer:
	pass

# import our variables
min_mer_range    = int(os.environ.get("min_mer_range", 6));
max_mer_range    = int(os.environ.get("max_mer_range", 10));
min_mer_count    = int(os.environ.get("min_mer_count", 0));
max_select       = int(os.environ.get("max_select", 15));
max_mer_distance = int(os.environ.get("max_mer_distance", 5000));
nb_max_consecutive_binding = int(os.environ.get("max_consecutive_binding", 4));


binding = { 'A': 'T', 'T': 'A',	'C': 'G', 'G': 'C',	'_': False }

def max_consecutive_binding(mer1, mer2):
	if len(mer2) > len(mer1):
		mer1, mer2 = mer2, mer1
	
	# save the len because it'll change when we do a ljust
	mer1_len = len(mer1)
	# reverse mer2,
	mer2 = mer2[::-1]
	# pad mer one to avoid errors
	mer1 = mer1.ljust(mer1_len + len(mer2), "_")

	max_bind = 0;
	for offset in range(mer1_len):
		consecutive = 0
		for x in range(len(mer2)):
			if binding[mer1[offset+x]] == mer2[x]:
				consecutive += 1
				if consecutive > max_bind:
					max_bind = consecutive
			else:
				consecutive = 0

	return max_bind

def populate_locations(input_fn, mers, mer):
	''' Run the strstreamone command, and parse in the integers that are output
			by the command, and add it to mers[mer].pts 
	'''

	cmd = 'strstreamone ' + mer + " < " + input_fn
	
	strstream = Popen(cmd, stdout=PIPE, shell=True)
	for line in strstream.stdout:
		mers[mer].pts.append(int(line))


def apply_filters(combination):
	for mer in combination:
		for other_mer in combination:
			if not mer == other_mer:
				if mer in other_mer:
					return False

	for combo in combinations(combination, 2):
		if heterodimer_dic[combo] > nb_max_consecutive_binding:
			return False

	return True

def score_mers(selected):
	import time
	# import gmpy

	p = Pool()

	fh = open(output_file, 'w');
	fh.write("scores:\n");
	for select_n in range(1, max_select+1):
		print "scoring size ", select_n,
		t = time.time()
		scores_it = p.imap_unordered(score, ifilter(apply_filters, combinations(selected, select_n)), chunksize=128)
		for score_res in scores_it:
			if score_res is not None:
				fh.write(str(score_res) + "\n");
		print "size ", select_n, "took:", time.time()	- t


heterodimer_dic = {}
def score(combination):
# input is a string of mers like 
# ['ACCAA', 'ACCCGA', 'ACGTATA']


	#if not apply_filters(combination):
	#	return [combination, "filter"]
	# fg points
	fg_pts = []
	fg_dist = []

	for mer in combination:
		fg_pts = fg_pts + fg_mers[mer].pts

	fg_pts.sort()

	# fg distances
	fg_dist = np.array([abs(fg_pts[i] - fg_pts[i-1]) for i in range(1, len(fg_pts))])

  # return without calculating scores if any objects are higher than our max distance
	if any(dist > max_mer_distance for dist in fg_dist):
		#ret.append("max")
		return [combination, "max", max(fg_dist)]

	min_mer_distance = max(len(i) for i in combination)
	# return without calculating scores if any mers are closer than the length of our longest mer in the combination
	if any(dist < min_mer_distance for dist in fg_dist):
		return [combination, "minx", min(fg_dist)]

	# bg points
	bg_pts = []
	bg_dist = []

	for mer in combination:
		bg_pts = bg_pts + bg_mers[mer].pts

	bg_pts.sort()

	# bg distances
	bg_dist = np.array([abs(bg_pts[i] - bg_pts[i-1]) for i in range(1, len(bg_pts))])

	nb_primers = len(combination)
	fg_mean_dist =  np.mean(fg_dist)
	fg_variance_dist = np.var(fg_dist)
	bg_mean_dist = np.mean(bg_dist)
	bg_variance_dist = np.var(bg_dist)

	# this is our equation
	score = (nb_primers * fg_mean_dist * fg_variance_dist) / ((bg_mean_dist * bg_variance_dist) + .000001)

	return [score, fg_mean_dist, fg_variance_dist, bg_mean_dist, bg_variance_dist]

def pop_fg(mer):
	''' helper for map function '''
	populate_locations(fg_fasta_fn, fg_mers, mer)

def pop_bg(mer):
	''' helper for map function '''
	populate_locations(bg_fasta_fn, bg_mers, mer)

def main():
	import time
	selected = []
	selectivity_fh = open(selectivity_fn, "r")
	
	# get our genome length
	fg_genome_length = os.path.getsize(fg_fasta_fn)
	bg_genome_length = os.path.getsize(bg_fasta_fn)

	for row in selectivity_fh:
		(mer, fg_count, bg_count, selectivity) = row.split()
		fg_mers[mer] = Mer()
		fg_mers[mer].pts = []
		fg_mers[mer].count = fg_count
		bg_mers[mer] = Mer()
		bg_mers[mer].pts = []
		bg_mers[mer].count = bg_count
		selected.append([mer, selectivity])
		
	selected =	selected[-35:] 
	selected_mers = [row[0] for row in selected]

	print "Populating foreground locations"

	map(pop_fg, selected_mers)
	print "Populating background locations"

	map(pop_bg, selected_mers)

	print "calculating heterodimer distances"
	for (mer1, mer2) in combinations(selected_mers, 2):
		if (mer1, mer2) not in heterodimer_dic:
			heterodimer_dic[(mer1, mer2)] = max_consecutive_binding(mer1, mer2)

	print "scoring mer combinations"
	score_mers(selected_mers)

	print "fg_genome_length", fg_genome_length
	print "bg_genome_length", bg_genome_length
	print "output_file:", output_file
	

if __name__ == "__main__":
	sys.exit(main())
