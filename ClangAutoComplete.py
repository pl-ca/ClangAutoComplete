import sublime, sublime_plugin, os, ntpath, subprocess, codecs, re, sys
import os.path as path
from os.path import dirname, realpath, join

MY_PLUGIN = dirname(realpath(__file__))
sys.path.append(join(MY_PLUGIN, "deps"))

import clang.cindex as cindex


file_ext_re = re.compile("[^\.]+\.([^\\n]+)")
# Variable $project_base_path in settings will be replaced by sublime's project path
settings = sublime.load_settings("ClangAutoComplete.sublime-settings")

try:
	cindex.Config.set_library_file(settings.get("libclangso_path"))
except:
	print("error here is fine")


class Util():
	def CursorWord(nview):
		for region in nview.sel():
			if region.begin() == region.end():
				word = nview.word(region)
			else:
				word = region
			if not word.empty():
				keyword = nview.substr(word)
				searchterm = keyword
		return searchterm

	def EnforceFileExtension(view):
		#dont trigger on non-c source file
		file_ext = re.findall(file_ext_re, view.file_name())
		allow = 0;
		file_xts = settings.get("completion_file_extensions")
		for i in range(0, len(file_xts)):
			if file_xts[i] == file_ext[0]:
				allow = 1
		return allow

	def find_typerefsFormat(node, typename, resTable):
		try:
			if node.kind.is_reference:
				if node.displayname.decode('utf-8').find(typename) == 0:
					print(node.spelling)
					opencommand = "{0}:{1}:{2}".format(node.location.file.name.decode('utf-8'), node.location.line, node.location.column)
					print(opencommand)
					#defResults.append([opencommand, c.get_definition().displayname.decode('utf-8')])
		except:
			print("unknown cursor kind, update the python bindings, but no point as they are too slow need to move to unmanaged solution")

		for c in node.get_children():
			Util.find_typerefsFormat(c, typename, resTable)

class GotoDefinitiontwoCommand(sublime_plugin.WindowCommand):
	resMenu = [];
	def on_resmenu_done(self, index):
		if index == -1:
			return
		nview = self.window.active_view()
		nview.window().open_file(self.resMenu[index][0], sublime.ENCODED_POSITION)

	def run(self):
		nview = self.window.active_view()
		if nview.file_name() is None:
			return
		if Util.EnforceFileExtension(nview) == 0:
			return

		searchterm = Util.CursorWord(nview);
		if searchterm == "":
			return

		index = cindex.Index.create()
		tu = index.parse(nview.file_name())
		node = tu.cursor
		defResults = [];
		for c in node.get_children():
			if c.is_definition():
				#print(c.kind)
				#print (c.get_definition().displayname)
				disname = c.displayname.decode('utf-8')
				funccomp = 1
				if len(disname) > len(searchterm) and disname[len(searchterm)] != "(":
					funccomp = 0
				if disname.find(searchterm) == 0 and funccomp:
					opencommand = "{0}:{1}:{2}".format(c.location.file.name.decode('utf-8'), c.location.line, c.location.column)
					defResults.append([opencommand, c.get_definition().displayname.decode('utf-8')])
		
		if len(defResults) == 0:
			return;

		if settings.get("goto_single_popupbox") != "true" and len(defResults) == 1:
			nview.window().open_file(defResults[0][0], sublime.ENCODED_POSITION)
		else:
			items = [];
			for c in defResults:
				items.append(c[1] + "   " + c[0])
			self.resMenu = defResults;
			nview.show_popup_menu(items, self.on_resmenu_done)

class ClangAutoComplete(sublime_plugin.EventListener):

	compl_sugar = re.compile("[#<>\[\]]")
	compl_regex = re.compile("COMPLETION: ([^ ]+) : ([^\\n]+)")
	file_ext = re.compile("[^\.]+\.([^\\n]+)")
	project_name_regex = re.compile("([^\.]+).sublime-project")
	settings_time = 0
	first_load = 0

	def on_post_save_async(self, view):
		self.load_settings(view)

	def on_activated_async(self, view):
		if view.file_name() is not None:
			self.load_settings(view)

	def load_settings(self, view):
		# Only load the settings if they have changed
		settings_modified_time = path.getmtime(sublime.packages_path()+"/ClangAutoComplete/"+"ClangAutoComplete.sublime-settings")
		if (self.settings_time == settings_modified_time):
			return
		
		project_path=""
		if sublime.active_window().project_data() is not None:
			project_path = (sublime.active_window().project_data().get("folders")[0].get("path"))

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

		self.tmp_file_path    = settings.get("tmp_file_path")
		self.default_encoding = settings.get("default_encoding")
		self.selectors        = settings.get("selectors")
		self.include_dirs     = settings.get("include_dirs")
		self.clang_binary     = settings.get("clang_binary")
		self.completion_sugar     = settings.get("completion_sugar")
		self.completion_file_extensions     = settings.get("completion_file_extensions")
		for i in range(0, len(self.include_dirs)):
			self.include_dirs[i] = re.sub("(\$project_base_path)", project_path, self.include_dirs[i])
			self.include_dirs[i] = re.sub("(\$project_name)", project_name, self.include_dirs[i])

		#recurse from root folder looking for src/ folders
		for root, dirnames, filenames in os.walk(project_path):
			for dirname in dirnames:
				if dirname == "src":
					self.include_dirs.append(os.path.join(root, dirname));

		#add current dir
		if view.file_name() is not None:
			self.include_dirs.append(os.path.dirname(view.file_name()));
			
	def on_query_completions(self, view, prefix, locations):
		if self.first_load == 0:
			self.load_settings(view)
			first_load = 1
		#dont trigger on non-c source file
		file_ext = re.findall(self.file_ext, view.file_name())
		allow = 0;
		for i in range(0, len(self.completion_file_extensions)):
			if self.completion_file_extensions[i] == file_ext[0]:
				allow = 1
		if not allow:
			return []
		
		# Find exact Line:Column position of cursor for clang
		pos = view.sel()[0].begin()
		body = view.substr(sublime.Region(0, view.size()))
		cursorchar = body[pos-1:pos]

		# Verify that character under the cursor is one allowed selector
		allowcompletion = 1
		if self.complete_all == False:
			allowcompletion = 0
			for e in self.selectors:
				if e == cursorchar:
					if cursorchar == ":" and body[pos-2:pos-1] != ":":
						return ([], sublime.INHIBIT_WORD_COMPLETIONS)
					allowcompletion = 1

		if allowcompletion == 0:
			return []

		line_pos = body[:pos].count('\n')+1
		char_pos = pos-body.rfind("\n", 0, len(body[:pos]))

		# Create temporary file name that reflects what user is currently typing
		enc = view.encoding()
		if  enc == "Undefined":
			enc = self.default_encoding
		with open(self.tmp_file_path, "w", encoding=enc) as tmp_file:
			tmp_file.write(body)

		# Find file type (.c/.cpp) to set relevant clang flags 
		file_ext = re.findall(self.file_ext, view.file_name())
		cpp_flags = ""
		if len(file_ext) > 0 and file_ext[0] == "cpp":
			cpp_flags = "-x c++"

		# Build clang command
		clang_bin = self.clang_binary
		clang_flags = "-cc1 " + cpp_flags + " -fsyntax-only"
		clang_target = "-code-completion-at " + self.tmp_file_path+":"+str(line_pos)+":"+str(char_pos ) +" "+self.tmp_file_path
		clang_includes=" -I ."
		for dir in self.include_dirs:
			clang_includes += " -I " + dir

		# Execute clang command, exit 0 to suppress error from check_output()
		clang_cmd = clang_bin + " " + clang_flags + " " + clang_target + clang_includes
		output = subprocess.check_output(clang_cmd+";exit 0", shell=True)
		print(clang_cmd)

		# Process clang output, find COMPLETION lines and return them with a little formating
		output_text = ''.join(map(chr,output))
		output_lines = output_text.split('\n')
		result = []
		longest_len = 0
		for line in output_lines:
			tmp_res=re.findall(self.compl_regex, line)
			if len(tmp_res) <= 0:
				continue
			if len(tmp_res[0][0]) > longest_len:
				longest_len = len(tmp_res[0][0])

			#COMPLETION lines format sugar
			compl_line = tmp_res[0][1];
			if self.completion_sugar == "true":
				compl_line_head = tmp_res[0][0];
				if (compl_line_head == "operator="):
					continue;
				if (compl_line_head[0] == "~"):
					continue;
				if (tmp_res[0][1].find("::") != -1):
					continue;

				compl_line = compl_line.replace("]", " ")
				compl_line = re.sub(self.compl_sugar, "", compl_line)

			result.append([compl_line, compl_line_head])

		for tuple in result:
			tuple[0] = tuple[1].ljust(longest_len) + " - " + tuple[0]
		return (result, sublime.INHIBIT_WORD_COMPLETIONS)