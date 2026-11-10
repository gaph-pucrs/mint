#!/usr/bin/env python3
from subprocess import check_output

def elf_sizes(path):
	"""Returns the size in bytes of each region of the page, from the linker symbols.

	The linker scripts define them so that, together, they cover the page with no gaps:
	text + rodata + data ends at __bss_start, and text + rodata + data + bss is _end,
	where the heap starts. The scripts ASSERT that nothing sits between the sections.

	Do not use `size` instead: it reports raw section sizes, missing any alignment
	padding the linker inserts between .data and .bss. __bss_size is _end - __bss_start,
	so it includes that padding, as the kernel needs for the heap start.
	"""
	syms = {}
	for line in check_output(["riscv64-elf-nm", path]).decode().splitlines():
		fields = line.split()
		if len(fields) == 3:
			syms[fields[2]] = int(fields[0], 16)

	return {
		"text":   syms["__text_size"],
		"rodata": syms["__rodata_size"],
		"data":   syms["__data_size"],
		"bss":    syms["__bss_size"]
	}
