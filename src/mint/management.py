#!/usr/bin/env python3
from shutil import copytree
from os import listdir
from subprocess import run, check_output
from multiprocessing import cpu_count
from .sizes import elf_sizes

class Management:
	def __init__(self, platform_path, testcase_path):
		self.testcase_path = testcase_path
		
		self.source_path = "{}/management".format(platform_path)
		self.base_path = "{}/management".format(testcase_path)

	def copy(self):
		copytree(self.source_path, self.base_path, dirs_exist_ok=1)

	def build(self):
		NCPU = cpu_count()

		for task in listdir(self.base_path):
			if task == "common":
				continue
			make = run(["make", "-C", "{}/{}".format(self.base_path, task), "-j", str(NCPU)])
			if make.returncode != 0:
				raise Exception("Error build MA task {}.".format(task))

	def check_size(self, page_size):
		tasks = [task for task in listdir(self.base_path) if task != "common"]
		self.entry_points = {}
		used = {}

		for task in tasks:
			path = "{}/{}/{}.elf".format(self.base_path, task, task)

			used[task] = sum(elf_sizes(path).values())

			out = check_output(["riscv64-elf-readelf", path, "-h"]).split(b'\n')[10].split(b' ')[-1]
			self.entry_points[task] = int(out, 16)
			
		print("\n***************************** MA page size report *****************************")
		for task in tasks:
			if used[task] > page_size:
				raise Exception("Task {} memory usage of {} is bigger than page size of {}".format(task, used[task], page_size))
			print("Task {} memory usage {}/{} bytes".format(task.rjust(29), str(used[task]).rjust(6), str(page_size).ljust(6)))
		print("*************************** End MA page size report ***************************")
