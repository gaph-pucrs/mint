import sys
from argparse import ArgumentParser
from os import getenv
from . import testcase_build, applications_build, scenario_build, simulate, memphis_all, debug

def main():
	parser = ArgumentParser(description="Memphis-V platform generator and simulator.")
	subparsers = parser.add_subparsers(dest="option")

	tc_parser = subparsers.add_parser("testcase", help="Generate a testcase")
	tc_parser.add_argument("TESTCASE_FILE", help="Path to testcase description (yaml)")
	tc_parser.add_argument("--skipdebug", action="store_true", help="Disables debugger configuration")

	app_parser = subparsers.add_parser("applications", help="Generate applications")
	app_parser.add_argument("TESTCASE_FOLDER", help="Path to generated testcase folder")
	app_parser.add_argument("APPLICATIONS_FILE", help="Path to applications description (yaml)")
	app_parser.add_argument("--repodebug", action="store_true", help="Generates repository/appstart debug files")

	sc_parser = subparsers.add_parser("scenario", help="Generate a scenario")
	sc_parser.add_argument("TESTCASE_FOLDER", help="Path to generated testcase folder")
	sc_parser.add_argument("SCENARIO_FILE", help="Path to scenario description (yaml)")
	sc_parser.add_argument("--skipdebug", action="store_true", help="Disables debugger configuration")
	sc_parser.add_argument("--repodebug", action="store_true", help="Generates repository/appstart debug files")

	sim_parser = subparsers.add_parser("simulate", help="Simulate a scenario")
	sim_parser.add_argument("SCENARIO_FOLDER", help="Path to generated scenario folder")
	sim_parser.add_argument("--timeout", help="Simulation timeout in milliseconds")
	sim_parser.add_argument("--nogui", action="store_true", help="Disables graphical debugger")
	sim_parser.add_argument("--wave", action="store_true", help="Enables wave visualization.")

	all_parser = subparsers.add_parser("all", help="Simulate a scenario")
	all_parser.add_argument("TESTCASE_FILE", help="Path to testcase description (yaml)")
	all_parser.add_argument("APPLICATIONS_FILE", help="Path to applications description (yaml)")
	all_parser.add_argument("SCENARIO_FILE", help="Path to scenario description (yaml)")
	all_parser.add_argument("--timeout", help="Simulation timeout in milliseconds")
	all_parser.add_argument("--nogui", action="store_true", help="Disables graphical debugger.")
	all_parser.add_argument("--wave", action="store_true", help="Enables wave visualization.")
	all_parser.add_argument("--skipdebug", action="store_true", help="Disables debugger configuration")
	all_parser.add_argument("--repodebug", action="store_true", help="Generates repository/appstart debug files")

	dbg_parser = subparsers.add_parser("debug", help="Runs the debugger on a previous simulation")
	dbg_parser.add_argument("SCENARIO_FOLDER", help="Path to simulated scenario folder")

	args = parser.parse_args()

	option = args.option

	nogui = False
	wave  = False

	ENV_DEBUGGER_PATH = "MEMPHIS_DEBUGGER_PATH"
	debugger_path = None
	if option == "simulate" or option == "all":
		try:
			nogui = args.nogui
		except:
			pass

		try:
			wave = args.wave
		except:
			pass

	if option == "simulate" or option == "all" or option == "debug":
		if not nogui:
			debugger_path = getenv(ENV_DEBUGGER_PATH)
			if debugger_path is None:
				sys.exit("ERROR: "+ENV_DEBUGGER_PATH+" not defined.")
    
	timeout = 0
	if option == "simulate" or option == "all":
		try:
			timeout = int(args.timeout)
		except:
			pass

	skipdebug = False
	if option == "testcase" or option == "scenario" or option == "all":
		try:
			skipdebug = args.skipdebug
		except:
			pass
	nogui = nogui or skipdebug

	repodebug = False
	if option == "applications" or option == "scenario" or option == "all":
		try:
			repodebug = args.repodebug
		except:
			pass

	scenario_folder = ""
	if option == "simulate" or option == "debug":
		scenario_folder = args.SCENARIO_FOLDER

	if option == "debug":
		try:
			debug(debugger_path, scenario_folder)
			sys.exit(0)
		except Exception as ex:
			sys.exit("\nERROR: {}".format(ex))

	ENV_PLATFORM_PATH = "MEMPHIS_PATH"
	platform_path = getenv(ENV_PLATFORM_PATH)
	if platform_path is None:
		sys.exit("ERROR: "+ENV_PLATFORM_PATH+" not defined.")
	
	testcase_file = ""
	if option == "testcase" or option == "all":
		testcase_file = args.TESTCASE_FILE
	
	testcase_folder = ""
	if option == "applications" or option == "scenario":
		testcase_folder = args.TESTCASE_FOLDER

	applications_file = ""
	if option == "applications" or option == "all":
		applications_file = args.APPLICATIONS_FILE

	scenario_file = ""
	if option == "scenario" or option == "all":
		scenario_file = args.SCENARIO_FILE
 
	try:
		if option == "testcase":
			testcase_build(platform_path, testcase_file, skipdebug)
		elif option == "applications":
			applications_build(platform_path, testcase_folder, applications_file, repodebug)
		elif option == "scenario":
			scenario_build(platform_path, testcase_folder, scenario_file, skipdebug, repodebug)
		elif option == "simulate":
			simulate(platform_path, debugger_path, scenario_folder, timeout, nogui, wave)
		else:
			# all
			memphis_all(platform_path, debugger_path, testcase_file, scenario_file, applications_file, timeout, nogui, wave, skipdebug, repodebug)
	except Exception as ex:
		sys.exit("\nERROR: {}".format(ex))
