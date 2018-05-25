#!/usr/bin/python

import os
import sys
import simplejson as json

import networkx as nx
import matplotlib.pyplot as plt

"""
sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/' + '../..'))
from aurbs import dummy
from aurbs.db import Database
from aurbs.config import AurBSConfig
from aurbs.static import *
from aurbs.helper import *


AurBSConfig("/etc/aurbs.yml")
db = Database()

pkgs = []
tree = {}

def add(pkgname):
	try:
		pkg = db.get_pkg(pkgname)
	except KeyError:
		pkg = dummy.aurpkg(pkgname)
	deps = []
	for dep in pkg['depends']:
		if dep in AurBSConfig().aurpkgs:
			deps.append(dep)
	for dep in pkg['makedepends']:
		if dep in AurBSConfig().aurpkgs:
			deps.append(dep)
	tree[pkgname] = deps


for pkgname in AurBSConfig().aurpkgs:
	add(pkgname)
#json.dump(tree, open('/tmp/dep.json', 'w'))
"""

tree = json.load(open('/tmp/dep.json', 'r'))


items = []

for pkgname, deps in tree.items():
	for dep in deps:
		items.append([pkgname, dep])
	if not deps:
		items.append([pkgname, "aurbs-root"])

G = nx.MultiDiGraph()
G.add_edges_from(items)

groups = {}
ypos = {}
pos = {}

def look(pkgname, deepth=0):
	if pkgname not in groups or groups[pkgname] < deepth:
		groups[pkgname] = deepth
		newdeepth = deepth + 1
		for depending_pkg in G.predecessors_iter(pkgname):
			look(depending_pkg, newdeepth)

look("aurbs-root")

for pkgname, group in groups.items():
	x = group
	y = ypos.get(group, 0)
	m = 1 if x > 1 else 0
	m = 1
	pos[pkgname] = (x, y * m)
	ypos[group] = y + 1

pos["aurbs-root"] = (0, ypos[1] / 2)

#pos=nx.spring_layout(G, iterations=10)
#nx.draw(G,pos)
#H=G.to_directed()
#pos=nx.graphviz_layout(G,prog='twopi',args='')
#plt.figure(figsize=(8,8))


plt.figure(figsize=(20,40))
nx.draw(G, pos, node_size=300, node_color='b')#, height=(ypos[0] * 300) )
plt.savefig("/tmp/dep.svg") # save as png
#plt.show()
