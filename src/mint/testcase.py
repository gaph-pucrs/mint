#!/usr/bin/env python3
from os.path import exists
from filecmp import cmp
from os import makedirs
from shutil import copyfile, rmtree
from yaml import safe_load
from .libs import Libs
from .kernel import Kernel
from .hardware import Hardware
from .management import Management

class Testcase:
	def __init__(self, platform_path, testcase_base):
		print("Loading testcase...")

		self.platform_path = platform_path
		self.path = platform_path
		self.base = testcase_base

		name = self.base.split(".yaml")[0].split("/")
		name = name[len(name) - 1]

		self.base_dir = name
		self.file = "{}/{}.yaml".format(self.base_dir, name)

		yaml = safe_load(open(self.base, "r"))

		self.PKG_N_PE_X = yaml["hw"]["mpsoc_dimension"][0]
		self.PKG_N_PE_Y = yaml["hw"]["mpsoc_dimension"][1]
		self.PKG_PAGE_SIZE_INST 	= yaml["hw"]["page_size_inst_KB"] * 1024
		self.PKG_PAGE_SIZE_DATA 	= yaml["hw"]["page_size_data_KB"] * 1024
		PKG_MAX_LOCAL_TASKS	= yaml["hw"]["tasks_per_PE"]

		# OSZ reserved region: (X, Y) size anchored at PE 0,0, or None when absent
		self.osz_window = self.__load_osz_window(yaml)

		self.simulator = "verilator"
		try:
			self.simulator = yaml["simulation"]["simulator"]
		except:
			pass

		self.trace = False
		try:
			self.trace = yaml["simulation"]["trace"]
		except:
			pass
				
		peripherals = {}
		for peripheral in yaml["hw"]["Peripherals"]:
			x = int(peripheral["pe"][0])
			y = int(peripheral["pe"][2])
			port = self.__port_code(peripheral["port"])
			peripherals[peripheral["name"]] = ((x, y), port)

		self.__check_osz_peripherals(peripherals)

		links = []
		try:
			for link in yaml["hw"]["links"]:
				links.append(((link["pe"][0], link["pe"][1], link["port"]), link["trojan"]))
		except:
			pass
				
		parameters = {}
		try:
			for parameter in yaml["hw"]["parameters"]:
				parameters[str(list(parameter.keys())[0])] = str(list(parameter.values())[0])
		except:
			pass

		self.libs = Libs(self.platform_path, self.base_dir)
		self.kernel = Kernel(self.platform_path, self.base_dir)

		self.hardware = Hardware(
			self.platform_path, 
			self.base_dir, 
			self.PKG_PAGE_SIZE_INST, 
			self.PKG_PAGE_SIZE_DATA, 
			PKG_MAX_LOCAL_TASKS, 
			self.PKG_N_PE_X, 
			self.PKG_N_PE_Y, 
			peripherals, 
			links,
			parameters,
			osz_window=self.osz_window
		)

		self.management = Management(self.platform_path, self.base_dir)

		print("Testcase {}.yaml loaded.".format(name))
		
	def copy(self, skipdebug):
		print("Copying testcase...")

		# If testcase has been updated, delete to rebuild everything
		if self.__is_obsolete():
			rmtree(self.base_dir)

		makedirs(self.base_dir, exist_ok=True)
		copyfile(self.base, self.file)

		self.libs.copy()
		self.kernel.copy()
		self.hardware.copy()
		self.management.copy()

		if not skipdebug:
			makedirs("{}/debug".format(self.base_dir), exist_ok=True)
			self.__create_platform()
			self.__create_services()
			self.__create_cpu()

		print("Testcase copied.")

	def build(self):
		print("Building testcase...")
		
		self.libs.build()
		
		self.kernel.build()
		self.management.build()

		self.hardware.build(self.simulator, self.trace)

		self.kernel.check_size(self.PKG_PAGE_SIZE_INST, self.PKG_PAGE_SIZE_DATA)
		self.management.check_size(self.PKG_PAGE_SIZE_INST, self.PKG_PAGE_SIZE_DATA)

		print("Testcase built.")

	def __load_osz_window(self, yaml):
		"""Parses hw.osz_window: [X, Y].

		The region always starts at PE 0,0 and covers x in [0, X-1] and
		y in [0, Y-1]; e.g. [3,2] covers 0,0 0,1 1,0 1,1 2,0 2,1. Column X
		stays free; non-secure tasks may only use x >= X+1.
		Returns (X, Y), or None when the key is absent (region disabled).
		"""
		window = yaml["hw"].get("osz_window")
		if window is None:
			return None

		if (
			not isinstance(window, list) or len(window) != 2 or
			not all(isinstance(v, int) and not isinstance(v, bool) for v in window)
		):
			raise Exception("hw.osz_window must be [X, Y] with integer sizes, got: {}".format(window))

		x, y = window
		if x < 1 or y < 1:
			raise Exception("hw.osz_window sizes must be at least 1, got: [{}, {}]".format(x, y))

		# Column X, right of the region, must stay free, and at least one column
		# x >= X+1 must remain for the management and non-secure applications
		if x > self.PKG_N_PE_X - 2:
			raise Exception(
				"hw.osz_window X = {} leaves no column for non-secure applications on the {}x{} mesh: "
				"column {} must stay free and non-secure tasks need x >= {}. X must be at most {}.".format(
					x, self.PKG_N_PE_X, self.PKG_N_PE_Y, x, x + 1, self.PKG_N_PE_X - 2
				)
			)

		if y > self.PKG_N_PE_Y:
			raise Exception(
				"hw.osz_window Y = {} does not fit inside the {}x{} mesh.".format(
					y, self.PKG_N_PE_X, self.PKG_N_PE_Y
				)
			)

		return (x, y)

	def __check_osz_peripherals(self, peripherals):
		"""No peripheral may sit on a PE inside the OSZ region: a sealed zone
		would cut it off from the rest of the mesh."""
		if self.osz_window is None:
			return

		osz_x, osz_y = self.osz_window
		for name, ((x, y), _port) in peripherals.items():
			if x < osz_x and y < osz_y:
				raise Exception(
					"Peripheral {} at PE {},{} is inside the OSZ region [{}, {}] "
					"(PEs 0,0 to {},{}). Move it outside the region.".format(
						name, x, y, osz_x, osz_y, osz_x - 1, osz_y - 1
					)
				)

	def __is_obsolete(self):
		if exists(self.file):
			if not cmp(self.base, self.file):
				return True
		
		return False

	def __create_platform(self):
		with open("{}/debug/platform.cfg".format(self.base_dir), "w") as cfg:
			cfg.write("router_addressing XY\n")
			cfg.write("channel_number {}\n".format(2))
			cfg.write("mpsoc_x {}\n".format(self.PKG_N_PE_X))
			cfg.write("mpsoc_y {}\n".format(self.PKG_N_PE_Y))
			cfg.write("flit_size {}\n".format(32))
			cfg.write("clock_period_ns {}\n".format(10))

			# Legacy lines. This will 'trick' the debugger into assigning no master
			cfg.write("cluster_x {}\n".format(self.PKG_N_PE_X))
			cfg.write("cluster_y {}\n".format(self.PKG_N_PE_Y))
			cfg.write("manager_position_x {}\n".format(self.PKG_N_PE_X))
			cfg.write("manager_position_y {}\n".format(self.PKG_N_PE_Y))

		
	def __create_services(self):
		with open("{}/libmemphis/src/include/memphis/services.h".format(self.base_dir), "r") as services:
			with open("{}/debug/services.cfg".format(self.base_dir), "w") as cfg:
				for line in services:
					words = line.split()
					if len(words) > 2 and "#define" in words:
						key = words[1]
						value = 0
						value = int(words[2], base=16)
						cfg.write("{} {:x}\n".format(key, value))

				services.close()

				cfg.write("\n")
				cfg.write("$TASK_ALLOCATION_SERVICE 42 23\n")
				cfg.write("$TASK_TERMINATED_SERVICE 06 23\n")

	def __create_cpu(self):
		with open("{}/debug/cpu.cfg".format(self.base_dir), "w") as cfg:
			cfg.write("Interruption\t65536\n")
			cfg.write("Scheduler\t262144\n")
			cfg.write("Idle\t524288\n")

	def __port_code(self, char):
		if char == 'E':
			return "HERMES_EAST"
		if char == 'W':
			return "HERMES_WEST"
		if char == 'N':
			return "HERMES_NORTH"
		if char == 'S':
			return "HERMES_SOUTH"
		if char == 'L':
			return "HERMES_LOCAL"
		return 5
