from os.path import exists
from subprocess import Popen
from .testcase import Testcase
from .applications import Applications
from .scenario import Scenario
from .simulation import Simulation

def path_to_yaml(path):
	testcase_name = path.split("/")
	testcase_name = testcase_name[len(testcase_name) - 1]
	return "{}/{}.yaml".format(path, testcase_name)

def yaml_to_name(yaml):
	name = yaml.split(".")
	name = name[len(name) - 2]
	name = name.split("/")
	name = name[len(name) - 1]
	return name

def check_yaml(tc, app=None, sc=None):
	if not exists(tc):
		raise Exception("Testcase {} not found.".format(tc))

	if app is not None and not exists(app):
		raise Exception("Applications {} not found.".format(app))

	if sc is not None and not exists(sc):
		raise Exception("Scenario {} not found.".format(sc))

def testcase_build(platform_path, testcase_file, skipdebug):
	check_yaml(testcase_file)
	tc = Testcase(platform_path, testcase_file)
	tc.copy(skipdebug)
	tc.build()

def applications_build(platform_path, testcase_folder, applications_file, repodebug):
	check_yaml(path_to_yaml(testcase_folder), applications_file)
	apps = Applications(platform_path, testcase_folder, applications_file)
	apps.copy()
	apps.build(repodebug)

def scenario_build(platform_path, testcase_folder, scenario_file, skipdebug, repodebug):
	check_yaml(path_to_yaml(testcase_folder), sc=scenario_file)
	scenario = Scenario(platform_path, testcase_folder, scenario_file)
	scenario.copy(skipdebug)
	scenario.build(repodebug)

def simulate(platform_path, debugger_path, scenario_folder, timeout, nogui, wave):
	if not exists(scenario_folder):
		raise Exception("Scenario folder {} not found.".format(scenario_folder))

	simulation = Simulation(platform_path, debugger_path, scenario_folder, timeout, (not nogui), wave)
	simulation.run()

def memphis_all(platform_path, debugger_path, testcase_file, scenario_file, applications_file, timeout, nogui, wave, skipdebug, repodebug):
	testcase_build(platform_path, testcase_file, skipdebug)

	testcase_name = yaml_to_name(testcase_file)

	applications_build(platform_path, testcase_name, applications_file, repodebug)
	scenario_build(platform_path, testcase_name, scenario_file, skipdebug, repodebug)

	scenario_name = yaml_to_name(scenario_file)

	simulate(platform_path, debugger_path, "{}/{}".format(testcase_name, scenario_name), timeout, nogui, wave)

def debug(debugger_path, scenario_folder):
	if not exists(scenario_folder):
		raise Exception("Scenario folder {} not found.".format(scenario_folder))

	debugger = Popen(["java", "-jar", "{}/Memphis_Debugger.jar".format(debugger_path), "{}/debug/platform.cfg".format(scenario_folder)])

	try:
		debugger.wait()
	except KeyboardInterrupt:
		pass
