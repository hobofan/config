# powerline.output - Output and formatting functions
# (c) 2008 Pianohacker, licensed under the GPLv3


"""Output and formatting functions.

Functions
=========

ordinalize and join are both for string formatting. Both currently only work with English, unfortunately.
"""

def ordinalize(num):
	# FIXME: Port this to PyICU
	# Copied from http://vandahm.org/2006/10/03/cool-python-function/
	"""Transforms a number into its ordinal equivalent.

	>>> ordinalize(1), ordinalize(2), ordinalize(3), ordinalize(4)
	('1st', '2nd', '3rd', '4th')
	>>> ordinalize(11), ordinalize(21), ordinalize(50002)
	('11th', '21st', '50002nd')
	"""
	
	special_suffixes = { '1': 'st', '2': 'nd', '3': 'rd' }
	default_return = 'th'

	digits = str(abs(num)) # To work with negative numbers
	last_digit = digits[-1:]

	if last_digit in special_suffixes.keys():
		# Numbers that end in 11, 12, and 13 just get 'th'
		if len(digits) == 1 or digits[-2] != '1':
			default_return = special_suffixes[last_digit]

	return str(num) + default_return

def join(list_, conjunction = 'or'):
	#FIXME: Port this to PyICU if possible
	"""Joins a list together in a readable form.

	>>> join(['a', 'b', 'c'])
	'a, b or c'
	>>> join(['a', 'b'])
	'a or b'
	>>> join(['a', 'b', 'c'], 'and')
	'a, b and c'
	>>> join(['a'])
	'a'
	>>> join([])
	''
	"""

	if len(list_) == 0:
		return ''
	elif len(list_) == 1:
		return str(list_[0])
	elif len(list_) == 2:
		return (' %s ' % conjunction).join(list_)
	else:
		return ', '.join(list_[:-1]) + (' %s ' % conjunction) + list_[-1]

if __name__ == '__main__':
	import doctest; doctest.testmod()
