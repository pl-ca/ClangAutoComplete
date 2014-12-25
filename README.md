#ClangAutoComplete
=================

Sublime Text 3 plugin that offers auto-completion of C/C++ structure members or class attributes and methods.


##Installation

1. Install "clang".
2. Clone this repository and put it in your Sublime's packages directory.
3. Edit the settings to your needs.
4. Make sure Sublime's own auto-complete settings are properly configured, I've had trouble with mine.

##Bonus Instructions
1. This plugin is only for Sublime Text 3.
2. If you are not getting completions open the debug console of sublime (ctrl + `) and see what the clang command is. Run the command in terminal looking for errors, most likely clang does not have the path to headers. Add those paths to include_dirs.
3. Sublime autocomplete settings must have:
	"auto_complete": true,
	"auto_complete_selector": "source - comment",
	"auto_complete_triggers":
	[
		{
			"characters": "."
		},
		{
			"characters": ">"
		},
		{
			"characters": ":"
		}
	],

##Settings

 - include_dirs: List of directories where relevant header files are located
 - autocomplete_all: Trigger auto-completion on every keypress (will slow down sublime)
 - selectors: List of characters that will trigger auto-completion ( if "autocomplete_all" is set to "false" )
 
