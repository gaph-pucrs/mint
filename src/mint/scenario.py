#!/usr/bin/env python3
from yaml import safe_load
from os import makedirs
from shutil import copyfile, rmtree, copytree
from .descriptor import Descriptor
from .application import Application
from .repository import Repository
from os.path import exists
from filecmp import cmp

class Scenario:
	def __init__(self, platform_path, testcase_path, scenario_file):
		print("Loading scenario...")

		self.platform_path = platform_path
		self.testcase_path = testcase_path

		self.base = scenario_file

		name = self.base.split(".yaml")[0].split("/")
		name = name[len(name) - 1]

		self.base_dir = "{}/{}".format(self.testcase_path, name)
		self.file = "{}/{}.yaml".format(self.base_dir, name)

		yaml = safe_load(open(self.base, "r"))

		tc_name = self.testcase_path.split("/")
		tc_name = tc_name[len(tc_name) - 1]

		tc_yaml = safe_load(open("{}/{}.yaml".format(self.testcase_path, tc_name), "r"))
		self.PKG_PAGE_SIZE_INST 	= tc_yaml["hw"]["page_size_inst_KB"] * 1024
		self.PKG_PAGE_SIZE_DATA 	= tc_yaml["hw"]["page_size_data_KB"] * 1024

		self.simulator = "verilator"
		try:
			self.simulator = tc_yaml["simulation"]["simulator"]
		except:
			pass

		# OSZ region (X, Y) anchored at PE 0,0, already validated by the testcase; None when absent
		osz_window = tc_yaml["hw"].get("osz_window")
		self.osz_window = tuple(osz_window) if osz_window is not None else None

		self.ma_tasks = []

		for task in yaml["management"]:
			self.ma_tasks.append(task)

		self.__check_osz_management()

		self.links = []
		try:
			for link in yaml["links"]:
				param = {}
				try:
					param = link["parameters"]
				except:
					pass
				self.links.append(((link["pe"][0], link["pe"][1], link["port"]), (link["trojan"], param)))
		except:
			pass

		apps_dir = "{}/applications".format(testcase_path)
		self.applications = []

		# A missing or empty apps list means no applications; any other error
		# in an entry must surface instead of silently dropping every app.
		for app in (yaml.get("apps") or []):
			app_name = app["name"]

			app_inst = "default"
			try:
				app_inst = app["instance"]
			except:
				pass

			start_ms = 0
			try:
				start_ms = app["start_time_ms"]
			except:
				print("Using 0 ms as starting time for app {}".format(app_name))

			mapping = []
			try:
				mapping = app["static_mapping"]
			except:
				print("Using pure dinamic mapping for app {}".format(app_name))

			secure = app.get("secure", False)
			if not isinstance(secure, bool):
				raise Exception("apps[].secure of app {} must be a boolean, got: {}".format(app_name, secure))

			if secure and self.osz_window is None:
				print(
					"WARNING: app {} is secure but the testcase has no hw.osz_window. "
					"Running it as non-secure.".format(app_name)
				)
				secure = False

			self.__check_osz_app_mapping(app_name, mapping, secure)

			self.applications.append(Application(app_name, app_inst, platform_path, apps_dir, testcase_path, start_ms=start_ms, mapping=mapping, secure=secure))

		self.applications.sort(key=lambda x: x.start_ms) # Sort by start time

		print("Scenario {}.yaml loaded.".format(name))
		
	def copy(self, skipdebug):
		print("Copying scenario...")

		if self.__is_obsolete():
			rmtree(self.base_dir)

		makedirs("{}/debug/available".format(self.base_dir), exist_ok=True)
		makedirs("{}/debug/request".format(self.base_dir),   exist_ok=True)
		makedirs("{}/debug/pipe".format(self.base_dir),      exist_ok=True)
		makedirs("{}/debug/ram".format(self.base_dir),       exist_ok=True)
		makedirs("{}/debug/cpu".format(self.base_dir),       exist_ok=True)
		makedirs("{}/debug/dmni".format(self.base_dir),      exist_ok=True)
		makedirs("{}/debug/safe".format(self.base_dir),      exist_ok=True)
		makedirs("{}/debug/link".format(self.base_dir),      exist_ok=True)
		makedirs("{}/log".format(self.base_dir),		     exist_ok=True)
		makedirs("{}/link".format(self.base_dir), 			 exist_ok=True)

		copyfile("{}/Phivers/sim/sim.mk".format(self.testcase_path), "{}/sim.mk".format(self.base_dir))
		copyfile(self.base, self.file)

		if not skipdebug:
			copytree("{}/debug".format(self.testcase_path), "{}/debug".format(self.base_dir), dirs_exist_ok=1)
			self.__append_platform()

		print("Scenario copied.")

	def build(self, repodebug):
		print("Building scenario...")

		self.__generate_ma_descr(repodebug)

		self.__generate_link_cfg()

		self.__generate_ma_start(repodebug)
		self.__generate_app_start(repodebug)

		print("Scenario built.")

	def __generate_app_start(self, repodebug):
		start = Repository()

		for app in self.applications:
			start.add(app.get_full_name(), "App name")
			start.add(app.start_ms, "Start time (ms)")
			start.add(1 if app.secure else 0, "Secure" if app.secure else "Not secure")

			tasks = app.get_tasks()
			for task in app.mapping:
				if task not in tasks:
					raise Exception("Task {} in static_mapping list not present in application {}".format(task, app.app_name))
		
			for task in tasks:
				address = 0xffffffff
				map_comment = ""
				if task in app.mapping:
					addr_x = app.mapping[task][0]
					addr_y = app.mapping[task][1]
					address = addr_x << 8 | addr_y
					map_comment = "statically mapped to PE {}x{}".format(addr_x, addr_y)
				else:
					map_comment = "dynamically mapped"
				
				start.add("{:04x}".format(address), "Task {} is {}".format(task, map_comment))
		
		start.write(self.base_dir+"/app_start.txt")
		
		if repodebug:
			start.write_debug(self.base_dir+"/app_start_debug.txt")

	def __generate_ma_start(self, repodebug):
		start = Repository()

		start.add(len(self.ma_tasks), "Number of tasks")

		for task in self.ma_tasks:
			name = task["task"]

			try:
				address = task["static_mapping"]
				addr_x = int(address[0])
				addr_y = int(address[1])
				address = addr_x << 8 | addr_y
				map_comment = "statically mapped to PE {}x{}".format(addr_x, addr_y)
				start.add("{:04x}".format(address), "Task {} is {}".format(name, map_comment))
			except:
				raise Exception("All management tasks must be STATICALLY MAPPED")
						
			try:
				descr = Descriptor("{}/management/{}/config.yaml".format(self.testcase_path, task["task"]), task["task"])
				task_type = descr.get_type()
				start.add("{:08x}".format(task_type), "Task type tag")
			except:
				raise Exception("All management tasks must have a config.yaml with its task type tag")
			
		start.write("{}/ma_start.txt".format(self.base_dir))

		if repodebug:
			start.write_debug("{}/ma_start_debug.txt".format(self.base_dir))

	def __generate_link_cfg(self):
		for link in self.links:
			if link[1][0] == "rs":
				with open("{}/link/rs{}x{}-{}.cfg".format(self.base_dir, link[0][0], link[0][1], link[0][2]), "w") as file:
					file.write("{}\n".format(self.__link_param_or_default(link[1][1], "tick_begin",        0)))
					file.write("{}\n".format(self.__link_param_or_default(link[1][1], "cycle_min",        50)))
					file.write("{}\n".format(self.__link_param_or_default(link[1][1], "cycle_max",        75)))
					file.write("{}\n".format(self.__link_param_or_default(link[1][1], "chance",		      33)))
					file.write("{}\n".format(self.__link_param_or_default(link[1][1], "filter_app",       -1)))
					file.write("{}\n".format(self.__link_param_or_default(link[1][1], "filter_prod",      -1)))
					file.write("{}\n".format(self.__link_param_or_default(link[1][1], "filter_cons",      -1)))
			else:
				raise Exception("Invalid link type at {}x{}-{}".format(link[0][0], link[0][1], link[0][2]))

	def __link_param_or_default(self, dict, key, default):
		try:
			return dict[key]
		except:
			return default

	def __generate_ma_descr(self, repodebug):
		descr = Repository()

		for idx, task in enumerate(self.ma_tasks):
			if idx == 0 and task["task"] != "mapper_task":
				raise Exception("First management task must be mapper_task")
			descr.add(task["task"], "Task name")

		descr.write("{}/ma_tasks.txt".format(self.base_dir))

		if repodebug:
			descr.write_debug("{}/ma_tasks_debug.txt".format(self.base_dir))

	def __append_platform(self):
		task_lines = []
		app_lines = []

		app_id = 1

		for app in self.applications:
			app_lines.append("{}\t{}\n".format(app.get_full_name(), app_id))
			
			tasks = app.get_tasks()
			for t in range(len(tasks)):
				task_lines.append("{} {}\n".format(tasks[t], app_id << 8 | t))

			app_id += 1

		cfg = open("{}/debug/platform.cfg".format(self.base_dir), "a")

		cfg.write("BEGIN_task_name_relation\n")

		for t in range(len(self.ma_tasks)):
			cfg.write("{} {}\n".format(self.ma_tasks[t]["task"], t))

		cfg.writelines(task_lines)
		cfg.write("END_task_name_relation\n")

		cfg.write("BEGIN_app_name_relation\n")

		cfg.write("management\t0\n")
		cfg.writelines(app_lines)

		cfg.write("END_app_name_relation\n")

		cfg.close()
  
	def __in_osz(self, x, y):
		return self.osz_window is not None and x < self.osz_window[0] and y < self.osz_window[1]

	def __osz_desc(self):
		return "[{}, {}] (PEs 0,0 to {},{})".format(
			self.osz_window[0], self.osz_window[1], self.osz_window[0] - 1, self.osz_window[1] - 1
		)

	def __check_osz_management(self):
		"""Management tasks are never secure: none may be pinned inside the OSZ region."""
		if self.osz_window is None:
			return

		for task in self.ma_tasks:
			if "static_mapping" not in task:
				continue	# Reported later: every management task must be statically mapped
			x, y = int(task["static_mapping"][0]), int(task["static_mapping"][1])
			if self.__in_osz(x, y):
				raise Exception(
					"Management task {} is statically mapped to PE {},{}, inside the OSZ region {}. "
					"Management tasks must be mapped outside it.".format(task["task"], x, y, self.__osz_desc())
				)

	def __check_osz_app_mapping(self, app_name, mapping, secure):
		"""A secure app may only be pinned inside the OSZ region, a non-secure one only outside."""
		if self.osz_window is None:
			return

		for task in mapping:
			x, y = int(mapping[task][0]), int(mapping[task][1])
			inside = self.__in_osz(x, y)
			if secure and not inside:
				raise Exception(
					"Task {} of secure app {} is statically mapped to PE {},{}, outside the OSZ region {}. "
					"Secure apps must be mapped inside it.".format(task, app_name, x, y, self.__osz_desc())
				)
			if not secure and inside:
				raise Exception(
					"Task {} of non-secure app {} is statically mapped to PE {},{}, inside the OSZ region {}. "
					"Non-secure apps must be mapped outside it.".format(task, app_name, x, y, self.__osz_desc())
				)

	def __is_obsolete(self):
		if exists(self.file):
			if not cmp(self.base, self.file):
				return True
		
		return False
