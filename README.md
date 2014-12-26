#ClangAutoComplete
=================

Sublime Text 3 plugin that offers auto-completion of C/C++ structure members or class attributes and methods.
Now also offers buggy Go to Definition.


##Installation

1. Install "clang".
2. Clone this repository and put it in your Sublime's packages directory.
3. Edit the settings to your needs.
4. Make sure Sublime's own auto-complete settings are properly configured, I've had trouble with mine.
5. Go To Definition support is quite experimental and sometimes jumps to the wrong thing and also does not detect current scope. Ex:   char * buf;  buf = malloc(50); Go To Definition of buf will not jump.  The problem behind this is working with libclang especially through python bindings is quite confusing and slow.  Scanning all function for all children nodes takes a while.  
6. To get Go To Definition set a hotkey { "keys": ["f12"], "command": "goto_definitiontwo" }, to goto_definitiontwo.  This is to prevent overriding the origin goto_definition.
7. To get Go To Definition you must set "libclangso_path" to your libclang.so file, commonly on debian "/usr/lib/llvm-3.5/lib/libclang.so".  

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
		}
	],

##Known bugs
1. Go to definition / auto-complete might not read all the required paths correctly. If anyone knows how to fix that, that would be great.  For example making GoToDef on printf.
2. Anything inside a {} scope wont be parsed, its too slow atm.

##Future of this plugin
1. To get any reasonably effective, quick and accurate autocomplete for C++ large integration with libclang needs to be done and preferably not directly through python bindings. 
2. Integrating http://kfunk.org/2014/04/28/gsoc-2014-improving-the-clang-integration-in-kdevelop/ (Clang for KDevelop) is a very reasonable option.

##Settings

 - include_dirs: List of directories where relevant header files are located
 - autocomplete_all: Trigger auto-completion on every keypress (will slow down sublime)
 - selectors: List of characters that will trigger auto-completion ( if "autocomplete_all" is set to "false" )
 
