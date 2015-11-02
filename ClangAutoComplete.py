#
# Provides completion suggestions for C/C++ languages
# based on clang output
#

import sublime, sublime_plugin, os, ntpath, subprocess, codecs, re, tempfile
import os.path as path

class ClangAutoComplete(sublime_plugin.EventListener):

	compl_regex = re.compile("COMPLETION: ([^ ]+) : ([^\\n]+)")
	file_ext = re.compile("[^\.]+\.([^\\n]+)")
	syntax_regex = re.compile("\/([^\/]+)\.tmLanguage")
	project_name_regex = re.compile("([^\.]+).sublime-project")
	settings_time = 0

	def load_settings(self):
		# Only load the settings if they have changed
		settings_modified_time = path.getmtime(sublime.packages_path()+"/ClangAutoComplete/"+"ClangAutoComplete.sublime-settings")
		if (self.settings_time == settings_modified_time):
			return

		# Variable $project_base_path in settings will be replaced by sublime's project path
		settings = sublime.load_settings("ClangAutoComplete.sublime-settings")
		
		project_path=""
		if sublime.active_window().project_data() is not None \
			and sublime.active_window().project_data().get("folders") is not None \
			and sublime.active_window().project_data().get("folders")[0].get("path") is not None:
			project_path = (sublime.active_window().project_data().get("folders")[0].get("path"))
			if os.name == "nt":
				project_path = re.sub("(\\\\)", "\\\\\\\\", project_path)
		
		proj_filename = sublime.active_window().project_file_name()
		project_name=""
		if proj_filename is not None:
			res = re.findall(self.project_name_regex,ntpath.basename(sublime.active_window().project_file_name()))
			if len(res) > 0:
				project_name = res[0]

		complete_all = settings.get("autocomplete_all")
		if complete_all == "false":
			self.complete_all = False
		else:
			self.complete_all = True
		self.tmp_file_path = settings.get("tmp_file_path")
		if settings.get("tmp_file_path") is None:
			self.tmp_file_path    = tempfile.gettempdir() + "/auto_complete_tmp"
		self.default_encoding = settings.get("default_encoding")
		self.selectors        = settings.get("selectors")
		self.include_dirs     = settings.get("include_dirs")
		self.clang_binary     = settings.get("clang_binary")
		for i in range(0, len(self.include_dirs)):
			self.include_dirs[i] = re.sub("(\$project_base_path)", project_path, self.include_dirs[i])
			self.include_dirs[i] = re.sub("(\$project_name)", project_name, self.include_dirs[i])
			if os.name == "nt":
				self.include_dirs[i] = re.sub("(/)", "\\\\", self.include_dirs[i])
				if "\"" not in self.include_dirs[i]:
					self.include_dirs[i] = "\"" + self.include_dirs[i] + "\""

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


