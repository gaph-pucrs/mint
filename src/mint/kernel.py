#!/usr/bin/env python3
from shutil import copytree, copyfile
from subprocess import run
from multiprocessing import cpu_count
from .sizes import elf_sizes

class Kernel:
	def __init__(self, platform_path, testcase_path):
		self.platform_path = platform_path
		self.testcase_path = testcase_path

	def copy(self):
		copytree("{}/MAestro".format(self.platform_path),          "{}/MAestro".format(self.testcase_path), dirs_exist_ok=1)
		copyfile("{}/MAestro/Makefile".format(self.platform_path), "{}/MAestro/Makefile".format(self.testcase_path))

	def build(self):
		NCPU = cpu_count()
		make = run(["make", "-C", "{}/MAestro".format(self.testcase_path), "-j", str(NCPU)])
		if make.returncode != 0:
			raise Exception("Error building kernel.")

	def check_size(self, page_size):
		sizes = elf_sizes("{}/MAestro/kernel.elf".format(self.testcase_path))
		used  = sum(sizes.values())

		print("\n*************************** Kernel page size report ***************************")
		if used > page_size:
			raise Exception("Kernel memory usage of {} is bigger than page size of {}".format(used, page_size))
		print("Kernel memory usage {}/{} bytes".format(str(used).rjust(45), str(page_size).ljust(6)))
		print("************************* End kernel page size report *************************")
