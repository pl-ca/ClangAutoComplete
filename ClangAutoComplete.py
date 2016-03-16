#
# Provides completion suggestions for C/C++ languages
# based on clang output
#

import sublime, sublime_plugin, os, ntpath, subprocess, codecs, re, tempfile
import os.path as path

class ClangAutoComplete(sublime_plugin.EventListener):

	compl_regex = re.compile("COMPLETION: ([^ ]+) : ([^\\n]+)")
	file_ext = re.compile("[^\.]+\.([^\\n]+)")
	syntax_regex = re.compile("\/([^\/]+)\.(?:tmLanguage|sublime-syntax)")
	settings_time = 0

	def to_bool(self, str_flag):
		return str_flag == "true"

	def load_settings(self):
		# Only load the settings if they have changed
		settings_modified_time = path.getmtime(
		                                       path.join(sublime.packages_path(),
		                                                 "ClangAutoComplete",
		                                                 "ClangAutoComplete.sublime-settings"))
		if (self.settings_time == settings_modified_time):
			return

		settings = sublime.load_settings("ClangAutoComplete.sublime-settings")

		# initialize these to nothing in case they are not present in the variables
		project_path=""
		project_name=""
		file_parent_folder=""

		# these variables should be populated by sublime text
		variables = sublime.active_window().extract_variables()
		if ('folder' in variables):
			project_path = variables['folder']
		if ('project_base_name' in variables):
			project_name = variables['project_base_name']
		if ('file' in variables):
			file_parent_folder = path.join(path.dirname(variables['file']), "..")

		include_parent_folder = self.to_bool(settings.get("include_file_parent_folder"))
		self.complete_all = self.to_bool(settings.get("autocomplete_all"))
		self.verbose = self.to_bool(settings.get("verbose"))
		self.tmp_file_path = settings.get("tmp_file_path")
		if settings.get("tmp_file_path") is None:
			self.tmp_file_path = path.join(tempfile.gettempdir(), "auto_complete_tmp")
		self.default_encoding = settings.get("default_encoding")
		self.selectors        = settings.get("selectors")
		self.include_dirs     = settings.get("include_dirs")
		self.clang_binary     = settings.get("clang_binary")

		for i, include_dir in enumerate(self.include_dirs):
			include_dir = re.sub("(\$project_base_path)", project_path, include_dir)
			include_dir = re.sub("(\$project_name)", project_name, include_dir)
			include_dir = os.path.abspath(include_dir)
			self.include_dirs[i] = include_dir

		if (self.verbose):
			print("project_base_name = {}".format(project_name))
			print("folder = {}".format(project_path))
			print("file_parent_folder = {}".format(file_parent_folder))

		if (include_parent_folder):
			self.include_dirs.append(file_parent_folder)


	def on_query_completions(self, view, prefix, locations):
		self.load_settings()
		# Find exact Line:Column position of cursor for clang
		pos = view.sel()[0].begin()
		body = view.substr(sublime.Region(0, view.size()))

		# Verify that character under the cursor is one allowed selector
		if self.complete_all == False and any(e in body[pos-len(e):pos] for e in self.selectors) == False:
			return []
		line_pos = body[:pos].count('\n')+1
		char_pos = pos-body.rfind("\n", 0, len(body[:pos]))


		# Create temporary file name that reflects what user is currently typing
		enc = view.encoding()
		if  enc == "Undefined":
			enc = self.default_encoding
		with open(self.tmp_file_path, "w", encoding=enc) as tmp_file:
			tmp_file.write(body)

		# Find language used (C vs C++) based first on
		# sublime's syntax settings (supporting "C" and "C++").
		# If we do not recognize the current settings, try to
		# decide based on file extension.
		syntax_flags = None
		c_flags = ""
		cpp_flags = "-x c++"
		if view.settings().get('syntax') is not None:
			syntax = re.findall(self.syntax_regex, view.settings().get('syntax'))
			if len(syntax) > 0:
				if syntax[0] == "C++":
					syntax_flags = cpp_flags
				elif syntax[0] == "C":
					syntax_flags = c_flags
		if syntax_flags is None and \
			view.file_name() is not None:
			file_ext = re.findall(self.file_ext, view.file_name())
			if len(file_ext) > 0 and file_ext[0] == "cpp":
				syntax_flags = cpp_flags
		if syntax_flags is None:
			syntax_flags = c_flags

		# Build clang command
		clang_bin = self.clang_binary
		clang_flags = "-cc1 " + syntax_flags + " -fsyntax-only"
		clang_target = "-code-completion-at " + self.tmp_file_path+":"+str(line_pos)+":"+str(char_pos ) +" "+self.tmp_file_path
		clang_includes=" -I ."
		for dir in self.include_dirs:
			clang_includes += " -I " + dir

		# Execute clang command, exit 0 to suppress error from check_output()
		clang_cmd = clang_bin + " " + clang_flags + " " + clang_target + clang_includes
		if (self.verbose):
			print("clang command: {}".format(clang_cmd))
		try:
			output = subprocess.check_output(clang_cmd, shell=True)
			output_text = ''.join(map(chr,output))
		except subprocess.CalledProcessError as e:
			output_text = e.output.decode("utf-8")
		# Process clang output, find COMPLETION lines and return them with a little formating
		output_lines = output_text.splitlines()
		result = []
		longest_len = 0
		for line in output_lines:
			tmp_res=re.findall(self.compl_regex, line)
			if len(tmp_res) <= 0:
				continue
			if len(tmp_res[0][0]) > longest_len:
				longest_len = len(tmp_res[0][0])
			result.append([tmp_res[0][1], tmp_res[0][0]])

		for tuple in result:
			tuple[0] = tuple[1].ljust(longest_len) + " - " + tuple[0]
		return (result, sublime.INHIBIT_WORD_COMPLETIONS)


